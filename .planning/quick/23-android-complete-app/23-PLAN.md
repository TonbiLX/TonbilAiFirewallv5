# Quick Task 23: Android App — Web Panel Tam Uyum

## Hedef
Web paneldeki TÜM 27 sayfanin, tüm toggle/CRUD/ayar/endpoint'lerin Android app'te karsiligi olacak.
Push Notification yonetim sayfasi da eklenecek.

## Mevcut Durum
- 6 ekran (Splash, Login, Dashboard, Devices, Security, Settings)
- ~44 API endpoint kullaniliyor (~160 mevcut)
- 51 Kotlin dosyasi, ~10,000 satir

## Hedef Durum
- ~25+ ekran (web panel ile 1:1)
- ~160 API endpoint kullanilacak
- Push Notification yonetimi
- FCM entegrasyonu

## Faz Yapisi

### Faz 1: Altyapi (Infrastructure)
- ApiRoutes.kt: ~116 yeni endpoint
- Yeni DTO dosyalari: VpnClient, ContentCategory, IpManagement, IpReputation, SecuritySettings, SystemMonitor, SystemManagement, SystemTime, Tls, AiSettings, SystemLogs, DeviceServices, PushNotification
- Repository genisletme: tum yeni CRUD methodlari
- AppModule.kt: yeni DI kayitlari

### Faz 2: Navigasyon Yeniden Yapilama
- Mevcut 4 bottom nav → 5 bottom nav (Panel, Cihaz, Ag, Guvenlik, Ayarlar)
- Her nav item → feature list (sub-navigation grid)
- NavRoutes.kt: ~20 yeni rota
- AppNavHost.kt: tum yeni destination'lar

### Faz 3: Yeni Ekranlar (Paralel - 8 Ajan)
**Ajan 1:** VpnClientScreen (sunucu CRUD, baglan/kes, import)
**Ajan 2:** ContentCategoriesScreen (kategori CRUD, blocklist baglama)
**Ajan 3:** DeviceServicesScreen (servis grid, per-service toggle)
**Ajan 4:** IpManagementScreen + IpReputationScreen
**Ajan 5:** SecuritySettingsScreen (5 tab: tehdit, DNS, uyari, guvenilir IP, istatistik)
**Ajan 6:** SystemMonitorScreen + SystemManagementScreen
**Ajan 7:** SystemTimeScreen + TlsScreen + AiSettingsScreen + SystemLogsScreen
**Ajan 8:** PushNotificationScreen + UserSettingsScreen (sifre degistir)

### Faz 4: Mevcut Ekran Duzeltmeleri (Paralel - 4 Ajan)
**Ajan A:** SecurityScreen DDoS toggle fix + Firewall edit
**Ajan B:** DevicesScreen (search, scan, IPTV) + DeviceDetailScreen
**Ajan C:** DNS (query logs, lookup, refresh) + DHCP (pool CRUD) + WiFi (guest/schedule/MAC)
**Ajan D:** Traffic (large transfers, history, filters) + Chat (clear, markdown) + Profiles (edit, categories)

### Faz 5: Entegrasyon + Build
- Navigasyon wiring
- Derleme hatalari duzeltme
- APK build
- Git commit

## Dosya Yapisi (Hedef)

```
feature/
├── auth/           (mevcut)
├── dashboard/      (mevcut)
├── devices/        (mevcut + services)
├── splash/         (mevcut)
├── security/       (mevcut, genisletilecek)
├── settings/       (mevcut, genisletilecek)
├── vpnclient/      (YENi)
├── categories/     (YENi)
├── ipmanagement/   (YENi)
├── ipreputation/   (YENi)
├── securitysettings/ (YENi)
├── systemmonitor/  (YENi)
├── systemmanagement/ (YENi)
├── systemtime/     (YENi)
├── tls/            (YENi)
├── aisettings/     (YENi)
├── systemlogs/     (YENi)
├── insights/       (YENi)
├── notifications/  (YENi - Push)
├── usersettings/   (YENi)
├── ddosmap/        (YENi)
└── traffic/        (YENi - ayri ekran)
```

## Tarih
Baslanma: 2026-03-10
