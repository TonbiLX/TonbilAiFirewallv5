# Pitfalls Research

**Domain:** Android Router Management App (Kotlin + Jetpack Compose)
**Researched:** 2026-03-06
**Confidence:** HIGH (Android developer docs, community post-mortems, well-documented Compose/OkHttp/FCM patterns)

---

## Critical Pitfalls

### Pitfall 1: WebSocket Baglantisi Lifecycle ile Senkronize Degil — Bellek Sizintisi ve Crash

**What goes wrong:**
WebSocket baglantisi Activity/Fragment lifecycle'ina baglanir, ama Compose'da lifecycle farklidir. ViewModel'de WebSocket acilir ama `onCleared()` sirasinda duzgun kapatilmaz. Veya daha kotu: Configuration change (ekran dondurme) sirasinda WebSocket yeniden acilir, eski baglanti kapanmaz — her dondurme yeni bir WebSocket yaratir, sunucu tarafinda baglanti sayisi patlar.

TonbilAiOS backend'i WebSocket uzerinden bandwidth, DNS, cihaz verisi gonderiyor (5 saniyede bir). Samsung S24 Ultra'da ekran dondurme, split-screen, picture-in-picture gibi durumlar sik yasanir.

**Why it happens:**
Compose'da ViewModel varsayilan olarak configuration change'lerde hayatta kalir, ama WebSocket baglantisini ViewModel constructor'inda acan gelistiriciler, `onCleared()` cagirilana kadar (Activity tamamen yok edilene kadar) baglantinin actik kaldigini varsayar. Sorun su: eger navigation graph degisirse veya composable scope degisirse, ViewModel yeniden yaratilabilir — eski WebSocket kapanmaz.

**How to avoid:**
1. WebSocket baglantilarini `OkHttpClient` + `WebSocketListener` ile yonet, ViewModel icinde `viewModelScope` coroutine'i ile bagla.
2. `onCleared()` icinde `webSocket.close(1000, "ViewModel cleared")` cagir — bu ZORUNLU.
3. SharedFlow kullan (replay=0) — yeni subscriber geldiginde eski veriyi tekrar gondermez.
4. Baglanti durumunu StateFlow olarak expose et (`Connecting`, `Connected`, `Disconnected`, `Error`).
5. Network durumu degistiginde (WiFi -> mobil) WebSocket'i yeniden baglama mekanizmasi ekle — exponential backoff ile.

**Warning signs:**
- Backend loglarinda ayni cihazdan birden fazla WebSocket baglantisi gorulur
- Uygulama bellek kullaniminin zaman icinde arttigi gorulur (LeakCanary ile)
- Ekran dondurdukten sonra veri iki kez gelir
- Backend WebSocket handler'inda connection count artip dusmez

**Phase to address:** WebSocket/real-time veri fazi — ViewModel lifecycle yonetimi ilk gun dogru kurulmali, sonradan duzeltmek cok zor.

---

### Pitfall 2: JWT Token Yenileme Yarisi (Race Condition) — Paralel Isteklerde 401 Cascading Failure

**What goes wrong:**
Access token suresi dolmus, birden fazla API istegi ayni anda gonderilir (dashboard acildiginda 5-6 endpoint ayni anda cagirilir). Ilk istek 401 alir ve refresh token ile yenileme baslatir. Ama diger 4-5 istek de ayni anda 401 alir ve hepsi ayni anda refresh token ile yenileme denemesi yapar. Backend sadece ilk refresh'i kabul eder, digerlerini reddeder — kullanici login ekranina atilir.

TonbilAiOS dashboard'u acildiginda en az 6 paralel istek gider: summary, devices, dns-stats, bandwidth, vpn-status, firewall-rules. Hepsi ayni anda 401 alirsa kaos baslar.

**Why it happens:**
OkHttp Interceptor'da token yenileme kodu `synchronized` degil. Her 401 response kendi refresh istegiini baslatir. Backend tarafinda refresh token rotation aktifse (guvenlik icin olmali), ilk refresh sonrasi eski refresh token gecersiz olur — diger istekler basarisiz olur.

