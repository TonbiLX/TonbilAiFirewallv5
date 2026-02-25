# TonbilAiOS - AI-Powered Router Management System

## Proje Genel Bakis

TonbilAiOS, Raspberry Pi uzerinde calisan yapay zeka destekli bir router yonetim sistemidir.
DNS filtreleme, cihaz yonetimi, VPN, DHCP, DDoS koruma, trafik izleme ve AI tabanli guvenlik analizleri sunar.

## Mimari

```
Raspberry Pi (192.168.1.2)
├── Backend:  Python/FastAPI + uvicorn (systemd: tonbilaios-backend)
├── Frontend: React 18 + TypeScript + Vite (static build → /opt/tonbilaios/frontend/dist/)
├── Veritabani: MariaDB (tonbilaios)
├── Cache:    Redis
└── Erisim:   pi.tonbil.com:2323 (SSH jump host) → 192.168.1.2 iki ssh içinde kullanıcı adı ve şifre: admin/benbuyum9087
```

## Teknoloji Yigini

### Frontend
| Teknoloji | Versiyon | Aciklama |
|-----------|----------|----------|
| React | 18.3.0 | UI framework |
| TypeScript | 5.6.0 | Tip guvenligi |
| Vite | 6.0.0 | Build tool |
| TailwindCSS | 3.4.0 | Utility-first CSS |
| react-grid-layout | 2.2.2 | Dashboard surukle-birak grid |
| Recharts | 2.13.0 | Grafik kutuphanesi |
| Lucide React | 0.460.0 | Ikon seti |
| clsx | - | Kosullu sinif birlestirme |

### Backend
| Teknoloji | Aciklama |
|-----------|----------|
| FastAPI | REST API + WebSocket |
| SQLAlchemy | ORM (MariaDB) |
| Redis | Cache + realtime veri |
| Paramiko | SSH islemleri |
| nftables | Firewall kurallar |
| WireGuard | VPN yonetimi |

## Tema: Cyberpunk Glassmorphism

```css
--neon-cyan:    #00F0FF   /* Ana vurgu */
--neon-magenta: #FF00E5   /* Ikincil vurgu */
--neon-green:   #39FF14   /* Basari/aktif */
--neon-amber:   #FFB800   /* Uyari */
--neon-red:     #FF003C   /* Hata/tehlike */
--glass-bg:     rgba(255,255,255,0.05)
--glass-border: rgba(255,255,255,0.12)
```

- Arka plan: Koyu mor-siyah gradient
- Kartlar: Yarisaydam cam efekti (backdrop-blur)
- Animasyonlar: Neon glow, pulse efektleri

## Dizin Yapisi

### Frontend (`frontend/src/`)

