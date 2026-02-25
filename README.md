<h1 align="center">TonbilAiFirewall</h1>

<p align="center">
  <strong>Yapay Zeka Destekli Yeni Nesil Router Yonetim Sistemi</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Raspberry%20Pi-c51a4a?style=flat-square&logo=raspberrypi" alt="Raspberry Pi">
  <img src="https://img.shields.io/badge/frontend-React%2018-61dafb?style=flat-square&logo=react" alt="React">
  <img src="https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/ai-LLM%20Powered-8B5CF6?style=flat-square&logo=openai" alt="AI">
  <img src="https://img.shields.io/badge/license-Private-red?style=flat-square" alt="License">
</p>

---

## Nedir?

**TonbilAiFirewall**, Raspberry Pi uzerinde calisan, yapay zeka destekli bir ag guvenligi ve router yonetim sistemidir. DNS filtreleme, cihaz yonetimi, VPN, DDoS koruma, trafik analizi ve AI tabanli tehdit tespiti gibi kapsamli ozellikler sunar.

Cyberpunk/glassmorphism temali modern web arayuzu ile tum ag operasyonlarinizi tek bir panelden yonetebilirsiniz.

---

## Ozellikler

### Ag Yonetimi
- **Cihaz Kesfetme ve Yonetimi** - ARP tabanli otomatik cihaz tespiti, hostname cozumleme
- **Gercek Zamanli Bant Genisligi Izleme** - Cihaz bazli upload/download takibi
- **DHCP Sunucu Yonetimi** - IP havuzlari, statik kiralamalar, aktif kiralama listesi
- **IP Yonetimi** - Beyaz/kara liste, IP bazli erisim kontrolu

### Guvenlik
- **DNS Filtreleme** - 100.000+ domain engelleme listeleri, otomatik guncelleme
- **Guvenlik Duvari (nftables)** - Kural tabanli trafik kontrolu, port engelleme
- **DDoS Koruma** - Anomali tespiti, otomatik engelleme, canli saldiri haritasi
- **VPN (WireGuard)** - Sunucu ve istemci yonetimi, peer yapilandirma
- **TLS/SSL Yapilandirma** - Sifreleme ayarlari, sertifika yonetimi
- **5651 Kanun Uyumu** - 2 yil log saklama, kriptografik log imzalama

### Yapay Zeka
- **AI Sohbet Asistani** - Dogal dilde ag sorulari sorma ve yanitlama
- **Tehdit Analizi** - Trafik paternlerinden anomali tespiti
- **AI Icgoruler** - Ag sagligi raporlari ve oneriler
- **LLM Entegrasyonu** - Coklu LLM saglayici destegi

### Bildirimler
- **Telegram Entegrasyonu** - Anlik guvenlik uyarilari, cihaz bildirimleri
- **Icerik Kategorileri** - Web icerik filtreleme (yetiskin, kumar, vb.)
- **Profil Yonetimi** - Cihaz gruplari icin ozel guvenlik politikalari

### Dashboard
- **Dinamik Widget Sistemi** - Surukle-birak ile yeniden duzenlenebilir
- **Responsive Tasarim** - Mobil, tablet ve masaustu uyumlu
- **Gercek Zamanli Veriler** - WebSocket ile canli guncelleme
- **Widget Gizle/Goster** - Kisisellestirilabilir gorunum

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

### Cihaz Yonetimi
> Agdaki tum cihazlarin detayli goruntulenmesi, trafik analizi ve bireysel guvenlik ayarlari.

<p align="center">
  <img src="docs/screenshots/devices.png" alt="Cihaz Yonetimi" width="900">
</p>

---

### DNS Filtreleme
> Engelleme listeleri yonetimi, DNS sorgu logları, domain arama ve ozel kurallar.

<p align="center">
  <img src="docs/screenshots/dns-blocking.png" alt="DNS Filtreleme" width="900">
</p>

---

### DDoS Saldiri Haritasi
> Canli saldiri gorselestirmesi, dunya haritasi uzerinde saldiri kaynaklari ve animasyonlu saldiri akisi.

<p align="center">
  <img src="docs/screenshots/ddos-map.png" alt="DDoS Haritasi" width="900">
</p>

---

### VPN Yonetimi (WireGuard)
> VPN sunucu yapilandirmasi, peer ekleme/cikarma, baglanti durumu izleme.