**How to avoid:**
1. OkHttp `Authenticator` interface'ini kullan (Interceptor degil) — OkHttp 401'de otomatik olarak Authenticator'u cagiriyor.
2. Authenticator icinde `synchronized` blok veya `Mutex` (coroutine) kullan — ayni anda sadece bir refresh istegi yapilsin.
3. Refresh sirasinda bekleyen diger istekler yeni token'i alsn ve tekrar denensin.
4. Refresh basarisiz olursa (refresh token da gecersizse), kullaniciyi login'e yonlendir — ama sadece bir kez, cascading 401'lerin hepsi icin degil.
5. Token'i EncryptedSharedPreferences'ta sakla (Android Keystore-backed AES256).

**Warning signs:**
- Kullanici dashboard'a girdiginde rastgele login ekranina atiliyor
- Backend loglarinda ayni device'tan saniyeler icinde birden fazla refresh token istegi
- "Token expired" hatasi uygulamayi kullanirken sik sik cikiyor
- Race condition debug'u zor — "bazen calisiyor bazen calismiyor" semptomu

**Phase to address:** Auth/networking altyapi fazi — bu ILKE cozulmeli, UI'dan once. Interceptor/Authenticator dogru yazilmazsa her sayfa etkilenir.

---

### Pitfall 3: FCM Token Yonetimi Eksik — Push Bildirimler Sessizce Calismaz Hale Gelir

**What goes wrong:**
FCM token uygulama ilk kurulumda alinir ve backend'e gonderilir. Ama FCM token'i degisebilir: uygulama yeniden kurulma, uygulama verileri silinme, cihaz restore, veya Google'in periyodik token yenileme yapmasindan dolayi. Token degistiginde backend eski token'a gondermeye devam eder — bildirimler sessizce kaybolur, hata donmez (FCM "basarili" der ama cihaza ulasmaz).

Ayrica: Doze mode ve App Standby, normal oncelikli mesajlari geciktirir veya toplu gonderir. Kullanici "DDoS saldirisi var" bildirimini 2 saat sonra alir — bu bir router yonetim uygulamasi icin kabul edilemez.

**Why it happens:**
- FCM token degisikligini dinleyen `onNewToken()` callback'i implement edilmez veya backend'e yeni token'i gondermez.
- Backend eski token'lari temizlemez — `NotRegistered` hatasini ignore eder.
- Mesaj onceligi `normal` olarak gonderilir (varsayilan) — `high` olmasi gereken guvenlik bildirimleri Doze'da gecikir.

**How to avoid:**
1. `FirebaseMessagingService.onNewToken()` override et — her token degisikliginde backend'e yeni token'i POST et.
2. Uygulama her acildiginda `FirebaseMessaging.getInstance().token` ile guncel token'i al ve backend ile karsilastir.
3. Backend'te FCM gonderim sonucunda `NotRegistered` veya `InvalidRegistration` hatasi gelirse, o token'i DB'den sil.
4. DDoS, guvenlik alarmi gibi acil bildirimler icin `priority: "high"` kullan — Doze mode'da bile aninda teslim edilir.
5. Backend'te `POST /api/v1/devices/fcm-token` endpoint'i ekle — token kayit ve guncelleme icin.
6. Notification channel'lari dogru kur: `IMPORTANCE_HIGH` ile ses ve titresim, `IMPORTANCE_DEFAULT` ile normal bildirimler.

**Warning signs:**
- Kullanici "bildirim gelmiyor" diyor ama backend "basariyla gonderildi" logluyor
- FCM console'da token gecersiz hatalari birikiyor
- Uygulama yeniden kurulduktan sonra bildirimler calismaz hale geliyor
- Acil guvenlik bildirimleri dakikalarca gecikiyor

**Phase to address:** Push notification fazi — backend endpoint + Android service ayni fazda yapilmali. Token lifecycle ILKE dogru kurulmazsa sonradan duzeltmek cok zor.

---