```
src/
├── main.tsx                    # Uygulama giris noktasi
├── App.tsx                     # Router yapisi
├── index.css                   # Global stiller + grid CSS overrides
├── ddos-map-animations.css     # DDoS harita animasyonlari
├── vite-env.d.ts              # Vite tip tanimlari
│
├── types/                      # TypeScript tip tanimlari
│   ├── index.ts               # Genel tipler
│   ├── websocket.ts           # WebSocket veri tipleri
│   └── dashboard-grid.ts      # Dashboard grid tipleri (WidgetDefinition, GRID_CONFIG)
│
├── config/
│   └── widgetRegistry.tsx     # Widget tanimlari (11 widget, varsayilan layout'lar)
│
├── hooks/
│   ├── useWebSocket.ts        # Canli veri akisi (bandwidth, DNS, cihazlar)
│   ├── useDashboard.ts        # Dashboard ozet verileri
│   ├── useDashboardLayout.ts  # Grid layout state + localStorage persist
│   ├── useDhcp.ts             # DHCP verileri
│   └── useDnsBlocking.ts      # DNS engelleme verileri
│
├── services/                   # API istemcileri
│   ├── api.ts                 # Axios instance (base URL, auth interceptor)
│   ├── tokenStore.ts          # JWT token yonetimi
│   ├── authApi.ts             # Kimlik dogrulama
│   ├── dashboardApi.ts        # Dashboard verileri
│   ├── deviceApi.ts           # Cihaz CRUD
│   ├── dnsApi.ts              # DNS sorgular + engelleme
│   ├── contentCategoryApi.ts  # Icerik kategorileri CRUD + blocklist baglama
│   ├── dhcpApi.ts             # DHCP yonetimi
│   ├── firewallApi.ts         # Guvenlik duvari
│   ├── vpnApi.ts              # WireGuard VPN
│   ├── ddosApi.ts             # DDoS koruma
│   ├── telegramApi.ts         # Telegram bildirimler
│   ├── chatApi.ts             # AI sohbet
│   └── ...                    # Diger servisler
│
├── components/
│   ├── common/                # Paylasilan bilesenler
│   │   ├── GlassCard.tsx      # Cam efektli kart
│   │   ├── StatCard.tsx       # Istatistik karti
│   │   ├── NeonBadge.tsx      # Neon etiket
│   │   └── LoadingSpinner.tsx # Yukleme animasyonu
│   │
│   ├── layout/                # Sayfa iskelet bilesenler
│   │   ├── MainLayout.tsx     # Ana layout (sidebar + icerik)
│   │   ├── Sidebar.tsx        # Sol gezinme cubugu
│   │   └── TopBar.tsx         # Ust cubuk (baslik + actions slot + kullanici menu)
│   │
│   ├── dashboard/             # Dashboard grid bilesenler
│   │   ├── DashboardGrid.tsx  # react-grid-layout Responsive container
│   │   ├── WidgetWrapper.tsx  # Widget sarmalayici (drag handle + GlassCard)
│   │   └── WidgetToggleMenu.tsx # Widget gizle/goster dropdown
│   │
│   ├── charts/                # Grafik bilesenler
│   │   ├── BandwidthGauge.tsx
│   │   ├── CategoryPie.tsx
│   │   └── TrafficChart.tsx
│   │
│   ├── ddos/                  # DDoS bilesenler
│   │   ├── DdosWorldMap.tsx   # Dunya haritasi (SVG)
│   │   └── AttackFeed.tsx     # Canli saldiri akisi
│   │
│   └── ...                    # Diger bilesenler (auth, devices, dns, dhcp, firewall, profiles)
│
└── pages/                     # Sayfa bilesenler
    ├── DashboardPage.tsx      # Ana dashboard (dinamik grid)
    ├── DevicesPage.tsx        # Cihaz listesi
    ├── DeviceDetailPage.tsx   # Cihaz detay
    ├── DnsBlockingPage.tsx    # DNS engelleme
    ├── ContentCategoriesPage.tsx # Icerik kategorileri (blocklist baglama + ozel domain)
    ├── ProfilesPage.tsx       # Profiller (dinamik kategori listesi + bandwidth)
    ├── DhcpPage.tsx           # DHCP yonetimi
    ├── FirewallPage.tsx       # Guvenlik duvari
    ├── VpnPage.tsx            # VPN yonetimi
    ├── DdosMapPage.tsx        # DDoS saldiri haritasi
    ├── TrafficPage.tsx        # Trafik izleme
    ├── ChatPage.tsx           # AI sohbet
    ├── TelegramPage.tsx       # Telegram bildirimleri
    ├── LoginPage.tsx          # Giris sayfasi
    └── ...                    # Diger sayfalar
```

### Backend (`backend/app/`)

