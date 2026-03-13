---
phase: 14-android-enhancements
plan: 01
subsystem: android-widget-tiles
tags: [android, glance, widget, quick-settings, workmanager, kotlin]
dependency_graph:
  requires: []
  provides: [glance-widget, dns-filter-tile, device-block-tile]
  affects: [android-app, TonbilWidget, DnsFilterTileService, DeviceBlockTileService]
tech_stack:
  added:
    - glance-appwidget 1.1.0
    - glance-material3 1.1.0
    - work-runtime-ktx 2.9.1
  patterns:
    - GlanceAppWidget + DataStore ile widget render
    - TileService + CoroutineScope (SupervisorJob) ile QS tile
    - PreferenceDataStoreFactory ile baska DataStore'dan okuma (worker/tile icin)
key_files:
  created:
    - android/app/src/main/java/com/tonbil/aifirewall/widget/TonbilWidget.kt
    - android/app/src/main/java/com/tonbil/aifirewall/widget/TonbilWidgetReceiver.kt
    - android/app/src/main/java/com/tonbil/aifirewall/widget/TonbilWidgetWorker.kt
    - android/app/src/main/java/com/tonbil/aifirewall/tile/DnsFilterTileService.kt
    - android/app/src/main/java/com/tonbil/aifirewall/tile/DeviceBlockTileService.kt
    - android/app/src/main/res/xml/tonbil_widget_info.xml
    - android/app/src/main/res/drawable/ic_dns_tile.xml
    - android/app/src/main/res/drawable/ic_device_block_tile.xml
  modified:
    - android/gradle/libs.versions.toml
    - android/app/build.gradle.kts
    - android/app/src/main/AndroidManifest.xml
    - android/app/src/main/java/com/tonbil/aifirewall/TonbilApp.kt
decisions:
  - Widget DataStore ayri "tonbil_widget" adinda — server_config ile cakismiyor
  - TonbilWidgetWorker ve TileService'ler Koin DI kullanmiyor — context guvenilirligi icin dogrudan HttpClient
  - PreferenceDataStoreFactory.create ile baska DataStore'dan okuma (extension property yerine)
  - DNS toggle: 4 alan birden (dnssec + tunneling + doh + dga) — backend tek boolean sunmuyor
  - DeviceBlockTile: onStartListening'de guncel liste API'den cekilir, state in-memory tutulur
  - WorkManager KEEP politikasi: uygulama her basladikta var olan is korunur, duplike olusmaz
metrics:
  duration_minutes: 25
  completed_date: "2026-03-13"
  tasks_completed: 3
  files_created: 8
  files_modified: 4
---

# Phase 14 Plan 01: Glance Widget + Quick Settings Tile'lari Ozeti

Glance API ile cyberpunk temali ana ekran widget'i ve Quick Settings panelinde DNS filtreleme + cihaz engelleme tile'lari olusturuldu.

## Ne Yapildi

### Task 1: Glance Widget + WorkManager Altyapisi

- `glance-appwidget 1.1.0`, `glance-material3 1.1.0`, `work-runtime-ktx 2.9.1` bagimliliklari eklendi
- `TonbilWidget`: GlanceAppWidget — ayrı `tonbil_widget` DataStore'dan veri okur, cyberpunk renk paleti kullanir (cyan baslik, neon red tehdit, yesil bandwidth). Tiklaninca MainActivity acar.
- `TonbilWidgetReceiver`: GlanceAppWidgetReceiver — widget sisteme kayitli alici
- `TonbilWidgetWorker`: CoroutineWorker — EncryptedSharedPreferences'tan token, server_config DataStore'dan URL okur; Ktor ile dashboard/summary ceker; DataStore'a yazar; aktif widget instance'larini gunceller
- `tonbil_widget_info.xml`: 180x80dp minimum, yatay+dikey resize, updatePeriodMillis=0 (WorkManager kontrollu)
- `TonbilApp.onCreate()`: CONNECTED constraint ile 15 dakika periyodik WorkManager isi planlamasi (KEEP politikasi)
- AndroidManifest: widget receiver + APPWIDGET_UPDATE intent-filter

### Task 2: Quick Settings DNS Filtre Tile