### Pitfall 4: Self-Signed veya Ozel Sertifika ile HTTPS Baglanti — CertPathValidatorException

**What goes wrong:**
wall.tonbilx.com Let's Encrypt veya baska bir CA sertifikasi kullaniyorsa sorun yok. Ama eger self-signed veya ozel CA sertifikasi varsa, Android varsayilan olarak guvenmiyor — `SSLHandshakeException: CertPathValidatorException: Trust anchor for certification path not found` hatasi aliyor. Gelistirici "cozum" olarak TrustManager'i bypass eder (tum sertifikalari kabul et) — bu MITM saldirisi kapisi acar.

Yerel agda 192.168.1.2'ye HTTP ile baglanmak da ayri bir sorun: Android 9+ varsayilan olarak cleartext HTTP'yi reddeder.

**Why it happens:**
- Test sirasinda "hizli cozum" olarak `X509TrustManager` override edilir, uretimde kalir.
- Yerel ag icin HTTP kullanmak istenir ama `android:usesCleartextTraffic="true"` eklenir — bu TUM domainler icin cleartext'i acar, sadece yerel ag icin degil.
- Certificate pinning yapilmaz — sertifika degistiginde uygulama kirilir.

**How to avoid:**
1. wall.tonbilx.com icin Let's Encrypt sertifikasi kullan (ucretsiz, otomatik yenileme) — Android buna varsayilan olarak guvenir, ek konfigurasyon gereksiz.
2. Yerel ag icin `res/xml/network_security_config.xml` kullan — sadece 192.168.1.0/24 icin cleartext izni ver, diger domainler icin HTTPS zorunlu kalsin.
3. ASLA `TrustManager` bypass etme — bunun yerine sertifikayi Android trust store'a ekle veya network security config ile pin'le.
4. Certificate pinning'i dikkatlice kullan: pin yenileme stratejisi olmadan pinning yapmak, sertifika yenilendiginde uygulamanin tamamen calismaz hale gelmesine neden olur. Backup pin ekle.

**Warning signs:**
- Kodda `TrustAllCerts`, `ALLOW_ALL_HOSTNAME_VERIFIER`, veya `hostnameVerifier = { _, _ -> true }` gorulur
- AndroidManifest'te global `usesCleartextTraffic="true"` var
- Sertifika yenileme sonrasi uygulama aniden baglanamaz hale gelir (pinning sorunu)

**Phase to address:** Networking altyapi fazi (ilk faz) — OkHttp client konfigurasyonu projenin temeli, yanlis baslangic her seyi etkiler.

---

### Pitfall 5: Compose Recomposition Patlamasi — Canli Veri Gosterimine Jank ve Battery Drain

**What goes wrong:**
Dashboard'da bandwidth grafigi, canli akislar, cihaz listesi gibi veriler 3-5 saniyede bir guncelleniyor. Her guncelleme tum ekranin recompose edilmesine neden olur — fps duser, ScrollState kaybolur, animasyonlar takilir. Samsung S24 Ultra'nin 120Hz ekraninda bu ozellikle goze carpar.

Daha kotu: LazyColumn icinde `items()` kullanirken `key` parametresi verilmez — her guncelleme tum listeyi sifirdan olusturur, scroll pozisyonu kaybolur.

**Why it happens:**
- State degisikligi root composable'da okunur — tum alt agac recompose olur.
- `List<Flow>` gibi unstable tipler kullanilir — Compose bunlari her zaman "degismis" olarak isler.
- WebSocket'ten gelen her mesaj yeni bir `List` objesi yaratir — referans esitligi (===) saglanamaz, icerik ayni olsa bile recompose tetiklenir.
- `derivedStateOf` kullanilmaz — her state degisikligi UI'yi tetikler.

