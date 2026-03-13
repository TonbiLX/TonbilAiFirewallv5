---
phase: 14-android-enhancements
plan: 02
subsystem: android-haptic-shortcuts
tags: [android, haptic, shortcuts, deep-link, kotlin, ux]
dependency_graph:
  requires: [14-01]
  provides: [haptic-feedback, app-shortcuts, deep-link-navigation]
  affects: [android-app, TonbilApp, MainActivity, HapticHelper, ShortcutHelper]
tech_stack:
  added: []
  patterns:
    - ActivityLifecycleCallbacks ile WeakReference<Activity> takibi
    - View.performHapticFeedback ile izinsiz titresim (HapticFeedbackConstants)
    - ShortcutManagerCompat.setDynamicShortcuts ile 3 app shortcut
    - Intent.ACTION_VIEW + navigate_to extra ile deep link routing
key_files:
  created:
    - android/app/src/main/java/com/tonbil/aifirewall/util/HapticHelper.kt
    - android/app/src/main/java/com/tonbil/aifirewall/util/ShortcutHelper.kt
  modified:
    - android/app/src/main/java/com/tonbil/aifirewall/TonbilApp.kt
    - android/app/src/main/java/com/tonbil/aifirewall/MainActivity.kt
decisions:
  - HapticFeedbackConstants.REJECT critical icin, CONFIRM warning icin — izin gerektirmiyor
  - ActivityLifecycleCallbacks onActivityResumed/Paused ile WeakReference guncelleme — memory-safe
  - Arka plandayken haptic tetiklenmiyor — bildirim zaten vibrate pattern icerir
  - navigate_to deep link: giris yapildiysa dogrudan hedef, giris yapilmamissa normal akis
  - ShortcutManagerCompat: core-ktx 1.15.0 icerisinde — ek bagimlilik gerekmez
metrics:
  duration_minutes: 12
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 14 Plan 02: Haptic Feedback + App Shortcuts Ozeti

Kritik guvenlik olaylarinda dokunsal geri bildirim ve uygulama ikonundan hizli erisim kisayollari eklenerek native Android deneyimi tamamlandi.

## Ne Yapildi

### Task 1: Haptic Feedback Sistemi

- `HapticHelper` singleton olusturuldu:
  - `currentActivity: WeakReference<Activity>?` — memory-safe Activity tutma
  - `registerActivity` / `unregisterActivity` — ActivityLifecycleCallbacks ile otomatik guncelleme
  - `triggerHaptic(severity)`: "critical" → `REJECT` (guclu titresim), "warning" → `CONFIRM` (hafif titresim), diger → hic titresim yok
  - Hic Android izni gerektirmiyor (View.performHapticFeedback kullanir)
- `TonbilApp.onCreate`'e `ActivityLifecycleCallbacks` kaydedildi:
  - `onActivityResumed` → `HapticHelper.registerActivity(activity)`
  - `onActivityPaused` → `HapticHelper.unregisterActivity()`
- `TonbilApp.observeSecurityEvents`'e haptic tetikleme eklendi (bildirimden once)

### Task 2: App Shortcuts + Deep Link Isleme

- `ShortcutHelper` singleton olusturuldu — 3 dinamik kisayol:
  - `status_check` — Durum / "Ag Durumu" → dashboard
  - `device_block` — Cihazlar / "Cihaz Yonetimi" → devices
  - `ai_chat` — AI Chat / "AI Asistan" → chat
  - Her kisayolda `Intent.ACTION_VIEW` + `navigate_to` extra + `ic_splash_logo` ikonu
  - `ShortcutManagerCompat.setDynamicShortcuts` ile kayit
- `TonbilApp.onCreate`'e `ShortcutHelper.setupDynamicShortcuts(this)` eklendi
- `MainActivity.onCreate`'de deep link isleme:
  - `intent?.getStringExtra("navigate_to")` okunur
  - Kullanici giris yapmissa: "dashboard" → `DashboardRoute`, "devices" → `DevicesRoute`, "chat" → `ChatRoute`
  - Giris yapilmamissa veya navigateTo null ise normal Splash/Login akisi

## Dogrulamalar

- `./gradlew assembleDebug` — BUILD SUCCESSFUL (Task 1 temiz derleme + Task 2 artimsal 4s)
- HapticHelper WeakReference ile Activity tutulur — memory leak yok
- ActivityLifecycleCallbacks sadece resumed/paused'da tetiklenir — minimum overhead
- 3 shortcut sabit ID ile kayitli — pinned shortcut silinmez
- Deep link: giris yapildiysa dogrudan ekrana, yapilmamissa LoginRoute

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Build artifact bozulmasi**
- **Bulundu:** Task 1 ilk derleme denemesinde
- **Sorun:** `app/build/tmp/kotlin-classes/debug/` altinda bozuk dosya/dizin yapisi (snapshot hatasi)
- **Duzeltme:** `rm -rf app/build/` ile build klasoru temizlendi, sonraki derleme temiz gecti
- **Commit:** Task 1 icinde duzeltildi (ayri commit yapilmadi — derleme asamasi)

## Self-Check: PASSED

Olusturulan dosyalar:
- HapticHelper.kt: FOUND
- ShortcutHelper.kt: FOUND

Commitler:
- 27a38ad: feat(14-02): haptic feedback sistemi
- 55f1bff: feat(14-02): app shortcuts + MainActivity deep link isleme
