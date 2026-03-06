# Technology Stack — TonbilAiOS Android App

**Project:** TonbilAiOS v2.0 Android App
**Researched:** 2026-03-06
**Overall Confidence:** HIGH (versions verified via official docs and Maven repositories)

---

## Recommended Stack

### Build System & Language

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Kotlin | 2.3.10 | Primary language | Stable release (Feb 2026). KSP support, Compose compiler built-in. Avoid 2.3.20-RC2 (release candidate). | HIGH |
| Android Gradle Plugin | 9.0.1 | Build toolchain | Stable (Jan 2026). Built-in Kotlin support (no separate kotlin-android plugin needed). AGP 9.1 is too fresh. | HIGH |
| Gradle | 9.1.0+ | Build automation | Required by AGP 9.0. Use `libs.versions.toml` version catalog for dependency management. | HIGH |
| Compose Compiler | Built-in | Kotlin→Compose compilation | Kotlin 2.0+ bundles the Compose compiler plugin. No separate `kotlinCompilerExtensionVersion` needed. | HIGH |

### Core UI Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Jetpack Compose BOM | 2026.02.01 | UI toolkit version management | Latest stable BOM. Manages all Compose library versions automatically. | HIGH |
| Compose UI | 1.10.4 (via BOM) | Core UI rendering | Stable, well-tested. No need to pin individual versions when using BOM. | HIGH |
| Material 3 | 1.4.0 (via BOM) | Design system | Supports custom dark color schemes — essential for cyberpunk theme. `darkColorScheme()` with neon hex values. | HIGH |
| Compose Animation | 1.10.4 (via BOM) | Neon glow/pulse effects | Built-in animation APIs for glow effects, pulsing badges, transition animations. | HIGH |

### Navigation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Navigation Compose | 2.9.7 | Screen navigation | Type-safe routes with `@Serializable` (stable since 2.8.0). Compose-first API. Avoid Navigation3 (prerelease). | HIGH |
| Kotlin Serialization Plugin | 2.3.10 | Route serialization | Required by type-safe navigation. Match Kotlin version exactly. | HIGH |

### Networking — REST API

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Ktor Client | 3.4.1 | HTTP client (REST + WebSocket) | Latest stable (March 2026). Kotlin-native, coroutine-based, multiplatform-ready. Single library for both REST and WebSocket — no need for separate OkHttp + WebSocket libs. | HIGH |
| Ktor Client OkHttp Engine | 3.4.1 | HTTP engine for Android | OkHttp engine is the most mature Android engine. Handles connection pooling, TLS, HTTP/2 transparently. | HIGH |
| Ktor Content Negotiation | 3.4.1 | JSON serialization | Plugs into Ktor client for automatic JSON (de)serialization of request/response bodies. | HIGH |
| Ktor Client WebSockets | 3.4.1 | Real-time data (WebSocket) | Native WebSocket support in same Ktor client. Integrates with Kotlin Flows for reactive data streams. Replaces existing web frontend's `useWebSocket.ts`. | HIGH |
| Ktor Client Auth | 3.4.1 | JWT bearer token handling | Built-in bearer token provider with automatic refresh. No manual interceptor code needed. | HIGH |
| Kotlinx Serialization JSON | 1.7.3 | JSON parsing | Kotlin-native serialization. Faster than Gson/Moshi, no reflection. Works with Ktor content negotiation. | MEDIUM |

### Dependency Injection

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Koin | 4.1.1 (via Koin BOM) | Dependency injection | Kotlin DSL-based, zero annotation processing, fast build times. Better for single-developer projects than Hilt (less boilerplate). Compose integration built-in via `koinViewModel()`. | HIGH |
| Koin Android | 4.1.1 | Android-specific DI | ViewModel injection, WorkManager integration, Android lifecycle awareness. | HIGH |
| Koin Compose | 4.1.1 | Compose DI integration | Direct `koinViewModel()` in Composables. No need for Hilt's `@HiltViewModel` + `hiltViewModel()` ceremony. | HIGH |

### Authentication

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| AndroidX Biometric | 1.1.0 | Fingerprint/face auth | Latest stable. Provides `BiometricPrompt` with PIN/password fallback. S24 Ultra supports fingerprint + face. | HIGH |
| AndroidX Biometric (alpha) | 1.4.0-alpha05 | Compose-friendly auth | Optional upgrade: `registerForAuthenticationResult()` API, `biometric-compose` module. Only if stable API feels limiting. | LOW |

### Secure Storage

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| DataStore Preferences | 1.2.0 | Local key-value storage | Replaces SharedPreferences. Coroutine-based, type-safe. For JWT tokens, user preferences, server URL. | HIGH |
| Google Tink Android | 1.16.0 | Encryption for DataStore | EncryptedSharedPreferences is DEPRECATED (security-crypto 1.1.0-alpha07). Tink + DataStore is the official replacement. AES-GCM encryption with Android Keystore key management. | HIGH |

