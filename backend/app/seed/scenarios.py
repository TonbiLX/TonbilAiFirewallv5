# --- Ajan: MUHAFIZ (THE GUARDIAN) + ANALIST (THE ANALYST) ---
# Faz 1 + Faz 2 seed verileri için test senaryo tanimlari.
# Gercekci aile agi simulasyonu, güvenlik test vakalari,
# DNS engelleme listeleri ve DHCP havuz konfigurasyonlari.

PROFILES = [
    {
        "name": "Yetişkin - Ebeveyn",
        "profile_type": "adult",
        "allowed_hours": {"start": "00:00", "end": "23:59"},
        "content_filters": [],
        "bandwidth_limit_mbps": None,
    },
    {
        "name": "Çocuk - Elif (10 yas)",
        "profile_type": "child",
        "allowed_hours": {"start": "08:00", "end": "21:00"},
        "content_filters": ["gambling", "adult", "malicious", "social"],
        "bandwidth_limit_mbps": 20,
    },
    {
        "name": "Çocuk - Ahmet (14 yas)",
        "profile_type": "child",
        "allowed_hours": {"start": "07:00", "end": "22:00"},
        "content_filters": ["gambling", "adult", "malicious"],
        "bandwidth_limit_mbps": 50,
    },
    {
        "name": "Misafir",
        "profile_type": "guest",
        "allowed_hours": {"start": "08:00", "end": "23:00"},
        "content_filters": ["gambling", "adult", "malicious"],
        "bandwidth_limit_mbps": 10,
    },
]

DEVICES = [
    {
        "mac": "AA:BB:CC:DD:EE:01", "ip": "192.168.1.101",
        "hostname": "Ahmet-iPhone", "manufacturer": "Apple",
        "profile_name": "Çocuk - Ahmet (14 yas)",
    },
    {
        "mac": "AA:BB:CC:DD:EE:02", "ip": "192.168.1.102",
        "hostname": "Elif-Tablet", "manufacturer": "Samsung",
        "profile_name": "Çocuk - Elif (10 yas)",
    },
    {
        "mac": "AA:BB:CC:DD:EE:03", "ip": "192.168.1.103",
        "hostname": "SmartTV-Salon", "manufacturer": "LG",
        "profile_name": "Yetişkin - Ebeveyn",
    },
    {
        "mac": "AA:BB:CC:DD:EE:04", "ip": "192.168.1.104",
        "hostname": "Baba-Laptop", "manufacturer": "Lenovo",
        "profile_name": "Yetişkin - Ebeveyn",
    },
    {
        "mac": "AA:BB:CC:DD:EE:05", "ip": "192.168.1.105",
        "hostname": "IoT-AkilliBulb-01", "manufacturer": "Philips",
        "profile_name": "Yetişkin - Ebeveyn",
    },
    {
        "mac": "AA:BB:CC:DD:EE:06", "ip": "192.168.1.106",
        "hostname": "Misafir-Telefon", "manufacturer": "Xiaomi",
        "profile_name": "Misafir",
    },
    {
        "mac": "AA:BB:CC:DD:EE:07", "ip": "192.168.1.107",
        "hostname": "Anne-PC", "manufacturer": "Dell",
        "profile_name": "Yetişkin - Ebeveyn",
    },
    {
        "mac": "AA:BB:CC:DD:EE:08", "ip": "192.168.1.108",
        "hostname": "Çocuk-Tablet", "manufacturer": "Amazon",
        "profile_name": "Çocuk - Elif (10 yas)",
    },
]

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Güvenlik test senaryolari: sistemin tespit etmesi gereken tehdit kosullari
SECURITY_SCENARIOS = [
    {
        "description": "Çocuk cihazi kumar sitesine erisme girişimi",
        "device_hostname": "Elif-Tablet",
        "domain": "kumar-sitesi.bet",
        "category": "gambling",
        "expected_severity": "critical",
    },
    {
        "description": "IoT cihazi C2 sunucusuna bağlantı (botnet göstergesi)",
        "device_hostname": "IoT-AkilliBulb-01",
        "domain": "malware-c2.evil",
        "category": "malicious",
        "expected_severity": "critical",
    },
    {
        "description": "Misafir cihaz asiri bant genisligi kullanımi",
        "device_hostname": "Misafir-Telefon",
        "domain": "torrent-site.org",
        "category": "p2p",
        "expected_severity": "warning",
    },
    {
        "description": "Gece saatlerinde çocuk cihaz aktivitesi",
        "device_hostname": "Çocuk-Tablet",
        "domain": "tiktok.com",
        "category": "social",
        "expected_severity": "warning",
    },
]

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Faz 2: Varsayilan blocklist tanimlari
DEFAULT_BLOCKLISTS = [
    {
        "name": "AdGuard DNS Filter",
        "url": "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt",
        "description": "AdGuard temel reklam ve izleyici engelleme listesi",
        "format": "adblock",
        "enabled": True,
        "update_frequency_hours": 24,
    },
    {
        "name": "Steven Black Unified",
        "url": "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts",
        "description": "Reklam + zararli yazilim birlesik hosts dosyasi",
        "format": "hosts",
        "enabled": True,
        "update_frequency_hours": 48,
    },
    {
        "name": "TonbilAi Çocuk Koruma",
        "url": "https://tonbilai.local/lists/child-protection.txt",
        "description": "TonbilAi özel çocuk koruma listesi (kumar, yetişkin, suc)",
        "format": "domain_list",
        "enabled": True,
        "update_frequency_hours": 168,
    },
    {
        "name": "Reklam ve Izleyici Engelleme",
        "url": "https://raw.githubusercontent.com/anudeepND/blacklist/master/adservers.txt",
        "description": "Reklam sunucusu ve izleyici engelleme listesi",
        "format": "hosts",
        "enabled": False,
        "update_frequency_hours": 24,
    },
]

