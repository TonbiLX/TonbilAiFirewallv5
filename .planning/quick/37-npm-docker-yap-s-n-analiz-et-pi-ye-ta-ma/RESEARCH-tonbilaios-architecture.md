# TonbilAiOS v5 - Nginx Yonetim Paneli Entegrasyon Mimari Analizi

## 1. Mevcut Frontend Yapisi

### 1.1 Sayfa Dosyalari (27 sayfa)

```
frontend/src/pages/
├── AiSettingsPage.tsx          # Yapay Zeka Ayarlari
├── ChatPage.tsx                # AI Asistan
├── ContentCategoriesPage.tsx   # Icerik Filtreleri
├── DashboardPage.tsx           # Ana Dashboard
├── DdosMapPage.tsx             # DDoS Harita
├── DeviceDetailPage.tsx        # Cihaz Detay
├── DevicesPage.tsx             # Cihazlar
├── DeviceServicesPage.tsx      # Cihaz Servisleri
├── DhcpPage.tsx                # DHCP
├── DnsBlockingPage.tsx         # DNS Engelleme
├── FirewallPage.tsx            # Guvenlik Duvari (tab'li: rules/connections/scanner/ddos/security/reputation)
├── InsightsPage.tsx            # AI Insights
├── IpManagementPage.tsx        # IP Yonetimi
├── LoginPage.tsx               # Giris
├── ProfilesPage.tsx            # Profiller
├── SecuritySettingsPage.tsx    # Guvenlik Ayarlari
├── SettingsPage.tsx            # Hesap Ayarlari
├── SystemLogsPage.tsx          # Sistem Loglari
├── SystemManagementPage.tsx    # Sistem Yonetimi
├── SystemMonitorPage.tsx       # Sistem Monitoru
├── SystemTimePage.tsx          # Saat & Tarih
├── TelegramPage.tsx            # Telegram Bot
├── TlsPage.tsx                 # TLS Sifreleme (sertifika yonetimi referans)
├── TrafficPage.tsx             # Trafik
├── VpnClientPage.tsx           # Dis VPN Istemci
├── VpnPage.tsx                 # VPN (Uzak Erisim)
└── WifiPage.tsx                # WiFi AP
```

### 1.2 Router Yapisi (App.tsx)

Tum sayfalar `AuthGuard > MainLayout > Routes` icinde tanimli. Yeni sayfa eklemek icin:

```typescript
// App.tsx'e eklenmesi gereken:
import { NginxProxyPage } from "./pages/NginxProxyPage";

// Routes icine:
<Route path="/nginx-proxy" element={<NginxProxyPage />} />
```

### 1.3 Sidebar Yapisi (Sidebar.tsx)

`navItems` dizisi ile tanimli. Lucide React ikonlari kullanilir. Yeni menu ogesi:

```typescript
// navItems dizisine eklenmesi gereken (VPN Client'tan sonra):
{ to: "/nginx-proxy", icon: Server, label: "Reverse Proxy" },
```

**Not:** `Server` ikonu `lucide-react`'tan import edilmeli.

### 1.4 API Servis Yapisi

