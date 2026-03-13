# Quick Task 37: NPM Yapısı Analiz & Nginx Panel Entegrasyonu — Sentez Raporu

**Tarih:** 2026-03-13
**Araştırma Ajanları:** 5 paralel Opus 4.6 ajan
**Toplam Araştırma Süresi:** ~15 dakika

---

## MEVCUT DURUM ÖZETİ

### Ağ Topolojisi

```
Internet → ISP Modem (192.168.1.1) → Port 80/443 → 192.168.1.4 (NPM)
                                    → Port 2323  → 192.168.1.9 (SSH Jump)

192.168.1.2 (Pi 5, 4GB)  ← TonbilAiOS Firewall + DNS + VPN + Backend
192.168.1.4 (Pi 5, 8GB)  ← NPM Docker + Nextcloud + 10 container
192.168.1.5              ← NAS (Sonarr/Radarr/Plex...)
192.168.1.7              ← DNS Server (Technitium/Pi-hole)
192.168.1.9              ← NAS-2 (Jump host)
```

### 192.168.1.2 (TonbilAiOS Pi)
- **Donanım:** Raspberry Pi 5, 4GB RAM, ARM Cortex-A76 x4
- **RAM:** %40 kullanım (1.6GB/4GB), 2.3GB kullanılabilir
- **Disk:** %7 kullanım (7.7GB/118GB)
- **Docker:** KURULU DEĞİL
- **Nginx:** 1.26.3, port 80/93/443, tek site config (tonbilaios)
- **Servisler:** FastAPI, MariaDB, Redis, dnsmasq, hostapd, fail2ban, WireGuard, nftables

### 192.168.1.4 (NPM Sunucusu)
- **Donanım:** Raspberry Pi 5, 8GB RAM
- **NPM:** v2.14.0 (Docker, jc21/nginx-proxy-manager:latest)
- **Proxy Host:** 25 aktif yapılandırma
- **SSL:** 62 Let's Encrypt sertifikası
- **Data:** 203MB
- **CPU:** %0.70 (idle)
- **Diğer Container:** Nextcloud, Portainer, PhotoPrism, FileBrowser, Redis, MariaDB x2, Watchtower

### NPM Proxy Host Dağılımı (25 host)
| Hedef IP | Sayı | Servisler |
|----------|------|-----------|
| 192.168.1.4 | 11 | Nextcloud, Portainer, PhotoPrism, FileBrowser, Mastodon... |
| 192.168.1.5 | 8 | Sonarr, Radarr, Bazarr, Prowlarr, Plex, Ombi... |
| 192.168.1.9 | 3 | NAS, LuCI, FileBrowser |
| 192.168.1.7 | 2 | Pi-hole, Technitium DNS |
| 192.168.1.2 | 2 | wall.tonbilx.com, guard.tonbilx.com |

---

## 4 SENARYO KARŞILAŞTIRMASI

| Kriter | A: NPM Docker Pi'ye | B: Native Nginx | C: Uzaktan Yönetim | D: Hybrid |
|--------|---------------------|------------------|--------------------|-----------|
| **Kesinti** | 15-30 dk | 30-60 dk | **0 dk** | 20-40 dk |
| **Pi RAM etkisi** | +300-500MB ⚠️ | +0MB | **+0MB** | +50-100MB |
| **Uygulama zorluğu** | Orta | Yüksek | **Düşük** | Çok Yüksek |
| **İş yükü** | 1 saat | 5-8 saat | **3-4 saat** | 6-10 saat |
| **Rollback** | 5-10 dk | 5-10 dk | **Anında** | 5-10 dk |
| **SPOF riski** | Çözülür | Çözülür | **Değişmez** | Kısmen |
| **Pi 4GB uygunluğu** | KRİTİK ⚠️ | İDEAL | **İDEAL** | Uygun |

### Senaryo A: NPM Docker → Pi (RİSKLİ)
- Pi 4GB RAM + Docker (~300MB) + NPM (~200MB) = swap thrashing riski
- Port 80 çakışması (nginx vs NPM)
- DNS proxy ile Docker DNS çakışması

### Senaryo B: Native Nginx + Certbot (GELECEK İÇİN)
- En iyi uzun vadeli çözüm
- 25 conf dosyası hazırlamak yüksek iş yükü
- SSL rate limit riski (haftada 5 sertifika)
- Sıfır ek RAM kullanımı

### Senaryo C: Uzaktan Yönetim (ÖNERİLEN ✅)
- NPM olduğu yerde kalır
- TonbilAiOS paneline "Reverse Proxy" sayfası eklenir
- NPM API (192.168.1.4:81) üzerinden CRUD yönetim
- Sıfır kesinti, sıfır kaynak etkisi, düşük risk

### Senaryo D: Hybrid (PRATİK DEĞİL)
- Port forwarding kısıtlaması (aynı port tek hedefe)
- Çift katman proxy karmaşıklığı
- İki farklı SSL yönetim noktası

---

## ÖNERİLEN YOL HARİTASI

```
AŞAMA 1 (ŞİMDİ): Senaryo C — NPM API Panel Entegrasyonu
├── TonbilAiOS panelinden NPM'i görme ve yönetme
├── İş yükü: 3-4 saat
├── Kesinti: 0
└── Risk: Düşük

AŞAMA 2 (GELECEK): Pi RAM upgrade veya donanım değişikliği sonrası
├── Senaryo B — Native Nginx + Certbot
├── NPM tamamen bırakılır
├── TonbilAiOS üzerinden tam nginx yönetimi
├── İş yükü: 5-8 saat
└── Planlanan kesinti: 30-60 dakika
```