**How to avoid:**
1. State'i olabildigince dar scope'ta oku — `BandwidthChart` composable'i sadece bandwidth state'ini okusun, device listesi okumasi.
2. LazyColumn/LazyRow'da HER ZAMAN `key = { it.id }` kullan.
3. Data class'lari `@Immutable` veya `@Stable` ile annote et — Compose smart recomposition yapabilsin.
4. Sik degisen veriler icin `derivedStateOf` kullan — sadece sonuc degistiginde recompose tetikle.
5. `snapshotFlow` ile Flow -> Compose State donusumunu kontrol et.
6. Compose compiler metrics'i aktif et (`composeCompiler { metricsDestination }`) — hangi composable'larin skip edilemedigini gor.

**Warning signs:**
- Layout Inspector'da gereksiz recomposition sayilari gorulur
- Canli veri gosterimi sirasinda UI kasmalari (jank)
- ScrollState surekli sifirlaniyor (liste basina atlama)
- Batarya tuketimi yuksek (surekli UI render)
- Profiler'da Compose fase sureleri normalin 3-4 kati

**Phase to address:** UI/Dashboard fazi — ilk composable'lardan itibaren dogru pattern kullanilmali. Sonradan optimize etmek "her seyi refactor et" demek.

---

### Pitfall 6: Yerel Ag vs Dis Ag Gecisi — Dual Endpoint Yonetimi Karmasikligi

**What goes wrong:**
Uygulama ev agindayken 192.168.1.2'ye dogrudan, disaridayken wall.tonbilx.com uzerinden baglanmali. Gelistirici base URL'i sabit yapar (birini secer) — ya evde ya disarida calismaz. Veya kullanici WiFi'dan mobil veriye gectiginde uygulama hala yerel IP'ye baglanmaya calisiyor — timeout, sonra crash.

WebSocket icin bu daha da kritik: yerel agda `ws://192.168.1.2:8000/ws`, disarida `wss://wall.tonbilx.com/ws`. Baglanti kopunca yeniden baglanma hangi endpoint'e yapilacak?

**Why it happens:**
- Ag degisikligi dinlenmez — uygulama baslangicdaki ag durumunu varsayar.
- ConnectivityManager callback'i kullanilmaz veya yanlis implement edilir.
- Base URL degisikligi sirasinda aktif istekler basarisiz olur ve retry mekanizmasi yoktur.

**How to avoid:**
1. `ConnectivityManager.registerDefaultNetworkCallback()` ile ag degisikliklerini dinle.
2. Ag degistiginde, once yerel IP'ye ping at (timeout 2 saniye) — basariliysa yerel, degilse dis endpoint kullan.
3. OkHttp Interceptor ile base URL'i dinamik olarak degistir — her istek icin gecerli endpoint'i sec.
4. WebSocket kopunca, yeniden baglanmada once yerel sonra dis endpoint dene.
5. Kullaniciya ag durumunu goster: "Yerel Ag" (yesil) vs "Dis Ag" (sari) badge.
6. Her iki endpoint icin de ayni auth token gecerli olmali — backend ayni oldugu icin sorun yok.

