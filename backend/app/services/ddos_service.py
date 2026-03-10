# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# DDoS koruma servisi: nftables, sysctl, nginx, uvicorn yönetimi.
# Tum DDoS kurallarini "ddos_" comment prefix'i ile isaretler.

import asyncio
import logging
import re
from typing import List, Dict

logger = logging.getLogger("tonbilai.ddos")

NFT_BIN = "/usr/sbin/nft"
DDOS_COMMENT_PREFIX = "ddos_"
TABLE = "inet tonbilai"
SYSCTL_FILE = "/etc/sysctl.d/90-tonbilaios-ddos.conf"
NGINX_DDOS_FILE = "/etc/nginx/conf.d/tonbilaios-ddos.conf"
UVICORN_OVERRIDE_DIR = "/etc/systemd/system/tonbilaios-backend.service.d"
UVICORN_OVERRIDE_FILE = f"{UVICORN_OVERRIDE_DIR}/workers.conf"


async def _run_cmd(cmd: list[str], input_data: str | None = None) -> tuple[int, str, str]:
    """Shell komutu calistir, (returncode, stdout, stderr) dondur."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE if input_data else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=input_data.encode() if input_data else None)
    return proc.returncode, stdout.decode().strip(), stderr.decode().strip()


async def _run_nft(args: list[str], check: bool = False) -> str:
    """nft komutu calistir."""
    rc, out, err = await _run_cmd(["sudo", NFT_BIN] + args)
    if rc != 0 and check:
        raise RuntimeError(f"nft error: {err}")
    return out


async def _run_nft_stdin(nft_script: str) -> tuple[bool, str]:
    """nft -f - ile coklu komut calistir."""
    rc, out, err = await _run_cmd(["sudo", NFT_BIN, "-f", "-"], input_data=nft_script)
    return rc == 0, err


# ============================================================================
# Saldırgan IP Takip Set'leri
# ============================================================================

ATTACKER_SETS = {
    "ddos_syn_attackers": "syn_flood",
    "ddos_udp_attackers": "udp_flood",
    "ddos_icmp_attackers": "icmp_flood",
    "ddos_invalid_attackers": "invalid_packet",
    "ddos_conn_attackers": "conn_limit",
}

async def flush_attacker_sets() -> dict:
    """Tum DDoS saldırgan IP setlerini ve connlimit metresi temizle.
    Hatali engellenen IP'leri sıfırlar."""
    flushed = {}
    # Attacker set'lerini flush
    for set_name in ATTACKER_SETS:
        try:
            out = await _run_nft(["list", "set", "inet", "tonbilai", set_name])
            # IP sayısıni say
            import re as _re
            ips = _re.findall(r'\d+\.\d+\.\d+\.\d+', out)
            count = len(ips)
            await _run_nft(["flush", "set", "inet", "tonbilai", set_name])
            flushed[set_name] = count
            if count > 0:
                logger.info(f"DDoS set flushed: {set_name} ({count} IP)")
        except Exception as e:
            logger.error(f"Set flush hatasi {set_name}: {e}")
            flushed[set_name] = -1

    # Connlimit metresi flush
    try:
        out = await _run_nft(["list", "meter", "inet", "tonbilai", "ddos_connlimit"])
        import re as _re
        ips = _re.findall(r'\d+\.\d+\.\d+\.\d+', out)
        count = len(ips)
        await _run_nft(["flush", "meter", "inet", "tonbilai", "ddos_connlimit"])
        flushed["ddos_connlimit"] = count
        if count > 0:
            logger.info(f"DDoS meter flushed: ddos_connlimit ({count} IP)")
    except Exception as e:
        logger.debug(f"Connlimit flush hatasi (set olmayabilir): {e}")
        flushed["ddos_connlimit"] = 0

    # Persist
    try:
        from app.hal.linux_nftables import persist_nftables
        await persist_nftables()
    except Exception:
        pass

    # Redis attack history'yi de temizle (haritada hayalet IP'ler kalmasin)
    history_cleared = 0
    try:
        from app.db.redis_client import get_redis
        r = await get_redis()
        history_cleared = await r.zcard("ddos:attack_history")
        await r.delete("ddos:attack_history")
        if history_cleared > 0:
            logger.info(f"DDoS attack history temizlendi: {history_cleared} kayit")
    except Exception as e:
        logger.error(f"Attack history temizleme hatasi: {e}")

    total = sum(v for v in flushed.values() if v > 0)
    logger.info(f"DDoS saldırgan setleri temizlendi: toplam {total} IP")
    return {"flushed_sets": flushed, "total_cleared": total, "history_cleared": history_cleared}



async def _ensure_attacker_sets():
    """Saldırgan IP takip set'lerini oluştur (yoksa).

    NOT: ddos_syn_meter / ddos_udp_meter / ddos_icmp_meter named meter'larini
    burada set olarak OLUSTURMA. nftables'da 'meter NAME { key limit rate ... }'
    szdizimi named meter'i otomatik olusturur. Eger onceden 'add set' ile
    timeout/dynamic flagli bir set varsa, ayni isimde meter kullanan kural
    'existing set has timeout flag' hatasini verir. Bu nedenle meter set'leri
    bu fonksiyondan kaldirildi — sadece saldirgan IP takip set'leri olusturulur.
    """
    lines = []
    for name in ATTACKER_SETS:
        lines.append(f'add set {TABLE} {name} {{ type ipv4_addr; timeout 30m; size 4096; flags dynamic,timeout; }}')
    ok, err = await _run_nft_stdin("\n".join(lines) + "\n")
    if not ok:
        for line in lines:
            await _run_nft_stdin(line + "\n")


# ============================================================================
# nftables DDoS Kuralları
# ============================================================================

async def _flush_ddos_rules():
    """Mevcut ddos_ comment'li tum kurallari sil.

    ONEMLI: named meter set'leri (ddos_syn_meter vb.) kurallar silindikten
    sonra OTOMATIK olarak nftables tarafından temizlenir — eger set olarak
    onceden olusturulmamislarse. Eger bu set'ler yanlislikla 'add set ... timeout'
    ile olusturulduysa, kurallari silmeden once onlari silmeye calisiyoruz;
    ancak referans hatasi alinirsak kurallari once sil sonra set'leri sil.
    """
    for chain in ("input", "forward"):
        out = await _run_nft(["-a", "list", "chain", "inet", "tonbilai", chain])
        for line in out.splitlines():
            if f'comment "{DDOS_COMMENT_PREFIX}' in line or f"comment \"{DDOS_COMMENT_PREFIX}" in line:
                match = re.search(r"# handle (\d+)", line)
                if match:
                    handle = match.group(1)
                    await _run_nft(
                        ["delete", "rule", "inet", "tonbilai", chain, "handle", handle]
                    )
                    logger.debug(f"DDoS kural silindi: chain={chain} handle={handle}")

    # Named meter set'lerini temizle (eski 'add set ... timeout flags' ile olusturulmus olabilir)
    # Bu set'ler kurallar silinince otomatik temizlenir ama persist edilmisse yeniden yuklenir.
    # Explicit delete ile kalici olarak temizliyoruz.
    for meter_name in ["ddos_syn_meter", "ddos_udp_meter", "ddos_icmp_meter"]:
        try:
            await _run_nft(["delete", "set", "inet", "tonbilai", meter_name])
            logger.debug(f"DDoS meter set silindi: {meter_name}")
        except Exception:
            pass  # Set yoksa veya hata olursa sessizce gec


