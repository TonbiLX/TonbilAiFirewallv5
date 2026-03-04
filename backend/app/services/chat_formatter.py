# --- Ajan: ANALIST (THE ANALYST) ---
# Chat yanit formatlama yardimcilari.
# Tum handler'lar bu merkezi fonksiyonlari kullanarak tutarli, bolumlenmis yanitlar uretir.

"""
Markdown formatlama kurallari:
- **bold** -> kalın
- `code`   -> kod
- _italic_ -> italik
- ───      -> gorsel ayirici (separator)
- · item   -> madde isareti
"""


# =====================================================================
# Temel Yapi Tashlari
# =====================================================================

def separator() -> str:
    """Gorsel ayirici çizgi."""
    return "━━━━━━━━━━━━━━━━━━━━━━━"


def section_header(title: str, icon: str = "") -> str:
    """Bolum basligi + ayirici."""
    prefix = f"{icon} " if icon else ""
    return f"{prefix}**{title}**\n{separator()}"


def stat_line(label: str, value, bold_value: bool = True) -> str:
    """İstatistik satiri (2 bosluk girinti)."""
    val = f"**{value}**" if bold_value else str(value)
    return f"  {label}: {val}"


def stat_line_extra(label: str, value, extra: str = "", bold_value: bool = True) -> str:
    """Ek bilgili istatistik satiri."""
    val = f"**{value}**" if bold_value else str(value)
    ext = f" ({extra})" if extra else ""
    return f"  {label}: {val}{ext}"


def device_line(
    hostname: str,
    ip: str,
    manufacturer: str | None = None,
    is_online: bool = False,
    profile_name: str | None = None,
    alias_name: str | None = None,
    is_blocked: bool = False,
) -> str:
    """Standart cihaz satiri."""
    status = "🟢" if is_online else "🔴"
    name = hostname or "Bilinmeyen"
    parts = [f"{status} **{name}** — `{ip}`"]
    if manufacturer:
        parts.append(f"· {manufacturer}")
    if profile_name:
        parts.append(f"[{profile_name}]")
    if alias_name:
        parts.append(f"_({alias_name})_")
    if is_blocked:
        parts.append("⛔")
    return " ".join(parts)


def domain_line(domain: str, count: int | None = None, action: str | None = None) -> str:
    """Domain satiri."""
    parts = [f"  · `{domain}`"]
    if count is not None:
        parts.append(f"— **{count}** sorgu")
    if action:
        parts.append(f"({action})")
    return " ".join(parts)


def log_line(timestamp: str, ip: str, domain: str, blocked: bool, reason: str | None = None) -> str:
    """DNS log satiri."""
    icon = "🔴" if blocked else "🟢"
    action = "ENGEL" if blocked else "IZIN"
    reason_text = f" ({reason})" if reason else ""
    return f"{icon} {timestamp} · `{ip}` · `{domain}` · {action}{reason_text}"


def result_badge(success: bool, message: str) -> str:
    """Basari/hata göstergesi."""
    icon = "✅" if success else "❌"
    return f"{icon} {message}"


def info_box(message: str) -> str:
    """Bilgi/ipucu kutusu."""
    return f"💡 _{message}_"


def warning_box(message: str) -> str:
    """Uyari kutusu."""
    return f"⚠️ _{message}_"


def summary_line(total: int, **extras) -> str:
    """Özet satiri."""
    parts = [f"Toplam: **{total}**"]
    for key, val in extras.items():
        parts.append(f"**{val}** {key}")
    return "  " + ", ".join(parts)


# =====================================================================
# Yuksek Seviye Formatlayicilar
# =====================================================================

