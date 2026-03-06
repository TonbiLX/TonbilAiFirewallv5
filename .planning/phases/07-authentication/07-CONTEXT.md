# Phase 7: Authentication - Context

**Gathered:** 2026-03-06
**Status:** Complete (retroaktif olusturuldu)

<domain>
## Phase Boundary

Kullanici guvenli bir sekilde hesabina erisebiliyor — sifre, biyometrik veya otomatik token ile. Sunucu baglantisi yerel/uzak arasinda otomatik gecis yapiyor. Yeni kullanici kendi basina kurulum yapabilecek sunucu ayarlari ekrani mevcut.

</domain>

<decisions>
## Implementation Decisions

### Token Depolama
- EncryptedSharedPreferences ile AES256_GCM MasterKey kullanilarak JWT token guvenli depolanir
- DataStore Preferences ile sunucu URL ve onboarding durumu persist edilir (SharedPreferences degil)
- Token CRUD: saveToken, getToken, clearToken, saveUserInfo, getUserInfo, isLoggedIn
- Biyometrik tercih ayri flag olarak saklanir (setBiometricEnabled/isBiometricEnabled)

### Sunucu Kesfetme (Auto-Discovery)
- 3 adimli kesif sirasi: lastConnectedUrl -> LOCAL_URL (192.168.1.2) -> BASE_URL (wall.tonbilx.com)
- Ilk basarili baglanti URL'si lastConnectedUrl olarak kaydedilir (hizli resume)
- Baglanti testi: GET dashboard/summary ile (interceptorsuz, kisa timeout: connect 3s, request 5s)
- Manuel URL degistirme: switchToUrl() ile sunucu ayarlari ekranindan

### Auth Interceptor
- Ktor 3.4.0 createClientPlugin API ile (deprecated HttpSend degil)
- onRequest: tokenManager.getToken() varsa Authorization: Bearer header eklenir
- onResponse: 401 gelirse tokenManager.clearToken() (token expired)
- Token refresh yok — backend 24 saat gecerli token veriyor, expired olunca login ekranina yonlendirilir

### Login Ekrani
- Cyberpunk temali: gradient arka plan, GlassCard form, neon cyan vurgular
- Username/password alanlari: OutlinedTextField, Person/Lock ikonlari, sifre goster/gizle toggle
- Hata mesajlari NeonRed renkte gosterilir
- IME action: username'de Next, password'da Done (login tetikler)
- Giris butonu: FilledTonalButton, NeonCyan, yukleme durumunda CircularProgressIndicator

### Biyometrik Auth
- BiometricHelper: AndroidX Biometric API, sadece BIOMETRIC_STRONG (DEVICE_CREDENTIAL fallback yok)
- Ilk basarili giristen sonra biyometrik prompt gosterilir (cihaz destekliyorsa)
- Donen kullanici: token gecerli + biyometrik enabled ise LoginScreen biometric-only modda acilir
- Biometric-only mod: buyuk parmak izi ikonu + "Dokunarak Giris Yap" + "Sifre ile giris" fallback butonu
- Biyometrik opsiyonel: hata olsa bile dashboard'a gecis yapilir

### Sunucu Ayarlari Ekrani
- 3 bolum: Otomatik Kesif, Hizli Secim (yerel/uzak), Manuel URL
- Baglanti testi sonucu: basarili (NeonGreen + check) veya basarisiz (NeonRed + hata)
- Basarili bağlantıdan 1.5 saniye sonra otomatik geri navigasyon
- "Sunucu Ayarlari" text butonu LoginScreen'den erisilebilir

### Navigasyon Auth Guard
- Token yoksa: LoginRoute baslangic destinasyonu
- Token var + biyometrik enabled: LoginRoute (biometric-only mod)
- Token var + biyometrik disabled: DashboardRoute (direkt giris)
- Login -> Dashboard gecisinde popUpTo(LoginRoute, inclusive=true) — geri butonuyla login'e donulmez
- Bottom nav: LoginRoute ve ServerSettingsRoute'ta gizlenir

### Koin DI Yapisi
- Named qualifier: test HttpClient (interceptorsuz, kisa timeout) vs ana HttpClient (auth interceptor + discovery)
- appModule: TokenManager, ServerConfig, ServerDiscovery, ana HttpClient, AuthRepository
- featureModules: LoginViewModel, ServerSettingsViewModel + mevcut 4 ViewModel

### Claude's Discretion
- Exact error message wording (Turkce)
- Animation timing details
- Keyboard dismiss behavior
- Focus management between fields

</decisions>

<specifics>
## Specific Ideas

- "Bunu bir urun olarak tasarliyoruz — baska bir kisi cihazi aldiginda ayarlari yapabilmeli" (Phase 6'dan)
- Donen kullanici deneyimi: biyometrik ile tek dokunusla giris, sifre alanlari gizli
- Sunucu kesfinde 3 adimli fallback: en son basarili -> yerel -> uzak

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- TokenManager (data/local/): JWT CRUD + kullanici bilgisi + biyometrik tercih
- ServerConfig (data/local/): DataStore ile sunucu URL + onboarding durumu
- ServerDiscovery (data/remote/): Yerel/uzak otomatik gecis
- AuthInterceptor (data/remote/): Ktor plugin — Bearer token injection + 401 handling
- AuthRepository (data/repository/): login/logout/getCurrentUser Result pattern
- BiometricHelper (feature/auth/): AndroidX Biometric sarmalayici
- GlassCard (ui/components/): Glassmorphism kart bileseni
- CyberpunkTheme (ui/theme/): Neon renk paleti + Material 3 darkColorScheme

### Established Patterns
- Result<T> pattern: repository katmaninda tum API cagrilari Result.success/Result.failure dondurur
- Named Koin qualifier: farkli HttpClient instance'lari ayirmak icin
- Auth-aware navigation: startDestination token durumuna gore belirlenir
- Conditional bottom nav: route tipine gore goster/gizle

### Integration Points
- Backend: POST /api/v1/auth/login (username + password -> JWT)
- Backend: GET /api/v1/auth/me (token dogrulama)
- Backend: POST /api/v1/auth/logout
- ApiRoutes: AUTH_LOGIN, AUTH_ME, AUTH_LOGOUT, AUTH_CHECK sabitleri

</code_context>

<deferred>
## Deferred Ideas

- Onboarding ekranlari (2 sayfa tanitim) — Phase 6 CONTEXT'te karar verildi ama henuz uygulanmadi. Ayri bir insert phase olarak eklenebilir.
- QR kod ile sunucu kesfetme — Phase 6 CONTEXT'te karar verildi, henuz uygulanmadi
- mDNS/LAN tarama — Phase 6 CONTEXT'te karar verildi, henuz uygulanmadi (ServerDiscovery sadece bilinen URL'leri deniyor)

</deferred>

---

*Phase: 07-authentication*
*Context gathered: 2026-03-06 (retroaktif)*
