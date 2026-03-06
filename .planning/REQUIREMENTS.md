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

- [ ] **DASH-01**: Ana dashboard ekrani — baglanti durumu, bant genisligi, cihaz sayisi, DNS ozet
- [ ] **DASH-02**: WebSocket canli veri akisi — bandwidth, DNS, cihaz guncellemeleri (lifecycle-safe)
- [ ] **DASH-03**: Istatistik kartlari — toplam trafik, engellenen sorgu, aktif cihaz, tehdit sayisi
- [ ] **DASH-04**: Bant genisligi grafigi (Vico chart)
- [ ] **DASH-05**: Home screen widget (Glance) — bant genisligi, cihaz sayisi, son tehdit
- [ ] **DASH-06**: Quick Settings tile — DNS filtreleme toggle + cihaz engelleme toggle

### Device Management

- [ ] **DEV-01**: Cihaz listesi — isim, IP, MAC, durum gostergesi, anlik bant genisligi
- [ ] **DEV-02**: Cihaz detay ekrani — trafik gecmisi, DNS sorgulari, profil bilgisi
- [ ] **DEV-03**: Tek dokunusla cihaz engelleme/engel kaldirma (internet durdurma)
- [ ] **DEV-04**: Cihaza profil atama/degistirme
- [ ] **DEV-05**: Pull-to-refresh tum cihaz ekranlarinda

### DNS Filtering

- [ ] **DNS-01**: DNS ozet ekrani — toplam sorgu, engelleme sayisi, en cok sorgulanan/engellenen domainler
- [ ] **DNS-02**: DNS filtreleme hizli toggle (tek dokunusla ac/kapa)
- [ ] **DNS-03**: Icerik kategorileri goruntuleme + blocklist baglama yonetimi
- [ ] **DNS-04**: Profil yonetimi — profil olusturma/duzenleme, kategori secimi, bandwidth limiti

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

- [ ] **DDOS-01**: DDoS koruma durumu ekrani
- [ ] **DDOS-02**: Basitlestirilmis saldiri haritasi (mobil optimized)
- [ ] **DDOS-03**: Canli saldiri akisi (son tehditler)

### Traffic Monitoring

- [ ] **TRAF-01**: Canli akislar ekrani — per-flow baglanti listesi (5s yenileme)
- [ ] **TRAF-02**: Buyuk transferler listesi (>1MB flowlar)
- [ ] **TRAF-03**: Trafik gecmisi ekrani (sayfalama destegi)
- [ ] **TRAF-04**: Per-device bant genisligi zaman serisi grafikleri (Vico)

### Push Notifications

- [ ] **NOTIF-01**: FCM push notification altyapisi — backend token kayit endpoint
- [ ] **NOTIF-02**: Backend bildirim dispatch servisi (yeni cihaz, DDoS, DNS, VPN durum degisikligi)
- [ ] **NOTIF-03**: Android bildirim kanallari (Guvenlik, Cihaz, Trafik, Sistem)
- [ ] **NOTIF-04**: Bildirim ayarlari ekrani — kanal bazli ac/kapa

### AI Chat

- [ ] **CHAT-01**: Mobil AI sohbet ekrani — mevcut /api/v1/chat endpoint kullanimi
- [ ] **CHAT-02**: Mesaj gecmisi goruntuleme
- [ ] **CHAT-03**: Yapilandirilmis yanit goruntuleme (JSON/tablo formati)

### Telegram

- [ ] **TELE-01**: Telegram bot yapilandirma ekrani (token, chat ID)
- [ ] **TELE-02**: Telegram bildirim ayarlari

### WiFi AP

- [ ] **WIFI-01**: WiFi erisim noktasi durumu goruntuleme
- [ ] **WIFI-02**: SSID, sifre, kanal degistirme
- [ ] **WIFI-03**: WiFi AP acma/kapatma

### DHCP

- [ ] **DHCP-01**: DHCP havuz bilgileri goruntuleme
- [ ] **DHCP-02**: Statik IP atamalari yonetimi

### Security Settings

- [ ] **SEC-01**: Guvenlik ayarlari ekrani — tehdit/DNS/DDoS esik degerleri
- [ ] **SEC-02**: Ayar degistirme ve kaydetme (hot-reload backend)

### UX Polish

- [ ] **UX-01**: Haptic feedback — kritik uyarilarda titresim
- [ ] **UX-02**: App shortcuts — uzun basma menusu (durum kontrol, cihaz engelle, AI chat)
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
| DASH-01 | Phase 8 | Pending |
| DASH-02 | Phase 8 | Pending |
| DASH-03 | Phase 8 | Pending |
| DASH-04 | Phase 8 | Pending |
| DASH-05 | Phase 14 | Pending |
| DASH-06 | Phase 14 | Pending |
| DEV-01 | Phase 9 | Pending |
| DEV-02 | Phase 9 | Pending |
| DEV-03 | Phase 9 | Pending |
| DEV-04 | Phase 9 | Pending |
| DEV-05 | Phase 9 | Pending |
| DNS-01 | Phase 10 | Pending |
| DNS-02 | Phase 10 | Pending |
| DNS-03 | Phase 10 | Pending |
| DNS-04 | Phase 10 | Pending |
| FW-01 | Phase 11 | Pending |
| FW-02 | Phase 11 | Pending |
| FW-03 | Phase 11 | Pending |
| VPN-01 | Phase 11 | Pending |
| VPN-02 | Phase 11 | Pending |
| VPN-03 | Phase 11 | Pending |
| VPN-04 | Phase 11 | Pending |
| DDOS-01 | Phase 11 | Pending |
| DDOS-02 | Phase 11 | Pending |
| DDOS-03 | Phase 11 | Pending |
| TRAF-01 | Phase 12 | Pending |
| TRAF-02 | Phase 12 | Pending |
| TRAF-03 | Phase 12 | Pending |
| TRAF-04 | Phase 12 | Pending |
| NOTIF-01 | Phase 13 | Pending |
| NOTIF-02 | Phase 13 | Pending |
| NOTIF-03 | Phase 13 | Pending |
| NOTIF-04 | Phase 13 | Pending |
| CHAT-01 | Phase 13 | Pending |
| CHAT-02 | Phase 13 | Pending |
| CHAT-03 | Phase 13 | Pending |
| TELE-01 | Phase 13 | Pending |
| TELE-02 | Phase 13 | Pending |
| WIFI-01 | Phase 13 | Pending |
| WIFI-02 | Phase 13 | Pending |
| WIFI-03 | Phase 13 | Pending |
| DHCP-01 | Phase 13 | Pending |
| DHCP-02 | Phase 13 | Pending |
| SEC-01 | Phase 13 | Pending |
| SEC-02 | Phase 13 | Pending |
| UX-01 | Phase 14 | Pending |
| UX-02 | Phase 14 | Pending |
| UX-03 | Phase 15 | Pending |

**Coverage:**
- v1 requirements: 59 total
- Mapped to phases: 59
- Unmapped: 0

---
*Requirements defined: 2026-03-06*
*Last updated: 2026-03-06 after roadmap creation*
