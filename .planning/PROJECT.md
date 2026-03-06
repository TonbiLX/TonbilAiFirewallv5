# TonbilAiOS v5 — Proje Durumu

## Tamamlanan Milestone'lar

### 1. Bridge Izolasyon Gecisi (2026-02-25 → 2026-03-04) — %100

Seffaf kopru (transparent bridge) modundan izole router moduna gecis. Modem sadece Pi'yi goruyor, tum LAN cihazlari modemden gizli.

| Aşama | İçerik | Durum |
|-------|--------|-------|
| 01 | Bridge Isolation Core — L2 drop + NAT MASQUERADE + rollback | TAMAMLANDI |
| 02 | Accounting Chain Migration — split upload/download chains | TAMAMLANDI |
| 03 | TC Mark Chain Migration — split tc_mark_up/tc_mark_down | TAMAMLANDI |
| 04 | Startup and Persistence — sysctl.d + modules-load.d + nftables.service | TAMAMLANDI |
| 05 | DHCP Gateway and Validation — gateway .1→.2 + validate.sh | TAMAMLANDI |

### 2. Telegram Tam Yetenek Güncellemesi (2026-03-04) — %100

16 yeni intent, JSON fix, onay mekanizması, v5.0 versiyon. Commit: `d02cc87`.

### 3. WiFi AP Yönetim Sistemi (2026-03-04) — %100

RPi 5 dahili WiFi (CYW43455) ile hostapd tabanlı erişim noktası yönetimi. Commit: `4742aa8`.

**Mimari:** hostapd (wlan0) → br0 bridge üyesi → 192.168.1.0/24 (aynı subnet)

### 4. Güvenlik Ayarları Sayfası (2026-03-04) — %100

Çok katmanlı güvenlik sistemi (DDoS, tehdit analizi, DNS filtreleme, DGA tespiti) için UI tabanlı yapılandırma sayfası. ~25 hardcoded sabit → DB-backed config + Redis hot-reload.

| Bileşen | Detay | Durum |
|---------|-------|-------|
| Backend Model | `security_config.py` — singleton, ~30 kolon | TAMAMLANDI + DEPLOY |
| Backend Schema | `security_config.py` — Response, Update, Stats | TAMAMLANDI + DEPLOY |
| Backend API | `security_settings.py` — 6 REST endpoint | TAMAMLANDI + DEPLOY |
| Startup Sync | `main.py` — DB→Redis push | TAMAMLANDI + DEPLOY |
| threat_analyzer hot-reload | 13 sabit → Redis dinamik okuma | TAMAMLANDI + DEPLOY |
| dns_proxy hot-reload | Rate limit + blocked qtypes + sinkhole (30sn cache) | TAMAMLANDI + DEPLOY |
| ddos_service hot-reload | Alert thresholds + cooldown | TAMAMLANDI + DEPLOY |
| dns_fingerprint hot-reload | TTL + cooldown + min_matches | TAMAMLANDI + DEPLOY |
| Frontend Page | 5-tab UI (Tehdit/DNS/Uyarı/IP/İstatistik) | TAMAMLANDI + DEPLOY |
| Frontend Routing | Güvenlik Duvarı sayfasında 5. tab olarak entegre | TAMAMLANDI + DEPLOY |
| Toggle Fix | Açık/kapalı toggle buton taşma düzeltmesi (left-0) | TAMAMLANDI + DEPLOY |

**Yeni dosyalar (6):** security_config model, schema, API endpoint, securityApi.ts, SecuritySettingsPage.tsx, SecuritySettingsTab.tsx
**Düzenlenen dosyalar (10):** models/__init__, router, main, threat_analyzer, dns_proxy, ddos_service, dns_fingerprint, types/index.ts, FirewallPage.tsx, Sidebar.tsx
**Yedek:** `/opt/tonbilaios/backup-security-20260304-1548/`
**Not:** Güvenlik Ayarları ayrı sayfa değil, Güvenlik Duvarı sayfasında DDoS Koruma'dan sonra 5. tab olarak yer alır.

### 5. Bandwidth Accounting Gecisi + Trafik Tablo Iyilestirmeleri (2026-03-05) — %100

Bridge hook → inet forward hook gecisi. br_netfilter aktifken bridge hook'lari trafigin %99'unu kaciriyordu.

| Bilesen | Detay | Durum |
|---------|-------|-------|
| inet bw_accounting | Yeni nftables tablo: IP bazli forward hook, per-IP + total counter | TAMAMLANDI + DEPLOY |
| bandwidth_monitor | MAC→IP gecisi, POLL_INTERVAL 10s→3s, `_get_known_device_ips()` | TAMAMLANDI + DEPLOY |
| cleanup_bridge_accounting | Eski bridge upload/download chain temizligi (TC mark korunur) | TAMAMLANDI + DEPLOY |
| Traffic API sort fix | `sort` → `sort_by` + `sort_order`, `last_seen`/`first_seen` sort desteği | TAMAMLANDI + DEPLOY |
| TrafficPage siralama | Tum sutun baslikları tiklanabilir (asc/desc toggle), zaman sutunu | TAMAMLANDI + DEPLOY |
| DeviceDetailPage siralama | Ayni siralama + zaman sutunu, varsayilan: last_seen desc | TAMAMLANDI + DEPLOY |

