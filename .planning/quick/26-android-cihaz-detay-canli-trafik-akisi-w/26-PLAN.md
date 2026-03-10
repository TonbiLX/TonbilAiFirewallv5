---
phase: quick-26
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - android/app/src/main/java/com/tonbil/aifirewall/data/repository/DeviceRepository.kt
  - android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DeviceDetailViewModel.kt
  - android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DeviceDetailScreen.kt
  - android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt
autonomous: true
requirements: [QUICK-26]
must_haves:
  truths:
    - "Cihaz detay ekraninin Trafik tab'inda canli akislar listesi goruntulenebilir"
    - "Akislar 5 saniyede bir otomatik yenilenir"
    - "Yon (gelen/giden), hedef domain, protokol, uygulama, durum, boyut, hiz sutunlari gosterilir"
    - "Siralama chip'leri (Hiz, Boyut, Protokol, Isim) calisiyor"
  artifacts:
    - path: "android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DeviceDetailScreen.kt"
      provides: "TrafficTab icinde LiveFlowsSection composable"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DeviceDetailViewModel.kt"
      provides: "loadDeviceLiveFlows() fonksiyonu + liveFlows state"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/data/repository/DeviceRepository.kt"
      provides: "getDeviceLiveFlows(deviceId) fonksiyonu"
  key_links:
    - from: "DeviceDetailScreen.kt TrafficTab"
      to: "DeviceDetailViewModel.liveFlows"
      via: "uiState.liveFlows collectAsStateWithLifecycle"
    - from: "DeviceDetailViewModel.loadDeviceLiveFlows"
      to: "SecurityRepository.getLiveFlows (device_id filtre)"
      via: "Repository call with device_id query param"
---

<objective>
Android cihaz detay ekraninin "Trafik" tab'ina web paneldeki gibi canli trafik akisi (live flows) listesi ekle.

Purpose: Suan Trafik tab'i sadece trafik ozeti (toplam akis, gelen/giden byte) ve en cok erisilen domain/port listesi gosteriyor. Kullanici, bir cihazin gercek zamanli olarak hangi baglantilari actigini (hedef domain, hiz, boyut, uygulama) gormek istiyor.
Output: Guncellenmis DeviceDetailScreen.kt, DeviceDetailViewModel.kt, DeviceRepository.kt
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DeviceDetailScreen.kt
@android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DeviceDetailViewModel.kt
@android/app/src/main/java/com/tonbil/aifirewall/data/repository/DeviceRepository.kt
@android/app/src/main/java/com/tonbil/aifirewall/data/repository/SecurityRepository.kt
@android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiRoutes.kt
@android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/SecurityDtos.kt
@android/app/src/main/java/com/tonbil/aifirewall/feature/traffic/TrafficScreen.kt

<interfaces>
<!-- Key types and contracts the executor needs. -->

From SecurityDtos.kt — LiveFlowDto (MEVCUT, yeniden olusturma):
```kotlin
@Serializable
data class LiveFlowDto(
    @SerialName("flow_id") val flowId: String = "",
    val protocol: String = "",
    @SerialName("src_ip") val srcIp: String = "",
    @SerialName("src_port") val srcPort: Int? = null,
    @SerialName("dst_ip") val dstIp: String = "",
    @SerialName("dst_port") val dstPort: Int? = null,
    @SerialName("dst_domain") val dstDomain: String? = null,
    @SerialName("bytes_sent") val bytesIn: Long = 0,
    @SerialName("bytes_received") val bytesOut: Long = 0,
    @SerialName("bytes_total") val bytesTotal: Long = 0,
    @SerialName("bps_in") val bpsIn: Double = 0.0,
    @SerialName("bps_out") val bpsOut: Double = 0.0,
    val state: String? = null,
    @SerialName("service_name") val serviceName: String? = null,
    @SerialName("app_name") val appName: String? = null,
    val direction: String? = null,
    @SerialName("device_id") val deviceId: Int? = null,
    @SerialName("device_hostname") val hostname: String? = null,
    @SerialName("device_ip") val deviceIp: String? = null,
)
```

From ApiRoutes.kt — MEVCUT route:
```kotlin
const val TRAFFIC_FLOWS_LIVE = "traffic/flows/live"
```

Backend API: GET /api/v1/traffic/flows/live?device_id={id} — zaten device_id query param destekliyor.

From SecurityRepository.kt — MEVCUT fonksiyon (device_id parametresi eksik):
```kotlin
suspend fun getLiveFlows(): Result<List<LiveFlowDto>> = runCatching {
    client.get(ApiRoutes.TRAFFIC_FLOWS_LIVE).body()
}
```

From DeviceDetailViewModel.kt — mevcut UiState:
```kotlin
data class DeviceDetailUiState(
    val device: DeviceResponseDto? = null,
    val profiles: List<ProfileResponseDto> = emptyList(),
    val connectionHistory: List<ConnectionHistoryDto> = emptyList(),
    val dnsLogs: List<DnsQueryLogDto> = emptyList(),
    val trafficSummary: DeviceTrafficSummaryDto? = null,
    val bandwidth: WsDeviceBandwidthDto? = null,
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val selectedTab: Int = 0,
)
```