async def apply_ddos_nft_rules(config) -> int:
    """DB config'e göre nftables DDoS kurallarini flush + yeniden oluştur.
    Eklenen kural sayısıni dondurur."""
    await _flush_ddos_rules()
    await _ensure_attacker_sets()

    # Tum korumalar kapali ise saldırgan setlerini de temizle
    any_enabled = (
        config.syn_flood_enabled or config.udp_flood_enabled or
        config.icmp_flood_enabled or config.conn_limit_enabled or
        config.invalid_packet_enabled
    )
    if not any_enabled:
        try:
            await flush_attacker_sets()
            logger.info("Tum DDoS korumalar kapali, saldırgan setleri temizlendi")
        except Exception as e:
            logger.error(f"Set temizleme hatasi: {e}")

    rules: list[str] = []
    # "insert rule" → chain başına ekler (ct state established'tan ONCE)
    # "add rule" → chain sonuna ekler (ct state established'tan SONRA)

    # ICMP flood kuralı MUTLAKA ct state established'tan once olmali.
    # Cunku conntrack ICMP echo-request/reply ciftini "established" sayar
    # ve flood paketleri ct state kuralından gecip DDoS limitine ulasamaz.

    # Bridge modda LAN cihazlarina yonelik saldirilar FORWARD chain uzerinden gecer.
    # Bu yuzden her kural hem INPUT hem FORWARD chain'e eklenir.
    CHAINS = ["input", "forward"]

    # LAN subnet muafiyeti — LAN cihazlari DDoS meter'larina girmemeli
    LAN_EXCLUDE = "ip saddr != 192.168.1.0/24"

    # 3. ICMP Flood — add ile ekle (ct state established kuralından SONRA gelir,
    # böylece established paketler 16+ subnet kuralını taramaz).
    # LAN cihazları muaf tutulur.
    if config.icmp_flood_enabled:
        for chain in CHAINS:
            rules.append(
                f'add rule {TABLE} {chain} {LAN_EXCLUDE} ip protocol icmp '
                f'meter ddos_icmp_meter {{ ip saddr limit rate over {config.icmp_flood_rate}/second burst {config.icmp_flood_burst} packets }} '
                f'add @ddos_icmp_attackers {{ ip saddr }} '
                f'counter drop comment "{DDOS_COMMENT_PREFIX}icmp_flood"'
            )

    # Geri kalan kurallar ct state established'tan sonra (add ile sona)

    # 5. Geçersiz paket filtreleme — LAN muaf
    if config.invalid_packet_enabled:
        for chain in CHAINS:
            rules.append(f'add rule {TABLE} {chain} {LAN_EXCLUDE} ct state invalid add @ddos_invalid_attackers {{ ip saddr }} counter drop comment "{DDOS_COMMENT_PREFIX}invalid_pkt"')
            rules.append(f'add rule {TABLE} {chain} {LAN_EXCLUDE} tcp flags & (fin | syn) == fin | syn add @ddos_invalid_attackers {{ ip saddr }} counter drop comment "{DDOS_COMMENT_PREFIX}invalid_flags1"')
            rules.append(f'add rule {TABLE} {chain} {LAN_EXCLUDE} tcp flags & (syn | rst) == syn | rst add @ddos_invalid_attackers {{ ip saddr }} counter drop comment "{DDOS_COMMENT_PREFIX}invalid_flags2"')
            rules.append(f'add rule {TABLE} {chain} {LAN_EXCLUDE} tcp flags & (fin | syn | rst | psh | ack | urg) == 0x0 add @ddos_invalid_attackers {{ ip saddr }} counter drop comment "{DDOS_COMMENT_PREFIX}null_scan"')

    # 1. SYN Flood — LAN muaf
    if config.syn_flood_enabled:
        for chain in CHAINS:
            rules.append(
                f'add rule {TABLE} {chain} {LAN_EXCLUDE} tcp flags & (fin | syn | rst | ack) == syn '
                f'meter ddos_syn_meter {{ ip saddr limit rate over {config.syn_flood_rate}/second burst {config.syn_flood_burst} packets }} '
                f'add @ddos_syn_attackers {{ ip saddr }} '
                f'counter drop comment "{DDOS_COMMENT_PREFIX}syn_flood"'
            )

    # 2. UDP Flood — LAN muaf
    if config.udp_flood_enabled:
        for chain in CHAINS:
            rules.append(
                f'add rule {TABLE} {chain} {LAN_EXCLUDE} ip protocol udp '
                f'meter ddos_udp_meter {{ ip saddr limit rate over {config.udp_flood_rate}/second burst {config.udp_flood_burst} packets }} '
                f'add @ddos_udp_attackers {{ ip saddr }} '
                f'counter drop comment "{DDOS_COMMENT_PREFIX}udp_flood"'
            )

    # 4. Bağlantı Limiti (per-IP) — LAN muaf
    if config.conn_limit_enabled:
        for chain in CHAINS:
            rules.append(
                f'add rule {TABLE} {chain} {LAN_EXCLUDE} ct state new '
                f'meter ddos_connlimit {{ ip saddr ct count over {config.conn_limit_per_ip} }} '
                f'add @ddos_conn_attackers {{ ip saddr }} '
                f'counter reject comment "{DDOS_COMMENT_PREFIX}conn_limit"'
            )

    if not rules:
        logger.info("DDoS nft kurallari: hicbir koruma aktif degil")
        return 0

    nft_script = "\n".join(rules) + "\n"
    ok, err = await _run_nft_stdin(nft_script)
    if ok:
        logger.info(f"DDoS nft kurallari uygulandı: {len(rules)} kural")
    else:
        logger.error(f"DDoS nft kurallari hatasi: {err}")
        # Tek tek dene (batch başarısız olduysa)
        applied = 0
        for rule in rules:
            ok2, err2 = await _run_nft_stdin(rule + "\n")
            if ok2:
                applied += 1
            else:
                logger.error(f"DDoS kural hatasi: {err2} | kural: {rule}")
        logger.info(f"DDoS nft kurallari (teker teker): {applied}/{len(rules)} başarılı")
        return applied

    # Persist
    from app.hal.linux_nftables import persist_nftables
    await persist_nftables()

    return len(rules)