def format_device_list(
    devices: list[dict],
) -> str:
    """
    Tam cihaz listesi.
    devices: [{"hostname", "ip", "manufacturer", "is_online", "profile_name", "alias_name", "is_blocked"}]
    """
    online = sum(1 for d in devices if d.get("is_online"))
    blocked = sum(1 for d in devices if d.get("is_blocked"))

    lines = [
        f"📡 **Ag Cihazlari** — {len(devices)} cihaz, {online} çevrimiçi",
        separator(),
    ]

    for d in devices:
        lines.append(device_line(
            hostname=d.get("hostname", ""),
            ip=d.get("ip", ""),
            manufacturer=d.get("manufacturer"),
            is_online=d.get("is_online", False),
            profile_name=d.get("profile_name"),
            alias_name=d.get("alias_name"),
            is_blocked=d.get("is_blocked", False),
        ))

    lines.append(separator())

    extras = []
    if blocked:
        extras.append(f"{blocked} engelli")
    if extras:
        lines.append(f"  {', '.join(extras)}")

    return "\n".join(lines)


def format_profile_list(profiles: list[dict]) -> str:
    """
    Profil listesi.
    profiles: [{"name", "profile_type", "bandwidth_limit"}]
    """
    lines = [
        f"👤 **Profiller** — {len(profiles)} tanimli",
        separator(),
    ]
    for p in profiles:
        bw = p.get("bandwidth_limit")
        bw_text = f"{bw} Mbps" if bw else "Sinirsiz"
        lines.append(f"  · **{p['name']}** ({p.get('profile_type', '?')}) — Bant: {bw_text}")

    lines.append(separator())
    return "\n".join(lines)


def format_system_status(stats: dict) -> str:
    """
    Sistem durumu.
    stats: {"devices", "online", "blocked", "dns_rules", "dns_blocks", "dns_allows",
            "blocklist_count", "fw_rules", "vpn_active", "critical_count"}
    """
    lines = [
        "🖥️ **TonbilAiOS Sistem Durumu**",
        separator(),
        "",
        "📡 **Ag**",
        stat_line_extra("Cihaz", stats.get("devices", 0),
                        f"{stats.get('online', 0)} çevrimiçi, {stats.get('blocked', 0)} engelli"),
        "",
        "🛡️ **DNS Engelleme**",
        stat_line_extra("Kural", stats.get("dns_rules", 0),
                        f"{stats.get('dns_blocks', 0)} engel, {stats.get('dns_allows', 0)} izin"),
        stat_line("Blocklist", f"{stats.get('blocklist_count', 0)} aktif"),
        "",
        "🔥 **Firewall**",
        stat_line("Kural", f"{stats.get('fw_rules', 0)} aktif"),
        "",
        "🌐 **VPN**",
        stat_line("Durum", "Aktif" if stats.get("vpn_active") else "Kapali", bold_value=False),
        "",
        "⚠️ **Uyarilar**",
        stat_line("Kritik", stats.get("critical_count", 0)),
    ]
    return "\n".join(lines)


def format_dns_stats(stats: dict, recent_domains: list[str] | None = None) -> str:
    """
    DNS istatistikleri.
    stats: {"rules", "blocks", "allows", "blocklist_count"}
    """
    lines = [
        "🛡️ **DNS Engelleme İstatistikleri**",
        separator(),
        "",
        stat_line_extra("Toplam kural", stats.get("rules", 0),
                        f"{stats.get('blocks', 0)} engel, {stats.get('allows', 0)} izin"),
        stat_line("Blocklist", stats.get("blocklist_count", 0)),
    ]
    if recent_domains:
        lines.append("")
        lines.append("  **Son engellenen:**")
        for d in recent_domains[:5]:
            lines.append(f"  · `{d}`")

    lines.append(separator())
    return "\n".join(lines)


def format_threat_status(stats: dict, blocked_ips: list[dict] | None = None) -> str:
    """
    Tehdit durumu.
    stats: {"blocked_ip_count", "total_auto_blocks", "total_suspicious", "total_external_blocked", "last_threat_time"}
    blocked_ips: [{"ip", "reason", "remaining_seconds"}]
    """
    lines = [
        "🚨 **DNS Tehdit Durumu**",
        separator(),
        "",
        stat_line("Engellenen IP", stats.get("blocked_ip_count", 0)),
        stat_line("Otomatik engel", stats.get("total_auto_blocks", 0)),
        stat_line("Şüpheli sorgu", stats.get("total_suspicious", 0)),
        stat_line("Reddedilen dis sorgu", stats.get("total_external_blocked", 0)),
        stat_line("Son tehdit", stats.get("last_threat_time") or "Yok", bold_value=False),
    ]

    if blocked_ips:
        lines.append("")
        lines.append("**Engellenen IP'ler:**")
        for b in blocked_ips[:10]:
            mins = b.get("remaining_seconds", 0) // 60
            lines.append(f"  · `{b['ip']}` ({b.get('reason', '?')}) — {mins} dk kaldi")
        if len(blocked_ips) > 10:
            lines.append(f"  _... ve {len(blocked_ips) - 10} IP daha_")

    lines.append(separator())
    return "\n".join(lines)