# Varsayilan özel DNS kurallari
DEFAULT_DNS_RULES = [
    {
        "domain": "kumar-sitesi.bet",
        "rule_type": "block",
        "reason": "Kumar içerik - tum profiller için engellendi",
        "profile_name": None,
    },
    {
        "domain": "malware-c2.evil",
        "rule_type": "block",
        "reason": "Bilinen zararli yazilim C2 sunucusu",
        "profile_name": None,
    },
    {
        "domain": "school-portal.edu.tr",
        "rule_type": "allow",
        "reason": "Egitim portali - her zaman erişime açık",
        "profile_name": None,
    },
]

# --- Ajan: MIMAR (THE ARCHITECT) ---
# Faz 2: Varsayilan DHCP havuz tanimlari
DEFAULT_DHCP_POOLS = [
    {
        "name": "Ana AG",
        "subnet": "192.168.1.0",
        "netmask": "255.255.255.0",
        "range_start": "192.168.1.100",
        "range_end": "192.168.1.200",
        "gateway": "192.168.1.1",
        "dns_servers": ["192.168.1.1"],
        "lease_time_seconds": 86400,
        "enabled": True,
    },
    {
        "name": "Misafir AG",
        "subnet": "192.168.1.0",
        "netmask": "255.255.255.0",
        "range_start": "192.168.1.201",
        "range_end": "192.168.1.250",
        "gateway": "192.168.1.1",
        "dns_servers": ["192.168.1.1"],
        "lease_time_seconds": 3600,
        "enabled": True,
    },
]