```
app/
├── main.py                    # FastAPI uygulama + startup
├── config.py                  # Ortam degiskenleri
│
├── api/v1/                    # REST API endpoint'ler
│   ├── router.py              # Ana router (tum endpoint birlestirme)
│   ├── auth.py                # Kimlik dogrulama
│   ├── dashboard.py           # Dashboard verileri
│   ├── devices.py             # Cihaz CRUD
│   ├── dns.py                 # DNS sorgular + engelleme
│   ├── dhcp.py                # DHCP yonetimi
│   ├── firewall.py            # Guvenlik duvari kurallari
│   ├── vpn.py                 # WireGuard VPN
│   ├── ddos.py                # DDoS koruma
│   ├── ws.py                  # WebSocket endpoint
│   └── ...                    # Diger endpoint'ler
│
├── models/                    # SQLAlchemy modeller (MariaDB tablolari)
│   ├── device.py              # Cihaz modeli
│   ├── dns_query_log.py       # DNS sorgu loglari
│   ├── blocklist.py           # Engelleme listeleri
│   ├── content_category.py    # Icerik filtre kategorileri
│   ├── category_blocklist.py  # Kategori ↔ Blocklist coka-cok iliskisi
│   ├── profile.py             # Profil modeli (content_filters, bandwidth_limit)
│   ├── firewall_rule.py       # Guvenlik duvari kurallari
│   ├── vpn_peer.py            # VPN peer'lar
│   └── ...                    # 30 model
│
├── schemas/                   # Pydantic sema (istek/yanit dogrulama)
│
├── services/                  # Is mantigi servisleri
│   ├── ai_engine.py           # AI analiz motoru
│   ├── llm_service.py         # LLM entegrasyonu
│   ├── ddos_service.py        # DDoS tespit + koruma
│   ├── telegram_service.py    # Telegram bildirimler
│   └── ...
│
├── workers/                   # Arka plan islemciler
│   ├── device_discovery.py    # ARP tabanli cihaz kesfetme
│   ├── bandwidth_monitor.py   # Bant genisligi izleme
│   ├── dns_proxy.py           # DNS proxy + filtreleme (profil tabanli)
│   ├── blocklist_worker.py    # Blocklist indirme + kategori/profil domain rebuild
│   ├── traffic_monitor.py     # Trafik analiz (domain bazli agregasyon)
│   ├── flow_tracker.py        # Per-flow baglanti takibi (conntrack, 20s aralik)
│   └── ...
│
├── hal/                       # Donanim soyutlama katmani
│   ├── linux_driver.py        # Linux ag yonetimi
│   ├── linux_nftables.py      # nftables guvenlik duvari
│   ├── linux_tc.py            # Traffic control (QoS)
│   └── linux_dhcp_driver.py   # DHCP sunucu yonetimi
│
└── db/                        # Veritabani baglanti
    ├── session.py             # SQLAlchemy oturum
    ├── base.py                # Model base sinif
    └── redis_client.py        # Redis baglanti
```

## Dashboard Grid Sistemi

### Genel Bakis
Dashboard, `react-grid-layout v2.2.2` kullanarak surukle-birak, boyutlandirma ve widget gizle/goster ozellikleri sunar.

### Widget'lar (11 adet)

| # | ID | Baslik | Varsayilan Boyut (lg) |
|---|-----|--------|----------------------|
| 1 | connection-status | Baglanti Durumu | 12x1 |
| 2 | stat-cards | Istatistik Kartlari | 12x2 |
| 3 | bandwidth-chart | Bandwidth Grafigi | 12x4 |
| 4 | device-traffic | Cihaz Trafigi | 8x6 |
| 5 | dns-summary | DNS Ozet | 4x2 |
| 6 | device-status | Cihaz Durumu | 4x2 |
| 7 | vpn-status | VPN Durumu | 4x2 |
| 8 | top-domains | En Cok Sorgulanan | 4x5 |
| 9 | top-blocked | En Cok Engellenen | 4x5 |
| 10 | connected-devices | Bagli Cihazlar | 4x5 |
| 11 | top-clients | En Aktif Istemciler | 12x3 |

### Responsive Breakpoint'ler

| Breakpoint | Min Genislik | Sutun |
|-----------|-------------|-------|
| lg | 1200px | 12 |
| md | 996px | 12 |
| sm | 768px | 6 |
| xs | 0px | 4 |

### Veri Akisi

```
widgetRegistry.tsx          → Widget tanimlari + varsayilan layout'lar
         ↓
useDashboardLayout.ts       → Layout state + localStorage persist
         ↓
DashboardPage.tsx           → Widget render fonksiyonlari + veri baglama
         ↓
DashboardGrid.tsx           → react-grid-layout Responsive container
         ↓
WidgetWrapper.tsx            → GlassCard + drag handle
```