<p align="center">
  <img src="docs/screenshots/vpn.png" alt="VPN Yonetimi" width="900">
</p>

---

### AI Sohbet
> Dogal dilde ag sorulari sorun, yapay zeka ile guvenlik analizi yapin.

<p align="center">
  <img src="docs/screenshots/ai-chat.png" alt="AI Sohbet" width="900">
</p>

---

### Guvenlik Duvari
> nftables tabanli kural yonetimi, DDoS koruma ayarlari, port engelleme.

<p align="center">
  <img src="docs/screenshots/firewall.png" alt="Guvenlik Duvari" width="900">
</p>

---

### Sistem Monitoru
> CPU, RAM, disk ve ag kullanimi gercek zamanli izleme.

<p align="center">
  <img src="docs/screenshots/system-monitor.png" alt="Sistem Monitoru" width="900">
</p>

---

### Giris Ekrani
> Cyberpunk temali guvenli kimlik dogrulama.

<p align="center">
  <img src="docs/screenshots/login.png" alt="Giris Ekrani" width="900">
</p>

---

<details>
<summary><strong>Diger Ekran Goruntuleri (tiklayarak acin)</strong></summary>

| Sayfa | Goruntu |
|-------|---------|
| DHCP Yonetimi | <img src="docs/screenshots/dhcp.png" width="400"> |
| IP Yonetimi | <img src="docs/screenshots/ip-management.png" width="400"> |
| Dis VPN Istemci | <img src="docs/screenshots/vpn-client.png" width="400"> |
| TLS Sifreleme | <img src="docs/screenshots/tls.png" width="400"> |
| Trafik Analizi | <img src="docs/screenshots/traffic.png" width="400"> |
| AI Icgoruler | <img src="docs/screenshots/insights.png" width="400"> |
| Profiller | <img src="docs/screenshots/profiles.png" width="400"> |
| Icerik Kategorileri | <img src="docs/screenshots/content-categories.png" width="400"> |
| Telegram Bildirimleri | <img src="docs/screenshots/telegram.png" width="400"> |
| AI Ayarlari | <img src="docs/screenshots/ai-settings.png" width="400"> |
| Sistem Zamani | <img src="docs/screenshots/system-time.png" width="400"> |
| Hesap Ayarlari | <img src="docs/screenshots/settings.png" width="400"> |
| Sistem Yonetimi | <img src="docs/screenshots/system-management.png" width="400"> |
| Sistem Loglari | <img src="docs/screenshots/system-logs.png" width="400"> |

</details>

---

## Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                     Raspberry Pi                            │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │  Nginx   │───▶│   FastAPI    │───▶│    MariaDB      │   │
│  │ (Reverse │    │   Backend    │    │   (Veritabani)  │   │
│  │  Proxy)  │    │  :8000       │    │   :3306         │   │
│  │ :80/:443 │    │              │    └─────────────────┘   │
│  └──────────┘    │  Workers:    │    ┌─────────────────┐   │
│       │          │  - DNS Proxy │───▶│     Redis       │   │
│       │          │  - Bandwidth │    │   (Cache)       │   │
│       ▼          │  - Device    │    │   :6379         │   │
│  ┌──────────┐    │  - DDoS      │    └─────────────────┘   │
│  │ Frontend │    │  - Telegram  │                           │
│  │ (React)  │    │  - AI Engine │    ┌─────────────────┐   │
│  │ Static   │    │  - Traffic   │───▶│   nftables      │   │
│  │ dist/    │    │  - DHCP      │    │  (Firewall)     │   │
│  └──────────┘    └──────────────┘    └─────────────────┘   │
│                         │                                   │
│                         ▼                                   │
│                  ┌──────────────┐    ┌─────────────────┐   │
│                  │  WebSocket   │    │   WireGuard     │   │
│                  │  (Canli      │    │   (VPN)         │   │
│                  │   Veri)      │    │                 │   │
│                  └──────────────┘    └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
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
| **Firewall** | nftables | - |
| **VPN** | WireGuard | - |
| **DNS** | Ozel DNS Proxy | - |
| **DHCP** | dnsmasq | - |

---

## Gereksinimler

### Donanim
- Raspberry Pi 4/5 (4GB+ RAM onerilen)
- SD kart veya USB SSD (32GB+)
- Ethernet baglantisi

