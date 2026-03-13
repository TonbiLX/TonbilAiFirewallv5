# Requirements: TonbilAiOS Android App v2.0

**Defined:** 2026-03-06
**Core Value:** TonbilAiOS v5'in tum ozelliklerini Samsung S24 Ultra uzerinden yonetme ve izleme

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Project Setup

- [x] **SETUP-01**: Gelistirme ortami kurulumu — JDK 21, Android SDK, Gradle, komut satirindan APK build
- [x] **SETUP-02**: Kotlin + Jetpack Compose proje iskeleti (AGP 9.0, Compose BOM, Koin DI, Navigation)
- [x] **SETUP-03**: Cyberpunk tema — neon cyan/magenta/green/amber/red renk paleti + koyu arka plan
- [x] **SETUP-04**: Navigasyon yapisi — bottom navigation + ekranlar arasi gecis (type-safe routes)
- [x] **SETUP-05**: Ktor API client — base URL, JSON serialization, hata yonetimi

### Authentication

- [x] **AUTH-01**: Kullanici email/sifre ile giris yapabilir (mevcut JWT auth)
- [x] **AUTH-02**: Biyometrik kimlik dogrulama — parmak izi veya yuz tanima ile giris
- [x] **AUTH-03**: JWT token guvenli depolama (EncryptedSharedPreferences)
- [x] **AUTH-04**: Otomatik token yenileme (Mutex ile race condition onleme)
- [x] **AUTH-05**: Auto-discovery — yerel (192.168.1.2) / uzak (wall.tonbilx.com) otomatik gecis
- [x] **AUTH-06**: Sunucu ayarlari ekrani — manuel URL yapilandirma + baglanti testi

### Dashboard

- [x] **DASH-01**: Ana dashboard ekrani — baglanti durumu, bant genisligi, cihaz sayisi, DNS ozet
- [x] **DASH-02**: WebSocket canli veri akisi — bandwidth, DNS, cihaz guncellemeleri (lifecycle-safe)
- [x] **DASH-03**: Istatistik kartlari — toplam trafik, engellenen sorgu, aktif cihaz, tehdit sayisi
- [x] **DASH-04**: Bant genisligi grafigi (Vico chart)
- [x] **DASH-05**: Home screen widget (Glance) — bant genisligi, cihaz sayisi, son tehdit
- [x] **DASH-06**: Quick Settings tile — DNS filtreleme toggle + cihaz engelleme toggle

### Device Management

- [x] **DEV-01**: Cihaz listesi — isim, IP, MAC, durum gostergesi, anlik bant genisligi
- [x] **DEV-02**: Cihaz detay ekrani — trafik gecmisi, DNS sorgulari, profil bilgisi
- [x] **DEV-03**: Tek dokunusla cihaz engelleme/engel kaldirma (internet durdurma)
- [x] **DEV-04**: Cihaza profil atama/degistirme
- [x] **DEV-05**: Pull-to-refresh tum cihaz ekranlarinda

### DNS Filtering

- [x] **DNS-01**: DNS ozet ekrani — toplam sorgu, engelleme sayisi, en cok sorgulanan/engellenen domainler
- [x] **DNS-02**: DNS filtreleme hizli toggle (tek dokunusla ac/kapa)
- [x] **DNS-03**: Icerik kategorileri goruntuleme + blocklist baglama yonetimi
- [x] **DNS-04**: Profil yonetimi — profil olusturma/duzenleme, kategori secimi, bandwidth limiti

### Firewall

- [ ] **FW-01**: Firewall kural listesi goruntuleme
- [ ] **FW-02**: Kural ekleme/duzenleme/silme
- [ ] **FW-03**: Kural siralama (oncelik) yonetimi

### VPN

- [ ] **VPN-01**: WireGuard peer listesi goruntuleme
- [ ] **VPN-02**: Peer ekleme/silme
- [ ] **VPN-03**: VPN durumu gostergesi (aktif/pasif)
- [ ] **VPN-04**: Peer QR kodu goruntuleme/paylasma

### DDoS Protection

- [x] **DDOS-01**: DDoS koruma durumu ekrani
- [x] **DDOS-02**: Basitlestirilmis saldiri haritasi (mobil optimized)
- [x] **DDOS-03**: Canli saldiri akisi (son tehditler)

### Traffic Monitoring

- [x] **TRAF-01**: Canli akislar ekrani — per-flow baglanti listesi (5s yenileme)
- [x] **TRAF-02**: Buyuk transferler listesi (>1MB flowlar)
- [x] **TRAF-03**: Trafik gecmisi ekrani (sayfalama destegi)
- [x] **TRAF-04**: Per-device bant genisligi zaman serisi grafikleri (Vico)

### Push Notifications

- [x] **NOTIF-01**: FCM push notification altyapisi — backend token kayit endpoint
- [x] **NOTIF-02**: Backend bildirim dispatch servisi (yeni cihaz, DDoS, DNS, VPN durum degisikligi)
- [x] **NOTIF-03**: Android bildirim kanallari (Guvenlik, Cihaz, Trafik, Sistem)
- [x] **NOTIF-04**: Bildirim ayarlari ekrani — kanal bazli ac/kapa

### AI Chat

- [x] **CHAT-01**: Mobil AI sohbet ekrani — mevcut /api/v1/chat endpoint kullanimi
- [x] **CHAT-02**: Mesaj gecmisi goruntuleme
- [x] **CHAT-03**: Yapilandirilmis yanit goruntuleme (JSON/tablo formati)