Tum API servisleri `frontend/src/services/` altinda, her biri `api.ts`'deki Axios instance'i kullanir:
- Base URL: `/api/v1` (relative, Vite proxy ile backend'e yonlendirilir)
- JWT token interceptor otomatik eklenir
- 401 durumunda login'e yonlendirme

**Ornek yapi (firewallApi.ts):**
```typescript
import api from './api';
export const fetchFirewallRules = (params?: any) => api.get('/firewall/rules', { params });
export const createFirewallRule = (data: any) => api.post('/firewall/rules', data);
// ...
```

### 1.5 Tip Tanimlari (types/index.ts)

Tum interface'ler tek dosyada. ~900 satir, 60+ interface. Her API entity icin ayri interface tanimli.

### 1.6 Ortak Bilesenler

| Bilesen | Aciklama |
|---------|----------|
| `TopBar` | Sayfa basligi + actions slot |
| `GlassCard` | Cam efektli kart container |
| `StatCard` | Istatistik gosterim karti |
| `NeonBadge` | Renkli durum etiketi |
| `LoadingSpinner` | Yukleme animasyonu |

---

## 2. Mevcut Backend Yapisi

### 2.1 API Endpoint Dosyalari (32 dosya)

```
backend/app/api/v1/
├── router.py              # Ana router (tum modulleri birlestirir)
├── auth.py                # /auth
├── dashboard.py           # /dashboard
├── devices.py             # /devices
├── dns.py                 # /dns
├── dhcp.py                # /dhcp
├── firewall.py            # /firewall (referans CRUD yapisi)
├── vpn.py                 # /vpn
├── vpn_client.py          # /vpn-client
├── wifi.py                # /wifi
├── tls.py                 # /tls
├── traffic.py             # /traffic
├── insights.py            # /insights
├── chat.py                # /chat
├── profiles.py            # /profiles
├── content_categories.py  # /content-categories
├── services.py            # /services
├── system_logs.py         # /system-logs
├── system_time.py         # /system-time
├── system_monitor.py      # /system-monitor
├── system_management.py   # /system-management
├── telegram.py            # /telegram
├── ip_management.py       # /ip-management
├── ip_reputation.py       # /ip-reputation
├── ddos.py                # /ddos
├── ai_settings.py         # /ai-settings
├── security_settings.py   # /security
├── device_custom_rules.py # /device-rules
├── doh.py                 # /doh
├── push.py                # /push
├── ws.py                  # WebSocket
└── __init__.py
```

### 2.2 Router Kayit Deseni (router.py)

```python
from app.api.v1 import nginx_proxy  # yeni import
api_v1_router.include_router(
    nginx_proxy.router,
    prefix="/nginx-proxy",
    tags=["Nginx Reverse Proxy"]
)
```

### 2.3 Tipik API Endpoint Yapisi (firewall.py referans)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/rules", response_model=List[FirewallRuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # DB sorgusu + yanit
    ...

@router.post("/rules", response_model=FirewallRuleResponse, status_code=201)
async def create_rule(data: RuleCreate, ...):
    # Pydantic dogrulama + DB kayit
    ...
```

---

## 3. Mimari Analiz: Nginx Yonetim Paneli Entegrasyonu

### 3.1 Temel Karar: NPM API Proxy vs Dogrudan Nginx Kontrol

**Secenek A: NPM (Nginx Proxy Manager) API Proxy** (ONERILEN)

Ag topolojisinden:
- NPM zaten 192.168.1.4 (Tonbilx-n4) uzerinde Docker container olarak calisiyor
- NPM API: port 81 (emre@tonbil.com / benbuyum9087)
- TonbilAiOS backend → NPM API'ye HTTP istekleri proxy'ler

```
[Frontend] → /api/v1/nginx-proxy/* → [TonbilAiOS Backend] → HTTP → [NPM API :81]
```

**Avantajlar:**
- NPM zaten SSL, proxy host, stream, access list yonetimi yapiyor
- Tekrar icat etmeye gerek yok — NPM API'yi sarmalama yeterli
- SSL sertifika yonetimi (Let's Encrypt) NPM tarafinda zaten var
- Docker container izolasyonu korunur

**Secenek B: Dogrudan nginx.conf Kontrol** (ONERILMEZ)

- Pi uzerinde nginx.conf dosyasini dosya sistemi uzerinden yonetme
- Her degisiklikte `nginx -t && nginx -s reload`
- SSL sertifika yonetimini sifirdan yazmak gerekir
- Risk: yanlis config ile nginx crashleyebilir

### 3.2 NPM API Proxy Mimarisi

NPM API endpointleri (v2):

| NPM Endpoint | Aciklama |
|---------------|----------|
| `POST /api/tokens` | Login (JWT token al) |
| `GET /api/nginx/proxy-hosts` | Proxy host listele |
| `POST /api/nginx/proxy-hosts` | Proxy host olustur |
| `PUT /api/nginx/proxy-hosts/{id}` | Proxy host guncelle |
| `DELETE /api/nginx/proxy-hosts/{id}` | Proxy host sil |
| `GET /api/nginx/redirection-hosts` | Yonlendirme listele |
| `GET /api/nginx/streams` | TCP/UDP stream listele |
| `GET /api/nginx/certificates` | SSL sertifika listele |
| `POST /api/nginx/certificates` | Let's Encrypt sertifika al |
| `GET /api/nginx/access-lists` | Erisim listeleri |

---

## 4. Olusturulmasi Gereken Yeni Dosyalar

### 4.1 Backend (5 dosya)

| Dosya | Aciklama |
|-------|----------|
| `backend/app/api/v1/nginx_proxy.py` | API endpoint'ler: proxy host CRUD, SSL sertifika, stream, status |
| `backend/app/services/npm_client.py` | NPM API istemcisi: HTTP client, token yonetimi, hata yonetimi |
| `backend/app/schemas/nginx_proxy.py` | Pydantic semalar: ProxyHostCreate, ProxyHostResponse, CertificateResponse, StreamResponse |
| `backend/app/models/npm_config.py` | (Opsiyonel) NPM baglanti ayarlari DB modeli — alternatif olarak config.py'de sabit |
| `backend/app/config.py` | Mevcut dosyaya NPM_API_URL, NPM_EMAIL, NPM_PASSWORD ekleme |

### 4.2 Frontend (3 dosya)

| Dosya | Aciklama |
|-------|----------|
| `frontend/src/pages/NginxProxyPage.tsx` | Ana sayfa: tab yapili (Proxy Hosts / SSL Sertifikalar / Streams / Access Lists) |
| `frontend/src/services/nginxProxyApi.ts` | API cagrilari: CRUD fonksiyonlari |
| `frontend/src/types/index.ts` | Mevcut dosyaya yeni interface'ler ekleme |

---

## 5. Degistirilmesi Gereken Mevcut Dosyalar

| Dosya | Degisiklik |
|-------|-----------|
| `backend/app/api/v1/router.py` | `nginx_proxy` import + `include_router` ekleme |
| `backend/app/config.py` | NPM baglanti bilgileri (URL, email, sifre) |
| `frontend/src/App.tsx` | `NginxProxyPage` import + Route ekleme |
| `frontend/src/components/layout/Sidebar.tsx` | `navItems`'a Reverse Proxy menu ogesi ekleme |
| `frontend/src/types/index.ts` | Nginx/NPM ile ilgili TypeScript interface'leri ekleme |

---

## 6. Detayli Tasarim

### 6.1 Backend: npm_client.py (NPM API Istemcisi)

```python
# Temel yapi:
class NpmClient:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url  # http://192.168.1.4:81
        self.token = None
        self.token_expires = None

    async def _ensure_token(self):
        """NPM API token'i al veya yenile"""
        # POST /api/tokens → JWT token

    async def list_proxy_hosts(self) -> List[dict]:
        """GET /api/nginx/proxy-hosts"""

    async def create_proxy_host(self, data: dict) -> dict:
        """POST /api/nginx/proxy-hosts"""

    async def update_proxy_host(self, host_id: int, data: dict) -> dict:
        """PUT /api/nginx/proxy-hosts/{id}"""

    async def delete_proxy_host(self, host_id: int):
        """DELETE /api/nginx/proxy-hosts/{id}"""

    async def list_certificates(self) -> List[dict]:
        """GET /api/nginx/certificates"""

    async def request_certificate(self, domains: List[str], email: str) -> dict:
        """POST /api/nginx/certificates (Let's Encrypt)"""

    async def list_streams(self) -> List[dict]:
        """GET /api/nginx/streams"""

    async def get_npm_status(self) -> dict:
        """NPM durumu: erisilebilirlik, versiyon"""
```

### 6.2 Backend: nginx_proxy.py (API Endpoint'ler)

```python
router = APIRouter()

# --- Proxy Host CRUD ---
@router.get("/hosts")                    # Tum proxy host'lari listele
@router.get("/hosts/{host_id}")          # Tek proxy host detay
@router.post("/hosts")                   # Yeni proxy host olustur
@router.put("/hosts/{host_id}")          # Proxy host guncelle
@router.delete("/hosts/{host_id}")       # Proxy host sil
@router.post("/hosts/{host_id}/enable")  # Etkinlestir/devre disi birak

# --- SSL Sertifikalar ---
@router.get("/certificates")             # Sertifika listele
@router.post("/certificates/letsencrypt") # Let's Encrypt talep
@router.delete("/certificates/{cert_id}") # Sertifika sil

# --- TCP/UDP Streams ---
@router.get("/streams")                  # Stream listele
@router.post("/streams")                 # Stream olustur
@router.put("/streams/{stream_id}")      # Stream guncelle
@router.delete("/streams/{stream_id}")   # Stream sil

# --- Durum ---
@router.get("/status")                   # NPM baglanti durumu + istatistikler
```

### 6.3 Frontend: TypeScript Interface'leri

```typescript
// types/index.ts'e eklenecek:

export interface NpmProxyHost {
  id: number;
  domain_names: string[];
  forward_host: string;
  forward_port: number;
  forward_scheme: "http" | "https";
  certificate_id: number | null;
  ssl_forced: boolean;
  http2_support: boolean;
  block_exploits: boolean;
  caching_enabled: boolean;
  websocket_support: boolean;
  access_list_id: number | null;
  advanced_config: string;
  enabled: boolean;
  meta: Record<string, any>;
  created_on: string;
  modified_on: string;
}

export interface NpmCertificate {
  id: number;
  provider: string;  // "letsencrypt" | "other"
  nice_name: string;
  domain_names: string[];
  expires_on: string;
  created_on: string;
  is_deleted: boolean;
}

export interface NpmStream {
  id: number;
  incoming_port: number;
  forwarding_host: string;
  forwarding_port: number;
  tcp_forwarding: boolean;
  udp_forwarding: boolean;
  enabled: boolean;
  created_on: string;
  modified_on: string;
}

export interface NpmStatus {
  online: boolean;
  version: string | null;
  proxy_host_count: number;
  certificate_count: number;
  stream_count: number;
}
```

### 6.4 Frontend: nginxProxyApi.ts

```typescript
import api from './api';

// Proxy Hosts
export const fetchProxyHosts = () => api.get('/nginx-proxy/hosts');
export const getProxyHost = (id: number) => api.get(`/nginx-proxy/hosts/${id}`);
export const createProxyHost = (data: any) => api.post('/nginx-proxy/hosts', data);
export const updateProxyHost = (id: number, data: any) => api.put(`/nginx-proxy/hosts/${id}`, data);
export const deleteProxyHost = (id: number) => api.delete(`/nginx-proxy/hosts/${id}`);
export const toggleProxyHost = (id: number) => api.post(`/nginx-proxy/hosts/${id}/enable`);

// Certificates
export const fetchCertificates = () => api.get('/nginx-proxy/certificates');
export const requestLetsEncrypt = (data: any) => api.post('/nginx-proxy/certificates/letsencrypt', data);
export const deleteCertificate = (id: number) => api.delete(`/nginx-proxy/certificates/${id}`);

// Streams
export const fetchStreams = () => api.get('/nginx-proxy/streams');
export const createStream = (data: any) => api.post('/nginx-proxy/streams', data);
export const updateStream = (id: number, data: any) => api.put(`/nginx-proxy/streams/${id}`, data);
export const deleteStream = (id: number) => api.delete(`/nginx-proxy/streams/${id}`);

// Status
export const fetchNpmStatus = () => api.get('/nginx-proxy/status');
```

### 6.5 Frontend: NginxProxyPage.tsx Yapisi

```
NginxProxyPage
├── TopBar: "Reverse Proxy Yonetimi"
├── StatCard'lar: Proxy Host sayisi, SSL Sertifika, Stream, NPM Durumu
├── Tab Yapisi:
│   ├── Tab 1: "Proxy Host'lar"
│   │   ├── Tablo: domain, hedef, SSL, durum, islemler
│   │   └── Modal: Yeni/Duzenle formu (domain, forward_host, forward_port, SSL, websocket, cache)
│   ├── Tab 2: "SSL Sertifikalar"
│   │   ├── Tablo: domain, saglayici, son gecerlilik, durum
│   │   └── Let's Encrypt talep formu
│   ├── Tab 3: "TCP/UDP Streams"
│   │   ├── Tablo: gelen port, hedef, protokol, durum
│   │   └── Modal: Yeni/Duzenle formu
│   └── Tab 4: "Durum & Loglar"
│       └── NPM baglanti durumu, son islemler
```

---

## 7. Uygulama Adim Plani

### Adim 1: Backend NPM Client (npm_client.py)
- httpx veya aiohttp ile NPM API istemcisi
- Token yonetimi (otomatik login, token cache)
- Hata yonetimi (NPM erisilemez, timeout, auth hatasi)

### Adim 2: Backend API Endpoint'ler (nginx_proxy.py)
- CRUD endpoint'ler (proxy host, stream, certificate)
- Status endpoint
- Router kaydi

### Adim 3: Backend Schemas (nginx_proxy.py schemas)
- Pydantic v2 ile istek/yanit dogrulama

### Adim 4: Frontend API Servisi (nginxProxyApi.ts)
- Axios fonksiyonlari

### Adim 5: Frontend Tipler (types/index.ts)
- TypeScript interface'leri

### Adim 6: Frontend Sayfa (NginxProxyPage.tsx)
- Tab yapili tam sayfa
- CRUD modal/form
- Cyberpunk Glassmorphism tema uyumu

### Adim 7: Entegrasyon
- App.tsx route ekleme
- Sidebar.tsx menu ogesi ekleme

### Adim 8: Deploy
- Backend: dosya transfer + systemctl restart
- Frontend: npm run build

---

## 8. Bagimlilklar ve Riskler

| Risk | Cozum |
|------|-------|
| NPM API erisim hatasi (192.168.1.4:81 down) | Status endpoint ile baglanti kontrolu, graceful hata mesajlari |
| NPM API token suresi dolmasi | Otomatik token yenileme (npm_client icinde) |
| NPM API versiyon uyumsuzlugu | API versiyon kontrolu, fallback destegi |
| SSL sertifika talebi basarisiz | Let's Encrypt hata mesajlarini kullaniciya gosterme |
| NPM'de zaten tanimli host'larin goruntulenmesi | Sadece okuma modu destegi (NPM'den gelen verileri gosterme) |

---

## 9. Referans: TlsPage.tsx Benzerlikleri

TLS sayfasi zaten SSL sertifika yonetimi yapiyor (yapistirma + dosya yukleme + Let's Encrypt).
Nginx Proxy sayfasi bunun uzerine:
- Proxy host yonetimi (yeni)
- Stream yonetimi (yeni)
- NPM uzerinden SSL (TLS sayfasindakinden farkli — NPM API uzerinden)

TLS sayfasi Pi'nin kendi sertifikasini yonetirken, Nginx Proxy sayfasi NPM'deki sertifikalari yonetecek. Iki farkli kapsam.

---

## 10. Sonuc

- **Mimari:** NPM API Proxy yaklasimi en uygun. TonbilAiOS backend, NPM'ye HTTP istemci olarak baglanir.
- **Yeni dosya sayisi:** Backend 3 + Frontend 2 = 5 yeni dosya
- **Degisiklik sayisi:** 4 mevcut dosyada kucuk ekleme (router, App.tsx, Sidebar, types)
- **NPM API URL:** `http://192.168.1.4:81/api`
- **NPM Credentials:** emre@tonbil.com / benbuyum9087
- **Tahmini is yuku:** Orta (3-4 saat full-stack gelistirme)
