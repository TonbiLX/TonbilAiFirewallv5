# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# WireGuard VPN Sunucu API: Native WireGuard yönetimi (wg/wg-quick).
# Sunucu kurulumu, peer ekleme/silme, config indirme, QR kod.

import asyncio
import base64
import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.redis_client import get_redis
from app.models.user import User
from app.models.vpn_peer import VpnPeer, VpnConfig
from app.schemas.vpn_peer import (
    VpnPeerResponse,
    VpnPeerConfigResponse,
    VpnConfigResponse,
    VpnStatsResponse,
)
from app.hal.linux_nftables import (
    ensure_nat_postrouting_chain,
    add_vpn_nft_rules,
    remove_vpn_nft_rules,
    persist_nftables,
    run_nft,
)

router = APIRouter()
logger = logging.getLogger("tonbilai.vpn")

WG_CONFIG_DIR = Path("/etc/wireguard")
WG_INTERFACE = "wg0"
WG_CONF_PATH = WG_CONFIG_DIR / f"{WG_INTERFACE}.conf"
VPN_SUBNET = "10.13.13"
VPN_SERVER_IP = f"{VPN_SUBNET}.1"
VPN_DNS = "192.168.1.2"  # Pi'nin kendisi (DNS proxy)
VPN_PORT = 51820
VPN_ENDPOINT = "176.88.250.236"


async def _run_cmd(cmd: list, check: bool = True, timeout: float = 30) -> str:
    """Komut calistir (timeout korumali)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.error(f"Komut timeout ({timeout}s): {' '.join(cmd)}")
        raise RuntimeError(f"Komut zaman asimina ugradi: {' '.join(cmd[:3])}")
    out = stdout.decode().strip()
    err = stderr.decode().strip()
    if proc.returncode != 0 and check:
        logger.error(f"Komut hatasi: {' '.join(cmd)} -> {err}")
        raise RuntimeError(err)
    return out


async def _wg_genkey() -> tuple[str, str]:
    """WireGuard anahtar cifti oluştur."""
    private_key = await _run_cmd(["wg", "genkey"])
    proc = await asyncio.create_subprocess_exec(
        "wg", "pubkey",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate(input=private_key.encode())
    public_key = stdout.decode().strip()
    return private_key, public_key


async def _wg_show() -> dict:
    """sudo wg show wg0 ciktisini parse et."""
    result = {
        "active": False,
        "public_key": None,
        "listen_port": VPN_PORT,
        "peers": [],
    }

    try:
        out = await _run_cmd(["sudo", "wg", "show", WG_INTERFACE], check=False)
        if not out or "Unable to access" in out:
            return result

        result["active"] = True
        current_peer = None

        for line in out.splitlines():
            line = line.strip()
            if line.startswith("public key:"):
                if current_peer is None:
                    result["public_key"] = line.split(":", 1)[1].strip()
            elif line.startswith("listening port:"):
                result["listen_port"] = int(line.split(":", 1)[1].strip())
            elif line.startswith("peer:"):
                if current_peer:
                    result["peers"].append(current_peer)
                current_peer = {
                    "public_key": line.split(":", 1)[1].strip(),
                    "endpoint": None,
                    "allowed_ips": "",
                    "latest_handshake": None,
                    "transfer_rx": 0,
                    "transfer_tx": 0,
                }
            elif current_peer:
                if line.startswith("endpoint:"):
                    current_peer["endpoint"] = line.split(":", 1)[1].strip()
                elif line.startswith("allowed ips:"):
                    current_peer["allowed_ips"] = line.split(":", 1)[1].strip()
                elif line.startswith("latest handshake:"):
                    current_peer["latest_handshake"] = line.split(":", 1)[1].strip()
                elif line.startswith("transfer:"):
                    transfer = line.split(":", 1)[1].strip()
                    # "1.23 MiB received, 4.56 MiB sent"
                    rx_match = re.search(r"([\d.]+)\s+(\w+)\s+received", transfer)
                    tx_match = re.search(r"([\d.]+)\s+(\w+)\s+sent", transfer)
                    if rx_match:
                        current_peer["transfer_rx"] = _parse_transfer(rx_match.group(1), rx_match.group(2))
                    if tx_match:
                        current_peer["transfer_tx"] = _parse_transfer(tx_match.group(1), tx_match.group(2))

        if current_peer:
            result["peers"].append(current_peer)

    except Exception as e:
        logger.error(f"wg show hatasi: {e}")

    return result


WG_CONNECTED_TIMEOUT = 180  # 3 dakika — bu sureden eski handshake = bagli degil


def _parse_handshake_seconds(hs_str: str) -> int | None:
    """WireGuard handshake stringini saniyeye cevir. Orn: '2 minutes, 4 seconds ago' -> 124."""
    if not hs_str or hs_str == "0":
        return None
    total = 0
    for m in re.finditer(r"(\d+)\s+(second|minute|hour|day)", hs_str):
        val = int(m.group(1))
        unit = m.group(2)
        if unit == "second":
            total += val
        elif unit == "minute":
            total += val * 60
        elif unit == "hour":
            total += val * 3600
        elif unit == "day":
            total += val * 86400
    return total if total > 0 else None


def _parse_transfer(value: str, unit: str) -> int:
    """Transfer degerini byte'a cevir."""
    v = float(value)
    unit = unit.lower()
    if "kib" in unit or "kb" in unit:
        return int(v * 1024)
    elif "mib" in unit or "mb" in unit:
        return int(v * 1024 * 1024)
    elif "gib" in unit or "gb" in unit:
        return int(v * 1024 * 1024 * 1024)
    return int(v)


