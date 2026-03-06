# Architecture Research: TonbilAiOS Android App

**Domain:** Android mobil uygulama — mevcut FastAPI router yonetim backend'ine istemci
**Researched:** 2026-03-06
**Confidence:** HIGH

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ANDROID APP (Kotlin)                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    UI Layer (Compose)                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │
│  │  │Dashboard │ │ Devices  │ │   DNS    │ │ Traffic  │ ... │  │
│  │  │ Screen   │ │ Screen   │ │ Screen   │ │ Screen   │     │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘     │  │
│  └───────┼─────────────┼───────────┼───────────┼─────────────┘  │
│          │             │           │           │                │
│  ┌───────┴─────────────┴───────────┴───────────┴─────────────┐  │
│  │               ViewModel Layer (per screen)                 │  │
│  │  StateFlow<UiState> + sealed class Events                  │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┴────────────────────────────────┐  │
│  │                    Domain Layer                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │  │
│  │  │  UseCases    │  │  Models      │  │  Repository    │   │  │
│  │  │  (optional)  │  │  (domain)    │  │  Interfaces    │   │  │
│  │  └──────────────┘  └──────────────┘  └────────────────┘   │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                             │                                   │
│  ┌──────────────────────────┴────────────────────────────────┐  │
│  │                     Data Layer                             │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌─────────────────────┐  │  │
│  │  │Repository│  │  API Service │  │  Local Storage      │  │  │
│  │  │  Impls   │  │  (Ktor/OkHttp│  │  (DataStore +       │  │  │
│  │  │          │  │   + WebSocket│  │   Android Keystore) │  │  │
│  │  └──────────┘  └──────┬───────┘  └─────────────────────┘  │  │
│  └───────────────────────┼───────────────────────────────────┘  │
│                          │                                      │
│  ┌───────────────────────┴───────────────────────────────────┐  │
│  │                  Network Layer                             │  │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ NetworkManager  │  │ AuthInter-   │  │ WebSocket    │  │  │
│  │  │ (local/remote   │  │ ceptor (JWT) │  │ Client       │  │  │
│  │  │  base URL)      │  │              │  │              │  │  │
│  │  └─────────────────┘  └──────────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                Platform Services                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │Biometric │  │  FCM     │  │  Theme   │  │Connecti- │  │  │
│  │  │  Auth    │  │  Service │  │  Engine  │  │vity Mon. │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
                    HTTPS / WSS
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                  EXISTING BACKEND (Raspberry Pi)                │
│  FastAPI + SQLAlchemy + Redis + nftables                        │
│  22 REST endpoint grubu + WebSocket                             │
│  wall.tonbilx.com (remote) / 192.168.1.2 (local)               │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **UI Layer (Compose Screens)** | Kullanici arayuzu render, kullanici etkilesimi | ViewModel (state observe + event dispatch) |
| **ViewModel Layer** | Ekran state yonetimi, UI event isleme, UseCase/Repository cagrisi | Domain/Data layer, StateFlow ile UI'a state yayma |
| **Domain Layer** | Is mantigi (ince — cogu is mantigi backend'de), domain modeller, repository arayuzleri | Repository arayuzleri uzerinden Data layer |
| **Data Layer (Repository)** | Veri kaynaklari arasinda koordinasyon, cache stratejisi | API Service, Local Storage |
| **API Service** | HTTP istekleri (REST), WebSocket baglantisi | Backend (Ktor HttpClient + OkHttp WebSocket) |
| **Local Storage** | JWT token, kullanici tercihleri, son gorulen veriler | DataStore + Android Keystore |
| **NetworkManager** | Yerel/uzak ag secimi, base URL yonetimi | ConnectivityManager, API Service |
| **AuthInterceptor** | JWT token ekleme, 401 yakalama, token yenileme | TokenStorage, API Service |
| **BiometricAuth** | Parmak izi / yuz tanima ile oturum acma | BiometricPrompt API, TokenStorage |
| **FCM Service** | Push bildirim alma, token yonetimi | Firebase, Backend (token kayit) |
| **ConnectivityMonitor** | Ag durumu izleme, yerel/uzak gecis | Android ConnectivityManager |

## Recommended Project Structure

```
com.tonbil.aios/
├── app/                           # Application sinifi, Hilt entry point
│   └── TonbilApp.kt
│
├── di/                            # Dependency Injection modulleri
│   ├── NetworkModule.kt           # Ktor client, OkHttp, WebSocket
│   ├── RepositoryModule.kt        # Repository binding'leri
│   └── StorageModule.kt           # DataStore, Keystore
│
├── data/                          # Data Layer
│   ├── remote/                    # API servisleri
│   │   ├── api/                   # Endpoint tanimlari
│   │   │   ├── AuthApi.kt         # POST /auth/login, /auth/register
│   │   │   ├── DashboardApi.kt    # GET /dashboard/*
│   │   │   ├── DeviceApi.kt       # GET/POST/PUT /devices/*
│   │   │   ├── DnsApi.kt          # GET/POST /dns/*
│   │   │   ├── FirewallApi.kt     # GET/POST /firewall/*
│   │   │   ├── VpnApi.kt          # GET/POST /vpn/*
│   │   │   ├── TrafficApi.kt      # GET /traffic/*
│   │   │   ├── DdosApi.kt         # GET /ddos/*
│   │   │   ├── TelegramApi.kt     # GET/POST /telegram/*
│   │   │   ├── ChatApi.kt         # POST /chat/*
│   │   │   ├── WifiApi.kt         # GET/POST /wifi/*
│   │   │   ├── SecurityApi.kt     # GET/PUT /security/*
│   │   │   ├── ProfileApi.kt      # GET/POST /profiles/*
│   │   │   ├── ContentCategoryApi.kt
│   │   │   └── SystemApi.kt       # system-monitor, system-management
│   │   ├── dto/                   # Data Transfer Objects (API response/request)
│   │   │   ├── DashboardDto.kt
│   │   │   ├── DeviceDto.kt
│   │   │   └── ...
│   │   └── WebSocketClient.kt    # OkHttp WebSocket wrapper
│   │
│   ├── local/                     # Yerel depolama
│   │   ├── TokenStorage.kt        # JWT token (encrypted DataStore)
│   │   ├── PreferencesStorage.kt  # Kullanici tercihleri (base URL, tema)
│   │   └── CacheStorage.kt        # Son dashboard verisi (offline gorunum)
│   │
│   ├── repository/                # Repository uygulamalari
│   │   ├── AuthRepositoryImpl.kt
│   │   ├── DashboardRepositoryImpl.kt
│   │   ├── DeviceRepositoryImpl.kt
│   │   └── ...
│   │
│   └── network/                   # Ag altyapisi
│       ├── NetworkManager.kt      # Base URL secimi (local vs remote)
│       ├── AuthInterceptor.kt     # JWT header ekleme
│       ├── ConnectivityMonitor.kt # Ag durumu izleme
│       └── ApiResult.kt           # sealed class: Success/Error/Loading
│
├── domain/                        # Domain Layer (ince)
│   ├── model/                     # Domain modeller
│   │   ├── Device.kt
│   │   ├── DnsStats.kt
│   │   ├── FirewallRule.kt
│   │   └── ...
│   ├── repository/                # Repository arayuzleri
│   │   ├── AuthRepository.kt
│   │   ├── DashboardRepository.kt
│   │   └── ...
│   └── usecase/                   # Karmasik is mantigi (gerektiginde)
│       ├── BiometricLoginUseCase.kt
│       └── SwitchNetworkModeUseCase.kt
│
├── ui/                            # UI Layer (Jetpack Compose)
│   ├── theme/                     # Cyberpunk tema
│   │   ├── Color.kt              # Neon cyan, magenta, green, amber, red
│   │   ├── Type.kt               # Tipografi
│   │   ├── Shape.kt              # Glassmorphism kartlar
│   │   └── Theme.kt              # TonbilTheme composable
│   │
│   ├── navigation/                # Navigasyon
│   │   ├── NavGraph.kt           # Ana navigasyon grafigi
│   │   ├── Screen.kt             # @Serializable route tanimlari
│   │   └── BottomNavBar.kt       # Alt navigasyon cubugu
│   │
│   ├── common/                    # Paylasilan UI bilesenleri
│   │   ├── GlassCard.kt          # Glassmorphism kart (web ile tutarli)
│   │   ├── NeonBadge.kt
│   │   ├── StatCard.kt
│   │   ├── LoadingState.kt
│   │   └── ErrorState.kt
│   │
│   ├── screens/                   # Ekranlar (her biri ViewModel ile)
│   │   ├── login/
│   │   │   ├── LoginScreen.kt
│   │   │   └── LoginViewModel.kt
│   │   ├── dashboard/
│   │   │   ├── DashboardScreen.kt
│   │   │   └── DashboardViewModel.kt
│   │   ├── devices/
│   │   │   ├── DeviceListScreen.kt
│   │   │   ├── DeviceDetailScreen.kt
│   │   │   └── DevicesViewModel.kt
│   │   ├── dns/
│   │   ├── firewall/
│   │   ├── vpn/
│   │   ├── traffic/
│   │   ├── ddos/
│   │   ├── chat/
│   │   ├── telegram/
│   │   ├── wifi/
│   │   ├── security/
│   │   ├── profiles/
│   │   └── settings/             # Uygulama ayarlari (ag modu, tema)
│   │       ├── SettingsScreen.kt
│   │       └── SettingsViewModel.kt
│   │
│   └── widgets/                   # Dashboard widget'lari
│       ├── BandwidthGauge.kt
│       ├── ConnectionStatus.kt
│       ├── DnsSummaryCard.kt
│       └── ...
│
├── service/                       # Android servisleri
│   ├── FCMService.kt             # FirebaseMessagingService
│   └── BiometricHelper.kt        # BiometricPrompt wrapper
│
└── util/                          # Yardimci fonksiyonlar
    ├── DateFormatter.kt
    ├── ByteFormatter.kt           # Bandwidth formatlamasi
    └── Extensions.kt
```

### Structure Rationale

- **`data/remote/api/`**: Her backend endpoint grubu icin ayri Api sinifi. Backend'deki 22 route grubuna birebir eslesir — tutarlilik ve bulunabilirlik saglar.
- **`data/remote/dto/`**: API cevaplarinin Kotlin data class karsiliklari. Domain modellerinden ayri tutulur cunku backend sema degisiklikleri sadece bu katmani etkiler.
- **`domain/`**: Ince katman. Cogu is mantigi backend'de. Repository arayuzleri ve domain modeller burada. UseCase sadece karmasik senaryolar icin (biyometrik login akisi gibi).
- **`ui/screens/`**: Feature-based organizasyon. Her ekran kendi ViewModel'ini icerir. Web frontend'deki `pages/` + `hooks/` yapisinin Compose karsiligi.
- **`data/network/`**: Ag altyapisi. NetworkManager yerel/uzak gecisi yonetir. AuthInterceptor tum isteklere JWT ekler.

## Architectural Patterns

### Pattern 1: MVVM with UDF (Unidirectional Data Flow)

**What:** ViewModel StateFlow uzerinden UI state yayar, UI event'leri ViewModel'e gonderir. State tek yonlu akar.
**When to use:** Tum ekranlar icin standart pattern.
**Trade-offs:** Biraz boilerplate ama testability ve predictability cok yuksek.

```kotlin
// UiState sealed interface
sealed interface DashboardUiState {
    data object Loading : DashboardUiState
    data class Success(
        val bandwidth: BandwidthData,
        val deviceCount: Int,
        val dnsStats: DnsStats,
        val isLocalNetwork: Boolean
    ) : DashboardUiState
    data class Error(val message: String) : DashboardUiState
}

// ViewModel
@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val dashboardRepo: DashboardRepository,
    private val connectivityMonitor: ConnectivityMonitor
) : ViewModel() {

    private val _uiState = MutableStateFlow<DashboardUiState>(DashboardUiState.Loading)
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init { loadDashboard() }

    fun onRefresh() { loadDashboard() }

    private fun loadDashboard() {
        viewModelScope.launch {
            _uiState.value = DashboardUiState.Loading
            dashboardRepo.getSummary()
                .onSuccess { data -> _uiState.value = DashboardUiState.Success(...) }
                .onFailure { e -> _uiState.value = DashboardUiState.Error(e.message) }
        }
    }
}

// Screen (Compose)
@Composable
fun DashboardScreen(viewModel: DashboardViewModel = hiltViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    when (val state = uiState) {
        is DashboardUiState.Loading -> LoadingState()
        is DashboardUiState.Success -> DashboardContent(state)
        is DashboardUiState.Error -> ErrorState(state.message, onRetry = viewModel::onRefresh)
    }
}
```

### Pattern 2: Dual-Mode Network Manager

**What:** Yerel ag (192.168.1.2) ve uzak erisim (wall.tonbilx.com) arasinda otomatik gecis.
**When to use:** Her API cagrisi oncesinde base URL belirleme.
**Trade-offs:** Otomatik gecis kullanici deneyimini iyilestirir ama ag degisikliklerinde kisa sureli hatalar olabilir.

```kotlin
class NetworkManager @Inject constructor(
    private val connectivityMonitor: ConnectivityMonitor,
    private val preferencesStorage: PreferencesStorage
) {
    sealed interface NetworkMode {
        data object Local : NetworkMode    // 192.168.1.2
        data object Remote : NetworkMode   // wall.tonbilx.com
        data object Auto : NetworkMode     // Otomatik secim
    }

    private val _currentMode = MutableStateFlow<NetworkMode>(NetworkMode.Auto)

    fun getBaseUrl(): String {
        return when (_currentMode.value) {
            NetworkMode.Local -> "http://192.168.1.2:8000"
            NetworkMode.Remote -> "https://wall.tonbilx.com"
            NetworkMode.Auto -> {
                if (connectivityMonitor.isOnLocalNetwork()) {
                    "http://192.168.1.2:8000"
                } else {
                    "https://wall.tonbilx.com"
                }
            }
        }
    }

    // Yerel ag tespiti: WiFi bagli + 192.168.1.x subnet kontrolu
    // ConnectivityManager + LinkProperties ile
}
```

### Pattern 3: ApiResult Wrapper

**What:** Tum API cevaplarini Success/Error/NetworkError sealed class ile sarmalar. HTTP hata kodlarini ve ag hatalarini tutarli sekilde isler.
**When to use:** Tum Repository uygulamalarinda.
**Trade-offs:** Her API cagrisi try-catch gerektirmez, hata isleme merkezilesti.

```kotlin
sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(val code: Int, val message: String) : ApiResult<Nothing>()
    data class NetworkError(val exception: Throwable) : ApiResult<Nothing>()
}

suspend fun <T> safeApiCall(call: suspend () -> T): ApiResult<T> {
    return try {
        ApiResult.Success(call())
    } catch (e: ClientRequestException) {
        ApiResult.Error(e.response.status.value, e.message)
    } catch (e: IOException) {
        ApiResult.NetworkError(e)
    }
}
```

### Pattern 4: WebSocket ile Canli Veri Akisi

**What:** OkHttp WebSocket client ile backend'den canli dashboard verisi alma. Kotlin Flow olarak sarmalanir.
**When to use:** Dashboard canli guncelleme, trafik izleme.
**Trade-offs:** Pil tuketimi artabilir — arka planda WebSocket kapatilmali.

```kotlin
class WebSocketClient @Inject constructor(
    private val okHttpClient: OkHttpClient,
    private val networkManager: NetworkManager,
    private val tokenStorage: TokenStorage
) {
    fun connect(): Flow<WebSocketMessage> = callbackFlow {
        val token = tokenStorage.getToken()
        val baseUrl = networkManager.getBaseUrl()
            .replace("http", "ws")  // ws:// veya wss://
        val url = "$baseUrl/ws?token=$token"

        val request = Request.Builder().url(url).build()
        val ws = okHttpClient.newWebSocket(request, object : WebSocketListener() {
            override fun onMessage(webSocket: WebSocket, text: String) {
                trySend(parseMessage(text))
            }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                close(t)
            }
        })

        awaitClose { ws.close(1000, "Screen closed") }
    }.flowOn(Dispatchers.IO)
}
```

### Pattern 5: Type-Safe Navigation (Jetpack Navigation 2.8+)

**What:** @Serializable data class'lar ile rota tanimlama. Compile-time tip guvenligi.
**When to use:** Tum ekranlar arasi gecisler.
**Trade-offs:** Kotlin Serialization plugin gerektirir ama string-based route'lardan cok daha guvenli.

```kotlin
// Route tanimlari
@Serializable data object DashboardRoute
@Serializable data object DeviceListRoute
@Serializable data class DeviceDetailRoute(val deviceId: String)
@Serializable data object DnsRoute
@Serializable data object FirewallRoute

// NavGraph
NavHost(navController, startDestination = DashboardRoute) {
    composable<DashboardRoute> { DashboardScreen() }
    composable<DeviceListRoute> { DeviceListScreen(onDeviceClick = { id ->
        navController.navigate(DeviceDetailRoute(id))
    })}
    composable<DeviceDetailRoute> { backStackEntry ->
        val route = backStackEntry.toRoute<DeviceDetailRoute>()
        DeviceDetailScreen(deviceId = route.deviceId)
    }
}
```

## Data Flow

### Authentication Flow

```
[Uygulama acilis]
    |
[TokenStorage] --> Token var mi?
    |-- EVET --> Token gecerli mi? (exp kontrolu)
    |     |-- EVET --> [BiometricPrompt] --> Onay --> Ana ekran
    |     +-- HAYIR --> Login ekrani
    +-- HAYIR --> Login ekrani

[Login ekrani]
    |
Kullanici adi + sifre giris
    |
POST /api/v1/auth/login
    |
JWT token alindi
    |
[TokenStorage] --> Encrypted DataStore'a kaydet
    |
[BiometricHelper] --> "Biyometrik kaydet?" --> Evet --> Keystore'a kriptografik bag
    |
Ana ekran
```

### Dashboard Real-time Data Flow

```
[DashboardScreen]
    | observe
[DashboardViewModel]
    |-- StateFlow<DashboardUiState>  <-- REST: GET /dashboard/summary (ilk yuklenme)
    +-- SharedFlow<LiveUpdate>       <-- WebSocket /ws (canli guncelleme)
        |
[DashboardRepository]
    |-- dashboardApi.getSummary()    --> HTTP GET --> Backend
    +-- webSocketClient.connect()    --> WSS --> Backend
        |
[Backend Response]
    | parse (DTO --> Domain Model)
[ViewModel] --> _uiState.value = Success(...)
    | collectAsStateWithLifecycle()
[DashboardScreen] --> recompose
```

### Network Mode Selection Flow

```
[Uygulama baslarken]
    |
[ConnectivityMonitor] --> Ag durumu dinle
    |
WiFi bagli mi? --> EVET --> WiFi IP 192.168.1.x mi?
    |-- EVET --> NetworkMode.Local (http://192.168.1.2:8000)
    |          Daha dusuk latency, sifresiz HTTP (yerel ag)
    +-- HAYIR --> NetworkMode.Remote (https://wall.tonbilx.com)
               HTTPS zorunlu, internet uzerinden

[Ag degistiginde] --> ConnectivityMonitor callback
    |
[NetworkManager] --> Base URL guncelle
    |
[Aktif API cagrilari] --> Yeni base URL ile devam
[Aktif WebSocket] --> Yeniden baglan
```

### Push Notification Flow

```
[Backend olay meydana geldi] (DDoS saldirisi, yeni cihaz, vb.)
    |
Backend --> Firebase Admin SDK --> FCM sunucusu
    |
FCM --> Android cihaz
    |
[FCMService.onMessageReceived()]
    |
|-- Uygulama on planda --> Bildirim gosterme, UI guncelle
+-- Uygulama arka planda --> Android Notification Channel ile bildirim goster
    | kullanici tikladi
    Deep link ile ilgili ekrana git
```

### Key Data Flows Summary

1. **REST API (tek seferlik veri):** Screen acilir --> ViewModel init --> Repository.fetch() --> ApiService.get() --> HTTP GET --> JSON parse --> Domain Model --> StateFlow --> UI recompose
2. **WebSocket (canli veri):** ViewModel init --> WebSocketClient.connect() --> Flow<Message> --> ViewModel collect --> StateFlow update --> UI recompose
3. **Biyometrik auth:** Uygulama acilis --> Token var --> BiometricPrompt goster --> CryptoObject ile token decrypt --> API isteklerine JWT ekleme basla
4. **FCM push:** Backend olay --> FCM gonder --> FCMService aldi --> NotificationManager ile goster veya UI guncelle

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **TonbilAiOS Backend (REST)** | Ktor HttpClient, JSON serialization (kotlinx.serialization) | 22 endpoint grubu, JWT auth header |
| **TonbilAiOS Backend (WS)** | OkHttp WebSocket | Token query param ile auth, auto-reconnect gerekli |
| **Firebase Cloud Messaging** | firebase-messaging SDK, FirebaseMessagingService | Backend'e FCM token gondermek icin yeni endpoint gerekli |
| **Android Biometric** | androidx.biometric:biometric, BiometricPrompt | BIOMETRIC_STRONG + DEVICE_CREDENTIAL fallback |
| **Android Keystore** | java.security.KeyStore | JWT token sifreleme anahtari burada saklanir |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| UI <-> ViewModel | StateFlow (down), method calls / events (up) | Lifecycle-aware collection (collectAsStateWithLifecycle) |
| ViewModel <-> Repository | suspend fun calls, Flow returns | Coroutine scope ViewModel'de, IO dispatcher Repository'de |
| Repository <-> API | suspend fun HTTP calls | ApiResult wrapper, AuthInterceptor otomatik JWT ekler |
| Repository <-> LocalStorage | suspend fun DataStore read/write | Sifrelenmis token, kullanici tercihleri |
| App <-> FCM | FirebaseMessagingService callback | Token degisince backend'e bildir |

### Backend Integration: Required New Endpoints

Mevcut 22 endpoint grubuna ek olarak backend'de asagidaki endpoint'ler eklenmeli:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/auth/fcm-token` | POST | Mobil cihaz FCM token kaydi |
| `/api/v1/auth/fcm-token` | DELETE | FCM token silme (cikis yapinca) |
| `/api/v1/notifications/subscribe` | POST | Bildirim kategorileri secimi (DDoS, yeni cihaz, vb.) |
| `/api/v1/notifications/subscribe` | GET | Mevcut abonelik durumu |

## Anti-Patterns

### Anti-Pattern 1: Fat ViewModel

**What people do:** Tum is mantigi, ag cagrisi, veri donusumu ViewModel'de yapmak.
**Why it's wrong:** Test edilemez, okunmaz, 500+ satir ViewModel'ler olusur.
**Do this instead:** Repository pattern kullan. ViewModel sadece UI state yonetir, veri operasyonlari Repository'de.

### Anti-Pattern 2: Composable Icinde Dogrudan API Cagrisi

**What people do:** LaunchedEffect icinde dogrudan API cagrisi yapmak.
**Why it's wrong:** Recomposition'da tekrar calisir, lifecycle sorunlari, bellek sizintisi.
**Do this instead:** ViewModel.init{} veya event-driven API cagrilari. Composable sadece state gosterir.

### Anti-Pattern 3: Her Ekran Icin Ayri Network Instance

**What people do:** Her ViewModel'de yeni HttpClient olusturmak.
**Why it's wrong:** Bellek israfi, connection pool paylasimi yok, auth interceptor tekrari.
**Do this instead:** Hilt ile singleton HttpClient, tum Repository'ler ayni instance'i kullanir.

### Anti-Pattern 4: WebSocket'i Arka Planda Acik Birakma

**What people do:** App arka plana gecince WebSocket'i kapatmamak.
**Why it's wrong:** Pil tuketimi, gereksiz ag trafigi, backend'de zombie connection.
**Do this instead:** Lifecycle-aware WebSocket yonetimi. ON_STOP'da kapat, ON_START'da yeniden baglan. Dashboard ekranindayken acik, baska ekranda kapatilabilir.

### Anti-Pattern 5: Plaintext Token Storage

**What people do:** JWT token'i SharedPreferences'a sifresiz kaydetmek.
**Why it's wrong:** Root cihazlarda veya backup extraction ile token calinabilir.
**Do this instead:** DataStore + Android Keystore tabanli AES-GCM sifreleme kullan.

## Build Order (Dependency Chain)

Asagidaki siralama, bilesenlerin birbirine bagimliligina gore olusturulmustur:

```
Phase 1: TEMEL ALTYAPI (hicbir seye bagimli degil)
|-- Proje kurulumu (Gradle, Hilt, tema)
|-- NetworkManager + AuthInterceptor + ApiResult
|-- TokenStorage (encrypted DataStore + Keystore)
+-- Login ekrani + AuthRepository
    --> Sonuc: Uygulamaya giris yapilabiliyor, API'ye baglanti var

Phase 2: CEKIRDEK UI (Phase 1'e bagimli)
|-- Navigasyon grafigi + BottomNavBar
|-- GlassCard + ortak UI bilesenleri (NeonBadge, StatCard)
|-- Dashboard ekrani + DashboardRepository
+-- WebSocket client (canli veri)
    --> Sonuc: Dashboard calisiyor, canli veri akiyor

Phase 3: OZELLIK EKRANLARI (Phase 2'ye bagimli)
|-- Cihaz listesi + detay
|-- DNS filtreleme + kategoriler + profiller
|-- Guvenlik duvari
|-- VPN yonetimi
|-- Trafik izleme
+-- Diger ekranlar (DDoS, WiFi, Telegram, Chat, Security)
    --> Sonuc: Tum web ozelliklerin mobil karsiligi hazir

Phase 4: PLATFORM ENTEGRASYONU (Phase 1'e bagimli, Phase 3 ile paralel olabilir)
|-- Biyometrik auth (BiometricPrompt + Keystore)
|-- FCM push notification + backend endpoint'leri
|-- ConnectivityMonitor (yerel/uzak otomatik gecis)
+-- Deep linking (bildirimden ekrana)
    --> Sonuc: Mobil-ozel ozellikler hazir

Phase 5: CILALAMA + DAGITIM
|-- Offline/hata durumlari iyilestirme
|-- Pull-to-refresh tum ekranlarda
|-- Neon glow animasyonlari
+-- APK build + imzalama + dagitim
    --> Sonuc: Uretim kalitesinde uygulama
```

**Build order rationale:**
- Phase 1 olmadan hicbir sey calismaz — ag, auth ve token altyapisi her seyin temeli.
- Phase 2 (navigasyon + dashboard) uygulamanin iskeleti — diger ekranlar buna eklenir.
- Phase 3 ekranlari birbirinden bagimsiz, paralel gelistirilebilir.
- Phase 4 platform servisleri Phase 1 uzerine kurulur ama Phase 3 ile paralel ilerleyebilir.
- Phase 5 en sona kalir cunku tum fonksiyonellik hazir olmali.

## Scaling Considerations

| Concern | Bu Proje (tek kullanici) | Gelecek (coklu cihaz) |
|---------|--------------------------|----------------------|
| API istekleri | Tek cihaz, minimal yuk | Rate limiting zaten backend'de var |
| WebSocket | Tek baglanti | Backend MAX_WS_CONNECTIONS=100, sorun yok |
| Push notification | Tek FCM token | Coklu token destegi backend'e eklenmeli |
| Ag gecisi | Manuel/otomatik | Sorunsuz, ConnectivityManager callback |

Bu proje esasen tek kullanici (ev aglari icin router yonetimi). Olceklendirme kritik degil. Performans odagi: dusuk latency, dusuk pil tuketimi, hizli UI yaniti.

## Sources

- [Android Biometric Auth - Official Docs](https://developer.android.com/identity/sign-in/biometric-auth) - HIGH confidence
- [Jetpack Compose Architecture - Official](https://developer.android.com/develop/ui/compose/architecture) - HIGH confidence
- [Type-safe Navigation in Compose](https://developer.android.com/guide/navigation/design/type-safety) - HIGH confidence
- [Firebase Cloud Messaging Setup](https://firebase.google.com/docs/cloud-messaging/android/get-started) - HIGH confidence
- [Ktor vs Retrofit Comparison](https://proandroiddev.com/when-to-use-retrofit-and-when-to-use-ktor-a-guide-for-android-developers-918491dcf69a) - MEDIUM confidence
- [Hilt vs Koin - Compile-time vs Runtime DI](https://www.droidcon.com/2025/11/26/hilt-vs-koin-the-hidden-cost-of-runtime-injection-and-why-compile-time-di-wins/) - MEDIUM confidence
- [Secure JWT Storage with DataStore + Keystore](https://medium.com/@mohammad.hasan.mahdavi81/securely-storing-jwt-tokens-in-android-with-datastore-and-manual-encryption-741b104a93d3) - MEDIUM confidence
- [EncryptedSharedPreferences Deprecation Status](https://medium.com/@n20/encryptedsharedpreferences-is-deprecated-what-should-android-developers-use-now-7476140e8347) - MEDIUM confidence
- Backend kaynak kodu analizi: `backend/app/api/v1/router.py`, `auth.py`, `ws.py` - HIGH confidence (dogrudan okuma)

---
*Architecture research for: TonbilAiOS Android App*
*Researched: 2026-03-06*