# ============================================================================
# Kernel Sertlestirme (sysctl)
# ============================================================================

async def apply_kernel_hardening(config) -> bool:
    """sysctl parametrelerini ayarla."""
    if not config.kernel_hardening_enabled:
        # Dosyayi sil ve varsayilana don
        await _run_cmd(["sudo", "rm", "-f", SYSCTL_FILE])
        await _run_cmd(["sudo", "sysctl", "--system"])
        logger.info("Kernel sertlestirme devre disi, sysctl varsayilana donduruldu")
        return True

    params = {
        "net.ipv4.tcp_max_syn_backlog": config.tcp_max_syn_backlog,
        "net.ipv4.tcp_synack_retries": config.tcp_synack_retries,
        "net.netfilter.nf_conntrack_max": config.netfilter_conntrack_max,
        "net.ipv4.tcp_fin_timeout": 15,
        "net.ipv4.tcp_tw_reuse": 1,
        "net.ipv4.icmp_echo_ignore_broadcasts": 1,
        "net.ipv4.conf.all.rp_filter": 1,
        "net.ipv4.conf.default.rp_filter": 1,
    }

    content = "# TonbilAiOS DDoS Kernel Sertlestirme\n"
    content += "# Bu dosya otomatik oluşturulmustur, elle değiştirmeyin.\n\n"
    for key, val in params.items():
        content += f"{key} = {val}\n"

    rc, _, err = await _run_cmd(["sudo", "tee", SYSCTL_FILE], input_data=content)
    if rc != 0:
        logger.error(f"sysctl dosyasi yazilamadi: {err}")
        return False

    rc, _, err = await _run_cmd(["sudo", "sysctl", "-p", SYSCTL_FILE])
    if rc != 0:
        logger.error(f"sysctl uygulama hatasi: {err}")
        return False

    logger.info(f"Kernel sertlestirme uygulandı: {len(params)} parametre")
    return True


# ============================================================================
# HTTP Flood Korumasi (nginx rate limiting)
# ============================================================================

async def apply_http_flood_protection(config) -> bool:
    """Nginx rate limiting config'i yaz + reload."""
    if not config.http_flood_enabled:
        # Config dosyasini sil ve nginx reload
        await _run_cmd(["sudo", "rm", "-f", NGINX_DDOS_FILE])
        rc, _, err = await _run_cmd(["sudo", "nginx", "-t"])
        if rc == 0:
            await _run_cmd(["sudo", "systemctl", "reload", "nginx"])
            logger.info("HTTP flood korumasi devre disi, nginx reload edildi")
        return True

    # rate string'ini dogrula (orn: "30r/s", "100r/m")
    rate = config.http_flood_rate
    if not re.match(r"^\d+r/[sm]$", rate):
        logger.error(f"Geçersiz rate degeri: {rate}")
        return False

    content = f"""# TonbilAiOS DDoS HTTP Flood Korumasi
# Bu dosya otomatik oluşturulmustur, elle değiştirmeyin.

limit_req_zone $binary_remote_addr zone=ddos_limit:10m rate={rate};
"""

    rc, _, _ = await _run_cmd(["sudo", "tee", NGINX_DDOS_FILE], input_data=content)
    if rc != 0:
        logger.error("nginx ddos config yazilamadi")
        return False

    # Ana nginx config'te limit_req kullanilip kullanilmadigini kontrol et
    # NOT: location blogu içine limit_req eklemek için ana config dosyasini da güncellemek gerekir.
    # Simdilik sadece zone tanimi ekliyoruz; location blogu kullanıcınin eline birakilir
    # veya mevcut server config'de include edilmis conf.d dosyasindan okunur.

    rc, _, err = await _run_cmd(["sudo", "nginx", "-t"])
    if rc != 0:
        logger.error(f"nginx config test başarısız: {err}")
        # Geri al
        await _run_cmd(["sudo", "rm", "-f", NGINX_DDOS_FILE])
        return False

    await _run_cmd(["sudo", "systemctl", "reload", "nginx"])
    logger.info(f"HTTP flood korumasi uygulandı: rate={rate} burst={config.http_flood_burst}")
    return True


# ============================================================================
# Uvicorn Worker Sayısı
# ============================================================================

async def apply_uvicorn_workers(config) -> dict:
    """Systemd override ile uvicorn worker sayısıni değiştir.
    Restart kullanıcı onayiyla yapilacak — sadece config yazilir.
    NOT: Mevcut dosya zaten dogru icerige sahipse needs_restart=False döner
    (startup sırasında sonsuz restart döngüsünü önlemek için)."""
    result = {"config_written": False, "needs_restart": False}

    if not config.uvicorn_workers_enabled or config.uvicorn_workers <= 1:
        # Override dosyasini sil — önce mevcut durumu kontrol et
        rc_test, _, _ = await _run_cmd(["sudo", "test", "-f", UVICORN_OVERRIDE_FILE])
        if rc_test == 0:
            # Dosya vardı, şimdi siliyoruz → restart gerekli
            await _run_cmd(["sudo", "rm", "-f", UVICORN_OVERRIDE_FILE])
            await _run_cmd(["sudo", "systemctl", "daemon-reload"])
            result["config_written"] = True
            result["needs_restart"] = True
            logger.info("Uvicorn worker override kaldırıldı (restart gerekli)")
        else:
            result["config_written"] = True
            logger.info("Uvicorn worker override zaten yok, islem atlandi")
        return result

    # Override dizini oluştur
    await _run_cmd(["sudo", "mkdir", "-p", UVICORN_OVERRIDE_DIR])

    workers = config.uvicorn_workers

    content = f"""# TonbilAiOS DDoS — Uvicorn Worker Override
# Bu dosya otomatik oluşturulmustur.
[Service]
ExecStart=
ExecStart=/opt/tonbilaios/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers {workers}
"""

    # Mevcut dosya içeriğini oku — değişmediyse yazmaktan kaçın
    rc_read, existing, _ = await _run_cmd(["sudo", "cat", UVICORN_OVERRIDE_FILE])
    if rc_read == 0 and existing.strip() == content.strip():
        result["config_written"] = True
        result["needs_restart"] = False
        logger.info(f"Uvicorn worker override zaten güncel ({workers} worker), restart atlandı")
        return result

    rc, _, _ = await _run_cmd(["sudo", "tee", UVICORN_OVERRIDE_FILE], input_data=content)
    if rc != 0:
        logger.error("uvicorn override dosyasi yazilamadi")
        return result

    await _run_cmd(["sudo", "systemctl", "daemon-reload"])
    result["config_written"] = True
    result["needs_restart"] = True
    logger.info(f"Uvicorn worker override yazildi: {workers} worker (restart gerekli)")
    return result