REDIS_PEER_BASELINE_PREFIX = "vpn:peer:baseline:"


async def _get_session_transfer(pubkey: str, wg_rx: int, wg_tx: int, is_connected: bool) -> tuple[int, int]:
    """Peer oturum transferini hesapla. Bağlantı basinda baseline kaydeder,
    gosterilen deger = wg_transfer - baseline. Kopunca baseline silinir."""
    try:
        redis = await get_redis()
        key = f"{REDIS_PEER_BASELINE_PREFIX}{pubkey[:16]}"

        if not is_connected:
            # Bağlantı yok: baseline sil, sifir dondur
            await redis.delete(key)
            return 0, 0

        # Baseline var mi?
        baseline = await redis.hgetall(key)
        if not baseline:
            # Yeni bağlantı: mevcut wg degerini baseline olarak kaydet
            await redis.hset(key, mapping={"rx": str(wg_rx), "tx": str(wg_tx)})
            await redis.expire(key, 86400)  # 24 saat TTL
            return 0, 0

        base_rx = int(baseline.get("rx", 0))
        base_tx = int(baseline.get("tx", 0))

        # wg restart olduysa (wg degeri baseline'dan kucuk)
        if wg_rx < base_rx or wg_tx < base_tx:
            await redis.hset(key, mapping={"rx": str(wg_rx), "tx": str(wg_tx)})
            await redis.expire(key, 86400)
            return 0, 0

        return wg_rx - base_rx, wg_tx - base_tx
    except Exception as e:
        logger.error(f"Peer baseline hatasi: {e}")
        return wg_rx, wg_tx


def _next_peer_ip(existing_ips: list[str]) -> str:
    """Sonraki bos peer IP adresini bul."""
    used = set()
    for ip in existing_ips:
        parts = ip.split("/")[0].split(".")
        if len(parts) == 4:
            used.add(int(parts[3]))

    for i in range(2, 255):
        if i not in used:
            return f"{VPN_SUBNET}.{i}/32"
    raise ValueError("Bos peer IP yok")