def format_log_results(
    log_lines: list[str],
    total: int,
    blocked: int,
    shown: int,
    device_label: str | None = None,
    time_label: str = "son 24 saat",
    filter_info: str = "",
) -> str:
    """
    DNS log sonuçlari.
    log_lines: Onceden formatlanmis log satirlari (log_line() ile)
    """
    device_info = f" — **{device_label}**" if device_label else ""
    filter_text = f" {filter_info}" if filter_info else ""

    lines = [
        f"📋 **DNS Log Sonuçlari{device_info}** ({time_label}{filter_text})",
        summary_line(total, engellenen=blocked),
        separator(),
    ]

    lines.extend(log_lines)

    lines.append(separator())
    if shown < total:
        lines.append(info_box(f"{shown}/{total} kayit gösteriliyor"))

    return "\n".join(lines)


def format_top_domains(
    rows: list[dict],
    label: str,
    device_label: str | None = None,
    time_label: str = "son 24 saat",
) -> str:
    """
    En cok sorgulanan/engellenen domain'ler.
    rows: [{"domain", "count"}]
    """
    device_info = f" ({device_label})" if device_label else ""
    lines = [
        f"📊 **En Cok {label} Domain'ler{device_info}** ({time_label})",
        separator(),
    ]
    for i, row in enumerate(rows, 1):
        lines.append(f"  {i}. `{row['domain']}` — **{row['count']}** sorgu")

    lines.append(separator())
    return "\n".join(lines)


def format_action_result(
    action: str,
    target: str,
    success: bool = True,
    details: list[str] | None = None,
    detail_label: str | None = None,
) -> str:
    """
    Aksiyon sonuçu.
    action: "engellendi", "engeli kaldırıldı", "atandi", vb.
    target: "youtube", "192.168.1.10", vb.
    details: ["youtube.com", "youtu.be", ...]
    """
    badge = result_badge(success, f"**{target}** {action}")
    lines = [badge]

    if details:
        label = detail_label or "Domainler"
        lines.append(f"\n  {label} ({len(details)}):")
        for d in details:
            lines.append(f"  · `{d}`")

    return "\n".join(lines)


def format_device_action(
    device_name: str,
    action: str,
    target: str | None = None,
    success: bool = True,
    details: list[str] | None = None,
) -> str:
    """
    Cihaz bazli aksiyon sonuçu.
    """
    if target:
        msg = f"**{device_name}** için **{target}** {action}"
    else:
        msg = f"**{device_name}** {action}"

    badge = result_badge(success, msg)
    lines = [badge]

    if details:
        lines.append(f"\n  Domainler ({len(details)}):")
        for d in details:
            lines.append(f"  · `{d}`")

    return "\n".join(lines)


def format_vpn_status(
    external_active: bool,
    external_name: str | None = None,
    external_country: str | None = None,
    total_servers: int = 0,
    local_active: bool = False,
    local_peers: int = 0,
) -> str:
    """VPN durumu."""
    lines = [
        "🌐 **VPN Durumu**",
        separator(),
    ]

    if external_active and external_name:
        lines.append(f"\n🌍 **Dış VPN:** Aktif — {external_name} ({external_country or '?'})")
    else:
        extra = f" ({total_servers} sunucu tanimli)" if total_servers else ""
        lines.append(f"\n🌍 **Dış VPN:** Kapali{extra}")

    if local_active:
        lines.append(f"🔒 **Uzak Erisim:** Aktif ({local_peers} peer)")
    else:
        lines.append("🔒 **Uzak Erisim:** Kapali")

    lines.append(separator())
    return "\n".join(lines)