### react-grid-layout v2 API Notlari

v2, v1'den farkli bir API kullanir:

```typescript
// v1 (eski)
<ResponsiveGridLayout draggableHandle=".drag-handle" isDraggable={true} compactType="vertical" />

// v2 (mevcut)
<ResponsiveGridLayout dragConfig={{ handle: ".drag-handle" }} />
```

- `draggableHandle` → `dragConfig.handle`
- `isDraggable` → `dragConfig.enabled` (varsayilan: true)
- `isResizable` → `resizeConfig.enabled` (varsayilan: true)
- `compactType` → `compactor` (verticalCompactor, horizontalCompactor, noCompactor)
- `useCSSTransforms` → `positionStrategy` (transformStrategy varsayilan)
- `WidthProvider` sadece `react-grid-layout/legacy` modulunden erisilebilir

### localStorage Persistence

```
Key: tonbilaios_dashboard_prefs
Schema: { layouts: ResponsiveLayouts, visibleWidgets: string[], version: number }
```

- Her layout degisikliginde ve widget toggle'da otomatik kayit
- Sayfa yenilendiginde kayitli layout yuklenir
- "Sifirla" butonu ile varsayilana donus + localStorage temizleme
- `version` alani ile ileri uyumluluk (yeni widget eklendiginde)

## Erisim Bilgileri

| Hedef | Adres | Kullanici | Sifre |
|-------|-------|-----------|-------|
| SSH Jump Host | pi.tonbil.com:2323 | admin | benbuyum9087 |
| Pi (ic ag) | 192.168.1.2 | admin | benbuyum9087 |
| MariaDB | localhost:3306 | tonbilai | TonbilAiOS2026Router |
| DB Adi | tonbilaios | - | - |

## Deployment

### Dosya Transfer Yontemi (PC → Pi)

```python
# Yontem 1: Paramiko SFTP (ProxyJump tunnel ile)
# jump_client → pi.tonbil.com:2323 → channel → 192.168.1.2:22 → SFTP put
import paramiko
jump_client.connect("pi.tonbil.com", port=2323, username="admin", password="...")
channel = jump_transport.open_channel("direct-tcpip", ("192.168.1.2", 22), ("127.0.0.1", 0))
target_client.connect("192.168.1.2", username="admin", password="...", sock=channel)
sftp = target_client.open_sftp()
sftp.put(local_path, remote_path)

# Yontem 2: base64 chunked transfer (SSH uzerinden, eski)
content → base64 encode → 800-byte chunks → SSH echo >> tmp → base64 decode → sudo cp
```

### Build Komutu

```bash
cd /opt/tonbilaios/frontend && sudo npm run build
# tsc && vite build → dist/ klasorune statik dosyalar
```

### Backend Yeniden Baslatma

```bash
sudo systemctl restart tonbilaios-backend
```

### Sync Scripti (Pi → PC)

```bash
python sync_from_pi.py
# Tum frontend + backend dosyalarini E:\Nextcloud-Yeni\TonbilAiFirewallV41 altina indirir
```

## Onemli Dosya Konumlari

| Dosya | Yer | Aciklama |
|-------|-----|----------|
| Frontend kaynak | /opt/tonbilaios/frontend/src/ | React + TypeScript |
| Frontend build | /opt/tonbilaios/frontend/dist/ | Vite build ciktisi |
| Backend | /opt/tonbilaios/backend/app/ | FastAPI uygulama |
| systemd servis | tonbilaios-backend.service | Backend daemon |
| Lokal kopya | E:\Nextcloud-Yeni\TonbilAiFirewallV41 | PC sync dizini |

## Profil Tabanli DNS Filtreleme

### Genel Bakis

Icerik kategorileri gercek domain listelerine (blocklist + ozel domainler) baglanir. Profiller bu kategorileri referans alarak cihaz bazinda DNS filtreleme uygular. Servis engelleme (YouTube, Netflix vb.) profil filtrelemesinden bagimsiz calisir (UNION mantigi).