def _generate_peer_config(
    peer_private_key: str,
    peer_address: str,
    server_public_key: str,
) -> str:
    """Peer için indirilebilir WireGuard config oluştur."""
    return f"""[Interface]
PrivateKey = {peer_private_key}
Address = {peer_address}
DNS = {VPN_DNS}

[Peer]
PublicKey = {server_public_key}
Endpoint = {VPN_ENDPOINT}:{VPN_PORT}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""


async def _write_server_config(
    private_key: str,
    peers: list[dict],
):
    """wg0.conf dosyasini yeniden yaz.

    NOT: PostUp/PostDown KULLANILMAZ. nftables kurallari Python tarafindan
    start_vpn_server/stop_vpn_server endpoint'lerinde yonetilir.
    Bu sayede 'nft flush chain' gibi tehlikeli komutlar onlenir.
    """
    lines = [
        "[Interface]",
        f"Address = {VPN_SERVER_IP}/24",
        f"ListenPort = {VPN_PORT}",
        f"PrivateKey = {private_key}",
        "",
    ]

    for peer in peers:
        lines.append("[Peer]")
        lines.append(f"PublicKey = {peer['public_key']}")
        lines.append(f"AllowedIPs = {peer['allowed_ips']}")
        if peer.get("preshared_key"):
            lines.append(f"PresharedKey = {peer['preshared_key']}")
        lines.append("")

    content = "\n".join(lines) + "\n"

    # sudo tee ile yaz
    proc = await asyncio.create_subprocess_exec(
        "sudo", "tee", str(WG_CONF_PATH),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate(input=content.encode())

    # Izinleri ayarla
    await _run_cmd(["sudo", "chmod", "600", str(WG_CONF_PATH)], check=False)

    logger.info(f"WireGuard sunucu config yazildi: {WG_CONF_PATH} ({len(peers)} peer)")


async def _ensure_server_setup(db: AsyncSession) -> VpnConfig:
    """Sunucu yapılandirmasinin mevcut oldugunu kontrol et, yoksa oluştur."""
    result = await db.execute(select(VpnConfig).limit(1))
    config = result.scalar_one_or_none()

    if not config:
        # İlk kurulum - anahtar cifti oluştur
        private_key, public_key = await _wg_genkey()

        config = VpnConfig(
            interface_name=WG_INTERFACE,
            listen_port=VPN_PORT,
            server_private_key=private_key,
            server_public_key=public_key,
            server_address=f"{VPN_SERVER_IP}/24",
            dns_server=VPN_DNS,
            mtu=1420,
            route_all_traffic=False,
        )
        db.add(config)
        await db.flush()
        await db.refresh(config)
        logger.info("WireGuard sunucu ilk kurulum yapildi")
    else:
        # Eski seed verisini duzelt (10.0.0.x -> 10.13.13.x)
        changed = False
        if config.server_address != f"{VPN_SERVER_IP}/24":
            config.server_address = f"{VPN_SERVER_IP}/24"
            changed = True
        if config.dns_server != VPN_DNS:
            config.dns_server = VPN_DNS
            changed = True
        # wg0.conf ile DB arasindaki public key uyumsuzlugunu duzelt
        try:
            conf_path = Path(f"/etc/wireguard/{WG_INTERFACE}.conf")
            if conf_path.exists():
                with open(conf_path, "r") as f:
                    for line in f:
                        if line.strip().startswith("PrivateKey"):
                            conf_priv = line.split("=", 1)[1].strip()
                            if conf_priv and conf_priv != config.server_private_key:
                                # wg0.conf farkli key kullaniyor, DB'yi güncelle
                                proc = await asyncio.create_subprocess_exec(
                                    "wg", "pubkey",
                                    stdin=asyncio.subprocess.PIPE,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE,
                                )
                                stdout, _ = await proc.communicate(input=conf_priv.encode())
                                real_pub = stdout.decode().strip()
                                config.server_private_key = conf_priv
                                config.server_public_key = real_pub
                                changed = True
                                logger.warning(f"VPN key sync: wg0.conf private key DB ile uyumsuzdu, duzeltildi")
                            elif conf_priv == config.server_private_key:
                                # Private key ayni, public key dogru mu kontrol et
                                proc = await asyncio.create_subprocess_exec(
                                    "wg", "pubkey",
                                    stdin=asyncio.subprocess.PIPE,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE,
                                )
                                stdout, _ = await proc.communicate(input=conf_priv.encode())
                                real_pub = stdout.decode().strip()
                                if real_pub != config.server_public_key:
                                    config.server_public_key = real_pub
                                    changed = True
                                    logger.warning(f"VPN key sync: public key duzeltildi ({real_pub[:16]}...)")
                            break
        except Exception as e:
            logger.error(f"VPN key sync kontrol hatasi: {e}")
        if changed:
            await db.flush()
            logger.info("VPN config DB degerleri duzeltildi")

    return config


async def _ensure_vpn_nft_rules():
    """wg0 için masquerade kurallari yoksa ekle (peer ekleme sırasında)."""
    try:
        out = await run_nft(["list", "table", "inet", "nat"], check=False)
        if "vpn_wg0_masq" in out:
            return  # Zaten mevcut
        await ensure_nat_postrouting_chain()
        await add_vpn_nft_rules(WG_INTERFACE, f"{VPN_SUBNET}.0/24")
        logger.info("VPN nftables kurallari eklendi (peer ekleme sırasında)")
    except Exception as e:
        logger.error(f"VPN nft kural ekleme hatasi: {e}")


# ===== ENDPOINTS =====

@router.get("/config", response_model=VpnConfigResponse)
async def get_vpn_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """WireGuard sunucu konfigurasyonunu getir."""
    config = await _ensure_server_setup(db)
    wg_status = await _wg_show()

    return VpnConfigResponse(
        interface_name=config.interface_name or WG_INTERFACE,
        listen_port=config.listen_port or VPN_PORT,
        server_public_key=config.server_public_key,
        server_address=config.server_address or f"{VPN_SERVER_IP}/24",
        dns_server=config.dns_server or VPN_DNS,
        mtu=config.mtu or 1420,
        enabled=wg_status["active"],
    )


@router.post("/start")
async def start_vpn_server(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """WireGuard sunucusunu başlat."""
    config = await _ensure_server_setup(db)

    # Peer listesini DB'den al
    peer_result = await db.execute(select(VpnPeer))
    peers = [
        {
            "public_key": p.public_key,
            "allowed_ips": p.allowed_ips,
            "preshared_key": getattr(p, "preshared_key", None),
        }
        for p in peer_result.scalars().all()
    ]

    # Config dosyasini yaz
    await _write_server_config(config.server_private_key, peers)

    # Calisiyorsa durdur + eski nft kurallarini temizle
    await _run_cmd(["sudo", "wg-quick", "down", WG_INTERFACE], check=False)
    await remove_vpn_nft_rules(WG_INTERFACE)

    # postrouting chain'i garantile
    await ensure_nat_postrouting_chain()

    # Başlat
    await _run_cmd(["sudo", "wg-quick", "up", WG_INTERFACE])

    # nftables kurallari ekle (forward accept + masquerade)
    await add_vpn_nft_rules(WG_INTERFACE, f"{VPN_SUBNET}.0/24")

    # Kuralları kalici yap
    await persist_nftables()

    logger.info("WireGuard sunucu başlatildi")
    return {"status": "started", "interface": WG_INTERFACE, "port": VPN_PORT}


@router.post("/stop")
async def stop_vpn_server(
    current_user: User = Depends(get_current_user),
):
    """WireGuard sunucusunu durdur."""
    # Once nft kurallarini guvenle sil (sadece VPN kurallari, diger kurallara dokunmaz)
    await remove_vpn_nft_rules(WG_INTERFACE)

    await _run_cmd(["sudo", "wg-quick", "down", WG_INTERFACE], check=False)

    await persist_nftables()

    logger.info("WireGuard sunucu durduruldu")
    return {"status": "stopped", "interface": WG_INTERFACE}


@router.get("/peers", response_model=list[VpnPeerResponse])
async def list_peers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """WireGuard peer listesini DB + canlı veriden oku."""
    result = await db.execute(select(VpnPeer))
    db_peers = result.scalars().all()

    # Canlı veri
    wg_status = await _wg_show()
    live_peers = {p["public_key"]: p for p in wg_status.get("peers", [])}

    peers = []
    for p in db_peers:
        live = live_peers.get(p.public_key, {})
        hs_age = _parse_handshake_seconds(live.get("latest_handshake", ""))
        is_connected = hs_age is not None and hs_age <= WG_CONNECTED_TIMEOUT

        # Oturum bazli transfer (baseline cikarilmis)
        wg_rx = live.get("transfer_rx", 0)
        wg_tx = live.get("transfer_tx", 0)
        session_rx, session_tx = await _get_session_transfer(
            p.public_key, wg_rx, wg_tx, is_connected
        )

        peers.append(VpnPeerResponse(
            name=p.name,
            public_key=p.public_key,
            allowed_ips=p.allowed_ips,
            dns_servers=VPN_DNS,
            endpoint=live.get("endpoint") if is_connected else None,
            enabled=True,
            has_qr=True,
            is_connected=is_connected,
            last_handshake=live.get("latest_handshake") if is_connected else None,
            transfer_rx=session_rx,
            transfer_tx=session_tx,
        ))

    return peers


MAX_VPN_PEERS = 250  # Maksimum WireGuard peer sayısı


@router.post("/peers")
async def add_peer(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Yeni VPN peer ekle."""
    # Peer ismi doğrulama (command injection onlemi)
    import re as _re
    if not _re.match(r'^[a-zA-Z0-9_-]{1,64}$', name):
        raise HTTPException(status_code=400, detail="Peer ismi sadece harf, rakam, tire ve alt çizgi icermeli (maks 64 karakter)")

    config = await _ensure_server_setup(db)

    # Mevcut peer IP'lerini al
    result = await db.execute(select(VpnPeer))
    existing_peers = result.scalars().all()

    # Peer limiti kontrolü
    if len(existing_peers) >= MAX_VPN_PEERS:
        raise HTTPException(status_code=400, detail=f"Maksimum VPN peer sayısına ulasildi ({MAX_VPN_PEERS})")

    existing_ips = [p.allowed_ips for p in existing_peers]

    # Yeni peer için anahtar cifti
    private_key, public_key = await _wg_genkey()
    peer_ip = _next_peer_ip(existing_ips)

    # DB'ye kaydet
    peer = VpnPeer(
        name=name,
        public_key=public_key,
        private_key=private_key,
        allowed_ips=peer_ip,
        dns_servers=VPN_DNS,
        persistent_keepalive=25,
    )
    db.add(peer)
    await db.flush()
    await db.refresh(peer)

    # WireGuard'a canlı ekle (sunucu calisiyorsa)
    wg_status = await _wg_show()
    if wg_status["active"]:
        await _run_cmd([
            "sudo", "wg", "set", WG_INTERFACE,
            "peer", public_key,
            "allowed-ips", peer_ip,
        ], check=False)

        # Config dosyasini da güncelle
        all_peers = [
            {"public_key": p.public_key, "allowed_ips": p.allowed_ips}
            for p in existing_peers
        ] + [{"public_key": public_key, "allowed_ips": peer_ip}]
        await _write_server_config(config.server_private_key, all_peers)

        # Masquerade kurallarini garanti et (boot sonrası eksik olabilir)
        await _ensure_vpn_nft_rules()

    # Client config oluştur
    client_config = _generate_peer_config(
        private_key, peer_ip, config.server_public_key,
    )

    logger.info(f"Yeni VPN peer eklendi: {name} ({peer_ip})")

    return {
        "name": name,
        "public_key": public_key,
        "allowed_ips": peer_ip,
        "config_text": client_config,
    }


