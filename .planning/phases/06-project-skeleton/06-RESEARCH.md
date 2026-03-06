# Phase 6: Project Skeleton - Research

**Researched:** 2026-03-06
**Domain:** Android Native (Kotlin + Jetpack Compose) Project Setup
**Confidence:** HIGH

## Summary

Bu faz, TonbilAiOS Android uygulamasinin temel iskeletini olusturuyor. AGP 9.0+ ile gelen yerlesik Kotlin destegi, Compose BOM 2026.02.01, Koin 4.1.1 DI, Ktor 3.4.0 HTTP client ve Navigation Compose 2.9.7 (type-safe routes) kullanilacak. AGP 9.0, Kotlin Android eklentisini ayrica eklemeye gerek kalmadan yerlesik Kotlin derleme destegi sunuyor — bu onemli bir mimari degisiklik.

Proje, `android/` klasorunde feature-based paket yapisiyla olusturulacak. Cyberpunk tema, Material 3 `darkColorScheme()` uzerine ozel neon renk paleti eklenerek saglanacak. Bottom navigation 4 tab (Panel, Cihaz, Guvenlik, Ayar) ile kurulacak. Ktor client, wall.tonbilx.com adresine JSON istegi gonderebilecek sekilde yapilandirilacak.

**Primary recommendation:** AGP 9.0.1 + Gradle 9.1 + KGP 2.2.10 (yerlesik) + Compose BOM 2026.02.01 + Koin BOM 4.1.1 + Ktor 3.4.0 + Navigation 2.9.7 kullanin. Kotlin Android eklentisini EKLEMEYIN — AGP 9.0 bunu dahili olarak yonetiyor.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- 4 tab: Panel (Dashboard), Cihaz, Guvenlik, Ayar
- Guvenlik tab'i altinda: DNS Filtreleme, Firewall, VPN, DDoS Koruma
- Ayarlar tab'i altinda: AI Chat, Telegram, WiFi AP, DHCP, Guvenlik Ayarlari
- Trafik izleme: Dashboard icinde erisiliyor
- Profil yonetimi: Guvenlik > DNS icinde
- Proje yeri: Bu repo icinde `android/` klasoru (TonbilAiFirevallv5/android/)
- Package adi: com.tonbil.aifirewall
- Package organizasyonu: Feature-based
- Min API: 31 (Android 12) — S24 Ultra hedefli, Material You destegi
- Target API: En guncel (Android 14+)
- Splash screen: Neon animasyonlu (Android 12+ SplashScreen API)
- Onboarding: 2 sayfa — 1) Hosgeldin, 2) Sunucu baglanti ayarlari
- Sunucu kesfetme: mDNS/LAN tarama + QR kod + manuel URL girisi
- Glassmorphism: Sadelestirilmis cam efekti, minimal blur (performans onceligi)
- UI sistemi: Material 3 + ozel cyberpunk tema
- Neon glow: Sadece onemli ogelerde
- Arka plan: Koyu mor-siyah gradient