**Warning signs:**
- Kullanici WiFi'dan cikinca uygulama 30 saniye takilip timeout veriyor
- Evden ciktiktan sonra uygulama calismaz hale geliyor (yerel IP'ye takili kalmis)
- WebSocket baglantisi WiFi degisikliginden sonra geri gelmiyor
- "Baglanti hatasi" mesaji sik gorulur ama internet calisiyor

**Phase to address:** Networking altyapi fazi — bu mimari karar ilk fazda dogru alinmali. Sonradan iki endpoint yonetimi eklemek tum API katmanini etkiler.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Tum API cagrilarini Activity/Fragment'ta yapmak, ViewModel kullanmamak | Hizli prototip | Configuration change'de veri kaybi, bellek sizintisi, test edilemez kod | Never — Compose ile ViewModel zorunlu |
| Hardcoded base URL (`http://192.168.1.2:8000`) | Hizli gelistirme | Dis agdan erisim impossible, build variant gerektirir | Sadece ilk prototip icin, 1 hafta icinde refactor |
| `TrustAllCerts` ile HTTPS bypass | Test sirasinda kolaylik | MITM saldiri kapisi, Play Store red riski | Never — network_security_config kullan |
| WebSocket reconnect olmadan tek baglanti | Basit implementasyon | Ag degisikliginde kalici baglanti kopuklugu | Never — reconnect mekanizmasi ilk gunden olmali |
| Tum notification'lari tek channel'da gostermek | Az kod | Kullanici onemli/onemsiz bildirimleri ayiramaz, ses/titresim kontrolu yok | Sadece ilk prototip, 2. fazda channel'lara bol |
| Biometric auth'u sadece local gate olarak kullanmak (backend dogrulamasi yok) | Basit implementasyon | Cihaz rootlanmissa biometric bypass edilebilir, gercek guvenlik saglamaz | MVP icin kabul edilebilir, ama dokumante et |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FastAPI WebSocket + OkHttp | WebSocket mesaj formatini eslestirmemek — backend JSON gonderiyor ama Android parser farkli format bekliyor | Backend'in mevcut WebSocket formatini (useWebSocket.ts'ten) incele, ayni JSON schema'yi kullan |
| FCM + FastAPI backend | Backend'te `firebase-admin` SDK yerine ham HTTP API kullanmak — token yonetimi ve hata isleme eksik kalir | `firebase-admin` Python SDK kullan: `messaging.send()` ile retry ve hata yonetimi otomatik |
| Biometric + EncryptedSharedPreferences | BiometricPrompt sonucunu beklemeden token okumaya calismak — async callback zamanlama sorunu | `androidx.biometric:biometric-ktx` ile suspending coroutine API kullan — `authenticateWithBiometrics()` dogrudan result dondurur |
| OkHttp + wall.tonbilx.com | Sertifika pinning yaparken backup pin eklememek — sertifika yenilenince uygulama tamamen kirilir | `CertificatePinner` ile hem mevcut hem bir sonraki sertifikanin pin'ini ekle, veya pinning yapma (Let's Encrypt yeterli) |
| Retrofit + FastAPI pagination | FastAPI `skip/limit` pattern'ini Android'de `offset/limit` olarak yanlis map'lemek | Backend'in mevcut pagination yapisini (traffic.py: `skip`, `limit`, `sort_by`, `sort_order`) birebir kullan |
| Android Notification Channel + Telegram | Telegram zaten bildirim gonderiyor — Android push ile cift bildirim | Kullaniciya "Bildirim kanali" secimi sun: sadece Push, sadece Telegram, veya her ikisi. Backend'te topic-based subscription |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| WebSocket her mesajda tum listeyi gonderiyor, diff yok | Her 5 saniyede 50+ cihaz listesi parse ediliyor — gereksiz CPU ve batarya | Backend'te diff-based WebSocket mesajlari kullan veya client-side diff uygula | 30+ cihaz ile fark edilir |
| Bitmap/image caching olmadan cihaz ikonlari | Her scroll'da ikon yeniden yukleniyor — LazyColumn kasma | Coil ile `ImageLoader` konfigur et, memory + disk cache | 20+ cihaz listesinde goze carpar |
| Her ekran gecisinde API istegi — cache yok | Sayfa gecislerinde surekli loading spinner | Repository katmaninda in-memory cache + stale-while-revalidate pattern | Her navigasyonda fark edilir |
| Foreground Service olmadan uzun sureli WebSocket | Android 10+ arka planda WebSocket'i ~10 dakikada oldurur | WorkManager ile periyodik check + Foreground Service ile canli baglanti | Uygulama arka plana alindiginda |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| JWT token'i logcat'e yazdirmak (debug sirasinda) | Token calinabitir — ozellikle USB debug aktifken | ProGuard/R8 ile debug loglarini release build'den cikar, `HttpLoggingInterceptor.Level.HEADERS` kullan (BODY degil) |
| Biometric auth basarisiz olunca PIN/pattern fallback'i kendimiz implement etmek | Yanlis implementasyon guvenlik acigi yaratir | Android'in `setAllowedAuthenticators(BIOMETRIC_STRONG or DEVICE_CREDENTIAL)` kullan — sistem PIN/pattern'i kendisi yonetir |
| API key'leri (Firebase, vb.) source code'da | APK decompile ile key'ler gorunur | `google-services.json` gitignore'a ekle, CI/CD ile inject et veya Firebase App Check kullan |
| Backend auth token'i olmadan WebSocket baglantisi kabul etmek | Yetkisiz kullanicilar canli veri gorebilir | WebSocket handshake'inde JWT token'i query param veya header ile gonder, backend dogrula |
| Cleartext HTTP ile yerel agda hassas veri gonderimi | Ayni agdaki baska cihazlar trafigi okuyabilir | Yerel agda bile HTTPS kullan (self-signed cert ile) veya riski kabul edip dokumante et |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Baglanti kopunca bos ekran gostermek | Kullanici uygulamanin bozuldugunu dusunur | Son bilinen veriyi goster + "Baglanti kesildi, yeniden baglaniliyor..." banner |
| Her API hatasini ayni toast ile gostermek ("Bir hata olustu") | Kullanici ne yapacagini bilmez | Hataya ozel mesaj: "Sunucuya ulasilamadi" vs "Oturum suresi doldu" vs "Yetkisiz islem" |
| Dashboard'da tum widget'lari ayni anda yuklemek | Ilk acilista 3-5 saniye beyaz ekran | Skeleton/shimmer loader goster, widget'lari oncelik sirasina gore yukle |
| Cyberpunk tema'da dusuk kontrast metin | Yaslı kullanicilar veya gunes altinda okuyamaz | WCAG 2.1 AA kontrast oranini (4.5:1) sagla — neon renkler arka plana gore ayarla |
| Router yonetim islemlerinde onay olmadan islem yapmak | Yanlis tiklama ile firewall kurali silinir | Kritik islemlerde (kural silme, cihaz engelleme, VPN peer silme) confirmation dialog goster |

---

## "Looks Done But Isn't" Checklist

- [ ] **Auth flow:** Login calisiyor AMA token yenileme test edilmedi — 15 dakika sonra kullanici atilir
- [ ] **WebSocket:** Veri geliyor AMA ag degisikligi sonrasi reconnect test edilmedi — WiFi'dan cikinca kalici kopukluk
- [ ] **Push notifications:** Bildirim geliyor AMA uygulama kapaliyken (killed state) test edilmedi — foreground service olmadan calismaz
- [ ] **Biometric:** Parmak izi calisiyor AMA biyometrik kayitli degilse fallback test edilmedi — kullanici giremez
- [ ] **Dual endpoint:** Evde calisiyor AMA disaridan erisim test edilmedi — wall.tonbilx.com uzerinden 404/timeout
- [ ] **Offline durumu:** Internet varken calisiyor AMA internet yokken crash test edilmedi — NetworkOnMainThreadException veya bos ekran
- [ ] **Dark tema:** Cyberpunk renkleri guzel AMA sistem light mode'da test edilmedi — status bar/navigation bar renk uyumsuzlugu
- [ ] **Large screen:** S24 Ultra'da guzel AMA kucuk ekranda (5") test edilmedi — icerik tasiyor veya kesiyor
- [ ] **ProGuard/R8:** Debug'da calisiyor AMA release build'de test edilmedi — minification Retrofit model'lerini kirar (Keep rules eksik)
- [ ] **Battery:** Calisiyor AMA 1 saat acik kaldiktan sonra batarya etkisi test edilmedi — WebSocket + polling bataryayi eritir

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Token refresh race condition | MEDIUM | (1) OkHttp Authenticator'a `Mutex` ekle; (2) retry queue implement et; (3) tum API cagrilarini test et |
| WebSocket lifecycle leak | HIGH | (1) Tum ViewModel'leri refactor et; (2) WebSocket manager sinifi yaz; (3) lifecycle-aware baglanti yonetimi ekle |
| FCM token kaybi | LOW | (1) `onNewToken()` callback ekle; (2) uygulama acilisinda token sync; (3) backend'te eski token temizligi |
| Recomposition patlamasi | HIGH | (1) Compose compiler metrics aktif et; (2) tum data class'lari `@Stable`/`@Immutable` yap; (3) state okuma noktalarini tasi — neredeyse tum UI'yi etkiler |
| Dual endpoint eksikligi | MEDIUM | (1) NetworkManager sinifi yaz; (2) OkHttp Interceptor'a endpoint secim mantigi ekle; (3) tum API cagrilarini test et |
| ProGuard model kirma | LOW | (1) `@Keep` annotation veya `proguard-rules.pro`'ya Retrofit model keep rules ekle; (2) release build test et |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| WebSocket lifecycle leak | Phase 1: Networking altyapi | LeakCanary ile bellek testi, 10 dakika kullanim sonrasi WebSocket sayisi = 1 |
| JWT token refresh race | Phase 1: Auth altyapi | 6 paralel API istegi gonder, hepsi basarili donmeli (token expired durumunda) |
| Dual endpoint yonetimi | Phase 1: Networking altyapi | WiFi'dan mobil veriye gec — 5 saniye icinde API istekleri basarili olmali |
| HTTPS/sertifika konfigurasyonu | Phase 1: Networking altyapi | wall.tonbilx.com + 192.168.1.2 her ikisine de baglanabilmeli |
| Compose recomposition | Phase 2: UI/Dashboard | Layout Inspector'da gereksiz recomposition sayisi < 2 per frame |
| FCM token yonetimi | Phase 3: Push notifications | Uygulama sil-yeniden kur, bildirim 1 dakika icinde gelmeli |
| Foreground service (background WebSocket) | Phase 2: Real-time veri | Uygulama arka planda 30 dakika — WebSocket hala bagli |
| ProGuard model kirma | Phase 4: Release hazirligi | Release APK ile tum API cagrilari calismali |

---

## Sources

- [Jetpack Compose Performance Best Practices — Android Developers](https://developer.android.com/develop/ui/compose/performance/bestpractices) — Recomposition, stability, LazyColumn keys (HIGH confidence)
- [Overcoming Common Performance Pitfalls in Jetpack Compose — ProAndroidDev](https://proandroiddev.com/overcoming-common-performance-pitfalls-in-jetpack-compose-98e6b155fbb4) — Backwards writes, unstable types (MEDIUM confidence)
- [FCM on Android — Firebase Blog (2025)](https://firebase.blog/posts/2025/04/fcm-on-android/) — Doze mode, message priority, token lifecycle (HIGH confidence)
- [Handling JWT Token Expiration in Android Kotlin — Medium](https://medium.com/@prakash_ranjan/handling-jwt-token-expiration-and-re-authentication-in-android-kotlin-441838e5ce0a) — Refresh token race condition (MEDIUM confidence)
- [Secure Token Storage Best Practices — Capgo](https://capgo.app/blog/secure-token-storage-best-practices-for-mobile-developers/) — EncryptedSharedPreferences, Android Keystore (MEDIUM confidence)
- [HTTPS — OkHttp Official Docs](https://square.github.io/okhttp/features/https/) — Certificate pinning, TrustManager (HIGH confidence)
- [Monitor Connectivity Status — Android Developers](https://developer.android.com/training/monitoring-device-state/connectivity-status-type) — NetworkCallback, transport changes (HIGH confidence)
- [Network Security Config — Android Developers](https://developer.android.com/privacy-and-security/security-config) — Cleartext traffic, domain-specific config (HIGH confidence)
- [Handle WebSocket in Jetpack Compose with OkHttp and SharedFlow — Medium](https://medium.com/@danimahardhika/handle-websocket-in-jetpack-compose-with-okhttp-and-sharedflow-b1ed7c9fd713) — WebSocket + Compose lifecycle pattern (MEDIUM confidence)
- [Biometric Authentication with Backend Verification — ProAndroidDev](https://proandroiddev.com/biometric-authentication-with-backend-verification-6feaa0188963) — CryptoObject + JWT signing (MEDIUM confidence)

---
*Pitfalls research for: TonbilAiOS v2.0 Android App*
*Researched: 2026-03-06*