**CRITICAL: Do NOT use EncryptedSharedPreferences.** It is deprecated, has OEM-specific crashes ("keyset corruption"), and causes main-thread blocking. Use DataStore + Tink instead.

### Push Notifications

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Firebase BOM | 34.10.0 | Firebase version management | Latest BOM (Feb 2026). Manages all Firebase library versions. | MEDIUM |
| Firebase Cloud Messaging | via BOM | Push notifications | Android standard for push. FCM token registration → backend stores token → backend sends notifications via FCM HTTP v1 API. | HIGH |

### Image Loading

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Coil 3 | 3.4.0 | Image loading (device icons, avatars) | Kotlin-first, Compose-native (`AsyncImage`), coroutine-based. Lighter than Glide/Picasso. Compose integration is first-class. | HIGH |

### Architecture Components

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Lifecycle ViewModel Compose | latest via BOM | ViewModel in Compose | `viewModel()` composable function. State management per-screen. | HIGH |
| Lifecycle Runtime Compose | latest via BOM | Lifecycle-aware Compose | `collectAsStateWithLifecycle()` for Flow→State conversion respecting lifecycle. | HIGH |
| Kotlinx Coroutines Android | 1.10.1 | Async operations | Dispatchers.Main, structured concurrency, Flow for reactive streams. | MEDIUM |

### Charts & Visualization

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Vico | 2.1.2 | Charts (bandwidth, traffic) | Compose-native charting library. Supports line, bar, and combined charts. Alternative to MPAndroidChart (View-based, not Compose-native). | MEDIUM |

### Testing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| JUnit 5 | 5.11.x | Unit tests | Standard JVM testing framework. | HIGH |
| Compose UI Test | via BOM | UI tests | `createComposeRule()` for Compose UI testing. | HIGH |
| Ktor Client Mock | 3.4.1 | API mocking | Built-in mock engine for Ktor — no separate mock server needed. | HIGH |
| Koin Test | 4.1.1 | DI testing | `checkModules()` for verifying DI graph at test time. | HIGH |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| HTTP Client | Ktor Client 3.4.1 | Retrofit 2.x + OkHttp | Retrofit is Java-first, requires annotation processor. Ktor is Kotlin-native, coroutine-native, handles both REST and WebSocket in one library. Retrofit would need a separate WebSocket library. |
| DI Framework | Koin 4.1.1 | Hilt (Dagger) 2.x | Hilt requires KSP/KAPT annotation processing, adds build time, more boilerplate. For a single-developer project, Koin's DSL is faster to write and debug. Performance difference is negligible in real apps. |
| JSON Parser | Kotlinx Serialization | Gson / Moshi | Gson uses reflection (slow, ProGuard issues). Moshi is good but requires codegen. Kotlinx Serialization is compile-time, Kotlin-native, and required by Navigation Compose type-safe routes anyway. |
| Image Loading | Coil 3 | Glide 4.x / Picasso | Glide is View-based, requires `GlideImage` wrapper for Compose. Coil is Compose-native. Picasso is unmaintained. |
| Charts | Vico | MPAndroidChart | MPAndroidChart is View-based (requires `AndroidView` wrapper in Compose). Vico is Compose-native. |
| Secure Storage | DataStore + Tink | EncryptedSharedPreferences | DEPRECATED. Keyset corruption bugs on Samsung/Huawei devices. Main-thread blocking. Official guidance is to migrate to DataStore + Tink. |
| Navigation | Navigation Compose 2.9.7 | Voyager / Compose Destinations | Official Jetpack solution, type-safe since 2.8.0. Third-party navlibs add risk of abandonment. |
| WebSocket | Ktor Client WebSockets | Scarlet / OkHttp WebSocket | Ktor provides WebSocket in the same client. No separate dependency. Scarlet is unmaintained. |
| Biometric | AndroidX Biometric 1.1.0 | Custom fingerprint API | AndroidX Biometric abstracts hardware differences. Custom API would break on Samsung vs Pixel vs Xiaomi. |

---

## What NOT to Use

| Avoid | Why |
|-------|-----|
| **Retrofit** | Java-first API, requires separate WebSocket solution. Ktor covers REST + WebSocket in one library. |
| **Dagger (without Hilt)** | Raw Dagger is overkill for any project in 2026. If you want compile-time DI, use Hilt. But Koin is simpler here. |
| **Room Database** | This app is a thin client — all data lives on the Pi's MariaDB. Local caching uses DataStore, not a full SQL database. |
| **Jetpack Compose Multiplatform** | Scope is Android-only for v2.0. KMP adds complexity. If iOS is needed later, Ktor + Koin are already multiplatform-ready. |
| **XML Layouts** | Dead in 2026 for new projects. All UI must be Jetpack Compose. |
| **SharedPreferences** | Deprecated pattern. Use DataStore. |
| **EncryptedSharedPreferences** | Officially deprecated. Use DataStore + Tink. |
| **Gson** | Reflection-based, ProGuard issues. Use kotlinx.serialization. |
| **WorkManager for WebSocket** | WebSocket should use a foreground service, not WorkManager. WorkManager is for deferred background tasks. |