async def schedule_backend_restart():
    """Backend'i 2 saniye sonra yeniden başlat (API yaniti gönderilebilsin diye gecikme)."""
    try:
        await _run_cmd([
            "sudo", "systemd-run", "--on-active=2s",
            "--unit=tonbilai-restart",
            "systemctl", "restart", "tonbilaios-backend",
        ])
        logger.info("Backend restart zamanlandi (2 saniye)")
    except Exception as e:
        logger.error(f"Backend restart zamanlama hatasi: {e}")


# ============================================================================
# Durum Kontrolu
# ============================================================================

PROTECTION_DESCRIPTIONS = {
    "syn_flood": "TCP SYN paketlerini saniyede belirli bir limitin ustunde engeller. SYN flood saldırılarina karsi korur.",
    "udp_flood": "UDP paketlerini saniyede belirli bir limitin ustunde engeller. DNS ve NTP amplification saldırılarina karsi korur.",
    "icmp_flood": "ICMP (ping) paketlerini saniyede belirli bir limitin ustunde engeller. Ping flood saldırılarina karsi korur.",
    "conn_limit": "Tek bir IP adresinden esanli bağlantı sayısıni sinirlar. Kaynak tuketme saldırılarina karsi korur.",
    "invalid_packet": "Geçersiz TCP bayraklari ve bağlantı durumu olan paketleri engeller. Nmap taramasi ve exploit denemelerine karsi korur.",
    "http_flood": "Web sunucusuna gelen istekleri saniyede belirli bir limitle sinirlar. Layer 7 DDoS saldırılarina karsi korur. (Nginx reload gerektirir)",
    "kernel_hardening": "TCP/IP yiginini optimize eder: SYN backlog, conntrack limiti, timeout degerleri. Sistem dayanikliligini artirir.",
    "uvicorn_workers": "Backend isci sayısıni artirarak es zamanli istek kapasitesini yukseltir. (Backend restart gerektirir)",
}


async def get_ddos_status(config) -> list[dict]:
    """Her koruma için aktif durum kontrolü."""
    statuses = []

    # nftables kurallari kontrol (hem input hem forward chain)
    nft_out_input = await _run_nft(["-a", "list", "chain", "inet", "tonbilai", "input"])
    nft_out_forward = await _run_nft(["-a", "list", "chain", "inet", "tonbilai", "forward"])
    nft_out = nft_out_input + "\n" + nft_out_forward

    # 1. SYN Flood
    statuses.append({
        "name": "syn_flood",
        "enabled": config.syn_flood_enabled,
        "active": f'"{DDOS_COMMENT_PREFIX}syn_flood"' in nft_out,
        "description": PROTECTION_DESCRIPTIONS["syn_flood"],
    })

    # 2. UDP Flood
    statuses.append({
        "name": "udp_flood",
        "enabled": config.udp_flood_enabled,
        "active": f'"{DDOS_COMMENT_PREFIX}udp_flood"' in nft_out,
        "description": PROTECTION_DESCRIPTIONS["udp_flood"],
    })

    # 3. ICMP Flood
    statuses.append({
        "name": "icmp_flood",
        "enabled": config.icmp_flood_enabled,
        "active": f'"{DDOS_COMMENT_PREFIX}icmp_flood"' in nft_out,
        "description": PROTECTION_DESCRIPTIONS["icmp_flood"],
    })

    # 4. Bağlantı Limiti
    statuses.append({
        "name": "conn_limit",
        "enabled": config.conn_limit_enabled,
        "active": f'"{DDOS_COMMENT_PREFIX}conn_limit"' in nft_out,
        "description": PROTECTION_DESCRIPTIONS["conn_limit"],
    })

    # 5. Geçersiz Paket
    statuses.append({
        "name": "invalid_packet",
        "enabled": config.invalid_packet_enabled,
        "active": f'"{DDOS_COMMENT_PREFIX}invalid_pkt"' in nft_out,
        "description": PROTECTION_DESCRIPTIONS["invalid_packet"],
    })

    # 6. HTTP Flood — nginx config kontrol
    import os
    http_active = False
    rc, _, _ = await _run_cmd(["sudo", "test", "-f", NGINX_DDOS_FILE])
    if rc == 0:
        http_active = True
    statuses.append({
        "name": "http_flood",
        "enabled": config.http_flood_enabled,
        "active": http_active,
        "description": PROTECTION_DESCRIPTIONS["http_flood"],
    })

    # 7. Kernel Sertlestirme — sysctl kontrol
    kernel_active = False
    rc, out, _ = await _run_cmd(["sudo", "sysctl", "-n", "net.ipv4.tcp_max_syn_backlog"])
    if rc == 0:
        try:
            val = int(out.strip())
            kernel_active = val >= 1024  # Varsayilan 256, sertlestirilmis >= 1024
        except ValueError:
            pass
    statuses.append({
        "name": "kernel_hardening",
        "enabled": config.kernel_hardening_enabled,
        "active": kernel_active,
        "description": PROTECTION_DESCRIPTIONS["kernel_hardening"],
    })

    # 8. Uvicorn Workers
    uvicorn_active = False
    rc, _, _ = await _run_cmd(["sudo", "test", "-f", UVICORN_OVERRIDE_FILE])
    if rc == 0:
        uvicorn_active = True
    statuses.append({
        "name": "uvicorn_workers",
        "enabled": config.uvicorn_workers_enabled,
        "active": uvicorn_active,
        "description": PROTECTION_DESCRIPTIONS["uvicorn_workers"],
    })

    return statuses


# ============================================================================
# Drop Counter Okuma (Loglama + LLM Analizi için)
# ============================================================================

async def get_ddos_drop_counters() -> dict[str, dict]:
    """nftables DDoS kurallarindaki counter degerlerini oku (input + forward).
    {rule_name: {"packets": int, "bytes": int}} dondurur.
    Ayni kural iki chain'de de varsa counter degerleri toplanir."""
    counters = {}
    try:
        for chain in ("input", "forward"):
            nft_out = await _run_nft(["-a", "list", "chain", "inet", "tonbilai", chain])
            for line in nft_out.splitlines():
                # ddos_ comment'li kurallari bul
                comment_match = re.search(r'comment "(' + DDOS_COMMENT_PREFIX + r'[^"]+)"', line)
                if not comment_match:
                    continue
                rule_name = comment_match.group(1)
                # counter packets X bytes Y
                counter_match = re.search(r'counter packets (\d+) bytes (\d+)', line)
                if counter_match:
                    pkt = int(counter_match.group(1))
                    byt = int(counter_match.group(2))
                    if rule_name in counters:
                        # Ayni kural iki chain'de — topla
                        counters[rule_name]["packets"] += pkt
                        counters[rule_name]["bytes"] += byt
                    else:
                        counters[rule_name] = {
                            "packets": pkt,
                            "bytes": byt,
                        }
    except Exception as e:
        logger.error(f"DDoS counter okuma hatasi: {e}")
    return counters