# Statik IP atamalari
DEFAULT_STATIC_LEASES = [
    {"hostname": "SmartTV-Salon", "mac": "AA:BB:CC:DD:EE:03", "ip": "192.168.1.103"},
    {"hostname": "Baba-Laptop", "mac": "AA:BB:CC:DD:EE:04", "ip": "192.168.1.104"},
    {"hostname": "Anne-PC", "mac": "AA:BB:CC:DD:EE:07", "ip": "192.168.1.107"},
]

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Faz 2.5: Varsayilan Firewall kurallari
DEFAULT_FIREWALL_RULES = [
    {
        "name": "SSH Erisimi",
        "description": "SSH bağlantısina sadece yerel agdan izin ver",
        "direction": "inbound", "protocol": "tcp", "port": 22,
        "source_ip": "192.168.1.0/24", "action": "accept",
        "enabled": True, "priority": 10,
    },
    {
        "name": "HTTP/HTTPS Erisimine Izin",
        "description": "Web trafiğine izin ver",
        "direction": "outbound", "protocol": "tcp", "port": 80, "port_end": 443,
        "action": "accept", "enabled": True, "priority": 20,
    },
    {
        "name": "DNS Erisimine Izin",
        "description": "DNS sorgularina izin ver",
        "direction": "outbound", "protocol": "both", "port": 53,
        "action": "accept", "enabled": True, "priority": 15,
    },
    {
        "name": "WireGuard VPN Portu",
        "description": "VPN bağlantılari için WireGuard portu",
        "direction": "inbound", "protocol": "udp", "port": 51820,
        "action": "accept", "enabled": True, "priority": 5,
    },
    {
        "name": "Telnet Engelle",
        "description": "Guvenli olmayan Telnet bağlantılari engelle",
        "direction": "inbound", "protocol": "tcp", "port": 23,
        "action": "drop", "enabled": True, "priority": 50,
    },
    {
        "name": "ICMP Ping Izin",
        "description": "Ping isteklerine izin ver (ag teshis)",
        "direction": "inbound", "protocol": "icmp",
        "action": "accept", "enabled": True, "priority": 30,
    },
    {
        "name": "IoT Cihaz Disari Erisim Engeli",
        "description": "IoT cihazlarinin bilinmeyen portlara erişimini engelle",
        "direction": "forward", "protocol": "all",
        "source_ip": "192.168.1.105", "action": "drop",
        "enabled": False, "priority": 100, "log_packets": True,
    },
    {
        "name": "Misafir AG Ic Erisim Engeli",
        "description": "Misafir cihazlari yerel ag kaynaklarina erisemesin",
        "direction": "forward", "protocol": "all",
        "source_ip": "192.168.1.201", "dest_ip": "192.168.1.0/24",
        "action": "drop", "enabled": True, "priority": 40,
    },
]

# Faz 2.5: Varsayilan VPN Peer tanimlari
DEFAULT_VPN_PEERS = [
    {
        "name": "Baba-Telefon (Dış Erisim)",
        "allowed_ips": "10.0.0.2/32",
        "dns_servers": "10.0.0.1",
        "persistent_keepalive": 25,
    },
    {
        "name": "Anne-Tablet (Dış Erisim)",
        "allowed_ips": "10.0.0.3/32",
        "dns_servers": "10.0.0.1",
        "persistent_keepalive": 25,
    },
]

# --- Ajan: MUHAFIZ (THE GUARDIAN) ---
# Faz 3: Varsayilan admin kullanıcı
DEFAULT_ADMIN_USER = {
    "username": "admin",
    "password": "admin123",
    "display_name": "Yönetici",
    "is_admin": True,
}