### Karar Mantigi

```
DNS sorgusu geldi
    ↓
1) Whitelist kontrolu → izinli ise ALLOW
2) Cihaz engelli mi? → engelli ise BLOCK
3) Servis engelleme kontrolu (BAGIMSIZ, her zaman kontrol edilir)
    → Cihaza servis engeli varsa BLOCK
4) Profil VEYA global blocklist:
    → Cihazda profil VAR → sadece profil kategori domainleri kontrol edilir
    → Cihazda profil YOK → global blocklist kontrol edilir
5) Reputation kontrolu
```

### Veri Akisi

```
Blocklist dosyalari (cache)
    ↓
CategoryBlocklist (coka-cok) → ContentCategory.custom_domains
    ↓
rebuild_category_domains() → Redis SET dns:category_domains:{key}
    ↓
Profile.content_filters (JSON array: ["adult", "gambling", ...])
    ↓
rebuild_profile_domains() → Redis SUNIONSTORE → dns:profile_domains:{id}
    ↓
Device.profile_id → dns:device_profile:{device_id}
    ↓
dns_proxy.py → is_profile_domain_blocked() ile subdomain yuruyusu
```

### Redis Key'leri

| Key | Tip | Aciklama |
|-----|-----|----------|
| `dns:category_domains:{category_key}` | SET | Bir kategorinin tum domainleri |
| `dns:profile_domains:{profile_id}` | SET | Bir profilin tum domainleri (kategori birlesimleri) |
| `dns:device_profile:{device_id}` | STRING | Cihazin profil ID'si |
| `dns:blocked_domains` | SET | Global engelleme listesi (profilsiz cihazlar icin) |

### Anahtar Dosyalar