### Claude's Discretion
- Exact Gradle/AGP version pinning
- Compose BOM version selection
- Koin module structure
- Ktor client engine choice (OkHttp vs CIO)
- Navigation graph implementation details
- Splash animation specifics (duration, easing)
- Feature module internal package structure

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETUP-01 | Gelistirme ortami kurulumu — JDK 21, Android SDK, Gradle, komut satirindan APK build | AGP 9.0.1 + Gradle 9.1.0 + JDK 17+ (21 onerilir). Tum versiyon uyumlulugu dogrulandi. |
| SETUP-02 | Kotlin + Jetpack Compose proje iskeleti (AGP 9.0, Compose BOM, Koin DI, Navigation) | AGP 9.0 yerlesik Kotlin destegi, Compose BOM 2026.02.01, Koin 4.1.1 BOM, Navigation 2.9.7 type-safe routes |
| SETUP-03 | Cyberpunk tema — neon cyan/magenta/green/amber/red renk paleti + koyu arka plan | Material 3 darkColorScheme() + ozel renk esleme + CompositionLocal ile ek renkler |
| SETUP-04 | Navigasyon yapisi — bottom navigation + ekranlar arasi gecis (type-safe routes) | Navigation Compose 2.9.7 + @Serializable route objeler + NavigationBar composable |
| SETUP-05 | Ktor API client — base URL, JSON serialization, hata yonetimi | Ktor 3.4.0 + OkHttp engine + ContentNegotiation + kotlinx.serialization |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| AGP | 9.0.1 | Android build | En guncel stabil, yerlesik Kotlin destegi |
| Gradle | 9.1.0 | Build sistemi | AGP 9.0 minimum gereksinimi |
| Kotlin (KGP) | 2.2.10 | Dil | AGP 9.0 runtime bagimlilik olarak getiriyor |
| Compose BOM | 2026.02.01 | UI toolkit | En guncel stabil BOM |
| Material 3 | BOM'dan | Tasarim sistemi | Compose BOM ile versiyon yonetimi |
| Navigation Compose | 2.9.7 | Ekran navigasyonu | Type-safe routes, stabil |
| Koin BOM | 4.1.1 | Dependency injection | Kotlin-native, az boilerplate, Compose destegi |
| Ktor | 3.4.0 | HTTP client | REST + WebSocket tek kutuphane, Kotlin-native |
| kotlinx.serialization | KGP ile eslesir | JSON seri/deseri | Ktor ile dogal entegrasyon |
| core-splashscreen | 1.0.1 | Splash screen | Android 12+ SplashScreen API |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| koin-androidx-compose | BOM'dan | Compose DI | ViewModel injection composable icinden |
| koin-androidx-compose-navigation | BOM'dan | Nav + DI | NavGraph scoped ViewModel |
| ktor-client-okhttp | 3.4.0 | HTTP engine | Android icin en uygun engine |
| ktor-client-content-negotiation | 3.4.0 | JSON parse | API isteklerinde otomatik seri/deseri |
| ktor-serialization-kotlinx-json | 3.4.0 | JSON format | kotlinx.serialization Ktor entegrasyonu |
| ktor-client-logging | 3.4.0 | Debug log | Gelistirme sirasinda HTTP loglama |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OkHttp engine | CIO engine | OkHttp Android icin optimize, HTTP/2, sertifika pinning hazir; CIO multiplatform ama Android'e ozel ozellik eksik |
| Koin | Hilt | Hilt daha fazla boilerplate + kapt/ksp gerektirir; Koin runtime DI, daha basit setup |
| Ktor | Retrofit | Retrofit sadece REST; Ktor REST + WebSocket tek kutuphane |