def format_dhcp_info(pools: int, leases: int, static: int) -> str:
    """DHCP durumu."""
    lines = [
        "🔧 **DHCP Durumu**",
        separator(),
        "",
        stat_line("IP Havuzu", f"{pools} tanimli"),
        stat_line_extra("Aktif Kiralama", leases, f"{static} statik"),
        separator(),
    ]
    return "\n".join(lines)


def format_firewall_info(total: int, enabled: int) -> str:
    """Firewall durumu (basit)."""
    lines = [
        "🔥 **Güvenlik Duvarı Durumu**",
        separator(),
        "",
        stat_line_extra("Toplam kural", total, f"{enabled} aktif"),
        separator(),
    ]
    return "\n".join(lines)


def format_firewall_info_detailed(total: int, enabled: int, rules) -> str:
    """Firewall durumu (detayli, kurallarla birlikte)."""
    lines = [
        "🔥 **Güvenlik Duvarı Durumu**",
        separator(),
        "",
        stat_line_extra("Toplam kural", total, f"{enabled} aktif"),
    ]
    if rules:
        lines.extend(["", "**Son kurallar:**"])
        for r in rules[:10]:
            status = "✅" if r.enabled else "❌"
            proto = r.protocol.value if hasattr(r.protocol, "value") else r.protocol
            lines.append(f"  {status} `#{r.id}` {r.name} — Port {r.port}/{proto}")
    lines.extend(["", separator()])
    return "\n".join(lines)


def format_firewall_rules(rules) -> str:
    """Firewall kural listesi."""
    if not rules:
        return info_box("Henüz firewall kuralı tanimlanmamis.")
    lines = [section_header("Firewall Kuralları", "🔥"), ""]
    for r in rules:
        status = "✅" if r.enabled else "❌"
        proto = r.protocol.value if hasattr(r.protocol, "value") else r.protocol
        direction = r.direction.value if hasattr(r.direction, "value") else r.direction
        action = r.action.value if hasattr(r.action, "value") else r.action
        port_str = f"{r.port}" + (f"-{r.port_end}" if r.port_end else "")
        lines.append(
            f"  {status} `#{r.id}` **{r.name}** — "
            f"Port {port_str}/{proto} | {direction} | {action}"
        )
    lines.extend(["", separator()])
    return "\n".join(lines)


def format_help() -> str:
    """Yardim mesaji."""
    lines = [
        "👋 **TonbilAi Asistan**",
        separator(),
        "",
        "🌐 **Site Engelleme**",
        "  `facebook engelle` · `youtube ve netflix kapat`",
        "",
        "📱 **Cihaz Engelleme**",
        "  `babamin telefonunda youtube engelle` · `tablette tiktok kapat`",
        "",
        "📱 **Cihaz Yönetimi**",
        "  `babamin telefonunu engelle` · `cihazlari goster`",
        "",
        "🏷️ **Cihaz Isimlendirme**",
        "  `192.168.1.8 babamin telefonu olsun`",
        "",
        "🔍 **Cihaz Arama**",
        "  `babamin telefonu hangisi` · `su IP kimin`",
        "",
        "📌 **IP Sabitle**",
        "  `192.168.1.40 IP sabitle`",
        "",
        "👤 **Profil Atama**",
        "  `tableti çocuk profiline ata` · `profilleri goster`",
        "",
        "🔥 **Firewall**",
        "  `port 8080 ac` · `port 23 kapat`",
        "  `firewall kurallarini goster` · `kural #5 sil`",
        "  `kural #3 kapat` · `port 443 tcp accept kuralı ekle`",
        "",
        "🌍 **VPN**",
        "  `almanya vpn baglan` · `vpn durumu`",
        "",
        "🏷️ **Kategoriler**",
        "  `kumar kategorisini engelle`",
        "",
        "📊 **Bilgi**",
        "  `sistem durumu` · `dns istatistikleri`",
        "",
        "📋 **Log Sorgulama**",
        "  `bugunun loglari` · `en cok engellenen domainler`",
        "",
        "📊 **Dashboard & Trafik**",
        "  `dashboard özeti` · `canlı trafik` · `büyük transferler`",
        "",
        "🛡️ **DDoS Koruma**",
        "  `ddos durumu`",
        "",
        "🔧 **DHCP**",
        "  `dhcp kiralamaları` · `ip rezervasyonu yap`",
        "",
        "👤 **Profil Yönetimi**",
        "  `profil oluştur` · `profil sil`",
        "",
        "📂 **Kategoriler**",
        "  `kategorileri listele`",
        "",
        "⚙️ **Sistem**",
        "  `sistemi yeniden başlat`",
        "",
        separator(),
        info_box("Birden fazla işlemi tek seferde: `facebook, instagram ve tiktok engelle`"),
    ]
    return "\n".join(lines)