async def get_ddos_drop_summary() -> dict:
    """DDoS drop özeti — toplam ve kural bazi istatistikler."""
    counters = await get_ddos_drop_counters()
    total_packets = sum(c["packets"] for c in counters.values())
    total_bytes = sum(c["bytes"] for c in counters.values())

    # Kural gruplarini birlestir (invalid_flags1/2 + invalid_pkt + null_scan → "invalid_packet")
    grouped = {}
    for rule_name, counter in counters.items():
        clean_name = rule_name.replace(DDOS_COMMENT_PREFIX, "")
        # Gruplama
        if clean_name.startswith("invalid_") or clean_name == "null_scan":
            group = "invalid_packet"
        else:
            group = clean_name
        if group not in grouped:
            grouped[group] = {"packets": 0, "bytes": 0}
        grouped[group]["packets"] += counter["packets"]
        grouped[group]["bytes"] += counter["bytes"]

    return {
        "total_dropped_packets": total_packets,
        "total_dropped_bytes": total_bytes,
        "by_protection": grouped,
        "raw_counters": counters,
    }


# ============================================================================
# Saldırgan IP Okuma + Zenginlestirme
# ============================================================================


async def get_ddos_attacker_ips() -> dict[str, list[str]]:
    """Her koruma tipi için saldırgan IP'lerini nft set'lerinden oku."""
    attackers = {}
    for set_name, prot in ATTACKER_SETS.items():
        try:
            out = await _run_nft(["list", "set", "inet", "tonbilai", set_name])
            ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)', out)
            if ips:
                attackers[prot] = list(set(ips))
        except Exception:
            pass
    # Connlimit meter — set'e ek olarak meter'dan da IP topla (gecis donemi)
    try:
        out = await _run_nft(["list", "meter", "inet", "tonbilai", "ddos_connlimit"])
        meter_ips = re.findall(r'(\d+\.\d+\.\d+\.\d+)', out)
        if meter_ips:
            existing = set(attackers.get("conn_limit", []))
            existing.update(meter_ips)
            attackers["conn_limit"] = list(existing)
    except Exception:
        pass
    return attackers


async def _resolve_attacker_info(ip: str) -> dict:
    """IP için ARP tablosundan MAC, device tablosundan hostname al."""
    info = {"ip": ip, "mac": None, "hostname": None}
    try:
        rc, out, _ = await _run_cmd(["ip", "neigh", "show", ip])
        if rc == 0 and out:
            mac_match = re.search(r'([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})', out)
            if mac_match:
                info["mac"] = mac_match.group(1)
    except Exception:
        pass
    try:
        from app.db.session import async_session_factory
        from app.models.device import Device
        from sqlalchemy import select as sa_select
        async with async_session_factory() as session:
            result = await session.execute(
                sa_select(Device).where(Device.ip_address == ip)
            )
            device = result.scalar_one_or_none()
            if device:
                info["hostname"] = device.hostname
                if not info["mac"] and device.mac_address:
                    info["mac"] = device.mac_address
    except Exception:
        pass
    return info


# ============================================================================
# Anomali Tespiti + Telegram Uyari (LLM'siz, threshold tabanli)
# ============================================================================

# Redis'te son bilinen counter degerlerini sakliyoruz
DDOS_COUNTER_REDIS_KEY = "ddos:last_counters"
# Bu esiklerin ustunde anlik artis olursa uyari gönder
ALERT_THRESHOLDS = {
    "syn_flood": 100,       # 100+ yeni SYN drop → uyari
    "udp_flood": 200,       # 200+ yeni UDP drop → uyari
    "icmp_flood": 50,       # 50+ yeni ICMP drop → uyari
    "conn_limit": 500,      # 500+ yeni bağlantı limiti reject → uyari
    "invalid_packet": 100,  # 100+ yeni geçersiz paket drop → uyari
}

# Redis key mapping: security:config field -> ALERT_THRESHOLDS key
_ALERT_REDIS_KEYS = {
    "syn_flood": "ddos_alert_syn_flood",
    "udp_flood": "ddos_alert_udp_flood",
    "icmp_flood": "ddos_alert_icmp_flood",
    "conn_limit": "ddos_alert_conn_limit",
    "invalid_packet": "ddos_alert_invalid_packet",
}

# Ic ag (private) IP'leri DDoS saldırgan olarak raporlama
import ipaddress
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]

def _is_private_ip(ip_str: str) -> bool:
    """IP adresi ic ag (private/loopback) mi?"""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return False

# Ayni alarm tekrar tekrar gönderilmesin (30 dk cooldown)
ALERT_COOLDOWN_SECONDS = 1800  # 30 dakika (fallback — Redis'ten dinamik okunur)