| Dosya | Aciklama |
|-------|----------|
| `backend/app/models/category_blocklist.py` | Kategori ↔ Blocklist junction tablosu |
| `backend/app/workers/blocklist_worker.py` | 5 rebuild fonksiyonu: category_domains, profile_domains, device_profile cache |
| `backend/app/workers/dns_proxy.py` | `is_profile_domain_blocked()` + handle_query/handle_dot degisiklikleri |
| `backend/app/api/v1/content_categories.py` | Kategori CRUD + blocklist baglama + rebuild tetikleme |
| `backend/app/api/v1/profiles.py` | Profil CRUD + domain rebuild + bandwidth otomatik uygulama |
| `backend/app/api/v1/devices.py` | Profil atama → Redis cache + bandwidth guncelleme |
| `frontend/src/pages/ContentCategoriesPage.tsx` | Blocklist multi-selector + ozel domainler textarea |
| `frontend/src/pages/ProfilesPage.tsx` | Dinamik kategori listesi (API'den, domain sayilari ile) |

### Profil ↔ Cihaz ↔ Bandwidth Davranisi

- Cihaza profil atandiginda: `bandwidth_limit_mbps` profilden otomatik uygulanir
- Profil kaldirildiginda: bandwidth limiti sifirlanir
- Profilin bandwidth degistiginde: tum cihazlara yeni limit uygulanir

### Startup Sirasi (main.py lifespan)

```python
# Blocklist worker baslatilir (cache dosyalari indirilir)
# 10 saniye sonra:
await rebuild_all_category_domains(redis_client)    # Kategori → domain SET
await rebuild_all_profile_domains(redis_client)      # Profil → domain SUNIONSTORE
await rebuild_device_profile_cache(redis_client)     # Cihaz → profil mapping
```

### DB Tablolari

| Tablo | Aciklama |
|-------|----------|
| `content_categories` | Icerik kategorileri (key, name, icon, color, custom_domains, domain_count) |
| `category_blocklists` | Kategori ↔ Blocklist coka-cok iliskisi (category_id, blocklist_id) |
| `profiles` | Profiller (content_filters JSON array, bandwidth_limit_mbps) |

---

## Deep Traffic Flow Visibility (Per-Flow Baglanti Takibi)

### Genel Bakis

Her TCP/UDP baglantiyi per-flow takip eden sistem. Conntrack'ten 20 saniyede bir veri okunur, Redis'e canli yazilir, MariaDB'ye 60 saniyede bir sync edilir.

### Mimari

```
conntrack -L (20s)
    ↓
flow_tracker.py → parse + filtrele (LAN↔External)
    ↓                ↓
Redis (canli)    MariaDB (gecmis, 7 gun retention)
    ↓                ↓
API endpoints → Frontend (TrafficPage 3-tab + DeviceDetailPage)
```

### Anahtar Dosyalar

| Dosya | Aciklama |
|-------|----------|
| `backend/app/workers/flow_tracker.py` | Ana worker: conntrack parse, Redis + DB sync, servis tespiti |
| `backend/app/models/connection_flow.py` | SQLAlchemy model (connection_flows tablosu) |
| `backend/app/schemas/connection_flow.py` | Pydantic semalar (LiveFlowResponse, FlowHistoryResponse, FlowStatsResponse) |
| `backend/app/api/v1/traffic.py` | 5 flow endpoint: /flows/live, /flows/large-transfers, /flows/history, /flows/device/{id}/summary, /flows/stats |
| `frontend/src/pages/TrafficPage.tsx` | 3-tab layout: Canli Akislar (5s), Buyuk Transferler (3s), Gecmis (sayfalama) |

### Flow Tracker Ozellikleri

- **Cift yonlu takip:** LAN→External (outbound) + External→LAN (inbound, perspektif cevirme ile)
- **Servis/Uygulama Tespiti:** Port bazli (40+ port: SSH, MQTT, DNS, VPN...) + Domain bazli (80+ domain: WhatsApp, YouTube, Instagram...)
- **Delta BPS hesabi:** Her 20s'de onceki byte degerleri ile karsilastirma → anlik hiz
- **Buyuk transfer algilama:** >1MB flow'lar Redis ZSET'te ayrica izlenir
- **Debounced domain arama:** 400ms debounce ile arama filtresi (liveSearchText → liveDomainFilter)

### Redis Veri Yapisi

```
# Flow Tracker
flow:live:{flow_id}    → HASH (tum flow verisi, 60s TTL)
flow:active_ids        → SET (aktif flow_id'ler, 60s TTL)
flow:device:{device_id} → SET (cihaz bazli flow_id'ler, 60s TTL)
flow:large             → ZSET (buyuk transferler, score=bytes_total, 60s TTL)
flow:stats             → HASH (toplam istatistikler)

# DNS Filtreleme
dns:blocked_domains              → SET (global engelleme listesi)
dns:category_domains:{key}       → SET (kategori domainleri, rebuild ile guncellenir)
dns:profile_domains:{profile_id} → SET (profil domainleri, SUNIONSTORE ile)
dns:device_profile:{device_id}   → STRING (cihaz profil ID mapping)
dns:ip_to_device:{ip}            → STRING (IP → device_id mapping)
dns:blocked_device_ids           → SET (tamamen engelli cihaz ID'leri)
```

### Servis Tespit Katmanlari

1. **Port bazli:** `_PORT_SERVICE_MAP` → (service_name, app_name) — ornek: port 5228 → ("GCM/FCM", "Google Push")
2. **Domain bazli:** `_DOMAIN_APP_MAP` → app_name — ornek: "whatsapp.net" → "WhatsApp"
3. **Port+Domain kombinasyonu:** Ozel kurallar — ornek: port 5222 + whatsapp domain → "WhatsApp"

### Frontend Gorsel Ozellikler

- **Yon oklari:** ArrowUpRight (cyan, outbound) / ArrowDownLeft (magenta, inbound)
- **Uygulama sutunu:** app_name varsa NeonBadge ile renkli gosterim, yoksa service_name gri metin
- **Durum renklendirme:** ESTABLISHED=yesil, TIME_WAIT=gri, SYN_SENT=amber
- **Buyuk transfer vurgulama:** >10MB neon-magenta animasyonlu badge
- **Yenile butonlari:** Her tab'da ve DeviceDetailPage'de manuel refresh