def format_greeting(online: int, alias_count: int) -> str:
    """Selamlama."""
    lines = [
        "👋 Merhaba! Ben **TonbilAi Router** asistaniyim.",
        "",
        f"📡 Agda **{online}** cihaz çevrimiçi.",
    ]
    if alias_count > 0:
        lines.append(f"🏷️ Kayıtlı **{alias_count}** cihaz takma adi var.")
    lines.append("")
    lines.append(info_box("`yardim` yazarak tum yeteneklerimi görebilirsin"))
    return "\n".join(lines)


def _format_bytes(b: int | float) -> str:
    """Byte degerini okunabilir formata donustur."""
    if b is None:
        return "0 B"
    b = float(b)
    if b < 1024:
        return f"{b:.0f} B"
    elif b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    elif b < 1024 ** 3:
        return f"{b / (1024 ** 2):.1f} MB"
    else:
        return f"{b / (1024 ** 3):.2f} GB"


def format_dashboard_summary(data: dict) -> str:
    """
    Dashboard ozet bilgileri.
    data: {"total_devices", "online_devices", "blocked_devices",
           "dns_queries_24h", "dns_blocked_24h",
           "bandwidth_download", "bandwidth_upload",
           "top_domains": [{"domain", "count"}]}
    """
    lines = [
        "📊 **Dashboard Özeti**",
        separator(),
        "",
        "📡 **Ag**",
        stat_line_extra("Cihaz", data.get("total_devices", 0),
                        f"{data.get('online_devices', 0)} çevrimiçi, {data.get('blocked_devices', 0)} engelli"),
        "",
        "🛡️ **DNS (Son 24 Saat)**",
        stat_line("Toplam sorgu", data.get("dns_queries_24h", 0)),
        stat_line("Engellenen", data.get("dns_blocked_24h", 0)),
        "",
        "📶 **Bant Genişliği**",
        stat_line("İndirme", _format_bytes(data.get("bandwidth_download", 0)) + "/s"),
        stat_line("Yükleme", _format_bytes(data.get("bandwidth_upload", 0)) + "/s"),
    ]

    top_domains = data.get("top_domains", [])
    if top_domains:
        lines.append("")
        lines.append("🔝 **En Çok Sorgulanan (Top 5)**")
        for i, d in enumerate(top_domains[:5], 1):
            lines.append(f"  {i}. `{d['domain']}` — **{d['count']}** sorgu")

    lines.append(separator())
    return "\n".join(lines)


def format_live_flows(flows: list[dict], total: int) -> str:
    """
    Canlı akış listesi.
    flows: [{"direction", "device_name", "dest_ip", "dest_port", "bytes_total",
             "service_name", "app_name", "state"}]
    """
    lines = [
        f"🌊 **Canlı Trafik Akışları** — {total} aktif bağlantı",
        separator(),
    ]

    for f in flows[:15]:
        direction = f.get("direction", "outbound")
        arrow = "⬆️" if direction == "outbound" else "⬇️"
        device = f.get("device_name", "?")
        dest = f.get("dest_ip", "?")
        port = f.get("dest_port", "")
        size = _format_bytes(f.get("bytes_total", 0))
        app = f.get("app_name") or f.get("service_name") or ""
        app_text = f" [{app}]" if app else ""

        lines.append(f"  {arrow} **{device}** → `{dest}:{port}` — {size}{app_text}")

    if total > 15:
        lines.append(f"  _... ve {total - 15} akış daha_")

    lines.append(separator())
    return "\n".join(lines)