From DeviceDetailScreen.kt — mevcut TrafficTab sadece ozet + top domains + top ports gosteriyor.

From TrafficScreen.kt — LiveFlowCard composable referans pattern (direction icon, state color, app badge, src->dst, bytes+speed).

AppModule.kt Koin kaydi:
```kotlin
viewModel { params -> DeviceDetailViewModel(params.get(), get<DeviceRepository>(), get<ProfileRepository>(), get<WebSocketManager>()) }
```
DeviceDetailViewModel'e SecurityRepository eklenmeli VEYA DeviceRepository'ye getDeviceLiveFlows metodu eklenmeli. DeviceRepository'ye eklemek daha temiz (device-scoped veri).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Repository + ViewModel — canli akis veri katmani</name>
  <files>
    android/app/src/main/java/com/tonbil/aifirewall/data/repository/DeviceRepository.kt
    android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DeviceDetailViewModel.kt
  </files>
  <action>
1. **DeviceRepository.kt** — `getDeviceLiveFlows` fonksiyonu ekle:
```kotlin
suspend fun getDeviceLiveFlows(deviceId: Int): Result<List<LiveFlowDto>> = runCatching {
    client.get(ApiRoutes.TRAFFIC_FLOWS_LIVE) {
        url {
            parameters.append("device_id", deviceId.toString())
            parameters.append("sort_by", "bytes_total")
            parameters.append("sort_order", "desc")
            parameters.append("limit", "200")
        }
    }.body()
}
```
NOT: LiveFlowDto importu `com.tonbil.aifirewall.data.remote.dto.LiveFlowDto` olarak ekle.

2. **DeviceDetailViewModel.kt** — UiState'e `liveFlows` alani ekle:
```kotlin
data class DeviceDetailUiState(
    // ... mevcut alanlar aynen kalsin ...
    val liveFlows: List<LiveFlowDto> = emptyList(),
    val isLiveFlowsLoading: Boolean = false,
)
```

3. **DeviceDetailViewModel.kt** — `loadDeviceLiveFlows()` fonksiyonu ekle:
```kotlin
fun loadDeviceLiveFlows() {
    viewModelScope.launch {
        _uiState.update { it.copy(isLiveFlowsLoading = true) }
        deviceRepository.getDeviceLiveFlows(deviceId)
            .onSuccess { flows ->
                _uiState.update { it.copy(liveFlows = flows, isLiveFlowsLoading = false) }
            }
            .onFailure {
                _uiState.update { it.copy(isLiveFlowsLoading = false) }
            }
    }
}
```

4. **DeviceDetailViewModel.kt** — init blogundan sonra, `loadAll()` icine `getDeviceLiveFlows` da paralel cagir:
`loadAll()` fonksiyonunun `coroutineScope` blogu icinde mevcut async cagrilarin yanina ekle:
```kotlin
val liveFlowsDeferred = async { deviceRepository.getDeviceLiveFlows(deviceId) }
```
ve state update'te:
```kotlin
liveFlows = liveFlowsDeferred.await().getOrElse { emptyList() },
```