# Faz 3: İçerik filtre kategori tanimlari
DEFAULT_CONTENT_CATEGORIES = [
    {
        "key": "gambling",
        "name": "Kumar Siteleri",
        "description": "Online kumar, bahis ve sans oyunlari sitelerini engeller. Iddaa, casino, poker ve slot oyunlari dahildir.",
        "icon": "Dice5",
        "color": "#ef4444",
        "example_domains": ["bet365.com", "bets10.com", "iddaa.com", "kumar-sitesi.bet"],
        "domain_count": 1250,
    },
    {
        "key": "adult",
        "name": "Yetişkin İçerik",
        "description": "Pornografi ve yetişkinlere yonelik içerik barindiran siteleri engeller. 18+ içerikler dahildir.",
        "icon": "ShieldOff",
        "color": "#dc2626",
        "example_domains": ["adult-content-1.com", "adult-content-2.com"],
        "domain_count": 8500,
    },
    {
        "key": "malicious",
        "name": "Zararli Yazilim",
        "description": "Virus, trojan, ransomware ve phishing siteleri engeller. Botnet C2 sunuculari ve exploit kitleri dahildir.",
        "icon": "Bug",
        "color": "#991b1b",
        "example_domains": ["malware-c2.evil", "phishing-bank.xyz", "ransomware-pay.onion"],
        "domain_count": 45000,
    },
    {
        "key": "social",
        "name": "Sosyal Medya",
        "description": "Sosyal medya platformlarini engeller. TikTok, Instagram, Facebook, Twitter, Snapchat gibi platformlar dahildir.",
        "icon": "Users",
        "color": "#f59e0b",
        "example_domains": ["tiktok.com", "instagram.com", "facebook.com", "twitter.com", "snapchat.com"],
        "domain_count": 350,
    },
    {
        "key": "streaming",
        "name": "Video/Yayin Platformlari",
        "description": "Video izleme ve canlı yayin platformlarini engeller. YouTube, Netflix, Twitch gibi servisler dahildir.",
        "icon": "Tv",
        "color": "#8b5cf6",
        "example_domains": ["youtube.com", "netflix.com", "twitch.tv", "disneyplus.com"],
        "domain_count": 200,
    },
    {
        "key": "gaming",
        "name": "Oyun Siteleri",
        "description": "Online oyun platformlarini ve oyun icerigi barindiran siteleri engeller. Steam, Epic Games, Roblox dahildir.",
        "icon": "Gamepad2",
        "color": "#06b6d4",
        "example_domains": ["store.steampowered.com", "epicgames.com", "roblox.com"],
        "domain_count": 180,
    },
    {
        "key": "ads",
        "name": "Reklamlar ve Izleyiciler",
        "description": "Reklam aglari, izleme pikselleri ve analitik servislerini engeller. Sayfa yuklenme hizi artar, gizlilik korunur.",
        "icon": "Ban",
        "color": "#64748b",
        "example_domains": ["ad.doubleclick.net", "analytics.google.com", "facebook.net"],
        "domain_count": 95000,
    },
]

# Faz 3: Varsayilan Dış VPN Sunuculari (Surfshark ornekleri)
DEFAULT_VPN_CLIENT_SERVERS = [
    {
        "name": "Surfshark Turkiye",
        "country": "Turkiye",
        "country_code": "TR",
        "endpoint": "tr-ist.prod.surfshark.com:51820",
        "public_key": "mock_tr_public_key_base64==",
        "interface_address": "10.14.0.2/16",
        "allowed_ips": "0.0.0.0/0, ::/0",
        "dns_servers": "162.252.172.57, 149.154.159.92",
        "mtu": 1420,
    },
    {
        "name": "Surfshark Almanya",
        "country": "Almanya",
        "country_code": "DE",
        "endpoint": "de-fra.prod.surfshark.com:51820",
        "public_key": "mock_de_public_key_base64==",
        "interface_address": "10.14.0.3/16",
        "allowed_ips": "0.0.0.0/0, ::/0",
        "dns_servers": "162.252.172.57, 149.154.159.92",
        "mtu": 1420,
    },
    {
        "name": "Surfshark ABD",
        "country": "Amerika Birlesik Devletleri",
        "country_code": "US",
        "endpoint": "us-nyc.prod.surfshark.com:51820",
        "public_key": "mock_us_public_key_base64==",
        "interface_address": "10.14.0.4/16",
        "allowed_ips": "0.0.0.0/0, ::/0",
        "dns_servers": "162.252.172.57, 149.154.159.92",
        "mtu": 1420,
    },
]

# ===== FAZ 3.5 v9: YAPAY ZEKA YAPILANDIRMA =====
DEFAULT_AI_CONFIG = {
    "provider": "none",
    "api_key": None,
    "base_url": None,
    "model": None,
    "chat_mode": "tfidf",
    "temperature": 0.3,
    "max_tokens": 1024,
    "log_analysis_enabled": False,
    "log_analysis_interval_minutes": 60,
    "log_analysis_max_logs": 100,
    "daily_request_limit": 200,
    "daily_request_count": 0,
    "custom_system_prompt": None,
    "enabled": False,
}
