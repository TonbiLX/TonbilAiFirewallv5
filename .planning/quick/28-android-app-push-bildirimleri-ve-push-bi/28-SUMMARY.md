---
phase: quick-28
plan: 1
subsystem: push-notifications
tags: [android, backend, push, fastapi, kotlin, notifications]
dependency_graph:
  requires: [telegram-config, android-app-notifications-screen]
  provides: [push-api-endpoints, android-push-screen]
  affects: [backend-router, android-navigation]
tech_stack:
  added: []
  patterns: [fastapi-router, pydantic-schema, jetpack-compose-screen, koin-viewmodel]
key_files:
  created:
    - backend/app/schemas/push.py
    - backend/app/api/v1/push.py
    - deploy_quick28.py
    - deploy_quick28_result.txt
  modified:
    - backend/app/api/v1/router.py
    - android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsViewModel.kt
    - android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsScreen.kt
decisions:
  - Push kanallar Telegram bildirim config booleanlarini (notify_blocked_ip, notify_new_device vb.) saran bir abstraction katmani olarak tasarlandi
  - isRegistered placeholder olarak true set edildi (FCM entegrasyonu gelecekte tamamlanacak)
  - ArrowBack icin AutoMirrored variant kullanildi (deprecated uyarisini gidermek icin)
metrics:
  duration: "7 dakika"
  completed_date: "2026-03-10"
  tasks_completed: 3
  files_modified: 7
---

# Quick 28: Android Push Bildirimleri ve Backend Push API

**One-liner:** FastAPI push bildirim endpoint'leri (GET /channels, POST toggle, POST register) Telegram config uzerinden kanal tercihlerini yoneterek Pi'ye deploy edildi; Android PushNotificationsScreen geri butonu + Build.MODEL entegrasyonu ile iyilestirildi.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend push bildirim API endpoint'leri | 4f75903 | backend/app/schemas/push.py, backend/app/api/v1/push.py, backend/app/api/v1/router.py |
| 2 | Android PushNotifications ekranini iyilestir | 0ffeb43 | PushNotificationsViewModel.kt, PushNotificationsScreen.kt |
| 3 | Backend push endpoint'lerini Pi'ye deploy et | 419e978 | deploy_quick28.py, deploy_quick28_result.txt |

## What Was Built

### Backend Push API (`backend/app/api/v1/push.py`)

3 endpoint olusturuldu:

- **GET /api/v1/push/channels** — TelegramConfig'ten 4 sabit kanalı dondurur:
  - `security_threats` → `notify_blocked_ip`
  - `device_events` → `notify_new_device`
  - `trusted_ip_threats` → `notify_trusted_ip_threat`
  - `ai_insights` → `notify_ai_insight`

- **POST /api/v1/push/channels/{channel_id}/toggle** — Ilgili TelegramConfig boolean'ini tersine cevirir, `telegram_service.invalidate_cache()` cagirır

- **POST /api/v1/push/register** — FCM token kaydi (placeholder), gelecek entegrasyon icin hazır

Tum endpoint'ler `Depends(get_current_user)` ile JWT auth korumali.

### Pydantic Schemas (`backend/app/schemas/push.py`)

- `PushChannelResponse` — id, name, description, enabled
- `PushRegisterRequest` — token, platform, device_name
- `PushRegisterResponse` — success, message

### Android PushNotificationsScreen

- TopAppBar'a `navigationIcon` eklendi (AutoMirrored.Outlined.ArrowBack)
- `onRegister` lambdasi `Build.MODEL` kullanacak sekilde guncellendi (placeholder token yerine)
- "Kaydet" butonu "Etkinlestir" olarak degistirildi

### Android PushNotificationsViewModel

- `init` bloguna `checkRegistration()` eklendi
- `checkRegistration()`: isRegistered = true (backend her zaman success dondurdugu icin placeholder)

## Verification Results

Pi'de canlı test sonuclari:

```
GET /push/channels:
  - security_threats: Tehdit Bildirimleri (enabled=True)
  - device_events: Cihaz Bildirimleri (enabled=True)
  - trusted_ip_threats: Guvenilir IP Tehditleri (enabled=True)
  - ai_insights: AI Icgoruleri (enabled=False)
  4 kanal basariyla donduruldu

POST /push/channels/device_events/toggle:
  {"enabled":false} -- toggle calisiyor

POST /push/register:
  {"success":true,"message":"Token kaydedildi"}
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Deprecation] ArrowBack deprecated uyarisi giderildi**
- **Found during:** Task 2 Kotlin derleme testi
- **Issue:** `Icons.Outlined.ArrowBack` deprecated, Kotlin derleyicisi uyari verdi
- **Fix:** `Icons.AutoMirrored.Outlined.ArrowBack` kullanildi
- **Files modified:** PushNotificationsScreen.kt
- **Commit:** 0ffeb43

### Deploy Test Deviation

**Deploy scripti ilk calismada token alinamadi** — Deploy script calistiktan 5 saniye sonra backend hazir olmamisti. Manuel test ile dogrulandi; endpoint'ler calisıyor.

## Self-Check: PASSED

Olusturulan dosyalar:
- FOUND: backend/app/schemas/push.py
- FOUND: backend/app/api/v1/push.py
- FOUND: deploy_quick28.py
- FOUND: deploy_quick28_result.txt

Commitler:
- 4f75903: feat(quick-28): add push notification API endpoints
- 0ffeb43: feat(quick-28): improve Android PushNotifications screen
- 419e978: feat(quick-28): deploy push API to Pi and verify endpoints