def format_large_transfers(flows: list[dict]) -> str:
    """
    >1MB büyük transferler listesi.
    flows: [{"device_name", "dest_ip", "dest_port", "bytes_total", "app_name", "service_name"}]
    """
    if not flows:
        return info_box("Şu anda büyük transfer (>1MB) bulunmuyor.")

    lines = [
        f"📦 **Büyük Transferler** — {len(flows)} adet (>1MB)",
        separator(),
    ]

    for f in flows[:10]:
        device = f.get("device_name", "?")
        dest = f.get("dest_ip", "?")
        size = _format_bytes(f.get("bytes_total", 0))
        app = f.get("app_name") or f.get("service_name") or ""
        app_text = f" [{app}]" if app else ""
        lines.append(f"  · **{device}** → `{dest}` — **{size}**{app_text}")

    if len(flows) > 10:
        lines.append(f"  _... ve {len(flows) - 10} transfer daha_")

    lines.append(separator())
    return "\n".join(lines)


def format_device_traffic_summary(data: dict) -> str:
    """
    Tek cihaz trafik özeti.
    data: {"device_name", "active_flows", "total_bytes",
           "top_destinations": [{"dest_ip", "bytes_total", "app_name"}]}
    """
    lines = [
        f"📱 **{data.get('device_name', '?')} — Trafik Özeti**",
        separator(),
        "",
        stat_line("Aktif bağlantı", data.get("active_flows", 0)),
        stat_line("Toplam veri", _format_bytes(data.get("total_bytes", 0))),
    ]

    top_dests = data.get("top_destinations", [])
    if top_dests:
        lines.append("")
        lines.append("**En çok trafik:**")
        for d in top_dests[:5]:
            app = d.get("app_name") or ""
            app_text = f" [{app}]" if app else ""
            lines.append(f"  · `{d['dest_ip']}` — {_format_bytes(d.get('bytes_total', 0))}{app_text}")

    lines.append(separator())
    return "\n".join(lines)


def format_ddos_status(data: dict) -> str:
    """
    DDoS koruma durumu.
    data: {"enabled", "total_drops", "active_blocks", "last_attack_time",
           "blocked_ips": [{"ip", "reason", "drops"}]}
    """
    enabled = data.get("enabled", False)
    status_text = "Aktif" if enabled else "Kapalı"
    status_icon = "🟢" if enabled else "🔴"

    lines = [
        "🛡️ **DDoS Koruma Durumu**",
        separator(),
        "",
        stat_line("Durum", f"{status_icon} {status_text}", bold_value=False),
        stat_line("Toplam drop", data.get("total_drops", 0)),
        stat_line("Aktif engel", data.get("active_blocks", 0)),
        stat_line("Son saldırı", data.get("last_attack_time") or "Yok", bold_value=False),
    ]

    blocked_ips = data.get("blocked_ips", [])
    if blocked_ips:
        lines.append("")
        lines.append("**Engellenen IP'ler:**")
        for b in blocked_ips[:5]:
            lines.append(f"  · `{b['ip']}` — {b.get('reason', '?')} ({b.get('drops', 0)} drop)")

    lines.append(separator())
    return "\n".join(lines)


def format_dhcp_leases_list(leases: list[dict], static: int, total: int) -> str:
    """
    DHCP kiralama listesi.
    leases: [{"ip", "mac", "hostname", "is_static", "expires"}]
    """
    lines = [
        f"🔧 **DHCP Kiralamaları** — {total} aktif ({static} statik)",
        separator(),
    ]

    for l in leases[:20]:
        static_icon = "📌" if l.get("is_static") else "🔄"
        hostname = l.get("hostname") or "—"
        lines.append(f"  {static_icon} `{l.get('ip', '?')}` — {l.get('mac', '?')} — {hostname}")

    if total > 20:
        lines.append(f"  _... ve {total - 20} kiralama daha_")

    lines.append(separator())
    return "\n".join(lines)