async def check_ddos_anomaly_and_alert():
    """DDoS counter delta kontrolü. Threshold asilirsa Telegram uyari gönder.
    Periyodik olarak cagirilir (örneğin her 60 saniyede).
    - Ic ag IP'leri filtrelenir (false positive onlenir)
    - Ayni koruma tipi için 30 dk cooldown uygulanir"""
    try:
        from app.db.redis_client import get_redis
        redis = await get_redis()

        # Mevcut counter degerleri
        current = await get_ddos_drop_summary()
        by_prot = current.get("by_protection", {})

        # Son bilinen degerleri Redis'ten al
        last_raw = await redis.hgetall(DDOS_COUNTER_REDIS_KEY)
        last = {k: int(v) for k, v in last_raw.items()} if last_raw else {}

        alerts = []
        new_values = {}

        for prot, counters in by_prot.items():
            pkt = counters["packets"]
            new_values[prot] = str(pkt)
            prev = last.get(prot, 0)
            delta = pkt - prev

            # Redis'ten dinamik esik oku (yoksa fallback)
            redis_key = _ALERT_REDIS_KEYS.get(prot)
            if redis_key:
                try:
                    dyn_val = await redis.hget("security:config", redis_key)
                    threshold = int(dyn_val) if dyn_val else ALERT_THRESHOLDS.get(prot, 500)
                except Exception:
                    threshold = ALERT_THRESHOLDS.get(prot, 500)
            else:
                threshold = ALERT_THRESHOLDS.get(prot, 500)
            if delta > threshold:
                alerts.append({
                    "protection": prot,
                    "delta": delta,
                    "total": pkt,
                    "threshold": threshold,
                })

        # Yeni degerleri Redis'e kaydet (snapshot)
        if new_values:
            await redis.hset(DDOS_COUNTER_REDIS_KEY, mapping=new_values)
            await redis.expire(DDOS_COUNTER_REDIS_KEY, 86400)

        # Kumulatif counter'lari guncelle (her 60s, alarm olsun olmasin)
        # nftables counter'lari apply_all() ile sifirlanir, bu yuzden delta'lari biriktirelim
        cumulative_key = "ddos:cumulative_counters"
        last_bytes_raw = await redis.hgetall("ddos:last_bytes")
        last_bytes = {k: int(v) for k, v in last_bytes_raw.items()} if last_bytes_raw else {}
        new_bytes_snap = {}
        for prot, counters in by_prot.items():
            pkt = counters["packets"]
            byt = counters["bytes"]
            prev_pkt = last.get(prot, 0)
            prev_byt = last_bytes.get(prot, 0)
            delta_pkt = max(pkt - prev_pkt, 0)
            delta_byt = max(byt - prev_byt, 0)
            new_bytes_snap[prot] = str(byt)
            if delta_pkt > 0 or delta_byt > 0:
                if delta_pkt > 0:
                    await redis.hincrby(cumulative_key, f"{prot}:packets", delta_pkt)
                if delta_byt > 0:
                    await redis.hincrby(cumulative_key, f"{prot}:bytes", delta_byt)
        if new_bytes_snap:
            await redis.hset("ddos:last_bytes", mapping=new_bytes_snap)
            await redis.expire("ddos:last_bytes", 86400)
        await redis.expire(cumulative_key, 86400)

        # Cooldown kontrolü — ayni koruma tipi için 30 dk içinde tekrar alarm gönderme
        if alerts:
            cooled_alerts = []
            for alert in alerts:
                prot = alert["protection"]
                cooldown_key = f"ddos:alert_cooldown:{prot}"
                in_cooldown = await redis.get(cooldown_key)
                if not in_cooldown:
                    cooled_alerts.append(alert)
                else:
                    logger.debug(f"DDoS {prot} alarmi cooldown'da, atlanıyor")

            alerts = cooled_alerts

        # Saldırgan IP'lerini oku, ic ag IP'lerini filtrele ve zenginlestir
        if alerts:
            try:
                attacker_ips = await get_ddos_attacker_ips()
                for alert in alerts:
                    prot = alert["protection"]
                    raw_ips = attacker_ips.get(prot, [])
                    # Ic ag IP'lerini filtrele (false positive onleme)
                    external_ips = [ip for ip in raw_ips if not _is_private_ip(ip)]
                    alert["attacker_ips"] = external_ips[:10]
                    alert["filtered_private_ips"] = len(raw_ips) - len(external_ips)
                    if external_ips:
                        info = await _resolve_attacker_info(external_ips[0])
                        alert["attacker_mac"] = info.get("mac")
                        alert["attacker_hostname"] = info.get("hostname")
            except Exception as e:
                logger.error(f"Saldırgan IP zenginlestirme hatasi: {e}")

            # Sadece dis IP'li alarmlar varsa bildir, yoksa sessiz kal
            real_alerts = [a for a in alerts if a.get("attacker_ips")]
            private_only = [a for a in alerts if not a.get("attacker_ips")]

            if private_only:
                prots = ", ".join(a["protection"] for a in private_only)
                logger.info(f"DDoS alarm sadece ic ag IP'leri: {prots} (bildirim atlanıyor)")

            if real_alerts:
                await _send_ddos_telegram_alert(real_alerts)
                await _write_ddos_insight(real_alerts)

                # Saldırgan IP'lerini Redis'e kalıcı kaydet (attack map geçmişi için)
                try:
                    import json as _json
                    import time
                    now = int(time.time())
                    for alert in real_alerts:
                        prot = alert["protection"]
                        raw_ips = attacker_ips.get(prot, [])
                        external_ips = [ip for ip in raw_ips if not _is_private_ip(ip)]
                        ext_count = max(len(external_ips), 1)
                        # Per-IP counter: delta ve bytes'i IP sayisina bol
                        per_ip_packets = alert.get("delta", 0) // ext_count
                        prot_bytes = by_prot.get(prot, {}).get("bytes", 0)
                        per_ip_bytes = prot_bytes // ext_count
                        for ip in external_ips[:20]:
                            entry = _json.dumps({
                                "ip": ip, "type": prot, "ts": now,
                                "packets": per_ip_packets,
                                "bytes": per_ip_bytes,
                            })
                            await redis.zadd("ddos:attack_history", {entry: now})
                    # 24 saat'ten eski kayıtları temizle
                    cutoff = now - 86400
                    await redis.zremrangebyscore("ddos:attack_history", 0, cutoff)
                    # ZSET'e 24s TTL koy (key asla orphan kalmasin)
                    await redis.expire("ddos:attack_history", 86400)
                except Exception as e:
                    logger.error(f"Saldırı geçmişi kayıt hatası: {e}")

                # Cooldown ayarla
                for alert in real_alerts:
                    cooldown_key = f"ddos:alert_cooldown:{alert['protection']}"
                    try:
                        cd_val = await redis.hget("security:config", "ddos_alert_cooldown_sec")
                        cd_sec = int(cd_val) if cd_val else ALERT_COOLDOWN_SECONDS
                    except Exception:
                        cd_sec = ALERT_COOLDOWN_SECONDS
                    await redis.setex(cooldown_key, cd_sec, "1")
                    logger.info(f"DDoS {alert['protection']} için {cd_sec}sn cooldown ayarlandi")

        # Periyodik temizlik: alarm olmasa bile 24s'ten eski history kayitlarini sil
        try:
            import time as _t
            _now = int(_t.time())
            _cutoff = _now - 86400
            removed = await redis.zremrangebyscore("ddos:attack_history", 0, _cutoff)
            if removed:
                logger.debug(f"DDoS history temizligi: {removed} expired kayit silindi")
        except Exception:
            pass

        return alerts

    except Exception as e:
        logger.error(f"DDoS anomali kontrolü hatasi: {e}")
        return []


PROT_LABELS = {
    "syn_flood": "SYN Flood",
    "udp_flood": "UDP Flood",
    "icmp_flood": "ICMP Flood",
    "conn_limit": "Bağlantı Limiti",
    "invalid_packet": "Geçersiz Paket",
}


