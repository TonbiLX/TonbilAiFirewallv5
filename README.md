<h1 align="center">TonbilAiFirewall v5</h1>

<p align="center">
  <strong>Yapay Zeka Destekli Yeni Nesil Router Yonetim Sistemi</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-5.0-blue?style=flat-square" alt="v5.0">
  <img src="https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a?style=flat-square&logo=raspberrypi" alt="Raspberry Pi">
  <img src="https://img.shields.io/badge/frontend-React%2018-61dafb?style=flat-square&logo=react" alt="React">
  <img src="https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/firewall-nftables-orange?style=flat-square" alt="nftables">
  <img src="https://img.shields.io/badge/ai-LLM%20Powered-8B5CF6?style=flat-square" alt="AI">
  <img src="https://img.shields.io/badge/license-Private-red?style=flat-square" alt="License">
</p>

---

## Nedir?

**TonbilAiFirewall v5**, Raspberry Pi uzerinde calisan, yapay zeka destekli bir ag guvenligi ve router yonetim sistemidir.

v5 ile sistem **seffaf kopru (transparent bridge) modundan tam izole router moduna** gecis yapmistir. Modem artik sadece Pi'nin MAC adresini gorur — tum LAN cihazlari modemden tamamen gizlenir ve trafik Pi'nin IP stack'i uzerinden route edilir.

Cyberpunk/glassmorphism temali modern web arayuzu ile tum ag operasyonlarinizi tek bir panelden yonetebilirsiniz.

---

## v5'te Yeni

### Bridge Izolasyon (Router Modu)
- **L2 Forwarding Izolasyonu** — Bridge uzerinde eth0↔eth1 arasi Layer 2 trafik tamamen engellenir
- **NAT/MASQUERADE** — Pi kendi MAC adresi ile modemle iletisim kurar, LAN cihazlari gizlenir
- **Reboot Dayanikli Kalicilik** — sysctl.d, modules-load.d ve nftables.service ile tum yapilandirma reboot sonrasi otomatik uygulanir
- **Guvenli Rollback** — `remove_bridge_isolation()` ile tek komutla seffaf kopru moduna geri donus
- **DHCP Gateway Gecisi** — Gateway .1 (modem) → .2 (Pi) degisikligi, kisa kiralama sureli gecis proseduru

### Gelismis Trafik Izleme (Per-Flow)
- **Conntrack Tabanli Baglanti Takibi** — Her TCP/UDP baglantiyi 20 saniyede bir izler
- **Servis/Uygulama Tespiti** — 40+ port + 80+ domain eslesmesi (WhatsApp, YouTube, Instagram vb.)
- **Buyuk Transfer Algilama** — >1MB flow'lar otomatik isaretlenir
- **3 Sekmeli Trafik Sayfasi** — Canli akislar, buyuk transferler, gecmis kayitlari

### Profil Tabanli DNS Filtreleme
- **Icerik Kategorileri** — Blocklist dosyalari kategorilere baglanir (yetiskin, kumar, reklam vb.)
- **Profil Sistemi** — Cihaz gruplarina ozel filtreleme politikalari + bandwidth limiti
- **Subdomain Yuruyusu** — Alt alan adlari otomatik kontrol edilir
- **Servis Engelleme** — YouTube, Netflix vb. profil bazli bagimsiz engelleme

### Split Chain Mimarisi
- **Ayri Upload/Download Zincirleri** — Accounting ve TC mark chain'leri input/output hook'larina ayrildi
- **Hassas Bant Genisligi Olcumu** — nft reset ile atomik delta sayaclari
- **Per-Device QoS** — HTB qdisc ile cihaz bazli bandwidth limitleme

---

## Tum Ozellikler

### Ag Yonetimi
- **Cihaz Kesfetme ve Yonetimi** — ARP tabanli otomatik cihaz tespiti, hostname cozumleme
- **Gercek Zamanli Bant Genisligi Izleme** — Cihaz bazli upload/download takibi (split chain)
- **DHCP Sunucu Yonetimi** — IP havuzlari, statik kiralamalar, aktif kiralama listesi
- **Per-Flow Trafik Analizi** — Conntrack tabanli baglanti takibi, servis tespiti

### Guvenlik
- **DNS Filtreleme** — 100.000+ domain engelleme listeleri, profil tabanli filtreleme
- **Bridge Izolasyon** — L2 forwarding drop, NAT MASQUERADE, LAN cihaz gizleme
- **Guvenlik Duvari (nftables)** — Kural tabanli trafik kontrolu, port engelleme
- **DDoS Koruma** — Anomali tespiti, otomatik engelleme, canli saldiri haritasi
- **VPN (WireGuard)** — Sunucu ve istemci yonetimi, peer yapilandirma
- **5651 Kanun Uyumu** — 2 yil log saklama, kriptografik log imzalama

