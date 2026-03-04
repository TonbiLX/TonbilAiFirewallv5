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
| Frontend Routing | App.tsx route + Sidebar nav item | TAMAMLANDI + DEPLOY |

**Yeni dosyalar (5):** security_config model, schema, API endpoint, securityApi.ts, SecuritySettingsPage.tsx
**Düzenlenen dosyalar (10):** models/__init__, router, main, threat_analyzer, dns_proxy, ddos_service, dns_fingerprint, types/index.ts, App.tsx, Sidebar.tsx
**Yedek:** `/opt/tonbilaios/backup-security-20260304-1529/`

## Aktif Milestone

Henüz yeni milestone belirlenmedi.

## Constraints

- **Platform**: Raspberry Pi 5 (ARM64, Debian Bookworm)
- **Ağ**: br0 = eth0 (WAN) + eth1 (LAN), wlan0 bridge'e eklenebilir
- **Deployment**: Paramiko SSH (pi.tonbil.com:2323 → 192.168.1.2)

---
*Last updated: 2026-03-04 after Security Settings deploy*