### Yazilim
- Raspberry Pi OS (Debian 11/12 tabanli)
- Python 3.11+
- Node.js 18+
- MariaDB 10.x
- Redis 6+
- Nginx

---

## Hizli Kurulum (Tek Komut)

Raspberry Pi'ye dosyalari kopyalayin ve calistirin:

```bash
# 1. Repo'yu klonlayin
git clone https://github.com/TonbiLX/TonbilAiFirewall.git /opt/tonbilaios

# 2. Kurulumu baslatın
cd /opt/tonbilaios
sudo bash setup.sh
```

Bu kadar! Script otomatik olarak:
- Tum sistem paketlerini kurar (Python, Node.js, MariaDB, Redis, Nginx, nftables, WireGuard)
- MariaDB veritabanini ve kullaniciyi olusturur
- Python sanal ortam ve bagimliliklari kurar
- Frontend'i build eder
- `.env` dosyasini guvenli varsayilanlarla olusturur
- systemd servisini yapilandirir ve baslatir
- Nginx reverse proxy'yi yapilandirir

Kurulum tamamlandiginda asagidaki bilgiler gorunecek:

```
╔══════════════════════════════════════════════════╗
║         Kurulum Basariyla Tamamlandi!            ║
╠══════════════════════════════════════════════════╣
║  Dashboard:  http://192.168.1.X                  ║
║  API Docs:   http://192.168.1.X/docs             ║
╚══════════════════════════════════════════════════╝
```

---

## Manuel Kurulum

Adim adim kurulum yapmak istiyorsaniz:

### 1. Sistem Paketleri

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev \
    mariadb-server mariadb-client libmariadb-dev \
    redis-server nginx nftables dnsmasq \
    wireguard wireguard-tools \
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

# Sanal ortam
python3 -m venv venv
source venv/bin/activate

# Bagimliliklari kur
pip install -r requirements.txt

# .env dosyasi
cp ../.env.example .env
# .env dosyasini duzenleyin: DATABASE_URL, SECRET_KEY vb.
nano .env
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

---

## Yapilandirma

### .env Dosyasi

Backend `.env` dosyasi (`/opt/tonbilaios/backend/.env`):

| Degisken | Aciklama | Varsayilan |
|----------|----------|------------|
| `DATABASE_URL` | MariaDB baglanti URL'si | *(zorunlu)* |
| `REDIS_URL` | Redis baglanti URL'si | `redis://localhost:6379/0` |
| `ENVIRONMENT` | Calisma ortami | `development` |
| `SECRET_KEY` | JWT token imzalama anahtari (min 32 karakter) | *(zorunlu)* |
| `CORS_ORIGINS` | Izin verilen originler | `http://localhost:5173` |
| `TRUSTED_PROXIES` | Guvenilir proxy IP'leri | `172.16.0.0/12,...` |
| `LOG_RETENTION_DAYS` | Log saklama suresi (gun) | `730` (2 yil) |
| `DNS_BLOCKLIST_UPDATE_HOURS` | Engelleme listesi guncelleme suresi | `6` |

#### Guvenli SECRET_KEY Uretme

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## Servis Yonetimi

```bash
# Backend servisi
sudo systemctl start tonbilaios       # Baslat
sudo systemctl stop tonbilaios        # Durdur
sudo systemctl restart tonbilaios     # Yeniden baslat
sudo systemctl status tonbilaios      # Durum

# Loglar
sudo journalctl -u tonbilaios -f      # Canli log takibi
sudo journalctl -u tonbilaios -n 100  # Son 100 satir

# Nginx
sudo systemctl reload nginx           # Yapilandirma yeniden yukle
sudo nginx -t                         # Yapilandirma testi

# MariaDB
sudo systemctl status mariadb
sudo mysql -u tonbilai -p tonbilaios  # Veritabanina baglan

# Redis
redis-cli ping                        # Baglanti testi
redis-cli info memory                 # Bellek kullanimi
```

---

## Guncelleme

```bash
cd /opt/tonbilaios

# Yeni kodlari cek
git pull origin main

# Backend bagimliliklari guncelle
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Frontend yeniden build et
cd ../frontend
npm install
npm run build

# Servisi yeniden baslat
sudo systemctl restart tonbilaios
```