### Yapay Zeka
- **AI Sohbet Asistani** — Dogal dilde ag sorulari sorma ve yanitlama
- **Tehdit Analizi** — Trafik paternlerinden anomali tespiti
- **AI Icgoruler** — Ag sagligi raporlari ve oneriler
- **LLM Entegrasyonu** — Coklu LLM saglayici destegi

### Bildirimler ve Profiller
- **Telegram Entegrasyonu** — Anlik guvenlik uyarilari, cihaz bildirimleri
- **Icerik Kategorileri** — Blocklist + ozel domain bazli web icerik filtreleme
- **Profil Yonetimi** — Cihaz gruplari icin filtreleme + bandwidth politikalari

### Dashboard
- **Dinamik Widget Sistemi** — 11 widget, surukle-birak ile yeniden duzenlenebilir
- **Responsive Tasarim** — 4 breakpoint (lg/md/sm/xs), mobil uyumlu
- **Gercek Zamanli Veriler** — WebSocket ile canli guncelleme
- **localStorage Persist** — Layout tercihleri sayfa yenilemelerinde korunur

---

## Ekran Goruntuleri

### Ana Dashboard
> Suruklenebilir widget'lar ile kisisellestirilabilir dashboard. Gercek zamanli bandwidth grafigi, cihaz trafigi tablosu, DNS istatistikleri ve daha fazlasi.

<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="Dashboard" width="900">
</p>

**Dashboard Widget'lari:**
| Widget | Aciklama |
|--------|----------|
| Baglanti Durumu | WebSocket canli veri akisi gostergesi |
| Istatistik Kartlari | Upload, Download, DNS Sorgusu, Engellenen, Cihaz sayisi |
| Bandwidth Grafigi | Gercek zamanli upload/download AreaChart |
| Cihaz Trafigi | Siralanabilir trafik tablosu (hostname, upload, download, toplam) |
| DNS Ozet | Sorgu/dk, engelleme orani, engelli domain sayisi |
| Cihaz Durumu | Toplam, cevrimici, engelli cihaz sayisi |
| VPN Durumu | Sunucu durumu, bagli peer sayisi |
| En Cok Sorgulanan | Top 10 DNS domain |
| En Cok Engellenen | Top 10 engellenen domain |
| Bagli Cihazlar | Online cihaz listesi |
| En Aktif Istemciler | En cok DNS sorgusu yapan IP'ler |

---

<details>
<summary><strong>Diger Ekran Goruntuleri (tiklayarak acin)</strong></summary>

| Sayfa | Goruntu |
|-------|---------|
| Cihaz Yonetimi | <img src="docs/screenshots/devices.png" width="400"> |
| DNS Filtreleme | <img src="docs/screenshots/dns-blocking.png" width="400"> |
| DDoS Saldiri Haritasi | <img src="docs/screenshots/ddos-map.png" width="400"> |
| VPN Yonetimi | <img src="docs/screenshots/vpn.png" width="400"> |
| AI Sohbet | <img src="docs/screenshots/ai-chat.png" width="400"> |
| Guvenlik Duvari | <img src="docs/screenshots/firewall.png" width="400"> |
| Trafik Analizi | <img src="docs/screenshots/traffic.png" width="400"> |
| DHCP Yonetimi | <img src="docs/screenshots/dhcp.png" width="400"> |
| Sistem Monitoru | <img src="docs/screenshots/system-monitor.png" width="400"> |
| Profiller | <img src="docs/screenshots/profiles.png" width="400"> |
| Icerik Kategorileri | <img src="docs/screenshots/content-categories.png" width="400"> |
| Telegram Bildirimleri | <img src="docs/screenshots/telegram.png" width="400"> |
| Giris Ekrani | <img src="docs/screenshots/login.png" width="400"> |

</details>

---

## Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                     Raspberry Pi (Router Modu)               │
│                                                              │
│  ┌────────────────────────────────────────────────────┐      │
│  │  br0 = eth0 (WAN/Modem) + eth1 (LAN/Switch)       │      │
│  │  L2 Forward DROP (izolasyon) + NAT MASQUERADE      │      │
│  └────────────────────────────────────────────────────┘      │
│                          │                                    │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │  Nginx   │───▶│   FastAPI    │───▶│    MariaDB      │    │
│  │ (Reverse │    │   Backend    │    │   (Veritabani)  │    │
│  │  Proxy)  │    │  :8000       │    │   :3306         │    │
│  │ :80/:443 │    │              │    └─────────────────┘    │
│  └──────────┘    │  Workers:    │    ┌─────────────────┐    │
│       │          │  - DNS Proxy │───▶│     Redis       │    │
│       │          │  - Bandwidth │    │   (Cache)       │    │
│       ▼          │  - Device    │    │   :6379         │    │
│  ┌──────────┐    │  - Flow Track│    └─────────────────┘    │
│  │ Frontend │    │  - DDoS      │                            │
│  │ (React)  │    │  - Telegram  │    ┌─────────────────┐    │
│  │ Static   │    │  - AI Engine │───▶│   nftables      │    │
│  │ dist/    │    │  - Traffic   │    │  bridge filter   │    │
│  └──────────┘    │  - DHCP      │    │  bridge account  │    │
│                  └──────────────┘    │  inet tonbilai   │    │
│                         │            │  inet nat        │    │
│                         ▼            └─────────────────┘    │
│                  ┌──────────────┐    ┌─────────────────┐    │
│                  │  WebSocket   │    │   WireGuard     │    │
│                  │  (Canli      │    │   (VPN)         │    │
│                  │   Veri)      │    │                 │    │
│                  └──────────────┘    └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### nftables Zincir Yapisi (v5)

```
bridge filter forward     → L2 izolasyon (eth0↔eth1 drop)
bridge accounting upload   → input hook, iifname eth1, ether saddr MAC → byte sayaci
bridge accounting download → output hook, oifname eth1, ether daddr MAC → byte sayaci
bridge tc_mark_up          → input hook, iifname eth1, ether saddr MAC → meta mark
bridge tc_mark_down        → output hook, oifname eth1, ether daddr MAC → meta mark
inet tonbilai              → MAC bazli cihaz engelleme
inet nat                   → MASQUERADE (postrouting)
```

### Teknoloji Yigini

| Katman | Teknoloji | Versiyon |
|--------|-----------|----------|
| **Frontend** | React + TypeScript | 18.3 + 5.6 |
| **Build** | Vite | 6.0 |
| **Stil** | TailwindCSS | 3.4 |
| **Grid** | react-grid-layout | 2.2 |
| **Grafikler** | Recharts | 2.13 |
| **Ikonlar** | Lucide React | 0.460 |
| **Backend** | FastAPI + uvicorn | 0.115 + 0.32 |
| **ORM** | SQLAlchemy (async) | 2.0 |
| **Veritabani** | MariaDB | 10.x |
| **Cache** | Redis | 5.2+ |
| **Firewall** | nftables (bridge + inet) | - |
| **VPN** | WireGuard | - |
| **DNS** | Ozel DNS Proxy (profil tabanli) | - |
| **DHCP** | dnsmasq | - |
| **Trafik** | conntrack (per-flow) | - |

---

## Gereksinimler

### Donanim
- Raspberry Pi 4/5 (4GB+ RAM onerilen)
- SD kart veya USB SSD (32GB+)
- **2 Ethernet portu** (eth0: WAN/Modem, eth1: LAN/Switch) — USB Ethernet dongle veya hat switch

### Yazilim
- Raspberry Pi OS Bookworm (Debian 12 tabanli)
- Python 3.11+
- Node.js 18+
- MariaDB 10.x
- Redis 6+
- Nginx
- nftables, dnsmasq, conntrack-tools

---

## Hizli Kurulum

```bash
# 1. Repo'yu klonlayin
git clone https://github.com/TonbiLX/TonbilAiFirewallv5.git /opt/tonbilaios

# 2. Kurulumu baslatın
cd /opt/tonbilaios
sudo bash setup.sh
```

Script otomatik olarak:
- Tum sistem paketlerini kurar (Python, Node.js, MariaDB, Redis, Nginx, nftables, WireGuard)
- MariaDB veritabanini ve kullaniciyi olusturur
- Python sanal ortam ve bagimliliklari kurar
- Frontend'i build eder
- `.env` dosyasini guvenli varsayilanlarla olusturur
- systemd servisini yapilandirir ve baslatir
- Nginx reverse proxy'yi yapilandirir
- Bridge izolasyon kalicilik dosyalarini yazar (sysctl.d, modules-load.d, nftables.service)

---

## Manuel Kurulum

<details>
<summary><strong>Adim adim kurulum (tiklayarak acin)</strong></summary>

### 1. Sistem Paketleri

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev \
    mariadb-server mariadb-client libmariadb-dev \
    redis-server nginx nftables dnsmasq \
    wireguard wireguard-tools conntrack \
    curl wget git build-essential libffi-dev libssl-dev