5. **DeviceDetailViewModel.kt** — Trafik tab'i secildiginde (selectedTab == 1) 5 saniyede bir auto-refresh:
Bu islem TrafficTab composable tarafinda `LaunchedEffect` ile yapilacak (Task 2'de), ViewModel sadece `loadDeviceLiveFlows()` public fonksiyonu sunsun.
  </action>
  <verify>
    <automated>cd android && ./gradlew compileDebugKotlin 2>&1 | tail -5</automated>
  </verify>
  <done>DeviceRepository.getDeviceLiveFlows(deviceId) cihaz bazli canli akislari donduruyor. DeviceDetailUiState.liveFlows alani mevcut ve loadAll() ile paralel dolduruluyor. loadDeviceLiveFlows() public olarak erisilebilir.</done>
</task>

<task type="auto">
  <name>Task 2: TrafficTab UI — canli akis kartlari + siralama + auto-refresh</name>
  <files>
    android/app/src/main/java/com/tonbil/aifirewall/feature/devices/DeviceDetailScreen.kt
  </files>
  <action>
1. **DeviceDetailScreen.kt** — TrafficTab composable'ini guncelle. Mevcut ozet karti + top domains + top ports'un USTUNE "Canli Trafik Akislari" bolumu ekle. TrafficTab'a `viewModel` parametresi ekle (suan sadece uiState ve colors aliyor).

2. **TrafficTab imzasi degisecek:**
```kotlin
@Composable
private fun TrafficTab(
    uiState: DeviceDetailUiState,
    viewModel: DeviceDetailViewModel,
    colors: CyberpunkColors,
)
```
DeviceDetailScreen'deki cagriyi da guncelle: `1 -> TrafficTab(uiState, viewModel, colors)`

3. **Auto-refresh LaunchedEffect** (TrafficTab icinde, en uste):
```kotlin
LaunchedEffect(Unit) {
    while (true) {
        delay(5000L)
        viewModel.loadDeviceLiveFlows()
    }
}
```

4. **SortChipRow** — TrafficScreen.kt'deki mevcut SortChipRow composable'ini DeviceDetailScreen icine kopyala (private). Siralama secenek listesi: "speed" to "Hiz", "bytes" to "Boyut", "protocol" to "Protokol", "name" to "Hedef".

5. **Canli Trafik Akislari bolumu** (LazyColumn icinde, trafik ozetinden SONRA, top domains'den ONCE):
```kotlin
item {
    Text(
        text = "Canli Trafik Akislari",
        style = MaterialTheme.typography.titleMedium,
        color = colors.neonCyan,
        modifier = Modifier.padding(bottom = 4.dp),
    )
}
```

Ardindan siralama chip satirini goster ve akis kartlarini listele. `remember` ile sortKey state'i tut.

6. **DeviceLiveFlowCard composable** — TrafficScreen.kt'deki LiveFlowCard'dan uyarlanmis, daha kompakt:
- Ust satir: Yon ikonu (ArrowUpward=cyan outbound, ArrowDownward=magenta inbound) + protokol + uygulama badge (appName ?? serviceName) + durum badge (state ile renk: ESTABLISHED=NeonGreen, SYN_SENT=NeonAmber, TIME_WAIT=TextSecondary, CLOSE_WAIT=NeonRed)
- Orta satir: `dstDomain ?: dstIp` + `:dstPort` (monospace, tek satir, overflow ellipsis)
- Alt satir sol: `In: formatBytes(bytesIn)  Out: formatBytes(bytesOut)`
- Alt satir sag: Hiz gostergesi `formatSpeed(max(bpsIn, bpsOut))` (directionColor ile)
- GlassBg + GlassBorder RoundedCornerShape(8.dp), padding 10.dp
- Buyuk transfer vurgulama: bytesIn+bytesOut > 10MB ise NeonMagenta border glow (TrafficScreen LargeTransferCard pattern)

7. **Bos durum:** Canli akis yoksa "Bu cihazin aktif baglantisi yok" mesaji goster (TextSecondary, center).

8. **Renk ve format fonksiyonlari** — DeviceDetailScreen.kt'de formatBytes ve formatBps zaten mevcut. `formatSpeed` fonksiyonunu TrafficScreen.kt'den kopyala (private). `stateColor` fonksiyonunu da ekle:
```kotlin
private fun stateColor(state: String): Color = when (state.uppercase()) {
    "ESTABLISHED" -> NeonGreen
    "TIME_WAIT" -> TextSecondary
    "SYN_SENT" -> NeonAmber
    "CLOSE_WAIT" -> NeonRed
    else -> TextSecondary
}
```

Gerekli import'lar: `NeonCyan, NeonMagenta, NeonGreen, NeonAmber, NeonRed, TextSecondary, GlassBg, GlassBorder, DarkSurface` theme'den, `Icons.Outlined.ArrowUpward/ArrowDownward`, `RoundedCornerShape`, `border`, `horizontalScroll`, `rememberScrollState`, `clickable`, `delay` (kotlinx.coroutines).
  </action>
  <verify>
    <automated>cd android && ./gradlew compileDebugKotlin 2>&1 | tail -5</automated>
  </verify>
  <done>
Cihaz detay ekraninin Trafik tab'inda canli akis kartlari gosteriliyor. Yon (gelen/giden) ikonu, hedef domain, protokol, uygulama badge, durum renklendirmesi, byte boyutu, hiz gostergesi mevcut. Siralama chip'leri (Hiz, Boyut, Protokol, Hedef) calisiyor. 5 saniyede bir otomatik yenileme yapiliyor. Buyuk transferler (>10MB) neon-magenta vurgulanmis. Bos durumda bilgilendirme mesaji gosteriliyor.
  </done>
</task>

</tasks>

<verification>
1. `cd android && ./gradlew compileDebugKotlin` — derleme hatasi yok
2. Android Studio'dan build ve cihaza yukle
3. Herhangi bir cihaz detay ekranina git -> Trafik tab'ina tikla
4. Canli akis kartlarinin gorundugunu dogrula (en az 1 aktif baglantisi olan cihaz icin)
5. 5 saniye bekle, kartlarin guncellendagini dogrula
6. Siralama chip'lerine tikla — listenin sirasinin degistigini dogrula
</verification>

<success_criteria>
- Derleme hatasi yok
- Cihaz detay Trafik tab'inda canli akislar goruntulenebiliyor
- Her akis karti: yon ikonu, hedef, protokol, uygulama, durum, boyut, hiz iceriyor
- Siralama chip'leri calisiyor (Hiz, Boyut, Protokol, Hedef)
- 5 saniyede bir auto-refresh calisiyor
- Buyuk transferler (>10MB) vurgulanmis
- Bos durumda uygun mesaj gosteriliyor
</success_criteria>

<output>
After completion, create `.planning/quick/26-android-cihaz-detay-canli-trafik-akisi-w/26-SUMMARY.md`
</output>