- `ic_dns_tile.xml`: kalkan + filtre fonksiyonu VectorDrawable (24dp, beyaz)
- `DnsFilterTileService`: TileService — onStartListening'de GET security/config; dnssec + dns_tunneling + doh + dga alanlarinin hepsi true ise STATE_ACTIVE; onClick'te 4 alani birden PATCH ile toggle; onDestroy'da serviceScope.cancel()
- AndroidManifest: BIND_QUICK_SETTINGS_TILE permission + TOGGLEABLE_TILE meta-data

### Task 3: Quick Settings Cihaz Engelleme Tile

- `ic_device_block_tile.xml`: cihaz + engelleme simgesi VectorDrawable (24dp, beyaz)
- `DeviceBlockTileService`: TileService — onStartListening'de GET devices, is_blocked=true olan ilk cihazi STATE_ACTIVE ile goster; onClick'te POST deviceUnblock ile engeli kaldir; engellenmis cihaz yoksa STATE_INACTIVE + "Engelli yok"
- AndroidManifest: BIND_QUICK_SETTINGS_TILE permission + TOGGLEABLE_TILE meta-data

## Teknik Kararlar

**Widget DataStore ayrimasi:** `preferencesDataStore(name = "tonbil_widget")` — ServerConfig'in `"server_config"` DataStore'u ile kesinlikle cakismaz. Ayni Context uzerinde iki farkli DataStore instance'i calisir.

**Koin-free HttpClient:** Widget Worker ve TileService'ler bagimsiz Android component olarak calisabilir (uygulama sureci olmayabilir). Dogrudan `HttpClient(OkHttp) {}` olusturulur, `httpClient.close()` onDestroy'da cagirilir.

**PreferenceDataStoreFactory pattern:** Worker/Tile icinde server_config DataStore'a erisim icin `PreferenceDataStoreFactory.create { context.preferencesDataStoreFile("server_config") }` kullanildi. Bu, `preferencesDataStore` extension property tanimlamadan baska bir DataStore dosyasini acmak icin standart yontemdir.

**DNS toggle mantigi:** Backend birkac ayri alani yonetiyor (dnssec_enabled, dns_tunneling_enabled, doh_enabled + threat_analysis.dga_detection_enabled). SecurityConfigUpdateDto'nun flat nullable alanlari ile 4 alan ayni anda guncelleniyor.

## Dogrulamalar

- `./gradlew assembleDebug` — BUILD SUCCESSFUL (3 gorev sonrasinda)
- AndroidManifest: widget receiver + 2 tile service kayitli
- Widget DataStore "tonbil_widget" adinda, server_config ile cakismiyor
- Glance import'lari tamamen `androidx.glance.*` (compose.material3 karisimi yok)
- Her iki tile service coroutine scope SupervisorJob + Dispatchers.IO ile yonetiliyor, onDestroy'da iptal ediliyor

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Build artifact bozulmasi**
- **Bulundu:** Task 1 dogrulamasi sirasinda
- **Sorun:** `app/build/intermediates/merged_res_blame_folder/` altinda bozuk dosya/dizin yapisi
- **Duzeltme:** `rm -rf app/build/` ile build klasoru temizlendi, sonraki derleme temiz gecti
- **Commit:** tek seferlik (derleme asamasinda)

**2. [Rule 1 - Bug] DashboardSummaryDto alan referansi hatasi**
- **Bulundu:** Task 1 ilk derleme denemesinde
- **Sorun:** `summary.dns.topBlockedDomains` — bu alan DnsSummaryDto'da degil, DashboardSummaryDto'da dogrudan
- **Duzeltme:** `summary.topBlockedDomains.firstOrNull()?.domain` olarak duzeltildi
- **Commit:** duzeltme ayni gorev icinde

**3. [Rule 1 - Bug] GlanceAppWidget.updateAll() API farki**
- **Bulundu:** Task 1 ilk derleme denemesinde
- **Sorun:** `TonbilWidget().updateAll(context)` — Glance 1.1.0'da bu metot yok
- **Duzeltme:** `GlanceAppWidgetManager.getGlanceIds()` + `widget.update(context, glanceId)` pattern'ine gecildi

## Self-Check: PASSED