---

## Cyberpunk Theme Implementation

Material 3 `darkColorScheme()` maps directly to the existing web theme:

```kotlin
// Color.kt
val NeonCyan = Color(0xFF00F0FF)
val NeonMagenta = Color(0xFFFF00E5)
val NeonGreen = Color(0xFF39FF14)
val NeonAmber = Color(0xFFFFB800)
val NeonRed = Color(0xFFFF003C)
val DarkSurface = Color(0xFF0A0A14)       // Deep purple-black
val GlassBg = Color(0x0DFFFFFF)           // 5% white
val GlassBorder = Color(0x1FFFFFFF)       // 12% white

val CyberpunkDarkScheme = darkColorScheme(
    primary = NeonCyan,
    secondary = NeonMagenta,
    tertiary = NeonGreen,
    error = NeonRed,
    background = DarkSurface,
    surface = DarkSurface,
    onPrimary = Color.Black,
    onSecondary = Color.Black,
    onBackground = Color.White,
    onSurface = Color.White,
)
```

Neon glow effects via `Modifier.drawBehind` with `drawCircle` using radial gradients and `BlendMode.Screen`. No external library needed.

---

## Gradle Setup (libs.versions.toml)

```toml
[versions]
kotlin = "2.3.10"
agp = "9.0.1"
compose-bom = "2026.02.01"
ktor = "3.4.1"
koin-bom = "4.1.1"
navigation = "2.9.7"
biometric = "1.1.0"
datastore = "1.2.0"
tink = "1.16.0"
firebase-bom = "34.10.0"
coil = "3.4.0"
vico = "2.1.2"
serialization = "1.7.3"
coroutines = "1.10.1"

[libraries]
# Compose (managed by BOM)
compose-bom = { group = "androidx.compose", name = "compose-bom", version.ref = "compose-bom" }
compose-ui = { group = "androidx.compose.ui", name = "ui" }
compose-material3 = { group = "androidx.compose.material3", name = "material3" }
compose-ui-tooling = { group = "androidx.compose.ui", name = "ui-tooling" }
compose-ui-tooling-preview = { group = "androidx.compose.ui", name = "ui-tooling-preview" }
compose-animation = { group = "androidx.compose.animation", name = "animation" }

# Navigation
navigation-compose = { group = "androidx.navigation", name = "navigation-compose", version.ref = "navigation" }

# Ktor
ktor-client-core = { group = "io.ktor", name = "ktor-client-core", version.ref = "ktor" }
ktor-client-okhttp = { group = "io.ktor", name = "ktor-client-okhttp", version.ref = "ktor" }
ktor-client-content-negotiation = { group = "io.ktor", name = "ktor-client-content-negotiation", version.ref = "ktor" }
ktor-client-websockets = { group = "io.ktor", name = "ktor-client-websockets", version.ref = "ktor" }
ktor-client-auth = { group = "io.ktor", name = "ktor-client-auth", version.ref = "ktor" }
ktor-serialization-json = { group = "io.ktor", name = "ktor-serialization-kotlinx-json", version.ref = "ktor" }
ktor-client-logging = { group = "io.ktor", name = "ktor-client-logging", version.ref = "ktor" }
ktor-client-mock = { group = "io.ktor", name = "ktor-client-mock", version.ref = "ktor" }

# Koin
koin-bom = { group = "io.insert-koin", name = "koin-bom", version.ref = "koin-bom" }
koin-android = { group = "io.insert-koin", name = "koin-android" }
koin-compose = { group = "io.insert-koin", name = "koin-androidx-compose" }
koin-compose-viewmodel = { group = "io.insert-koin", name = "koin-compose-viewmodel" }

# Security
biometric = { group = "androidx.biometric", name = "biometric", version.ref = "biometric" }
datastore-preferences = { group = "androidx.datastore", name = "datastore-preferences", version.ref = "datastore" }
tink-android = { group = "com.google.crypto.tink", name = "tink-android", version.ref = "tink" }

# Firebase
firebase-bom = { group = "com.google.firebase", name = "firebase-bom", version.ref = "firebase-bom" }
firebase-messaging = { group = "com.google.firebase", name = "firebase-messaging" }

# Image
coil-compose = { group = "io.coil-kt.coil3", name = "coil-compose", version.ref = "coil" }
coil-network = { group = "io.coil-kt.coil3", name = "coil-network-okhttp", version.ref = "coil" }

# Charts
vico-compose-m3 = { group = "com.patrykandpatrick.vico", name = "compose-m3", version.ref = "vico" }

# Serialization
kotlinx-serialization-json = { group = "org.jetbrains.kotlinx", name = "kotlinx-serialization-json", version.ref = "serialization" }
kotlinx-coroutines-android = { group = "org.jetbrains.kotlinx", name = "kotlinx-coroutines-android", version.ref = "coroutines" }

# Lifecycle
lifecycle-viewmodel-compose = { group = "androidx.lifecycle", name = "lifecycle-viewmodel-compose" }
lifecycle-runtime-compose = { group = "androidx.lifecycle", name = "lifecycle-runtime-compose" }

[bundles]
ktor = ["ktor-client-core", "ktor-client-okhttp", "ktor-client-content-negotiation",
        "ktor-client-websockets", "ktor-client-auth", "ktor-serialization-json", "ktor-client-logging"]
koin = ["koin-android", "koin-compose", "koin-compose-viewmodel"]

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }
kotlin-compose = { id = "org.jetbrains.kotlin.plugin.compose", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
google-services = { id = "com.google.gms.google-services", version = "4.4.2" }
```

