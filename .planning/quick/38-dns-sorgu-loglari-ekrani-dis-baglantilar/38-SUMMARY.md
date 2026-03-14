---
phase: quick
plan: 38
subsystem: android-dns-external-connections
tags: [android, dns, external-connections, dot, doh, dns-bypass, web-panel]
key-decisions:
  - DnsQueryLogDto mevcut ayrı dosyada vardı — SecurityDtos.kt'ye duplicate eklenmedi, mevcut dosyaya yeni alanlar eklendi (id, source_type, device_id, block_reason)
  - DeviceRepository'de wrapper response parse için Json.decodeFromJsonElement kullanıldı
  - Device modeli os_type değil device_type içeriyor — endpoint'te buna göre düzeltildi
  - DnsBlockingScreen tab sistemi: 0=İstatistik, 1=Listeler, 2=Kurallar, 3=Sorgular
  - Sorgular tab lazy yükleme: sadece ilk kez açıldığında API çağrısı yapılır
  - Dış Bağlantılar: collapsible panel hem Android hem web'de, 1 saatlik pencere
key-files:
  created:
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/DnsQueryLogDto.kt (güncellendi — yeni alanlar)
  modified:
    - android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/SecurityDtos.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/repository/SecurityRepository.kt
    - android/app/src/main/java/com/tonbil/aifirewall/data/repository/DeviceRepository.kt
    - android/app/src/main/java/com/tonbil/aifirewall/feature/dnsblocking/DnsBlockingViewModel.kt
    - android/app/src/main/java/com/tonbil/aifirewall/feature/dnsblocking/DnsBlockingScreen.kt
    - android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DevicesViewModel.kt
    - android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DevicesScreen.kt
    - backend/app/api/v1/devices.py
    - frontend/src/pages/DevicesPage.tsx
    - frontend/src/services/deviceApi.ts
metrics:
  duration: ~30 min
  completed_date: "2026-03-14"
  tasks_completed: 3
  files_changed: 10
  commits: 4
---

# Quick Task 38: DNS Sorgu Logları + Dış Bağlantılar Tespiti — Özet

**Bir cümle:** Android'e DNS sorgu log tab'ı eklendi, backend'e DoT/DoH/DNS bypass tespiti endpoint'i yazılıp deploy edildi, hem Android hem web panele "Dış Bağlantılar" collapsible paneli eklendi.

## Yapılanlar

### Görev 1: Android DNS Sorgu Log Tab'ı

**DnsQueryLogDto güncellemesi (`DnsQueryLogDto.kt`):**
- `id`, `source_type` (INTERNAL/EXTERNAL/DOT), `device_id`, `block_reason` alanları eklendi
- Mevcut dosya güncellendi — SecurityDtos.kt'ye duplicate eklenmedi

**ExternalDnsConnectionDto (`SecurityDtos.kt`):**
- detection_type, dst_ip, dst_port, mac_address, hostname, os_type alanları ile yeni DTO

**SecurityRepository (`SecurityRepository.kt`):**
- `getDnsQueries(limit, blockedOnly, domainSearch)` eklendi — Ktor url parametreleri ile

**DnsBlockingViewModel (`DnsBlockingViewModel.kt`):**
- `queries`, `queriesLoading`, `queriesBlockedOnly`, `queriesDomainSearch` state alanları
- `loadQueries()`, `setQueriesBlockedOnly()`, `setQueriesDomainSearch()`, `applyQueriesSearch()`

**DnsBlockingScreen (`DnsBlockingScreen.kt`):**
- 4 tab sisteme dönüştürüldü: İstatistik / Listeler / Kurallar / Sorgular
- Sorgular tab: arama çubuğu + "sadece engellenenler" switch + DnsQueryLogCard
- DnsQueryLogCard: domain, IP, zaman, ENGELLENDI/IZIN badge, INTERNAL/EXTERNAL/DOT badge

### Görev 2: Backend Dış Bağlantılar Endpoint

**`GET /api/v1/devices/external-dns-connections` (`devices.py`):**
- DoT: dst_port == 853
- DoH: dst_port == 443 + 10 bilinen DoH IP (Google/Cloudflare/Quad9/OpenDNS/AdGuard)
- DNS Bypass: dst_port == 53 + dst_ip != 192.168.1.2 (Pi IP)
- connection_flows tablosundan son N saati sorgular
- Duplicate önleme (src_ip + dst_ip + dst_port + type key ile)
- Cihaz bilgisi (hostname, mac_address, device_type) Device tablosundan join

Deploy: SSH ProxyJump ile Pi'ye aktarıldı, `systemctl is-active` = active onaylandı.

### Görev 3: Android + Web "Dış Bağlantılar" UI

**Android:**
- `DeviceRepository.getExternalDnsConnections()` eklendi
- `DevicesViewModel`: externalConnections state, toggle + lazy load
- `DevicesScreen`: `ExternalConnectionsPanel` composable — collapsible, başlık satırında count badge
  - `ExternalConnectionRow`: DoT=mor, DoH=amber, DNS Bypass=kırmızı renk kodlaması
  - Hostname/IP + MAC + hedef IP:port gösterimi

**Web Panel:**
- `deviceApi.ts`: `fetchExternalDnsConnections()` eklendi
- `DevicesPage.tsx`: sayfa altında collapsible "Dış Bağlantılar" GlassCard
  - Tablo: Tespit Türü | Cihaz | MAC | Cihaz Tipi | Hedef IP | Port | Son Görülme
  - Cyberpunk tema uyumlu renkler (DoT=mor, DoH=amber, DNS Bypass=kırmızı)
  - Manuel yenileme butonu ve count badge

Frontend build + Pi'ye deploy tamamlandı.

## Commitler

| Hash | Açıklama |
|------|----------|
| 3201c15 | feat(38): DNS query log tab to DnsBlockingScreen |
| 708f55c | feat(38): external-dns-connections backend endpoint + deploy |
| bb5da38 | feat(38): external connections UI on Android + web panel |

## Deviasyonlar

**[Rule 1 - Bug] DnsQueryLogDto duplicate tespit edildi**
- Bulundu: Görev 1 sırasında SecurityDtos.kt'ye DTO eklenmeye çalışıldı
- Sorun: `DnsQueryLogDto.kt` ayrı dosyada zaten mevcut — build'de `Redeclaration` hatası
- Düzeltme: SecurityDtos.kt'deki duplicate kaldırıldı, mevcut dosyaya yeni alanlar eklendi
- Commit: 3201c15 içinde

**[Rule 2 - Missing] `refreshAllBlocklists` duplicate fonksiyon eklendi**
- SecurityRepository'de zaten `refreshAllBlocklists()` mevcuttu (farklı dönüş tipi ile)
- Eklenen duplicate kaldırıldı — mevcut metot korundu

## Self-Check: PASSED

- Tüm commitler mevcut: 3201c15, 708f55c, bb5da38
- SUMMARY.md oluşturuldu
- Android build hatasız tamamlandı (BUILD SUCCESSFUL)
- Backend deploy: active
- Frontend build: 8.55s, hatasız