@router.delete("/peers/{peer_name}")
async def remove_peer(
    peer_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """VPN peer sil."""
    result = await db.execute(
        select(VpnPeer).where(VpnPeer.name == peer_name)
    )
    peer = result.scalar_one_or_none()
    if not peer:
        raise HTTPException(status_code=404, detail=f"Peer bulunamadı: {peer_name}")

    # WireGuard'dan canlı kaldir
    wg_status = await _wg_show()
    if wg_status["active"]:
        await _run_cmd([
            "sudo", "wg", "set", WG_INTERFACE,
            "peer", peer.public_key, "remove",
        ], check=False)

    # DB'den sil
    await db.delete(peer)
    await db.flush()

    # Config dosyasini güncelle
    config_result = await db.execute(select(VpnConfig).limit(1))
    config = config_result.scalar_one_or_none()
    if config:
        remaining_result = await db.execute(select(VpnPeer))
        remaining = [
            {"public_key": p.public_key, "allowed_ips": p.allowed_ips}
            for p in remaining_result.scalars().all()
        ]
        await _write_server_config(config.server_private_key, remaining)

    logger.info(f"VPN peer silindi: {peer_name}")
    return {"status": "removed", "name": peer_name}


@router.get("/peers/{peer_name}/config", response_model=VpnPeerConfigResponse)
async def get_peer_config(
    peer_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Peer için indirilebilir WireGuard konfigurasyonu + QR kodu."""
    result = await db.execute(
        select(VpnPeer).where(VpnPeer.name == peer_name)
    )
    peer = result.scalar_one_or_none()
    if not peer:
        raise HTTPException(status_code=404, detail=f"Peer bulunamadı: {peer_name}")

    config = await _ensure_server_setup(db)
    config_text = _generate_peer_config(
        peer.private_key, peer.allowed_ips, config.server_public_key,
    )

    # QR kod oluştur
    qr_data = await _generate_qr(config_text)

    return VpnPeerConfigResponse(
        peer_name=peer_name,
        config_text=config_text,
        qr_data=qr_data,
    )


@router.get("/peers/{peer_name}/qr")
async def get_peer_qr(
    peer_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Peer QR kodunu dogrudan PNG olarak sun."""
    result = await db.execute(
        select(VpnPeer).where(VpnPeer.name == peer_name)
    )
    peer = result.scalar_one_or_none()
    if not peer:
        raise HTTPException(status_code=404, detail=f"Peer bulunamadı: {peer_name}")

    config = await _ensure_server_setup(db)
    config_text = _generate_peer_config(
        peer.private_key, peer.allowed_ips, config.server_public_key,
    )

    # QR PNG oluştur
    qr_bytes = await _generate_qr_png(config_text)
    if not qr_bytes:
        raise HTTPException(status_code=500, detail="QR kodu oluşturulamadi (qrencode yuklu mu?)")

    return Response(content=qr_bytes, media_type="image/png")


@router.get("/stats", response_model=VpnStatsResponse)
async def vpn_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """VPN istatistikleri."""
    config = await _ensure_server_setup(db)
    wg_status = await _wg_show()

    # Bagli peer sayısı ve oturum bazli transfer
    connected = 0
    total_rx = 0
    total_tx = 0
    for p in wg_status.get("peers", []):
        hs_age = _parse_handshake_seconds(p.get("latest_handshake", ""))
        is_conn = hs_age is not None and hs_age <= WG_CONNECTED_TIMEOUT
        if is_conn:
            connected += 1
            s_rx, s_tx = await _get_session_transfer(
                p["public_key"], p.get("transfer_rx", 0), p.get("transfer_tx", 0), True
            )
            total_rx += s_rx
            total_tx += s_tx

    return VpnStatsResponse(
        server_enabled=wg_status["active"],
        server_public_key=config.server_public_key,
        listen_port=config.listen_port or VPN_PORT,
        total_peers=len(wg_status.get("peers", [])),
        connected_peers=connected,
        total_transfer_rx=total_rx,
        total_transfer_tx=total_tx,
    )


@router.post("/fix-subnet")
async def fix_vpn_subnet(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eski seed verisindeki peer IP'lerini duzelt (10.0.0.x -> 10.13.13.x)."""
    result = await db.execute(select(VpnPeer))
    peers = result.scalars().all()
    fixed = 0

    for i, peer in enumerate(peers, start=2):
        expected_ip = f"{VPN_SUBNET}.{i}/32"
        if peer.allowed_ips != expected_ip:
            old_ip = peer.allowed_ips
            peer.allowed_ips = expected_ip
            fixed += 1
            logger.info(f"Peer subnet duzeltildi: {peer.name}: {old_ip} -> {expected_ip}")

        if peer.dns_servers and not peer.dns_servers.startswith("192.168."):
            peer.dns_servers = VPN_DNS

    if fixed:
        await db.flush()

    return {"fixed_peers": fixed, "subnet": f"{VPN_SUBNET}.0/24"}


async def _generate_qr(config_text: str) -> str | None:
    """QR kodu base64 string olarak oluştur."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "qrencode", "-t", "PNG", "-o", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate(input=config_text.encode())
        if proc.returncode == 0 and stdout:
            return base64.b64encode(stdout).decode("utf-8")
    except FileNotFoundError:
        logger.warning("qrencode bulunamadı, QR kod oluşturulamadi")
    return None


async def _generate_qr_png(config_text: str) -> bytes | None:
    """QR kodu PNG bytes olarak oluştur."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "qrencode", "-t", "PNG", "-o", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate(input=config_text.encode())
        if proc.returncode == 0 and stdout:
            return stdout
    except FileNotFoundError:
        logger.warning("qrencode bulunamadı")
    return None