```

Node.js 20.x kurulumu:
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt install -y nodejs
```

### 2. Veritabani

```bash
sudo systemctl enable mariadb --now

sudo mysql -u root <<EOF
CREATE DATABASE tonbilaios CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'tonbilai'@'localhost' IDENTIFIED BY 'GUCLU_SIFRE';
GRANT ALL PRIVILEGES ON tonbilaios.* TO 'tonbilai'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### 3. Backend

```bash
cd /opt/tonbilaios/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
nano .env  # DATABASE_URL, SECRET_KEY vb. duzenleyin
```

### 4. Frontend

```bash
cd /opt/tonbilaios/frontend
npm install
npm run build
```

### 5. systemd Servisi

```bash
sudo cp /opt/tonbilaios/config/tonbilaios.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tonbilaios --now
```

### 6. Nginx

```bash
sudo cp /opt/tonbilaios/config/nginx-tonbilaios.conf /etc/nginx/sites-available/tonbilaios
sudo ln -sf /etc/nginx/sites-available/tonbilaios /etc/nginx/sites-enabled/tonbilaios
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

</details>

---

## Servis Yonetimi

```bash
# Backend servisi
sudo systemctl start tonbilaios-backend
sudo systemctl stop tonbilaios-backend
sudo systemctl restart tonbilaios-backend
sudo systemctl status tonbilaios-backend

# Loglar
sudo journalctl -u tonbilaios-backend -f

# Bridge izolasyon durumu
sudo nft list chain bridge filter forward
sudo sysctl net.ipv4.ip_forward
sudo sysctl net.bridge.bridge-nf-call-iptables
```

---

## API Dokumantasyonu

Backend calisirken Swagger UI'a erisin:
- **Swagger UI:** `http://<PI_IP>/docs`
- **ReDoc:** `http://<PI_IP>/redoc`

---

## Guvenlik Notlari

- `.env` dosyasi **asla** Git'e eklenmemeli
- Uretim ortaminda `SECRET_KEY` en az 32 karakter olmali
- Bridge izolasyon aktifken modem sadece Pi'nin MAC adresini gorur
- nftables kurallari `/etc/nftables.conf` uzerinden reboot sonrasi otomatik yuklenir
- sysctl parametreleri `/etc/sysctl.d/99-bridge-isolation.conf` ile kalicidir
- `br_netfilter` modulu `/etc/modules-load.d/99-bridge-isolation.conf` ile boot'ta yuklenir
- 5651 sayili kanun uyumlulugu: Loglar 2 yil boyunca kriptografik imza ile saklanir

---

## Dizin Yapisi

```
/opt/tonbilaios/
├── setup.sh                    # Tek komut kurulum scripti
├── validate.sh                 # Bridge izolasyon dogrulama scripti (9 kontrol)
├── .env.example                # Ortam degiskenleri sablonu
│
├── backend/app/
│   ├── main.py                 # FastAPI uygulama + lifespan (bridge isolation)
│   ├── api/v1/                 # REST API endpoint'ler (25+)
│   ├── models/                 # SQLAlchemy modelleri (28+)
│   ├── schemas/                # Pydantic semalari
│   ├── services/               # Is mantigi (AI, DDoS, Telegram)
│   ├── workers/                # Arka plan islemciler
│   │   ├── dns_proxy.py        # Profil tabanli DNS filtreleme
│   │   ├── bandwidth_monitor.py # Split chain bant genisligi izleme
│   │   ├── flow_tracker.py     # Per-flow baglanti takibi (conntrack)
│   │   └── ...                 # 14+ worker
│   ├── hal/                    # Donanim soyutlama katmani
│   │   ├── linux_nftables.py   # Bridge izolasyon + accounting + TC mark
│   │   ├── linux_tc.py         # QoS / bandwidth limiting
│   │   └── linux_dhcp_driver.py # DHCP sunucu yonetimi
│   └── db/                     # Veritabani baglantisi
│
├── frontend/src/
│   ├── pages/                  # 23 sayfa bileseni
│   ├── components/             # UI bilesenleri (common, layout, dashboard, charts, ddos)
│   ├── hooks/                  # WebSocket, dashboard, DHCP, DNS hook'lari
│   ├── services/               # 20+ API istemcisi
│   └── config/                 # Widget yapilandirmasi (11 widget)
│
└── docs/screenshots/           # Ekran goruntuleri
```

---

<p align="center">
  <sub>TonbilAiFirewall v5 &copy; 2025-2026 TonbiLX. Tum haklari saklidir.</sub>
</p>