**Commit:** `804195d`
**Duzenlenen dosyalar (7):** linux_nftables.py, bandwidth_monitor.py, traffic.py, TrafficPage.tsx, DeviceDetailPage.tsx, trafficApi.ts
**Onceki sorun:** 98 Mbps speedtest'te dashboard 0 gosteriyordu (bridge hook). Simdi ~68 Mbps (10s poll) → ~95+ Mbps (3s poll)

### 6. VPN Client Outbound Routing Fix (2026-03-05) — %100

VPN client modunda LAN→VPN tünel yönlendirme düzeltmesi. rp_filter gevşetme. Commit: `37a841a`.

## Current Milestone: v2.0 TonbilAiOS Android App

**Goal:** Samsung S24 Ultra (Android) için Kotlin Native mobil uygulama — TonbilAiOS v5'in tüm özelliklerini yönetme ve izleme.

**Target features:**
- Dashboard (bant genişliği, cihaz sayısı, DNS özet, canlı durum)
- Cihaz yönetimi (liste, detay, profil atama, engelleme)
- DNS filtreleme (engelleme listeleri, kategoriler, profiller)
- Güvenlik duvarı kuralları yönetimi
- VPN peer yönetimi
- DDoS koruma izleme
- Trafik izleme (canlı akışlar, büyük transferler, geçmiş)
- Telegram bildirim ayarları
- AI sohbet
- WiFi AP yönetimi
- Güvenlik ayarları
- Push notification (FCM) + Telegram bildirimleri
- Biyometrik giriş (parmak izi / yüz tanıma) + JWT auth
- Cyberpunk tema (neon cyan/magenta, koyu arka plan)
- Dışarıdan erişim: wall.tonbilx.com üzerinden HTTPS API

**Platform:** Android önce (Kotlin Native), ileride iOS eklenebilir altyapı

## Requirements

### Validated

- ✓ Dashboard — web (existing)
- ✓ Cihaz yönetimi — web (existing)
- ✓ DNS filtreleme + profil tabanlı — web (existing)
- ✓ Güvenlik duvarı — web (existing)
- ✓ VPN yönetimi — web (existing)
- ✓ DDoS koruma — web (existing)
- ✓ Trafik izleme (per-flow) — web (existing)
- ✓ Telegram bildirimler — web + bot (existing)
- ✓ AI sohbet — web (existing)
- ✓ WiFi AP yönetimi — web (existing)
- ✓ Güvenlik ayarları — web (existing)
- ✓ Backend REST API — tüm endpoint'ler mevcut

### Active

- [ ] Kotlin Native Android uygulaması — tüm web özelliklerin mobil karşılığı
- [ ] Push notification (FCM) — backend + mobil entegrasyon
- [ ] Biyometrik kimlik doğrulama — parmak izi / yüz tanıma + JWT
- [ ] Dışarıdan erişim — wall.tonbilx.com üzerinden güvenli API bağlantısı
- [ ] Cyberpunk mobil tema — neon renk paleti + koyu arka plan

### Out of Scope

- iOS uygulaması — v2.0'da sadece Android, iOS ileride
- Offline mod — cihaz her zaman ağa bağlı olmalı
- Web arayüz değişiklikleri — mevcut web arayüzü olduğu gibi kalır

## Context

- Mevcut backend REST API tüm özellikleri destekliyor, yeni endpoint'ler push notification ve mobil auth için gerekecek
- wall.tonbilx.com zaten web panele dışarıdan erişim sağlıyor — aynı domain app için de kullanılabilir
- Samsung S24 Ultra: Snapdragon 8 Gen 3, Android 14+, büyük ekran (6.8")
- Kotlin Native + Jetpack Compose modern Android geliştirme standardı

## Constraints

- **Platform**: Android API 28+ (Android 9+), hedef: Android 14 (S24 Ultra)
- **Dil**: Kotlin (Jetpack Compose UI)
- **Backend**: Mevcut FastAPI REST API — yeni endpoint'ler eklenmeli (FCM token, push subscription)
- **Ağ**: wall.tonbilx.com üzerinden HTTPS, yerel ağda doğrudan 192.168.1.2
- **Deployment**: Pi'ye SSH ile backend değişiklikleri, app Google Play veya APK dağıtım

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Kotlin Native (Jetpack Compose) | En iyi Android performansı, modern UI toolkit, ileride KMP ile iOS | — Pending |
| Cyberpunk tema | Web ile tutarlı marka kimliği | — Pending |
| Biyometrik + JWT | Güvenlik + kullanım kolaylığı | — Pending |
| wall.tonbilx.com üzerinden erişim | Mevcut altyapı, ek VPN gerekmez | — Pending |
| FCM push notification | Android standart bildirim altyapısı | — Pending |

---
*Last updated: 2026-03-06 after milestone v2.0 initialization*