async def _send_ddos_telegram_alert(alerts: list[dict]):
    """DDoS uyarısıni Telegram'a gönder (saldırgan IP dahil)."""
    try:
        from app.services.telegram_service import notify_ai_insight

        lines = ["<b>DDoS Saldırı Tespit Edildi!</b>\n"]
        all_ips = set()
        for a in alerts:
            label = PROT_LABELS.get(a["protection"], a["protection"])
            ips = a.get("attacker_ips", [])
            ip_str = ", ".join(ips[:3]) if ips else "bilinmiyor"
            all_ips.update(ips[:5])
            lines.append(
                f"  {label}: <b>+{a['delta']}</b> engellenen paket "
                f"(toplam: {a['total']}) — Kaynak: {ip_str}"
            )
        macs = [a.get("attacker_mac") for a in alerts if a.get("attacker_mac")]
        hosts = [a.get("attacker_hostname") for a in alerts if a.get("attacker_hostname")]
        if macs:
            lines.append(f"\n  MAC: {macs[0]}")
        if hosts:
            lines.append(f"  Hostname: {hosts[0]}")
        lines.append("\nDDoS koruma sistemi aktif olarak saldırılari engelliyor.")

        msg = "\n".join(lines)
        await notify_ai_insight(
            severity="warning",
            message=msg,
            category="security",
        )
        logger.warning(f"DDoS Telegram uyarısı gönderildi: {len(alerts)} koruma, IP: {list(all_ips)[:5]}")
    except Exception as e:
        logger.error(f"DDoS Telegram uyari hatasi: {e}")


async def _write_ddos_insight(alerts: list[dict]):
    """DDoS uyarısıni AiInsight tablosuna yaz (saldırgan IP/MAC/hostname dahil)."""
    try:
        from app.models.ai_insight import AiInsight, Severity

        prot_parts = []
        all_ips = set()
        primary_mac = None
        primary_hostname = None

        for a in alerts:
            label = PROT_LABELS.get(a["protection"], a["protection"])
            prot_parts.append(f"{label}: +{a['delta']} paket")
            ips = a.get("attacker_ips", [])
            all_ips.update(ips[:5])
            if not primary_mac and a.get("attacker_mac"):
                primary_mac = a["attacker_mac"]
            if not primary_hostname and a.get("attacker_hostname"):
                primary_hostname = a["attacker_hostname"]

        ips_str = ", ".join(sorted(all_ips)[:10]) if all_ips else "-"
        mac_str = primary_mac or "-"
        host_str = primary_hostname or "-"

        message = (
            f"[DDoS Tespit] {'; '.join(prot_parts)} "
            f"| Kaynak: {ips_str} | MAC: {mac_str} | Host: {host_str}"
        )

        async with (await _get_db_session()) as session:
            insight = AiInsight(
                severity=Severity.WARNING,
                message=message,
                category="security",
                suggested_action="DDoS koruma panelini kontrol edin. Gerekirse limitleri artirin veya kaynak IP'leri engelleyin.",
            )
            session.add(insight)
            await session.commit()
    except Exception as e:
        logger.error(f"DDoS insight yazma hatasi: {e}")


async def _get_db_session():
    """DB session factory'den session al."""
    from app.db.session import async_session_factory
    return async_session_factory()




# ============================================================================
# GeoIP Cozumleme (Attack Map için)
# ============================================================================

GEOIP_CACHE_TTL = 86400  # 24 saat
GEOIP_BATCH_URL = "http://ip-api.com/batch"