---

## Dizin Yapisi

```
/opt/tonbilaios/
├── setup.sh                    # Tek komut kurulum scripti
├── .env.example                # Ortam degiskenleri sablonu
├── config/
│   ├── tonbilaios.service      # systemd servis dosyasi
│   └── nginx-tonbilaios.conf   # Nginx yapilandirmasi
│
├── backend/
│   ├── .env                    # Ortam degiskenleri (git'te YOK)
│   ├── requirements.txt        # Python bagimliliklari
│   ├── venv/                   # Python sanal ortam (git'te YOK)
│   └── app/
│       ├── main.py             # FastAPI uygulama giris noktasi
│       ├── config.py           # Yapilandirma yonetimi
│       ├── api/v1/             # REST API endpoint'ler (25+)
│       ├── models/             # SQLAlchemy modelleri (28+)
│       ├── schemas/            # Pydantic semalari
│       ├── services/           # Is mantigi servisleri
│       ├── workers/            # Arka plan islemciler (14+)
│       ├── hal/                # Donanim soyutlama katmani
│       └── db/                 # Veritabani baglantisi
│
├── frontend/
│   ├── package.json            # Node.js bagimliliklari
│   ├── tsconfig.json           # TypeScript yapilandirmasi
│   ├── vite.config.ts          # Vite build yapilandirmasi
│   ├── tailwind.config.js      # TailwindCSS temasi
│   ├── index.html              # HTML giris noktasi
│   ├── dist/                   # Build ciktisi (git'te YOK)
│   └── src/
│       ├── main.tsx            # React giris noktasi
│       ├── App.tsx             # Router yapisi
│       ├── index.css           # Global stiller
│       ├── pages/              # Sayfa bilesenleri (23)
│       ├── components/         # UI bilesenleri
│       ├── hooks/              # Ozel React hook'lari
│       ├── services/           # API istemcileri (20+)
│       ├── types/              # TypeScript tip tanimlari
│       └── config/             # Widget yapilandirmasi
│
└── docs/
    └── screenshots/            # Ekran goruntuleri
```

---

## Sorun Giderme

### Backend baslamiyor

```bash
# Loglari kontrol edin
sudo journalctl -u tonbilaios -n 50

# .env dosyasini kontrol edin
cat /opt/tonbilaios/backend/.env

# Manuel calistirmayi deneyin
cd /opt/tonbilaios/backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Veritabani baglanti hatasi

```bash
# MariaDB servisini kontrol edin
sudo systemctl status mariadb

# Veritabani erisimini test edin
mysql -u tonbilai -p -e "USE tonbilaios; SHOW TABLES;"
```

### Frontend build hatasi

```bash
cd /opt/tonbilaios/frontend

# Node modulleri temizle ve yeniden kur
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Nginx 502 Bad Gateway

```bash
# Backend'in calistigini kontrol edin
curl http://localhost:8000/health

# Nginx yapilandirmasini test edin
sudo nginx -t

# Nginx loglarini kontrol edin
sudo tail -f /var/log/nginx/error.log
```

### WebSocket baglantisi kurulamiyor

```bash
# Nginx config'inde WebSocket desteginin aktif oldugunu dogrulayin
grep -A5 "Upgrade" /etc/nginx/sites-available/tonbilaios
```

---

## API Dokumantasyonu

Backend calisirken Swagger UI'a erisin:
- **Swagger UI:** `http://<PI_IP>/docs`
- **ReDoc:** `http://<PI_IP>/redoc`
- **OpenAPI JSON:** `http://<PI_IP>/openapi.json`

---

## Guvenlik Notlari

- `.env` dosyasi **asla** Git'e eklenmemeli (`.gitignore`'da)
- Uretim ortaminda `SECRET_KEY` en az 32 karakter olmali
- `ENVIRONMENT=production` ayarlandiginda zayif anahtarlar reddedilir
- 5651 sayili kanun uyumlulugu: Loglar 2 yil boyunca kriptografik imza ile saklanir
- nftables kurallari uygulama basladiginda otomatik senkronize edilir
- CORS, CSRF ve guvenlik baslik korumalari aktif

---

<p align="center">
  <sub>TonbilAiFirewall &copy; 2025-2026 TonbiLX. Tum haklari saklidir.</sub>
</p>
