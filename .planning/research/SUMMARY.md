# Research Summary — TonbilAiOS Android App

**Project:** TonbilAiOS v2.0 Android App
**Domain:** Kotlin Native Android router management/monitoring app
**Researched:** 2026-03-06
**Confidence:** HIGH

## Executive Summary

Samsung S24 Ultra icin Kotlin Native Android uygulamasi, mevcut TonbilAiOS v5 FastAPI backend'ine baglanarak tum router yonetim ve izleme ozelliklerini mobil platformda sunacak. Jetpack Compose + Material 3 ile cyberpunk tema, Ktor ile REST + WebSocket, BiometricPrompt ile biyometrik giris, FCM ile push bildirimler.

## Key Findings

### Recommended Stack

**Core:**
- Kotlin 2.3.10 + AGP 9.0.1 + Jetpack Compose BOM 2026.02.01
- Material 3 1.4.0 (darkColorScheme ile cyberpunk renk paleti)
- Navigation Compose 2.9.7 (type-safe routes)
- Ktor Client 3.4.1 (REST + WebSocket tek kutuphane)
- Koin 4.1.1 (dependency injection — Hilt'e gore daha az boilerplate)
- AndroidX Biometric 1.1.0 (parmak izi / yuz tanima)

**Data & State:**
- Room 2.7.1 (offline cache — bildirim gecmisi, cihaz listesi)
- DataStore Preferences 1.1.4 (ayarlar, JWT token)
- EncryptedSharedPreferences (hassas veri — token, credentials)

**Push Notifications:**
- Firebase BOM 33.9.0 + firebase-messaging
- Backend: Yeni FCM token endpoint + bildirim dispatch servisi gerekli

**Charting:**
- Vico 2.1.2 (Compose-native grafik kutuphanesi)

### Feature Table Stakes

Mobil router app'te OLMASI GEREKEN (yoksa kullanilmaz):
1. Dashboard — tek bakista ag durumu (bant genisligi, cihaz sayisi, tehdit)
2. Push Notifications (FCM) — mobil app'in #1 avantaji web'e karsi
3. Cihaz listesi + detay + engelleme (tek dokunusla)
4. Biyometrik giris (parmak izi / yuz)
5. Pull-to-refresh her ekranda
6. Canli veri akisi (WebSocket)
7. DNS filtreleme toggle (hizli acma/kapama)
8. Profil yonetimi + cihaza atama
9. Uzaktan erisim (wall.tonbilx.com)
10. Cyberpunk koyu tema

### Differentiators

Rakiplerden fark yaratan ozellikler:
- Home Screen Widget (Glance) — bant genisligi, cihaz, tehdit
- Quick Settings Tile — DNS toggle, cihaz engelleme
- AI Chat mobil — dogal dil ile ag yonetimi
- Per-device trafik gorsellistirme (grafikler)
- Bildirim kategorileri (Android channels)
- Auto-discovery (yerel/uzak otomatik gecis)

### Anti-Features (YAPILMAMALI)

- Offline mod (yaniltici eski veri)
- SSH terminal (guvenlik riski)
- Multi-router yonetimi (kapsam disi)
- Ozel tema editoru (gereksiz karmasiklik)
- Tablet optimize layout (tek kullanici, telefon oncelikli)

### Architecture

**Katman yapisi:**
```
UI Layer (Compose Screens + ViewModels)
    |
Domain Layer (Use Cases — opsiyonel)
    |
Data Layer (Repositories → Ktor API + Room Cache)
    |
Core (DI, Theme, Navigation, Auth)
```

**Build order onerisi:**
1. Proje iskelet + tema + navigasyon
2. Auth (biyometrik + JWT) + API client
3. Dashboard + WebSocket canli veri
4. Cihaz yonetimi ekranlari
5. DNS filtreleme + profiller
6. Firewall + VPN + DDoS ekranlari
7. Trafik izleme + grafikler
8. Push notifications (FCM backend + mobil)
9. AI Chat + Telegram ayarlari
10. Widget + Quick Settings + polish

### Critical Pitfalls

1. **WebSocket lifecycle**: ViewModel'de WebSocket acilip `onCleared()`'da kapatilmamasi — bellek sizintisi ve baglanti patlamasi
2. **JWT token race condition**: Dashboard acilisinda 5-6 paralel istek 401 alirsa cascading failure — Mutex ile tek refresh
3. **Biyometrik + token senkronizasyonu**: BiometricPrompt callback'i token'i EncryptedSharedPreferences'tan almali
4. **FCM token rotation**: Backend token guncelleme endpoint'i sart, yoksa bildirimler kaybolur
5. **Cyberpunk tema renk kontrastı**: Neon renkler kucuk metinlerde okunmaz — WCAG 4.5:1 kontrast orani zorunlu
6. **Buyuk ekran (S24 Ultra 6.8")**: WindowSizeClass ile adaptive layout

## Implications for Roadmap

- Backend'e 2-3 yeni endpoint gerekli: FCM token kayit, bildirim dispatch, bildirim gecmisi
- Mevcut REST API'ler degisiklik gerektirmiyor — app dogrudan tuketebilir
- WebSocket endpoint ayni (`/ws`) — ama mobil icin reconnect stratejisi sart
- wall.tonbilx.com uzerinden HTTPS zaten calisiyor — CORS veya ek yapilandirma gerekmez (native app, browser degil)
- Proje yerel gelistirme ortami: Android Studio + fiziksel S24 Ultra test

## Confidence Assessment

| Alan | Guven | Not |
|------|-------|-----|
| Stack | HIGH | Kotlin 2.3.10 + Compose BOM 2026.02.01 guncel ve stabil |
| Features | HIGH | Rakip analizi (UniFi, Firewalla, Nighthawk) ile dogrulanmis |
| Architecture | HIGH | Standart MVVM + Repository pattern, iyi dokumanlanmis |
| Pitfalls | HIGH | Android developer docs + community post-mortem'lerden |

---
*Research completed: 2026-03-06*
*Ready for requirements: yes*