def format_category_list(categories: list[dict]) -> str:
    """
    İçerik kategorileri listesi.
    categories: [{"key", "name", "domain_count", "enabled"}]
    """
    lines = [
        f"📂 **İçerik Kategorileri** — {len(categories)} adet",
        separator(),
    ]

    for c in categories:
        enabled = "✅" if c.get("enabled") else "❌"
        count = c.get("domain_count", 0)
        lines.append(f"  {enabled} **{c.get('name', '?')}** (`{c.get('key', '')}`) — {count} domain")

    lines.append(separator())
    return "\n".join(lines)


def format_device_dns_queries(queries: list[dict], device_name: str) -> str:
    """
    Cihazın son DNS sorguları.
    queries: [{"domain", "timestamp", "blocked", "reason"}]
    """
    lines = [
        f"🔍 **{device_name} — Son DNS Sorguları**",
        separator(),
    ]

    if not queries:
        lines.append("  Henüz sorgu kaydı yok.")
    else:
        for q in queries[:20]:
            icon = "🔴" if q.get("blocked") else "🟢"
            ts = q.get("timestamp", "")
            reason = f" ({q['reason']})" if q.get("reason") else ""
            lines.append(f"  {icon} `{q.get('domain', '?')}` — {ts}{reason}")

        if len(queries) > 20:
            lines.append(f"  _... ve {len(queries) - 20} sorgu daha_")

    lines.append(separator())
    return "\n".join(lines)


def format_reboot_confirmation() -> str:
    """Reboot onay mesajı."""
    lines = [
        "⚠️ **Sistem Yeniden Başlatma**",
        separator(),
        "",
        "Bu işlem tüm bağlantıları kesecek ve ~30 saniye sürecektir.",
        "",
        "Onaylamak için **\"evet, reboot yap\"** yazın.",
        "İptal etmek için **\"iptal\"** yazın.",
        "",
        warning_box("Bu işlem geri alinamaz!"),
    ]
    return "\n".join(lines)


def format_profile_detail(name: str, action: str, bw: float | None = None, device_count: int = 0) -> str:
    """
    Profil oluşturma/güncelleme/silme sonucu.
    action: "oluşturuldu", "güncellendi", "silindi"
    """
    bw_text = f"{bw} Mbps" if bw else "Sınırsız"
    lines = [
        result_badge(True, f"Profil **{name}** {action}"),
    ]
    if action != "silindi":
        lines.append(stat_line("Bant genişliği", bw_text))
        if device_count:
            lines.append(stat_line("Bağlı cihaz", device_count))
    return "\n".join(lines)


def format_service_usage(service_name: str, device_map: dict[str, dict]) -> str:
    """
    Servisi kullanan cihazlar listesi.
    device_map: {device_name: {"flows": int, "bytes_up": int, "bytes_down": int}}
    """
    title = service_name.capitalize()
    lines = [
        f"🎬 **{title} Kullanan Cihazlar**",
        separator(),
        "",
    ]

    # Toplam byte'a göre sırala (büyükten küçüğe)
    sorted_devices = sorted(
        device_map.items(),
        key=lambda x: x[1]["bytes_up"] + x[1]["bytes_down"],
        reverse=True,
    )

    total_flows = 0
    for dname, info in sorted_devices:
        total_bytes = info["bytes_up"] + info["bytes_down"]
        total_flows += info["flows"]
        icon = "📱" if "telefon" in dname.lower() or "phone" in dname.lower() else "💻"
        lines.append(f"{icon} **{dname}**")
        lines.append(f"     ├─ {info['flows']} aktif bağlantı")
        lines.append(f"     ├─ Toplam: {_format_bytes(total_bytes)}")
        lines.append(f"     └─ ⬆️ {_format_bytes(info['bytes_up'])}  ⬇️ {_format_bytes(info['bytes_down'])}")
        lines.append("")

    lines.append(separator())
    lines.append(f"📊 Toplam: **{len(device_map)}** cihaz, **{total_flows}** bağlantı")

    return "\n".join(lines)


def format_service_not_found(service_name: str) -> str:
    """Servis kullanan cihaz bulunamadı mesajı."""
    title = service_name.capitalize()
    lines = [
        f"📡 Şu anda **{title}** kullanan cihaz bulunamadı.",
        "",
        info_box("Cihaz bağlı değilse veya servis aktif kullanılmıyorsa trafik görünmez."),
    ]
    return "\n".join(lines)