---

## AŞAMA 1 UYGULAMA PLANI (Senaryo C)

### Mimari

```
[Frontend]                    [Backend]                     [NPM]
NginxProxyPage.tsx  ──→  /api/v1/nginx-proxy/*  ──→  HTTP ──→  192.168.1.4:81/api
                              npm_client.py
```

### Backend Dosyaları (3 yeni + 2 değişiklik)

| # | Dosya | Tür | Açıklama |
|---|-------|-----|----------|
| 1 | `backend/app/services/npm_client.py` | YENİ | NPM API istemcisi (httpx, token yönetimi) |
| 2 | `backend/app/api/v1/nginx_proxy.py` | YENİ | API endpoint'ler (host/cert/stream CRUD + status) |
| 3 | `backend/app/schemas/nginx_proxy.py` | YENİ | Pydantic şemalar |
| 4 | `backend/app/api/v1/router.py` | DEĞİŞİKLİK | nginx_proxy router kaydı |
| 5 | `backend/app/config.py` | DEĞİŞİKLİK | NPM_API_URL, NPM_EMAIL, NPM_PASSWORD |

### Frontend Dosyaları (2 yeni + 3 değişiklik)

| # | Dosya | Tür | Açıklama |
|---|-------|-----|----------|
| 1 | `frontend/src/pages/NginxProxyPage.tsx` | YENİ | 4 tab'lı yönetim sayfası |
| 2 | `frontend/src/services/nginxProxyApi.ts` | YENİ | Axios API fonksiyonları |
| 3 | `frontend/src/types/index.ts` | DEĞİŞİKLİK | NpmProxyHost, NpmCertificate, NpmStream, NpmStatus |
| 4 | `frontend/src/App.tsx` | DEĞİŞİKLİK | Route: /nginx-proxy |
| 5 | `frontend/src/components/layout/Sidebar.tsx` | DEĞİŞİKLİK | Menü: "Reverse Proxy" |

### NginxProxyPage.tsx Yapısı

```
NginxProxyPage
├── TopBar: "Reverse Proxy Yönetimi"
├── StatCard'lar: Host Sayısı | SSL Sertifika | Stream | NPM Durumu
├── Tab 1: "Proxy Host'lar"
│   ├── Tablo: domain, hedef, SSL, durum, işlemler
│   └── Modal: Yeni/Düzenle (domain, forward_host/port, SSL, websocket, cache)
├── Tab 2: "SSL Sertifikalar"
│   ├── Tablo: domain, sağlayıcı, geçerlilik, durum
│   └── Let's Encrypt talep formu
├── Tab 3: "TCP/UDP Streams"
│   ├── Tablo: gelen port, hedef, protokol, durum
│   └── Modal: Yeni/Düzenle
└── Tab 4: "Durum & Loglar"
    └── NPM bağlantı durumu, nginx_online, son hata
```

### NPM API Endpoint'ler (Backend → NPM)

| TonbilAiOS API | NPM API | Açıklama |
|----------------|---------|----------|
| GET /nginx-proxy/hosts | GET /api/nginx/proxy-hosts | Listele |
| POST /nginx-proxy/hosts | POST /api/nginx/proxy-hosts | Oluştur |
| PUT /nginx-proxy/hosts/{id} | PUT /api/nginx/proxy-hosts/{id} | Güncelle |
| DELETE /nginx-proxy/hosts/{id} | DELETE /api/nginx/proxy-hosts/{id} | Sil |
| GET /nginx-proxy/certificates | GET /api/nginx/certificates | SSL listele |
| POST /nginx-proxy/certificates/letsencrypt | POST /api/nginx/certificates | SSL talep |
| GET /nginx-proxy/streams | GET /api/nginx/streams | Stream listele |
| GET /nginx-proxy/status | Bileşik | Durum + istatistik |

---

## FAYDA / ZARAR SONUÇ ANALİZİ

### Firewall'larda Nginx Kullanımı
- **OPNsense:** Nginx plugin (NAXSI WAF dahil) — en yakın referans
- **pfSense:** HAProxy tercih ediyor
- **Genel eğilim:** Reverse proxy opsiyonel plugin, zorunlu değil

### NPM Alternatifleri
| Çözüm | RAM | Pi Uygunluğu | Not |
|-------|-----|--------------|-----|
| NPM Docker | 200-300MB | Orta | CPU spike sorunu, proje 3-4 yıl güncellenmedi |
| Pure Nginx + Certbot | 4-10MB | Çok Yüksek | Pi'de zaten mevcut |
| Caddy | 20-30MB | Yüksek | Tek binary, otomatik HTTPS |
| Traefik | 50-100MB | Düşük | K8s/Docker odaklı, overengineered |

### SPOF Analizi
NPM .4'te kalsa bile Pi zaten ağın kritik yolunda (DNS, DHCP, firewall). Pi çökerse internet zaten durur — SPOF riski Senaryo C'de fiilen değişmiyor.

---

## ARAŞTIRMA DOSYALARI

1. `RESEARCH-npm-structure.md` — NPM Docker container detayları, 25 proxy host listesi
2. `RESEARCH-pi-current-state.md` — Pi donanım, nginx, servisler, nftables
3. `RESEARCH-tonbilaios-architecture.md` — Frontend/backend mimari, entegrasyon tasarımı
4. `RESEARCH-firewall-nginx-analysis.md` — Firewall nginx kullanımı, alternatifler, fayda/zarar
5. `RESEARCH-migration-strategy.md` — 4 senaryo detayı, risk matrisi, karşılaştırma