### Discretion Decisions (Claude)
- **AGP:** 9.0.1 (Ocak 2026 stabil, 9.1.0 Mart 2026'da cikti ama yeni proje icin 9.0.1 daha guvenli)
- **Compose BOM:** 2026.02.01
- **Ktor engine:** OkHttp (Android icin en iyi performans, HTTP/2, sertifika pinning)
- **Koin module yapisi:** Asagidaki Architecture Patterns bolumunde detaylandirildi

**Installation (libs.versions.toml):**
```toml
[versions]
agp = "9.0.1"
kotlin = "2.2.10"
composeBom = "2026.02.01"
koinBom = "4.1.1"
ktor = "3.4.0"
navigationCompose = "2.9.7"
coreSplashscreen = "1.0.1"
activityCompose = "1.10.1"
coreKtx = "1.16.0"

[libraries]
# Compose
compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "composeBom" }
compose-ui = { group = "androidx.compose.ui", name = "ui" }
compose-ui-graphics = { group = "androidx.compose.ui", name = "ui-graphics" }
compose-ui-tooling-preview = { group = "androidx.compose.ui", name = "ui-tooling-preview" }
compose-material3 = { group = "androidx.compose.material3", name = "material3" }
compose-material-icons = { group = "androidx.compose.material", name = "material-icons-extended" }
activity-compose = { group = "androidx.activity", name = "activity-compose", version.ref = "activityCompose" }

# Navigation
navigation-compose = { group = "androidx.navigation", name = "navigation-compose", version.ref = "navigationCompose" }

# Koin
koin-bom = { group = "io.insert-koin", name = "koin-bom", version.ref = "koinBom" }
koin-androidx-compose = { group = "io.insert-koin", name = "koin-androidx-compose" }
koin-androidx-compose-navigation = { group = "io.insert-koin", name = "koin-androidx-compose-navigation" }

# Ktor
ktor-client-core = { group = "io.ktor", name = "ktor-client-core", version.ref = "ktor" }
ktor-client-okhttp = { group = "io.ktor", name = "ktor-client-okhttp", version.ref = "ktor" }
ktor-client-content-negotiation = { group = "io.ktor", name = "ktor-client-content-negotiation", version.ref = "ktor" }
ktor-serialization-kotlinx-json = { group = "io.ktor", name = "ktor-serialization-kotlinx-json", version.ref = "ktor" }
ktor-client-logging = { group = "io.ktor", name = "ktor-client-logging", version.ref = "ktor" }

# AndroidX
core-ktx = { group = "androidx.core", name = "core-ktx", version.ref = "coreKtx" }
core-splashscreen = { group = "androidx.core", name = "core-splashscreen", version.ref = "coreSplashscreen" }

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
compose-compiler = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
```

**KRITIK:** `org.jetbrains.kotlin.android` eklentisini EKLEMEYIN. AGP 9.0 Kotlin derlemeyi dahili olarak yonetir.

## Architecture Patterns

### Recommended Project Structure
```
android/
├── build.gradle.kts              # Root build (plugins block)
├── settings.gradle.kts           # Module + dependency resolution
├── gradle.properties             # JVM args + Android props
├── gradle/
│   └── libs.versions.toml        # Version catalog
├── app/
│   ├── build.gradle.kts          # App module config
│   └── src/main/
│       ├── AndroidManifest.xml
│       ├── res/
│       │   ├── values/
│       │   │   ├── themes.xml    # Splash theme + base theme
│       │   │   └── colors.xml    # XML renk referanslari (splash icin)
│       │   ├── drawable/         # App icon, splash icon
│       │   └── mipmap-*/         # Launcher icons
│       └── java/com/tonbil/aifirewall/
│           ├── TonbilApp.kt              # Application sinifi (Koin init)
│           ├── MainActivity.kt           # Tek Activity (splash + Compose setContent)
│           ├── di/
│           │   ├── AppModule.kt          # Genel DI (Ktor client, vb.)
│           │   └── FeatureModules.kt     # Feature bazli DI modulleri
│           ├── ui/
│           │   ├── theme/
│           │   │   ├── Color.kt          # Neon renk paleti
│           │   │   ├── Type.kt           # Tipografi
│           │   │   ├── Theme.kt          # CyberpunkTheme composable
│           │   │   └── Shape.kt          # Kart koseleri, vb.
│           │   ├── navigation/
│           │   │   ├── NavRoutes.kt      # @Serializable route objeler
│           │   │   ├── AppNavHost.kt     # NavHost + graph tanimlari
│           │   │   └── BottomNavBar.kt   # Bottom navigation bar
│           │   └── components/
│           │       ├── GlassCard.kt      # Glassmorphism kart
│           │       ├── NeonBadge.kt      # Neon etiket
│           │       └── LoadingIndicator.kt
│           ├── feature/
│           │   ├── dashboard/
│           │   │   ├── DashboardScreen.kt
│           │   │   └── DashboardViewModel.kt
│           │   ├── devices/
│           │   │   ├── DevicesScreen.kt
│           │   │   └── DevicesViewModel.kt
│           │   ├── security/
│           │   │   ├── SecurityScreen.kt
│           │   │   └── SecurityViewModel.kt
│           │   └── settings/
│           │       ├── SettingsScreen.kt
│           │       └── SettingsViewModel.kt
│           └── data/
│               ├── remote/
│               │   ├── ApiClient.kt      # Ktor HttpClient factory
│               │   ├── ApiRoutes.kt      # Endpoint URL sabitleri
│               │   └── dto/              # API veri transfer objeleri
│               └── repository/           # (Phase 6'da bos, ilerideki fazlar icin)
```

### Pattern 1: AGP 9.0 Plugin Setup (Kotlin Android eklentisi YOK)
**What:** AGP 9.0 Kotlin derlemeyi dahili olarak yonetir
**When to use:** Her zaman (AGP 9.0+ projelerde)
**Example:**
```kotlin
// root build.gradle.kts
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.compose.compiler) apply false
    // DIKKAT: kotlin-android eklentisi YOK!
}
```

```kotlin
// app/build.gradle.kts
plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.compose.compiler)
    // DIKKAT: kotlin-android eklentisi YOK!
}

android {
    namespace = "com.tonbil.aifirewall"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.tonbil.aifirewall"
        minSdk = 31
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    // Compose BOM
    val composeBom = platform(libs.compose.bom)
    implementation(composeBom)
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.graphics)
    implementation(libs.compose.ui.tooling.preview)
    implementation(libs.compose.material3)
    implementation(libs.compose.material.icons)
    implementation(libs.activity.compose)
    debugImplementation("androidx.compose.ui:ui-tooling")

    // Navigation
    implementation(libs.navigation.compose)

    // Koin
    implementation(platform(libs.koin.bom))
    implementation(libs.koin.androidx.compose)
    implementation(libs.koin.androidx.compose.navigation)

    // Ktor
    implementation(libs.ktor.client.core)
    implementation(libs.ktor.client.okhttp)
    implementation(libs.ktor.client.content.negotiation)
    implementation(libs.ktor.serialization.kotlinx.json)
    implementation(libs.ktor.client.logging)

    // AndroidX
    implementation(libs.core.ktx)
    implementation(libs.core.splashscreen)
}
```

### Pattern 2: Cyberpunk Dark Theme (Material 3)
**What:** Ozel neon renk paleti + Material 3 darkColorScheme
**When to use:** Uygulama genelinde tema tanimlamak icin
**Example:**
```kotlin
// Color.kt
package com.tonbil.aifirewall.ui.theme

import androidx.compose.ui.graphics.Color

// Neon renk paleti (web ile tutarli)
val NeonCyan = Color(0xFF00F0FF)
val NeonMagenta = Color(0xFFFF00E5)
val NeonGreen = Color(0xFF39FF14)
val NeonAmber = Color(0xFFFFB800)
val NeonRed = Color(0xFFFF003C)

// Arka plan renkleri
val DarkBackground = Color(0xFF0A0A1A)      // Koyu mor-siyah
val DarkSurface = Color(0xFF12122A)          // Kart arka plani
val DarkSurfaceVariant = Color(0xFF1A1A3A)   // Yukseltilmis yuzey

// Glass efekt
val GlassBg = Color(0x0DFFFFFF)             // rgba(255,255,255,0.05)
val GlassBorder = Color(0x1FFFFFFF)         // rgba(255,255,255,0.12)

// Metin
val TextPrimary = Color(0xFFE0E0FF)
val TextSecondary = Color(0xFF8888AA)
```

```kotlin
// Theme.kt
package com.tonbil.aifirewall.ui.theme

import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color

private val CyberpunkColorScheme = darkColorScheme(
    primary = NeonCyan,
    onPrimary = Color.Black,
    secondary = NeonMagenta,
    onSecondary = Color.Black,
    tertiary = NeonGreen,
    onTertiary = Color.Black,
    error = NeonRed,
    onError = Color.Black,
    background = DarkBackground,
    onBackground = TextPrimary,
    surface = DarkSurface,
    onSurface = TextPrimary,
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = TextSecondary,
    outline = GlassBorder,
)

// Ek renkler icin CompositionLocal
data class CyberpunkColors(
    val neonCyan: Color = NeonCyan,
    val neonMagenta: Color = NeonMagenta,
    val neonGreen: Color = NeonGreen,
    val neonAmber: Color = NeonAmber,
    val neonRed: Color = NeonRed,
    val glassBg: Color = GlassBg,
    val glassBorder: Color = GlassBorder,
)

val LocalCyberpunkColors = staticCompositionLocalOf { CyberpunkColors() }

@Composable
fun CyberpunkTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalCyberpunkColors provides CyberpunkColors()) {
        MaterialTheme(
            colorScheme = CyberpunkColorScheme,
            typography = CyberpunkTypography,
            content = content
        )
    }
}

// Kolay erisim
object CyberpunkTheme {
    val colors: CyberpunkColors
        @Composable get() = LocalCyberpunkColors.current
}
```

### Pattern 3: Type-Safe Navigation (Navigation 2.9.7)
**What:** @Serializable route objeleri ile tip-guvenli navigasyon
**When to use:** Ekranlar arasi gecis tanimlamak icin
**Example:**
```kotlin
// NavRoutes.kt
package com.tonbil.aifirewall.ui.navigation

import kotlinx.serialization.Serializable

@Serializable object DashboardRoute
@Serializable object DevicesRoute
@Serializable object SecurityRoute
@Serializable object SettingsRoute

// Alt ekranlar (ilerideki fazlar icin hazirlik)
@Serializable data class DeviceDetailRoute(val deviceId: String)
```

```kotlin
// AppNavHost.kt
@Composable
fun AppNavHost(navController: NavHostController, modifier: Modifier = Modifier) {
    NavHost(
        navController = navController,
        startDestination = DashboardRoute,
        modifier = modifier
    ) {
        composable<DashboardRoute> { DashboardScreen() }
        composable<DevicesRoute> { DevicesScreen() }
        composable<SecurityRoute> { SecurityScreen() }
        composable<SettingsRoute> { SettingsScreen() }
    }
}
```

```kotlin
// BottomNavBar.kt
data class BottomNavItem(
    val label: String,
    val icon: ImageVector,
    val route: Any, // Serializable route
)

val bottomNavItems = listOf(
    BottomNavItem("Panel", Icons.Default.Home, DashboardRoute),
    BottomNavItem("Cihaz", Icons.Default.Smartphone, DevicesRoute),
    BottomNavItem("Guvenlik", Icons.Default.Shield, SecurityRoute),
    BottomNavItem("Ayar", Icons.Default.Settings, SettingsRoute),
)
```

### Pattern 4: Koin DI Setup
**What:** Application sinifinda Koin baslatma + module tanimlari
**Example:**
```kotlin
// TonbilApp.kt
class TonbilApp : Application() {
    override fun onCreate() {
        super.onCreate()
        startKoin {
            androidContext(this@TonbilApp)
            modules(appModule, featureModules)
        }
    }
}

// AppModule.kt
val appModule = module {
    single { createHttpClient() }
}

val featureModules = module {
    // Phase 6: placeholder ViewModel'ler
    viewModel { DashboardViewModel(get()) }
    viewModel { DevicesViewModel() }
    viewModel { SecurityViewModel() }
    viewModel { SettingsViewModel() }
}
```

### Pattern 5: Ktor Client Setup
**What:** OkHttp engine + JSON content negotiation + hata yonetimi
**Example:**
```kotlin
// ApiClient.kt
fun createHttpClient(): HttpClient {
    return HttpClient(OkHttp) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
                prettyPrint = false
            })
        }
        install(Logging) {
            level = LogLevel.BODY // Debug icin, release'de NONE
        }
        defaultRequest {
            url("https://wall.tonbilx.com/api/v1/")
            contentType(ContentType.Application.Json)
        }
        // Timeout
        install(HttpTimeout) {
            requestTimeoutMillis = 15_000
            connectTimeoutMillis = 10_000
        }
    }
}
```

### Pattern 6: SplashScreen API (Android 12+)
**What:** installSplashScreen() ile sistem splash ekrani
**Example:**
```kotlin
// MainActivity.kt
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        val splashScreen = installSplashScreen()

        // Splash'i biraz tutmak icin (ornegin tema yukleme)
        var keepSplash = true
        splashScreen.setKeepOnScreenCondition { keepSplash }

        super.onCreate(savedInstanceState)

        // Splash animasyonu bittikten sonra
        lifecycleScope.launch {
            delay(800) // Kisa bekleme
            keepSplash = false
        }

        setContent {
            CyberpunkTheme {
                MainScreen()
            }
        }
    }
}
```

```xml
<!-- res/values/themes.xml -->
<resources>
    <style name="Theme.TonbilAi.Splash" parent="Theme.SplashScreen">
        <item name="windowSplashScreenBackground">#0A0A1A</item>
        <item name="windowSplashScreenAnimatedIcon">@drawable/ic_splash_logo</item>
        <item name="postSplashScreenTheme">@style/Theme.TonbilAi</item>
    </style>

    <style name="Theme.TonbilAi" parent="Theme.Material3.DynamicColors.DayNight">
        <item name="android:windowBackground">#0A0A1A</item>
    </style>
</resources>
```

### Anti-Patterns to Avoid
- **kotlin-android eklentisi eklemek:** AGP 9.0 ile gereksiz ve cakisma yaratabilir
- **String-based route kullanmak:** Navigation 2.8+ type-safe route destekliyor, string route kullanmayin
- **Activity-per-screen:** Tek Activity + Compose Navigation kullanin
- **Hilt kullanmak:** Karar verildi: Koin. Hilt kapt/ksp gerektirir, daha fazla boilerplate
- **Retrofit kullanmak:** Karar verildi: Ktor. WebSocket icin ayri kutuphane gerekir

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON parsing | Manuel JSON parse | kotlinx.serialization + Ktor ContentNegotiation | Hata egilimli, tip guvenliksiz |
| DI container | Manuel singleton/factory | Koin | Yasam dongusu yonetimi, test destegi |
| HTTP client | Raw OkHttp | Ktor client | Plugin sistemi, content negotiation, platform soyutlama |
| Navigation | Manuel Fragment/Activity yonetimi | Navigation Compose | Backstack, deep link, type safety |
| Splash screen | Timer + Activity | core-splashscreen API | Sistem entegrasyonu, sorunsuz gecis |
| Renk yonetimi | Sabit Color() degerler her yerde | MaterialTheme + CompositionLocal | Tutarlilik, dinamik tema destegi |

## Common Pitfalls

### Pitfall 1: AGP 9.0 kotlin-android Eklenti Cakismasi
**What goes wrong:** `org.jetbrains.kotlin.android` eklentisi eklenirse AGP 9.0 ile cakisma oluyor
**Why it happens:** AGP 9.0 Kotlin derlemeyi dahili olarak yonetiyor, ayri eklenti gereksiz
**How to avoid:** Sadece `com.android.application`, `kotlin.plugin.serialization` ve `kotlin.plugin.compose` eklentilerini kullanin
**Warning signs:** Build sirasinda "kotlin plugin already applied" uyarisi

### Pitfall 2: Gradle Version Mismatch
**What goes wrong:** Gradle 8.x ile AGP 9.0 kullanilamaz
**Why it happens:** AGP 9.0 minimum Gradle 9.1.0 gerektiriyor
**How to avoid:** `gradle-wrapper.properties`'de Gradle 9.1.0 ayarlayin
**Warning signs:** "This version of AGP requires Gradle X or higher" hatasi

### Pitfall 3: compileSdk vs targetSdk Karisikligi
**What goes wrong:** AGP 9.0'da targetSdk belirtilmezse compileSdk'ya esitlenir
**Why it happens:** Eski AGP'lerde targetSdk minSdk'ya esitlenirdi, yeni davranis farkli
**How to avoid:** Her iki degeri de acikca belirtin: compileSdk = 36, targetSdk = 36

### Pitfall 4: Compose BOM Versiyon Cakismasi
**What goes wrong:** BOM disinda ayri Compose kutuphane versiyonu belirtilirse cakisma
**Why it happens:** BOM tum Compose kutuphanelerinin versiyonunu birlikte yonetiyor
**How to avoid:** BOM kullanirken compose kutuphanelerine versiyon YAZMAYIN

### Pitfall 5: Navigation Compose Route Serialization
**What goes wrong:** @Serializable olmayan sinif route olarak kullanilamaz
**Why it happens:** Navigation 2.8+ type-safe routes Kotlin serialization gerektiriyor
**How to avoid:** Tum route siniflarini/objelerini @Serializable ile isaretle, kotlinx.serialization eklentisini ekle

### Pitfall 6: Glassmorphism Performans
**What goes wrong:** Asiri blur + saydam gradient kullanimi dusuk performansa yol acar
**Why it happens:** `graphicsLayer { alpha }` + `blur()` GPU uzerinde pahali
**How to avoid:** Blur'u minimumda tut (0-4dp arasi), saydam overlay yerine solid koyu renkler tercih et
**Warning signs:** UI janking, dusuk FPS scrollda

## Code Examples

### MainActivity Tam Yapi (Phase 6)
```kotlin
// Source: AGP 9.0 docs + core-splashscreen docs + Compose docs
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        val splashScreen = installSplashScreen()
        super.onCreate(savedInstanceState)

        setContent {
            CyberpunkTheme {
                val navController = rememberNavController()
                Scaffold(
                    bottomBar = {
                        CyberpunkBottomNav(navController)
                    }
                ) { innerPadding ->
                    AppNavHost(
                        navController = navController,
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }
}
```

### GlassCard Composable
```kotlin
@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit
) {
    val cyberpunk = CyberpunkTheme.colors
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = cyberpunk.glassBg
        ),
        border = BorderStroke(1.dp, cyberpunk.glassBorder),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            content = content
        )
    }
}
```

### Placeholder Ekran (Phase 6 icin yeterli)
```kotlin
@Composable
fun DashboardScreen(viewModel: DashboardViewModel = koinViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "Panel",
            style = MaterialTheme.typography.headlineLarge,
            color = CyberpunkTheme.colors.neonCyan
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "API: ${uiState.connectionStatus}",
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| kotlin-android plugin | AGP built-in Kotlin | AGP 9.0 (Jan 2026) | Plugin kaldirilmali |
| String route navigation | @Serializable type-safe routes | Nav 2.8.0 (2024) | Derleme zamani tip guvenligi |
| Compose compiler ayri versiyon | Kotlin ile birlikte gelir | Kotlin 2.0+ | Versiyon uyumluluk sorunu yok |
| kapt (annotation processing) | KSP | 2024+ | Daha hizli build, kapt deprecated |
| Koin 3.x | Koin 4.1.1 (Kotlin 2.0+) | 2025 | Compose 1.8 destegi, BOM yaklasimi |
| Ktor 2.x | Ktor 3.4.0 | 2025 | Yeni API, OkHttp 5.1 entegrasyonu |

**Deprecated/outdated:**
- `org.jetbrains.kotlin.android` eklentisi: AGP 9.0 ile gereksiz
- `kapt`: KSP ile degistirildi (Koin zaten annotation processing gerektirmez)
- `Gradle 8.x`: AGP 9.0 ile uyumsuz
- String-based Navigation routes: 2.8.0'dan beri deprecated

## Open Questions

1. **Gradle 9.1 Wrapper Dagitimi**
   - What we know: AGP 9.0 minimum Gradle 9.1.0 gerektiriyor
   - What's unclear: Gradle wrapper'in komut satirindan kurulumu (Android Studio kullanilmiyor)
   - Recommendation: `gradle wrapper --gradle-version 9.1` komutu ile veya `gradle-wrapper.properties` dosyasini elle olusturun

2. **Splash Screen Animasyonu**
   - What we know: Android 12+ SplashScreen API animasyonlu ikon destekliyor
   - What's unclear: Animated Vector Drawable (AVD) olusturma sureci
   - Recommendation: Phase 6 icin basit statik ikon yeterli, animasyon Phase 14 UX Polish'te eklenebilir

3. **mDNS/LAN Tarama**
   - What we know: Kullanici onboarding'de sunucu kesfetme istiyor
   - What's unclear: Android 12+ NSD (Network Service Discovery) API kisitlamalari
   - Recommendation: Phase 6'da sadece manuel URL girisi + hardcoded test URL. mDNS/QR kod ilerideki fazlarda (Phase 7 AUTH-05/06)

## Sources

### Primary (HIGH confidence)
- [AGP 9.0.1 Release Notes](https://developer.android.com/build/releases/agp-9-0-0-release-notes) - Tum breaking changes, minimum gereksinimler, KGP 2.2.10 bagimlilik
- [Compose BOM](https://developer.android.com/develop/ui/compose/bom) - BOM 2026.02.01 dogrulandi
- [Koin Setup](https://insert-koin.io/docs/setup/koin/) - Koin BOM 4.1.1, koin-androidx-compose koordinatlari
- [Ktor Client Engines](https://ktor.io/docs/client-engines.html) - OkHttp engine, Ktor 3.4.0
- [Navigation Type-Safe Routes](https://developer.android.com/guide/navigation/type-safe-destinations) - @Serializable route objeleri

### Secondary (MEDIUM confidence)
- [JetBrains AGP 9 Migration](https://blog.jetbrains.com/kotlin/2026/01/update-your-projects-for-agp9/) - kotlin-android eklentisi kaldirilmasi
- [Koin 4.1 Blog](https://blog.kotzilla.io/koin-4.1-is-here) - Compose 1.8 destegi, yeni ozellikler
- [Ktor 3.3.0 Changelog](https://ktor.io/docs/whats-new-330.html) - OkHttp 5.1 upgrade bilgisi
- [core-splashscreen](https://developer.android.com/develop/ui/views/launch/splash-screen) - SplashScreen API kullanimi

### Tertiary (LOW confidence)
- Material 3 cyberpunk tema yaklasimi: Genel Compose theming dokumantasyonundan turetildi, ozel cyberpunk ornegi resmi kaynaklarda yok

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Tum versiyonlar resmi kaynaklardan dogrulandi (AGP 9.0.1, Gradle 9.1, KGP 2.2.10, Compose BOM 2026.02.01, Koin 4.1.1, Ktor 3.4.0)
- Architecture: HIGH - Feature-based yapi Android toplulugunda standart, AGP 9.0 plugin yapisi resmi dokumantasyondan
- Pitfalls: HIGH - AGP 9.0 breaking changes resmi release notes'dan, Compose BOM davranisi resmi dokumantasyondan
- Theme: MEDIUM - Material 3 darkColorScheme resmi, cyberpunk renk esleme kullanici kararindan turetildi

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (30 gun — stabil teknolojiler)