---

## Android Configuration

```kotlin
// build.gradle.kts (app module)
android {
    namespace = "com.tonbil.aios"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.tonbil.aios"
        minSdk = 28          // Android 9 (Pie)
        targetSdk = 36       // Android 15
        versionCode = 1
        versionName = "2.0.0"
    }

    buildFeatures {
        compose = true
    }
}
```

- **minSdk 28:** Android 9+ covers 95%+ of active devices. BiometricPrompt requires API 28+.
- **targetSdk 36:** Latest API level supported by AGP 9.0.
- **compileSdk 36:** Match targetSdk.

---

## Backend Changes Required

The existing FastAPI backend needs these additions for the Android app:

| Endpoint | Purpose | Effort |
|----------|---------|--------|
| `POST /api/v1/devices/fcm-token` | Register FCM token for push notifications | Low |
| `DELETE /api/v1/devices/fcm-token` | Unregister FCM token on logout | Low |
| `POST /api/v1/auth/refresh` | JWT token refresh (if not already present) | Low |
| Backend FCM sender | Python `firebase-admin` SDK to send push notifications | Medium |

---

## Sources

- [Jetpack Compose Releases](https://developer.android.com/jetpack/androidx/releases/compose) — Compose BOM 2026.02.01, Material 3 1.4.0 (HIGH)
- [Ktor 3.4.0 Release Blog](https://blog.jetbrains.com/kotlin/2026/01/ktor-3-4-0-is-now-available/) — Ktor 3.4.1 stable (HIGH)
- [Kotlin 2.3.0 Release Blog](https://blog.jetbrains.com/kotlin/2025/12/kotlin-2-3-0-released/) — Kotlin 2.3.10 stable (HIGH)
- [AGP 9.0.1 Release Notes](https://developer.android.com/build/releases/agp-9-0-0-release-notes) — AGP 9.0.1 (HIGH)
- [Navigation Compose Releases](https://developer.android.com/jetpack/androidx/releases/navigation) — 2.9.7 stable (HIGH)
- [Biometric Releases](https://developer.android.com/jetpack/androidx/releases/biometric) — 1.1.0 stable, 1.4.0-alpha05 (HIGH)
- [DataStore Releases](https://developer.android.com/jetpack/androidx/releases/datastore) — 1.2.0 stable (HIGH)
- [Koin Official](https://insert-koin.io/) — 4.1.1 via BOM (HIGH)
- [Firebase BOM Maven](https://mvnrepository.com/artifact/com.google.firebase/firebase-bom) — 34.10.0 (MEDIUM)
- [Coil GitHub](https://github.com/coil-kt/coil) — 3.4.0 (HIGH)
- [Tink Setup](https://developers.google.com/tink/setup/java) — tink-android 1.16.0 (MEDIUM)
- [EncryptedSharedPreferences Deprecated](https://www.droidcon.com/2025/12/16/goodbye-encryptedsharedpreferences-a-2026-migration-guide/) — Migration guide (HIGH)
- [Hilt vs Koin 2025 Droidcon](https://www.droidcon.com/2025/11/26/hilt-vs-koin-the-hidden-cost-of-runtime-injection-and-why-compile-time-di-wins/) — DI comparison (MEDIUM)
- [Vico Charts](https://github.com/patrykandpatrick/vico) — Compose-native charting (MEDIUM)

---

*Stack research for: TonbilAiOS v2.0 Android App*
*Researched: 2026-03-06*