### Telegram

- [x] **TELE-01**: Telegram bot yapilandirma ekrani (token, chat ID)
- [x] **TELE-02**: Telegram bildirim ayarlari

### WiFi AP

- [x] **WIFI-01**: WiFi erisim noktasi durumu goruntuleme
- [x] **WIFI-02**: SSID, sifre, kanal degistirme
- [x] **WIFI-03**: WiFi AP acma/kapatma

### DHCP

- [x] **DHCP-01**: DHCP havuz bilgileri goruntuleme
- [x] **DHCP-02**: Statik IP atamalari yonetimi

### Security Settings

- [x] **SEC-01**: Guvenlik ayarlari ekrani — tehdit/DNS/DDoS esik degerleri
- [x] **SEC-02**: Ayar degistirme ve kaydetme (hot-reload backend)

### UX Polish

- [x] **UX-01**: Haptic feedback — kritik uyarilarda titresim
- [x] **UX-02**: App shortcuts — uzun basma menusu (durum kontrol, cihaz engelle, AI chat)
- [ ] **UX-03**: APK build — imzali release APK olusturma ve S24 Ultra'ya yukleme

## v2 Requirements

Deferred to future release.

### Advanced Features

- **ADV-01**: Live traffic monitor (floating overlay / PiP modu)
- **ADV-02**: AMOLED dim tema varyanti
- **ADV-03**: Tablet responsive layout optimizasyonu
- **ADV-04**: iOS versiyonu (Kotlin Multiplatform ile)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Google Play yayin | Kisisel kullanim — APK sideload yeterli |
| Offline mod | Router yonetimi inherent olarak online; eski veri yaniltici |
| SSH terminal | Guvenlik riski, mobilde pratik degil — JuiceSSH/Termius var |
| Multi-router yonetimi | Tek Pi deployment — kapsam patlamasi |
| Ozel tema editoru | Cyberpunk tema marka kimligi |
| Bandwidth speed test | App phone-to-router olcer, internet degil — yaniltici |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 6 | Complete |
| SETUP-02 | Phase 6 | Complete |
| SETUP-03 | Phase 6 | Complete |
| SETUP-04 | Phase 6 | Complete |
| SETUP-05 | Phase 6 | Complete |
| AUTH-01 | Phase 7 | Complete |
| AUTH-02 | Phase 7 | Complete |
| AUTH-03 | Phase 7 | Complete |
| AUTH-04 | Phase 7 | Complete |
| AUTH-05 | Phase 7 | Complete |
| AUTH-06 | Phase 7 | Complete |
| DASH-01 | Phase 8 | Complete |
| DASH-02 | Phase 8 | Complete |
| DASH-03 | Phase 8 | Complete |
| DASH-04 | Phase 8 | Complete |
| DASH-05 | Phase 14 | Complete |
| DASH-06 | Phase 14 | Complete |
| DEV-01 | Phase 9 | Complete |
| DEV-02 | Phase 9 | Complete |
| DEV-03 | Phase 9 | Complete |
| DEV-04 | Phase 9 | Complete |
| DEV-05 | Phase 9 | Complete |
| DNS-01 | Phase 10 | Complete |
| DNS-02 | Phase 10 | Complete |
| DNS-03 | Phase 10 | Complete |
| DNS-04 | Phase 10 | Complete |
| FW-01 | Phase 11 | Pending |
| FW-02 | Phase 11 | Pending |
| FW-03 | Phase 11 | Pending |
| VPN-01 | Phase 11 | Pending |
| VPN-02 | Phase 11 | Pending |
| VPN-03 | Phase 11 | Pending |
| VPN-04 | Phase 11 | Pending |
| DDOS-01 | Phase 11 | Complete |
| DDOS-02 | Phase 11 | Complete |
| DDOS-03 | Phase 11 | Complete |
| TRAF-01 | Phase 12 | Complete |
| TRAF-02 | Phase 12 | Complete |
| TRAF-03 | Phase 12 | Complete |
| TRAF-04 | Phase 12 | Complete |
| NOTIF-01 | Phase 13 | Complete |
| NOTIF-02 | Phase 13 | Complete |
| NOTIF-03 | Phase 13 | Complete |
| NOTIF-04 | Phase 13 | Complete |
| CHAT-01 | Phase 13 | Complete |
| CHAT-02 | Phase 13 | Complete |
| CHAT-03 | Phase 13 | Complete |
| TELE-01 | Phase 13 | Complete |
| TELE-02 | Phase 13 | Complete |
| WIFI-01 | Phase 13 | Complete |
| WIFI-02 | Phase 13 | Complete |
| WIFI-03 | Phase 13 | Complete |
| DHCP-01 | Phase 13 | Complete |
| DHCP-02 | Phase 13 | Complete |
| SEC-01 | Phase 13 | Complete |
| SEC-02 | Phase 13 | Complete |
| UX-01 | Phase 14 | Complete |
| UX-02 | Phase 14 | Complete |
| UX-03 | Phase 15 | Pending |

**Coverage:**
- v1 requirements: 59 total
- Mapped to phases: 59
- Unmapped: 0

---
*Requirements defined: 2026-03-06*
*Last updated: 2026-03-06 after roadmap creation*
