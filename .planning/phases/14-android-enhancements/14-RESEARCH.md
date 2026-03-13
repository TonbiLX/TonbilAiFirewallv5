# Phase 14: Android Enhancements - Research

**Researched:** 2026-03-13
**Domain:** Android Native Features — Glance Widget, Quick Settings TileService, Haptic Feedback, App Shortcuts
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DASH-05 | Home screen widget (Glance) — bant genisligi, cihaz sayisi, son tehdit | Glance 1.1.0 + WorkManager periodic update + Ktor HTTP call in CoroutineWorker |
| DASH-06 | Quick Settings tile — DNS filtreleme toggle + cihaz engelleme toggle | TileService API (API 5+) + coroutine scope in onClick + SecurityRepository API call |
| UX-01 | Haptic feedback — kritik uyarilarda titresim | HapticFeedbackConstants.CONFIRM/REJECT (API 30+), LocalView in Compose, no permission needed |
| UX-02 | App shortcuts — uzun basma menusu (durum kontrol, cihaz engelle, AI chat) | ShortcutManagerCompat dynamic shortcuts + deep link Intent + Application.onCreate registration |

</phase_requirements>

---

## Summary

Bu fazda uygulamaya 4 native Android ozelligi ekleniyor: Glance ana ekran widget'i (DASH-05), Quick Settings tile'lar (DASH-06), haptic feedback (UX-01) ve app shortcuts (UX-02). Projenin mevcut mimarisi (Koin DI, Ktor HTTP client, WebSocketManager, SecurityRepository, DashboardRepository) bu ozelliklerin hepsine entegrasyon icin uygun altyapiyi sunuyor.

Teknik olarak en karmasik parca Glance widget'idir; uygulama sureci disinda calistigi icin Koin DI dogrudan kullanilamamakta, bunun yerine WorkManager CoroutineWorker + DataStore pattern'i benimsenmesi gerekmektedir. Quick Settings TileService, `onClick()` callback'inden coroutine scope ile API cagrisi yapmayi gerektiriyor. Haptic feedback tamamen izinsiz calisiyor ve minSdk=31 projesinde tum gerekli sabitler mevcuttur. App shortcuts ise en basit eklemedir — ShortcutManagerCompat ile Application.onCreate'de tanimlaniyor.

**Primary recommendation:** DASH-05 (Glance) icin ayri bir WorkManager + DataStore mimarisi kur; diger uc ozellik (DASH-06, UX-01, UX-02) mevcut Koin DI/ViewModel altyapisina dogrudan entegre edilebilir.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| androidx.glance:glance-appwidget | 1.1.0 | Home screen widget Compose API | En son stable; GlanceAppWidget + GlanceAppWidgetReceiver sagliyor |
| androidx.glance:glance-material3 | 1.1.0 | Glance icin Material 3 renk/tema | Cyberpunk tema renklerini Glance'e tasimak icin |
| androidx.work:work-runtime-ktx | 2.9.x | Widget veri guncelleme (arka plan) | Glance'i WorkManager ile beslemek standart pattern |
| androidx.datastore:datastore-preferences | 1.1.1 | Widget state persist (zaten projede var) | Glance'in surec disi ortami icin SharedState alternatifi |
| android.service.quicksettings.TileService | Android SDK (API 24+) | Quick Settings tile | Herhangi ek bagimliligi yok, SDK icinde |
| ShortcutManagerCompat | androidx.core:core (1.15.0) | Dynamic app shortcuts | Zaten core-ktx projede var |
| HapticFeedbackConstants | Android SDK | Haptic feedback | SDK icinde, izin gerektirmez |

### Notlar
- Proje mevcut `minSdk = 31`, `targetSdk = 35`
- Glance 1.1.0 icin minSdk 21+ yeterli; projede fazlasiylakar
- TileService: API 24+ gerektirir — projede sorun yok (minSdk=31)
- Quick Settings tile icon: 24x24dp beyaz-transparan VectorDrawable
- WorkManager icin mevcut `lifecycle-runtime-compose` yeterli, ek bagimliligi gerekmez