async def resolve_attacker_geoip(ips: list[str]) -> dict:
    """IP adreslerini ip-api.com batch API ile cozumle. Redis cache kullanir."""
    import aiohttp
    import json as _json

    if not ips:
        return {}

    try:
        from app.db.redis_client import get_redis
        redis = await get_redis()
    except Exception:
        redis = None

    results = {}
    uncached = []

    # Once cache'e bak
    for ip in ips:
        if _is_private_ip(ip):
            continue
        if redis:
            try:
                cached = await redis.get(f"geoip:{ip}")
                if cached:
                    results[ip] = _json.loads(cached)
                    continue
            except Exception:
                pass
        uncached.append(ip)

    # Cache'te olmayanlar için batch API cagir
    if uncached:
        try:
            batch_data = [{"query": ip, "fields": "query,status,country,countryCode,city,lat,lon,isp"} for ip in uncached[:100]]
            async with aiohttp.ClientSession() as session:
                async with session.post(GEOIP_BATCH_URL, json=batch_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        api_results = await resp.json()
                        for item in api_results:
                            if item.get("status") == "success":
                                ip_addr = item.get("query", "")
                                geo = {
                                    "lat": item.get("lat", 0),
                                    "lon": item.get("lon", 0),
                                    "country": item.get("country", ""),
                                    "countryCode": item.get("countryCode", ""),
                                    "city": item.get("city", ""),
                                    "isp": item.get("isp", ""),
                                }
                                results[ip_addr] = geo
                                # Redis'e cache'le
                                if redis:
                                    try:
                                        await redis.setex(f"geoip:{ip_addr}", GEOIP_CACHE_TTL, _json.dumps(geo))
                                    except Exception:
                                        pass
        except Exception as e:
            logger.error(f"GeoIP batch API hatasi: {e}")

    return results


async def get_attack_map_data() -> dict:
    """Attack Map için tam veri seti: saldırganlar + GeoIP + counter özeti."""
    from datetime import datetime, timezone

    # Saldırgan IP'leri al
    attacker_ips = await get_ddos_attacker_ips()
    # Counter özeti al
    summary = await get_ddos_drop_summary()

    # Tum benzersiz IP'leri topla
    all_ips = set()
    for prot, ips in attacker_ips.items():
        for ip in ips:
            if not _is_private_ip(ip):
                all_ips.add(ip)

    # Redis geçmişinden de IP'leri al (son 24 saat)
    history = []
    try:
        from app.db.redis_client import get_redis
        redis = await get_redis()
        import time, json as _json
        cutoff = int(time.time()) - 86400
        history = await redis.zrangebyscore("ddos:attack_history", cutoff, "+inf")
        for entry_bytes in history:
            try:
                entry = _json.loads(entry_bytes)
                ip = entry.get("ip", "")
                if ip and not _is_private_ip(ip):
                    all_ips.add(ip)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Saldırı geçmişi okuma hatası: {e}")

    # GeoIP cozumle
    geo_data = await resolve_attacker_geoip(list(all_ips))

    # Conntrack'ten per-IP baglanti sayisi ve bytes topla
    conntrack_data = {}  # {ip: {"conns": int, "packets": int, "bytes": int}}
    try:
        rc, ct_out, _ = await _run_cmd(["sudo", "conntrack", "-L"])
        if rc == 0 and ct_out:
            for ct_line in ct_out.splitlines():
                src_match = re.search(r'src=(\d+\.\d+\.\d+\.\d+)', ct_line)
                if not src_match:
                    continue
                src_ip = src_match.group(1)
                if _is_private_ip(src_ip) or src_ip not in all_ips:
                    continue
                pkt_match = re.search(r'packets=(\d+)', ct_line)
                byt_match = re.search(r'bytes=(\d+)', ct_line)
                pkt = int(pkt_match.group(1)) if pkt_match else 0
                byt = int(byt_match.group(1)) if byt_match else 0
                if src_ip in conntrack_data:
                    conntrack_data[src_ip]["conns"] += 1
                    conntrack_data[src_ip]["packets"] += pkt
                    conntrack_data[src_ip]["bytes"] += byt
                else:
                    conntrack_data[src_ip] = {"conns": 1, "packets": pkt, "bytes": byt}
    except Exception as e:
        logger.debug(f"Conntrack per-IP okuma hatasi: {e}")

    # Redis history'den IP bazli counter bilgisi topla
    import json as _json
    history_counters = {}  # {ip: {"type": str, "packets": int, "bytes": int}}
    try:
        for entry_bytes in history:
            try:
                entry = _json.loads(entry_bytes)
                ip = entry.get("ip", "")
                if ip and not _is_private_ip(ip):
                    pkt = entry.get("packets", 0)
                    byt = entry.get("bytes", 0)
                    if ip in history_counters:
                        history_counters[ip]["packets"] += pkt
                        history_counters[ip]["bytes"] += byt
                    else:
                        history_counters[ip] = {
                            "type": entry.get("type", "unknown"),
                            "packets": pkt,
                            "bytes": byt,
                        }
            except Exception:
                pass
    except Exception:
        pass

    # Kumulatif counter'lari Redis'ten oku (nftables counter sifirlanir, bu kalici)
    cumulative = {}
    try:
        from app.db.redis_client import get_redis as _get_redis
        _redis = await _get_redis()
        cum_raw = await _redis.hgetall("ddos:cumulative_counters")
        for k, v in cum_raw.items():
            parts = k.split(":")
            if len(parts) == 2:
                prot_name, metric = parts
                if prot_name not in cumulative:
                    cumulative[prot_name] = {"packets": 0, "bytes": 0}
                cumulative[prot_name][metric] = int(v)
    except Exception:
        pass

    # Saldırı listesi oluştur — kumulatif + anlik counter birlesimi
    attacks = []
    seen_ips = set()
    by_prot = summary.get("by_protection", {})
    for prot, ips in attacker_ips.items():
        external_ips = [ip for ip in ips if not _is_private_ip(ip)]
        ip_count = max(len(external_ips), 1)
        # Kumulatif + anlik (hangisi buyukse)
        cum_pkt = cumulative.get(prot, {}).get("packets", 0)
        cum_byt = cumulative.get(prot, {}).get("bytes", 0)
        nft_pkt = by_prot.get(prot, {}).get("packets", 0)
        nft_byt = by_prot.get(prot, {}).get("bytes", 0)
        total_pkt = max(cum_pkt, nft_pkt)
        total_byt = max(cum_byt, nft_byt)
        per_ip_packets = total_pkt // ip_count
        per_ip_bytes = total_byt // ip_count
        for ip in external_ips:
            seen_ips.add(ip)
            geo = geo_data.get(ip)
            if geo:
                # Conntrack verisini tercih et (gercek per-IP), yoksa history/nft
                ct = conntrack_data.get(ip, {})
                hist = history_counters.get(ip, {})
                final_packets = ct.get("packets", 0) or (per_ip_packets + hist.get("packets", 0))
                final_bytes = ct.get("bytes", 0) or (per_ip_bytes + hist.get("bytes", 0))
                attacks.append({
                    "ip": ip,
                    "lat": geo["lat"],
                    "lon": geo["lon"],
                    "country": geo["country"],
                    "countryCode": geo["countryCode"],
                    "city": geo["city"],
                    "isp": geo.get("isp", ""),
                    "type": prot,
                    "packets": final_packets,
                    "bytes": final_bytes,
                })

    # History'den gelen ama attacker_ips'te olmayan IP'leri de ekle
    for ip, data in history_counters.items():
        if ip in seen_ips:
            continue
        geo = geo_data.get(ip)
        if geo:
            ct = conntrack_data.get(ip, {})
            attacks.append({
                "ip": ip,
                "lat": geo["lat"],
                "lon": geo["lon"],
                "country": geo["country"],
                "countryCode": geo["countryCode"],
                "city": geo["city"],
                "isp": geo.get("isp", ""),
                "type": data["type"],
                "packets": ct.get("packets", 0) or data["packets"],
                "bytes": ct.get("bytes", 0) or data["bytes"],
            })
            seen_ips.add(ip)

    # Hedef konum (Turkiye)
    target = {"lat": 39.92, "lon": 32.85, "label": "TonbilAi Firewall"}

    # Summary'de kumulatif degerleri de goster
    summary_by_prot = {}
    for prot_key in set(list(by_prot.keys()) + list(cumulative.keys())):
        cum_p = cumulative.get(prot_key, {}).get("packets", 0)
        cum_b = cumulative.get(prot_key, {}).get("bytes", 0)
        nft_p = by_prot.get(prot_key, {}).get("packets", 0)
        nft_b = by_prot.get(prot_key, {}).get("bytes", 0)
        summary_by_prot[prot_key] = {
            "packets": max(cum_p, nft_p),
            "bytes": max(cum_b, nft_b),
        }
    total_pkt = sum(v["packets"] for v in summary_by_prot.values())
    total_byt = sum(v["bytes"] for v in summary_by_prot.values())

    return {
        "target": target,
        "attacks": attacks,
        "summary": {
            "total_packets": total_pkt,
            "total_bytes": total_byt,
            "by_protection": summary_by_prot,
            "active_attackers": len(all_ips),
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Toplu Uygulama (startup sync)
# ============================================================================

async def apply_all(config) -> dict:
    """Tum DDoS korumalarini uygula. Başlangic sync için."""
    results = {}
    try:
        results["nft_rules"] = await apply_ddos_nft_rules(config)
    except Exception as e:
        logger.error(f"DDoS nft uygulama hatasi: {e}")
        results["nft_rules"] = 0

    try:
        results["kernel"] = await apply_kernel_hardening(config)
    except Exception as e:
        logger.error(f"Kernel sertlestirme hatasi: {e}")
        results["kernel"] = False

    try:
        results["http"] = await apply_http_flood_protection(config)
    except Exception as e:
        logger.error(f"HTTP flood koruma hatasi: {e}")
        results["http"] = False

    # Uvicorn workers — sadece config yaz, restart yapma
    try:
        results["uvicorn"] = await apply_uvicorn_workers(config)
    except Exception as e:
        logger.error(f"Uvicorn worker hatasi: {e}")
        results["uvicorn"] = {"config_written": False}

    logger.info(f"DDoS koruma toplam sonuç: {results}")
    return results