def format_unknown() -> str:
    """Anlasilamayan komut."""
    lines = [
        "❓ Tam olarak ne yapmami istedigini anlayamadim.",
        "",
        "**Birkac örnek:**",
        "  · `facebook engelle`",
        "  · `babamin telefonunu engelle`",
        "  · `cihazlari goster`",
        "  · `sistem durumu`",
        "",
        info_box("`yardim` yazarak tum komutlari görebilirsin"),
    ]
    return "\n".join(lines)


# =====================================================================
# Telegram Özel Formatcilar (HTML)
# =====================================================================

def _telegram_separator() -> str:
    return "\u2500" * 20


def format_device_list_telegram(devices: list[dict]) -> str:
    """Telegram için okunakli HTML formatli cihaz listesi."""
    online = sum(1 for d in devices if d.get("is_online"))
    blocked = sum(1 for d in devices if d.get("is_blocked"))

    lines = [
        f"\U0001f4e1 <b>Ag Cihazlari</b> \u2014 {len(devices)} cihaz, {online} çevrimiçi",
        _telegram_separator(),
        "",
    ]

    for d in devices:
        status = "\U0001f7e2" if d.get("is_online") else "\U0001f534"
        name = d.get("hostname") or "Bilinmeyen"
        ip = d.get("ip", "")
        blocked_icon = " \u26d4" if d.get("is_blocked") else ""

        # Satır 1: durum + isim + engelli mi
        lines.append(f"{status} <b>{name}</b>{blocked_icon}")

        # Satır 2: IP + uretici + profil + alias
        detail_parts = [f"    <code>{ip}</code>"]
        if d.get("manufacturer"):
            detail_parts.append(d["manufacturer"])
        if d.get("profile_name"):
            detail_parts.append(f"[{d['profile_name']}]")
        if d.get("alias_name"):
            detail_parts.append(f"({d['alias_name']})")

        lines.append(" \u00b7 ".join(detail_parts))
        lines.append("")  # bos satir (cihazlar arasi bosluk)

    lines.append(_telegram_separator())
    if blocked:
        lines.append(f"\u26d4 {blocked} engelli cihaz")

    return "\n".join(lines)


def _strip_json_from_text(text: str) -> str:
    """Metin icindeki JSON bloklarini temizle."""
    import re as _re
    import json as _json

    stripped = text.strip()

    # Eger tum metin JSON ise, reply alanini cikar
    if stripped.startswith(("{", "[")):
        try:
            data = _json.loads(stripped)
            if isinstance(data, dict) and "reply" in data:
                return data["reply"]
            if isinstance(data, list) and data and isinstance(data[0], dict):
                replies = [d.get("reply", "") for d in data if isinstance(d, dict) and d.get("reply")]
                if replies:
                    return "\n".join(replies)
        except (ValueError, _json.JSONDecodeError):
            # Regex ile reply cikar
            m = _re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)"', stripped)
            if m:
                return m.group(1).replace("\\n", "\n").replace('\\"', '"')

    # ```json ... ``` bloklarini sil
    result = _re.sub(r'```(?:json)?\s*\n?\{[\s\S]*?\}\s*```', '', text)
    result = _re.sub(r'```(?:json)?\s*\n?\[[\s\S]*?\]\s*```', '', result)

    return result.strip() or text


def markdown_to_telegram_html(text: str) -> str:
    """Markdown formatli metni Telegram HTML'e donustur."""
    import re as _re
    import html as _html

    # Oncelikle JSON artiklari temizle
    result = _strip_json_from_text(text)

    # HTML ozel karakterleri kacisla (< > &)
    result = _html.escape(result)

    # Markdown -> HTML donusumleri (escape sonrasi, cunku tag ekliyoruz)
    # **bold** -> <b>bold</b>
    result = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result)

    # `code` -> <code>code</code>
    result = _re.sub(r"`(.+?)`", r"<code>\1</code>", result)

    # _italic_ -> <i>italic</i> (tek alt çizgi, bas/son)
    result = _re.sub(r"(?<![\w])_([^_]+?)_(?![\w])", r"<i>\1</i>", result)

    return result