**Installation (libs.versions.toml'a eklenecekler):**
```toml
# [versions]
glance = "1.1.0"
workRuntime = "2.9.1"

# [libraries]
glance-appwidget = { group = "androidx.glance", name = "glance-appwidget", version.ref = "glance" }
glance-material3 = { group = "androidx.glance", name = "glance-material3", version.ref = "glance" }
work-runtime-ktx = { group = "androidx.work", name = "work-runtime-ktx", version.ref = "workRuntime" }
```

**build.gradle.kts eklentileri:**
```kotlin
implementation(libs.glance.appwidget)
implementation(libs.glance.material3)
implementation(libs.work.runtime.ktx)
```

---

## Architecture Patterns

### Recommended Project Structure
```
android/app/src/main/java/com/tonbil/aifirewall/
├── widget/
│   ├── TonbilWidget.kt              # GlanceAppWidget subclass
│   ├── TonbilWidgetReceiver.kt      # GlanceAppWidgetReceiver
│   └── TonbilWidgetWorker.kt        # CoroutineWorker — API fetch + widget update
├── tile/
│   ├── DnsFilterTileService.kt      # DNS toggle QS tile
│   └── DeviceBlockTileService.kt    # Device block QS tile (opsiyonel)
├── feature/
│   └── dashboard/
│       └── DashboardViewModel.kt    # UX-01 haptic feedback burada tetikleniyor
└── util/
    └── NotificationHelper.kt        # Mevcut — UX-01 burada haptic eklenecek
```

```
android/app/src/main/res/xml/
├── tonbil_widget_info.xml           # AppWidgetProviderInfo
└── shortcuts.xml                    # Opsiyonel static shortcuts
```

---

### Pattern 1: Glance Widget — WorkManager + DataStore Architecture

**What:** Widget sureci uygulamadan bagimsiz; Koin DI erisilemez. Veri akisi: WorkManager -> DataStore -> Widget.

**When to use:** Widget veriyi periyodik olarak (15 dakikada bir) API'den alip DataStore'a yazar, Glance widget DataStore'dan okur.

```kotlin
// 1. GlanceAppWidget — DataStore okuyarak UI render eder
class TonbilWidget : GlanceAppWidget() {
    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val prefs = context.dataStore.data.first()
        val uploadBps = prefs[UPLOAD_BPS_KEY] ?: 0L
        val deviceCount = prefs[DEVICE_COUNT_KEY] ?: 0
        val lastThreat = prefs[LAST_THREAT_KEY] ?: ""

        provideContent {
            WidgetContent(uploadBps, deviceCount, lastThreat)
        }
    }
}

// 2. GlanceAppWidgetReceiver
class TonbilWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = TonbilWidget()
}

// 3. WorkManager CoroutineWorker — API cagir, DataStore'a yaz, widget'i guncelle
class TonbilWidgetWorker(
    val context: Context,
    params: WorkerParameters,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            // Ktor ile API cagri — Koin getKoin() ile HttpClient al
            val httpClient = KoinAndroidContext.get<HttpClient>()
            val summary = httpClient.get("${serverUrl}${ApiRoutes.DASHBOARD_SUMMARY}") {
                bearerAuth(tokenFromPrefs())
            }.body<DashboardSummaryDto>()

            // DataStore'a yaz
            context.dataStore.edit { prefs ->
                prefs[UPLOAD_BPS_KEY] = 0L  // WS'ten gelir, burasi API ozeti
                prefs[DEVICE_COUNT_KEY] = summary.devices.online
                prefs[LAST_THREAT_KEY] = summary.dns.blockedQueries24h.toString()
            }

            // Widget'i guncelle
            TonbilWidget().updateAll(context)
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}

// 4. Periyodik schedule — Application.onCreate veya widgetAdded callback'inde
val workRequest = PeriodicWorkRequestBuilder<TonbilWidgetWorker>(15, TimeUnit.MINUTES)
    .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
    .build()
WorkManager.getInstance(context).enqueueUniquePeriodicWork(
    "tonbil_widget_refresh",
    ExistingPeriodicWorkPolicy.KEEP,
    workRequest,
)
```

**AndroidManifest.xml eklentisi:**
```xml
<receiver
    android:name=".widget.TonbilWidgetReceiver"
    android:exported="true">
    <intent-filter>
        <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
    </intent-filter>
    <meta-data
        android:name="android.appwidget.provider"
        android:resource="@xml/tonbil_widget_info" />
</receiver>
```

**res/xml/tonbil_widget_info.xml:**
```xml
<appwidget-provider xmlns:android="http://schemas.android.com/apk/res/android"
    android:minWidth="110dp"
    android:minHeight="40dp"
    android:minResizeWidth="110dp"
    android:minResizeHeight="40dp"
    android:updatePeriodMillis="0"
    android:resizeMode="horizontal|vertical"
    android:widgetCategory="home_screen"
    android:initialLayout="@layout/glance_default_loading_layout" />
```

---

### Pattern 2: Quick Settings TileService

**What:** TileService, uygulamadan bagimsiz bir Service olarak calisir. `onClick()` icinde coroutine scope manuel olusturulur.

**When to use:** DNS toggle veya cihaz engelleme icin. STATE_ACTIVE = acik, STATE_INACTIVE = kapali.

```kotlin
// Source: https://developer.android.com/develop/ui/views/quicksettings-tiles
class DnsFilterTileService : TileService() {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onStartListening() {
        super.onStartListening()
        serviceScope.launch {
            // Mevcut DNS durumunu al
            val httpClient = KoinAndroidContext.get<HttpClient>()
            try {
                val config = httpClient.get("${serverUrl}${ApiRoutes.SECURITY_CONFIG}") {
                    bearerAuth(getToken())
                }.body<SecurityConfigDto>()

                withContext(Dispatchers.Main) {
                    qsTile.state = if (config.dnsFilteringEnabled)
                        Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
                    qsTile.label = "DNS Filtre"
                    qsTile.subtitle = if (config.dnsFilteringEnabled) "Acik" else "Kapali"
                    qsTile.updateTile()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    qsTile.state = Tile.STATE_UNAVAILABLE
                    qsTile.updateTile()
                }
            }
        }
    }

    override fun onClick() {
        super.onClick()
        serviceScope.launch {
            val newState = qsTile.state != Tile.STATE_ACTIVE
            // API ile toggle — SecurityRepository benzeri cagri
            val httpClient = KoinAndroidContext.get<HttpClient>()
            httpClient.patch("${serverUrl}${ApiRoutes.SECURITY_CONFIG}") {
                bearerAuth(getToken())
                contentType(ContentType.Application.Json)
                setBody(SecurityConfigUpdateDto(dnsFilteringEnabled = newState))
            }
            withContext(Dispatchers.Main) {
                qsTile.state = if (newState) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
                qsTile.updateTile()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }
}
```

**AndroidManifest.xml:**
```xml
<service
    android:name=".tile.DnsFilterTileService"
    android:exported="true"
    android:label="DNS Filtre"
    android:icon="@drawable/ic_dns_tile"
    android:permission="android.permission.BIND_QUICK_SETTINGS_TILE">
    <intent-filter>
        <action android:name="android.service.quicksettings.action.QS_TILE" />
    </intent-filter>
    <meta-data
        android:name="android.service.quicksettings.TOGGLEABLE_TILE"
        android:value="true" />
    <meta-data
        android:name="android.service.quicksettings.TILE_CATEGORY"
        android:value="android.service.quicksettings.CATEGORY_CONNECTIVITY" />
</service>
```

---

### Pattern 3: Haptic Feedback — Compose'da LocalView ile

**What:** Compose'da dogrudan haptic API yoktur. `LocalView.current` ile View referansi alinip `performHapticFeedback()` cagrisi yapilir. Hic izin gerekmez.

**When to use:** SecurityEventDto geldiginde (DDoS, block), WebSocket'ten gelen kritik olaylar icin.

```kotlin
// Source: https://developer.android.com/develop/ui/views/haptics/haptic-feedback

// TonbilApp.kt veya SecurityEventObserver'a ekle
private fun observeSecurityEventsWithHaptic(context: Context, view: View) {
    appScope.launch {
        wsManager.securityEvents.collect { event ->
            // Kritik severity'de haptic tetikle
            if (event.severity == "critical" || event.severity == "warning") {
                withContext(Dispatchers.Main) {
                    val constant = if (event.severity == "critical")
                        HapticFeedbackConstants.REJECT   // Guclu titresim — API 30+
                    else
                        HapticFeedbackConstants.CONFIRM  // Hafif titresim — API 30+
                    view.performHapticFeedback(constant)
                }
            }
            NotificationHelper.showSecurityNotification(context, event)
        }
    }
}

// MainActivity.kt'de (veya TonbilApp context Window icinden View alarak):
// window.decorView.performHapticFeedback(HapticFeedbackConstants.REJECT)
```

**Compose buton tiklama icin (opsiyonel):**
```kotlin
@Composable
fun HapticButton(onClick: () -> Unit) {
    val view = LocalView.current
    Button(onClick = {
        view.performHapticFeedback(HapticFeedbackConstants.CONFIRM)
        onClick()
    }) {
        Text("Engelle")
    }
}
```

**API Level Notlari:**
- `HapticFeedbackConstants.CONFIRM` — API 30+ (projede minSdk=31, sorun yok)
- `HapticFeedbackConstants.REJECT` — API 30+
- `HapticFeedbackConstants.LONG_PRESS` — API 5+ (eski uyumluluk icin fallback)
- `HapticFeedbackConstants.GESTURE_START/END` — API 31+

---

### Pattern 4: App Shortcuts — ShortcutManagerCompat

**What:** Uygulama ikonuna uzun basildiginda gorunen dynamic shortcuts. Maksimum 4 shortcut goruntulenir.

**When to use:** Application.onCreate'de kaydet, her calistirmada guncel tut.

```kotlin
// TonbilApp.kt veya yeni ShortcutManager.kt

fun setupAppShortcuts(context: Context) {
    val shortcuts = listOf(
        // 1. Durum Kontrol
        ShortcutInfoCompat.Builder(context, "status_check")
            .setShortLabel("Durum")
            .setLongLabel("Ag Durumunu Kontrol Et")
            .setIcon(IconCompat.createWithResource(context, R.drawable.ic_splash_logo))
            .setIntent(
                Intent(context, MainActivity::class.java).apply {
                    action = Intent.ACTION_VIEW
                    putExtra("navigate_to", "dashboard")
                    flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
                }
            )
            .build(),
        // 2. Cihaz Engelle
        ShortcutInfoCompat.Builder(context, "device_block")
            .setShortLabel("Cihaz Engelle")
            .setLongLabel("Cihaz Engelleme Listesine Git")
            .setIcon(IconCompat.createWithResource(context, R.drawable.ic_splash_logo))
            .setIntent(
                Intent(context, MainActivity::class.java).apply {
                    action = Intent.ACTION_VIEW
                    putExtra("navigate_to", "devices")
                    flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
                }
            )
            .build(),
        // 3. AI Chat
        ShortcutInfoCompat.Builder(context, "ai_chat")
            .setShortLabel("AI Chat")
            .setLongLabel("AI Asistanla Konusmaya Bas")
            .setIcon(IconCompat.createWithResource(context, R.drawable.ic_splash_logo))
            .setIntent(
                Intent(context, MainActivity::class.java).apply {
                    action = Intent.ACTION_VIEW
                    putExtra("navigate_to", "chat")
                    flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
                }
            )
            .build(),
    )

    ShortcutManagerCompat.setDynamicShortcuts(context, shortcuts)
}
```

**MainActivity.kt'de deep link isleme:**
```kotlin
override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val navigateTo = intent?.getStringExtra("navigate_to")
    // NavController'a baslangic rotasini ilet
}
```

---

### Anti-Patterns to Avoid

- **Glance'te Koin inject etmeye calisma:** Glance sureci uygulamadan bagimsiz. `KoinAndroidContext.get()` yerine `getKoin()` kullanim satirlari Glance context'inde NPE verir. DataStore pattern kullan.
- **TileService.onClick()'te ana thread'de blokla:** Ktor coroutine suspend fonksiyonlarini ana thread'de cagirma. `serviceScope.launch(Dispatchers.IO)` kullan.
- **Widget'te updatePeriodMillis > 0 koy:** 30 dakikalik sistem sinirini asma. WorkManager kullan, `updatePeriodMillis="0"` ayarla.
- **Haptic icin VIBRATE izni alma:** `HapticFeedbackConstants` ile `View.performHapticFeedback()` hic izin gerektirmez. `VibrationEffect` kullanma (izin gerektirir, fazla karmasik).
- **Shortcut ID'lerini degistirme:** Shortcut ID degisirse kullanici pinned shortcut kaybeder. `status_check`, `device_block`, `ai_chat` sabit tut.
- **Glance'te normal Compose composable kullanma:** `androidx.compose.material3.Text` degil `androidx.glance.text.Text` kullanilmali. Import karistirmasi derleyici hatalarina yol acar.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Widget state management | Manuel SharedPreferences yonetimi | DataStore + PreferencesGlanceStateDefinition | Process death, concurrent write, type safety sorunlari |
| Widget periyodik guncelleme | AlarmManager custom broadcaster | WorkManager PeriodicWorkRequest | Battery optimization, Doze mode, idempotency |
| Quick Settings | Overlay veya Notification korsanligi | TileService | Standart Android UX, izin modeli |
| Haptic permission handling | VIBRATE izni yonetimi | HapticFeedbackConstants | Izinsiz, sistem ayarlarina saygi, daha tutarli |
| Shortcut icon creation | Bitmap olusturma runtime'da | IconCompat.createWithResource() | Memory efficient, launcher caching |

**Key insight:** Glance widget'in en buyuk tuzagi Koin DI — uygulama sureci disi ortamda calistigindan Koin context mevcut degildir. Veri katmani DataStore uzerinden koprulenmeli.

---

## Common Pitfalls

### Pitfall 1: Glance'te Koin DI Erisim Hatasi
**What goes wrong:** `TonbilWidget.provideGlance()` icinde `get<DashboardRepository>()` NPE veya KoinApplication not started exception atar.
**Why it happens:** Glance widget, AppWidget framework tarafindan bagimsiz bir surec/process context'inde calistiriliyor; Koin Application.onCreate'de baslatilmis olsa bile Glance context'i ayri.
**How to avoid:** Widget UI kodu saf DataStore okumasi yapsin. Veri cekme isini WorkManager CoroutineWorker'a birak, worker'dan Koin erisebilirsin (o uygulamanin normal surec context'inde calisir).
**Warning signs:** `KoinApplication not started` veya null pointer Glance loglarinda.

### Pitfall 2: TileService onClick'te Coroutine Scope Sizdirmasi
**What goes wrong:** `serviceScope` `onDestroy()` iptal edilmezse, tile kaldirildiginda arka planda devam eden coroutine'ler memory leak ve API cagrisi sizdirmasi yapar.
**Why it happens:** TileService bir Android Service; lifecycle yonetimi manuel.
**How to avoid:** `onDestroy()` override'inda `serviceScope.cancel()` mutlaka cagir.
**Warning signs:** Tile kaldirildiktan sonra API log'larinda cagrilar devam ediyor.

### Pitfall 3: Glance Composable Import Karistirmasi
**What goes wrong:** `import androidx.compose.material3.Text` ile `import androidx.glance.text.Text` karisirsa derleme hatasi veya runtime crash.
**Why it happens:** Glance farkli composable set kullanir; Jetpack Compose UI composables'lari RemoteViews'e cevirilemiyor.
**How to avoid:** Glance dosyalarinda sadece `androidx.glance.*` import'larini kullan. IDE'nin otomatik import tekliflerini dikkatli kontrol et.
**Warning signs:** `ClassNotFoundException: RemoteViews` runtime hatasi.

### Pitfall 4: Quick Settings Tile Icon Formati Yanlis
**What goes wrong:** Tile iconu garip gorunuyor veya saydam arka plana ragmen siyah kutu olarak gorunuyor.
**Why it happens:** QS tile iconu 24x24dp, kati beyaz (#FFFFFF), saydam arka plan VectorDrawable olmali. Renkli veya PNG kullanilirsa sistem onu dogru render etmiyor.
**How to avoid:** `ic_dns_tile.xml` ve `ic_device_block_tile.xml` icin yeni VectorDrawable olustur; fillColor="#FFFFFF", arka plan yok.
**Warning signs:** Samsung One UI'da tile gorsel olarak bozuk.

### Pitfall 5: App Shortcut Icon Kısıtlaması
**What goes wrong:** Shortcut ikonunda tint/renk uygulanamaz, launcher onu siyah beyaz gosteriyor.
**Why it happens:** Android shortcut ikonlari tint desteklemiyor; ikon kaynagi ham drawable olmali.
**How to avoid:** Mevcut `R.drawable.ic_splash_logo` kullan (zaten var). Her shortcut icin farkli ikon gerekiyorsa ayri drawable olustur.
**Warning signs:** Kisayol listesinde tum ikonlar ayni gorunuyor ama farkli renklenmis olmasi bekleniyor.

### Pitfall 6: Samsung One UI Widget Minimum Boyutu
**What goes wrong:** Widget cok kucuk render ediliyor veya hic gorunmuyor.
**Why it happens:** Samsung One UI launcher minimum widget boyutuna saygi gostermeyebiliyor; `minWidth`/`minHeight` values cok kucuk olunca kesilebiliyor.
**How to avoid:** `tonbil_widget_info.xml` icinde `minWidth="110dp" minHeight="40dp"` kullan (2x1 grid hucre karsiligi).
**Warning signs:** S24 Ultra ana ekraninda widget icerigi kesiyor.

---

## Code Examples

Verified patterns from official sources:

### Glance Widget — provideGlance ile DataStore okuma
```kotlin
// Source: https://developer.android.com/develop/ui/compose/glance/create-app-widget
class TonbilWidget : GlanceAppWidget() {

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        val prefs = context.dataStore.data.first()

        provideContent {
            GlanceTheme {
                Column(
                    modifier = GlanceModifier
                        .fillMaxSize()
                        .background(Color(0xFF0D001A))
                        .padding(12.dp),
                ) {
                    Text(
                        text = "TonbilAiOS",
                        style = TextStyle(color = ColorProvider(Color(0xFF00F0FF)), fontSize = 12.sp),
                    )
                    Spacer(GlanceModifier.height(4.dp))
                    Row {
                        Text(
                            text = "${prefs[DEVICE_COUNT_KEY] ?: 0} cihaz",
                            style = TextStyle(color = ColorProvider(Color.White), fontSize = 11.sp),
                        )
                        Spacer(GlanceModifier.width(8.dp))
                        Text(
                            text = formatBps(prefs[UPLOAD_BPS_KEY] ?: 0L),
                            style = TextStyle(color = ColorProvider(Color(0xFF39FF14)), fontSize = 11.sp),
                        )
                    }
                    if (!prefs[LAST_THREAT_KEY].isNullOrBlank()) {
                        Text(
                            text = "Tehdit: ${prefs[LAST_THREAT_KEY]}",
                            style = TextStyle(color = ColorProvider(Color(0xFFFF003C)), fontSize = 10.sp),
                        )
                    }
                }
            }
        }
    }
}

// DataStore keys — widget package icinde tanimlanan companion object
val DEVICE_COUNT_KEY = intPreferencesKey("widget_device_count")
val UPLOAD_BPS_KEY = longPreferencesKey("widget_upload_bps")
val LAST_THREAT_KEY = stringPreferencesKey("widget_last_threat")
```

### TileService — onStartListening + onClick coroutine pattern
```kotlin
// Source: https://developer.android.com/develop/ui/views/quicksettings-tiles
class DnsFilterTileService : TileService() {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onStartListening() {
        super.onStartListening()
        serviceScope.launch {
            val enabled = fetchDnsStatus()
            withContext(Dispatchers.Main) {
                qsTile.state = if (enabled) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
                qsTile.updateTile()
            }
        }
    }

    override fun onClick() {
        super.onClick()
        serviceScope.launch {
            val toggle = qsTile.state != Tile.STATE_ACTIVE
            toggleDnsFilter(toggle)
            withContext(Dispatchers.Main) {
                qsTile.state = if (toggle) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
                qsTile.updateTile()
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }
}
```

### HapticFeedback — TonbilApp application scope
```kotlin
// Source: https://developer.android.com/develop/ui/views/haptics/haptic-feedback
// TonbilApp.kt'deki observeSecurityEvents'e eklenecek

private fun observeSecurityEvents() {
    appScope.launch {
        val wsManager = getKoin().get<WebSocketManager>()
        wsManager.securityEvents.collect { event ->
            NotificationHelper.showSecurityNotification(this@TonbilApp, event)

            // Haptic feedback — sadece criical/warning severity
            if (event.severity in listOf("critical", "warning")) {
                val mainActivity = currentActivity  // WeakReference ile tut
                mainActivity?.window?.decorView?.let { view ->
                    val constant = when (event.severity) {
                        "critical" -> HapticFeedbackConstants.REJECT    // API 30+
                        else       -> HapticFeedbackConstants.CONFIRM   // API 30+
                    }
                    view.performHapticFeedback(constant)
                }
            }
        }
    }
}
```

**Not:** Application context'te dogrudan View yok; MainActivity referansini Activity lifecycle callback'leriyle (ActivityLifecycleCallbacks) WeakReference olarak saklamak gerekir. Alternatif: SecurityEventDto'yu broadcast ile MainActivity'ye ilet, orada haptic tetikle.

### App Shortcuts — Application.onCreate registrasyonu
```kotlin
// Source: https://developer.android.com/develop/ui/views/launch/shortcuts/creating-shortcuts
// TonbilApp.kt onCreate'de:

fun setupDynamicShortcuts() {
    val shortcuts = listOf(
        ShortcutInfoCompat.Builder(this, "status_check")
            .setShortLabel("Durum")
            .setLongLabel("Ag Durumu")
            .setIcon(IconCompat.createWithResource(this, R.drawable.ic_splash_logo))
            .setIntent(Intent(this, MainActivity::class.java).apply {
                action = Intent.ACTION_VIEW
                putExtra("deep_link", "tonbilaios://dashboard")
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            })
            .build(),
        ShortcutInfoCompat.Builder(this, "device_block")
            .setShortLabel("Cihaz Engelle")
            .setLongLabel("Cihaz Engelleme")
            .setIcon(IconCompat.createWithResource(this, R.drawable.ic_splash_logo))
            .setIntent(Intent(this, MainActivity::class.java).apply {
                action = Intent.ACTION_VIEW
                putExtra("deep_link", "tonbilaios://devices")
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            })
            .build(),
        ShortcutInfoCompat.Builder(this, "ai_chat")
            .setShortLabel("AI Chat")
            .setLongLabel("AI Asistan")
            .setIcon(IconCompat.createWithResource(this, R.drawable.ic_splash_logo))
            .setIntent(Intent(this, MainActivity::class.java).apply {
                action = Intent.ACTION_VIEW
                putExtra("deep_link", "tonbilaios://chat")
                flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
            })
            .build(),
    )
    ShortcutManagerCompat.setDynamicShortcuts(this, shortcuts)
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| RemoteViews (XML tabanlı widget) | Glance (Compose tabanlı) | 2021+ (stable 1.0: 2023) | Tamamen Compose ile widget yazilabiliyor |
| Vibrator + createWaveform() | HapticFeedbackConstants | API 26+ | Izin gerekmez, sistem uyumlu |
| ShortcutManager (direkt) | ShortcutManagerCompat | 2018+ | API 25 altına uyumluluk, Google Shortcuts entegrasyonu |
| Widget updatePeriodMillis | WorkManager PeriodicWork | 2020+ | 15 dakikalık minimum, battery-aware |

**Deprecated/outdated:**
- `Vibrator.vibrate(long)`: API 26'da deprecated. `VibrationEffect` veya `HapticFeedbackConstants` kullan.
- `createWaveform()` / `createOneshot()`: Sessiz modda calismiyor, izin gerektirir. Kac.
- Widget'te `AppWidgetProvider.onUpdate()` ile manuel RemoteViews: Glance bunu otomatik yapiyor.

---

## Open Questions

1. **Glance'te Koin erisimi — KoinAndroidContext**
   - What we know: WorkManager CoroutineWorker uygulamanin process'inde calisir; `getKoin()` teorik olarak erisilebilir
   - What's unclear: Glance 1.1.0'da WorkManager context'i ile Koin interaksiyonu tam test edilmedi; bazen race condition olabiliyor
   - Recommendation: WorkManager worker'inda Ktor HttpClient'i Koin'den degil, dogrudan `DataStore`'dan okunan token + hardcoded URL ile olustur (en guvenli yol)

2. **TileService'te sunucu URL ve token erisimi**
   - What we know: TileService ayri bir Service instance'i; TokenManager EncryptedSharedPreferences'tan okuyabiliyor (ayni SharedPreferences dosya adi ile)
   - What's unclear: ServerDiscovery'nin TileService context'inde aktif URL'yi bilip bilmedigi
   - Recommendation: TileService icin DataStore'dan son bilinen URL'yi oku (ServerConfig ayni DataStore'i kullaniyorsa dogrudan erisebilir)

3. **Haptic feedback'i Activity disinda tetikleme**
   - What we know: `View.performHapticFeedback()` calisan bir View gerektiriyor; Application context'te View yok
   - What's unclear: TonbilApp'in MainActivity referansina erismesi icin en temiz yol
   - Recommendation: `ActivityLifecycleCallbacks` ile `currentResumedActivity: WeakReference<Activity>` tut; sadece app on foreground oldugunda tetikle. Arka plandayken bildirim zaten yeterli.

---

## Validation Architecture

> `workflow.nyquist_validation` key `.planning/config.json`'da yok — validation dahil edildi.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Android Instrumentation / manual APK test |
| Config file | build.gradle.kts (androidTest) |
| Quick run command | `./gradlew connectedAndroidTest` |
| Full suite command | `./gradlew connectedAndroidTest assembleDebug` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-05 | Widget ana ekranda gorunuyor, veri render ediliyor | manual-only | Widget S24 home screen'e eklenir, cihaz/bant sayisi gozlemlenir | N/A |
| DASH-06 | QS tile aciliyor, DNS toggle calisiyor | manual-only | QS panel acilir, tile toggle edilir, API log kontrol edilir | N/A |
| UX-01 | Kritik olay geldiginde telefon titriyor | manual-only | Test endpoint trigger edilir, titresim hissedilir | N/A |
| UX-02 | Uzun basma manusu 3 kisayol gosteriyor | manual-only | App ikonu uzun basilir, 3 shortcut gorunur ve calisiyor | N/A |

**Not:** Bu ozelliklerin tamami donanim/UI gerektiriyor (sensor, launcher, tile panel). Unit test edilebilir parcalar: WorkManager worker logic, ShortcutManager kayit sayisi.

### Wave 0 Gaps
- [ ] `android/app/src/main/res/xml/tonbil_widget_info.xml` — AppWidgetProviderInfo
- [ ] `android/app/src/main/java/.../widget/TonbilWidget.kt` — Wave 0 iskeleti
- [ ] `android/app/src/main/java/.../tile/DnsFilterTileService.kt` — Wave 0 iskeleti
- [ ] `android/app/src/main/res/drawable/ic_dns_tile.xml` — 24x24dp beyaz VectorDrawable
- [ ] `libs.versions.toml` — glance + work-runtime eklentileri

---

## Sources

### Primary (HIGH confidence)
- `https://developer.android.com/develop/ui/compose/glance/create-app-widget` — GlanceAppWidget yapisi, manifest, receiver
- `https://developer.android.com/develop/ui/compose/glance/glance-app-widget` — State management, update, WorkManager pattern
- `https://developer.android.com/develop/ui/views/quicksettings-tiles` — TileService tam implementasyon, state, manifest
- `https://developer.android.com/develop/ui/views/haptics/haptic-feedback` — HapticFeedbackConstants, Compose kullanimi, izin gereksizligi
- `https://developer.android.com/reference/android/view/HapticFeedbackConstants` — API level referansi (CONFIRM/REJECT=30+, GESTURE_*=31+)
- `https://developer.android.com/develop/ui/views/launch/shortcuts/creating-shortcuts` — ShortcutManagerCompat, dynamic shortcuts pattern

### Secondary (MEDIUM confidence)
- `https://mvnrepository.com/artifact/androidx.glance/glance-appwidget` — Glance 1.1.0 en son stable version dogrulama
- `https://medium.com/@ssharyk/android-widgets-with-glance-whats-new-with-google-i-o-2024` — Glance 2024 Google I/O guncellemeleri

### Tertiary (LOW confidence)
- Samsung One UI widget boyut uyumlulugu — resmi kaynak bulunamadi, pratik deneyim verisi

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Glance 1.1.0, TileService, HapticFeedbackConstants, ShortcutManagerCompat resmi Android docs ile dogrulandi
- Architecture: HIGH — WorkManager + DataStore pattern resmi Glance dokumantasyonunda onerilen standart
- Pitfalls: HIGH — Glance/Koin DI sorunu spesifik bir mimari sinir; diger pitfall'lar resmi docs'tan
- API levels: HIGH — developer.android.com/reference ile dogrulandi, projede minSdk=31 tum constantlar aktif

**Research date:** 2026-03-13
**Valid until:** 2026-09-13 (Glance major version degisimi olursa yenile)
