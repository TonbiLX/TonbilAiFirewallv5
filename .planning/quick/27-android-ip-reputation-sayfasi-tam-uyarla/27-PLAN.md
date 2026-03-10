---
phase: quick-27
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/IpReputationDtos.kt
  - android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiRoutes.kt
  - android/app/src/main/java/com/tonbil/aifirewall/data/repository/IpReputationRepository.kt
  - android/app/src/main/java/com/tonbil/aifirewall/feature/ipreputation/IpReputationViewModel.kt
  - android/app/src/main/java/com/tonbil/aifirewall/feature/ipreputation/IpReputationScreen.kt
autonomous: true
requirements: [QUICK-27]
must_haves:
  truths:
    - "API key Ayarlar tab'inda gorunur (maskeli) ve guncellenebilir"
    - "Ozet tab'i toplam kontrol, kritik, supheli, gunluk kota gosterir"
    - "IP'ler tab'i sorgulanan IP listesini skor/ulke/tarih ile gosterir"
    - "Kara liste tab'i AbuseIPDB blacklist IP'lerini listeler"
    - "Ulke engelleme Ayarlar tab'inda mevcut — ulke ekle/cikar islemi calisiyor"
    - "Web panelden ve Android'den API key girildiginde ayni key kullanilir (cakisma yok)"
  artifacts:
    - path: "android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/IpReputationDtos.kt"
      provides: "Backend API response format'iyla birebir eslesen DTO'lar"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/data/repository/IpReputationRepository.kt"
      provides: "Tum IP reputation endpoint'lerini cagiran repository (api-usage dahil)"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/feature/ipreputation/IpReputationViewModel.kt"
      provides: "Ulke engelleme state + API usage + config yonetimi"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/feature/ipreputation/IpReputationScreen.kt"
      provides: "4-tab ekran: Ozet, IP'ler, Kara Liste, Ayarlar (ulke engelleme dahil)"
  key_links:
    - from: "IpReputationDtos.kt"
      to: "Backend /ip-reputation/* endpoints"
      via: "SerialName annotations eslesmesi"
      pattern: "SerialName.*abuseipdb_key|blocked_countries|flagged_critical"
    - from: "IpReputationRepository.kt"
      to: "ApiRoutes.kt"
      via: "client.get(ApiRoutes.IP_REP_*)"
      pattern: "IP_REP_API_USAGE|IP_REP_BLACKLIST_API_USAGE"
    - from: "IpReputationScreen.kt SettingsTab"
      to: "IpReputationViewModel updateConfig"
      via: "blocked_countries listesi + abuseipdb_key"
      pattern: "blocked_countries|abuseipdb_key"
---

<objective>
Android IP Reputation sayfasini backend API'ye tam uyumlu hale getir.

Purpose: Mevcut Android IP Reputation ekrani tamamen yanlis DTO'lar kullanarak backend'e baglanmaya calisiyor.
Backend gercek response field'lari (abuseipdb_key, abuseipdb_key_set, blocked_countries, flagged_critical, flagged_warning, daily_checks_used vb.)
ile Android DTO field'lari (api_key, total_clean, total_suspicious, total_blocked vb.) BIREBIR ESLESMEZ.
Ayrica API usage endpoint'leri, ulke engelleme, ve response wrapper parse eksik.

Output: Calisan 4-tab IP Reputation ekrani (Ozet, IP'ler, Kara Liste, Ayarlar + ulke engelleme)
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@backend/app/api/v1/ip_reputation.py (Backend endpoint'ler — gercek response format'i)
@frontend/src/components/firewall/IpReputationTab.tsx (Web panel referans — tum ozellikler burada)
@frontend/src/services/ipReputationApi.ts (Web panel API calls)

<interfaces>
<!-- Backend /ip-reputation/ endpoint gercek response format'lari -->

GET /ip-reputation/config response:
```json
{
  "enabled": true,
  "abuseipdb_key": "abcd****efgh",
  "abuseipdb_key_set": true,
  "blocked_countries": ["CN", "RU", "KP"],
  "check_interval": 300,
  "max_checks_per_cycle": 10,
  "daily_limit": 900
}
```

PUT /ip-reputation/config request body:
```json
{
  "enabled": true,
  "abuseipdb_key": "full-api-key-string",
  "blocked_countries": ["CN", "RU"]
}
```

GET /ip-reputation/summary response:
```json
{
  "total_checked": 150,
  "flagged_critical": 12,
  "flagged_warning": 25,
  "daily_checks_used": 45,
  "daily_limit": 1000,
  "abuseipdb_remaining": 955,
  "abuseipdb_limit": 1000
}
```

GET /ip-reputation/ips?min_score=0 response:
```json
{
  "ips": [
    {
      "ip": "1.2.3.4",
      "abuse_score": 95,
      "total_reports": 42,
      "country": "China",
      "city": "Beijing",
      "isp": "ChinaNet",
      "org": "ChinaNet",
      "checked_at": "2026-03-09 14:23:00"
    }
  ],
  "total": 1
}
```

GET /ip-reputation/blacklist response:
```json
{
  "ips": [
    {
      "ip": "5.6.7.8",
      "abuse_score": 100,
      "country": "RU",
      "last_reported_at": "2026-03-09T10:00:00"
    }
  ],
  "total": 500,
  "last_fetch": "2026-03-09T08:00:00",
  "total_count": 500
}
```

GET /ip-reputation/blacklist/config response:
```json
{
  "auto_block": true,
  "min_score": 100,
  "limit": 10000,
  "daily_fetches": 1,
  "daily_limit": 5,
  "last_fetch": "2026-03-09T08:00:00",
  "total_count": 500
}
```

GET /ip-reputation/api-usage response:
```json
{
  "status": "ok",
  "message": "...",
  "data": {
    "limit": 1000,
    "used": 45,
    "remaining": 955,
    "usage_percent": 4.5,
    "retry_after": null
  }
}
```

GET /ip-reputation/blacklist/api-usage response:
```json
{
  "status": "ok",
  "data": {
    "limit": 5,
    "used": 1,
    "remaining": 4,
    "usage_percent": 20.0,
    "local_fetches": 1,
    "api_remaining": 4,
    "api_limit": 5,
    "last_fetch": "2026-03-09T08:00:00",
    "total_ips": 500
  }
}
```

POST /ip-reputation/test response:
```json
{
  "status": "ok",
  "message": "AbuseIPDB API anahtari gecerli ve calisiyor.",
  "data": {
    "tested_ip": "8.8.8.8",
    "abuse_score": 0,
    "total_reports": 1,
    "country": "US",
    "usage_type": "Data Center/Web Hosting/Transit",
    "isp": "Google LLC"
  }
}
```

DELETE /ip-reputation/cache response:
```json
{
  "status": "ok",
  "deleted": 150,
  "sql_deleted": 150,
  "message": "150 Redis + 150 SQL IP reputation kaydi silindi."
}
```

PUT /ip-reputation/blacklist/config request/response:
```json
{
  "auto_block": true,
  "min_score": 100,
  "limit": 10000
}
```

POST /ip-reputation/blacklist/fetch response:
```json
{
  "status": "ok",
  "message": "...",
  "new_ips": 5,
  "total": 500
}
```

<!-- Mevcut Android pattern'leri -->

ApiRoutes.kt pattern:
```kotlin
const val IP_REP_CONFIG = "ip-reputation/config"
// Eksik olanlar eklenecek:
// const val IP_REP_API_USAGE = "ip-reputation/api-usage"
// const val IP_REP_BLACKLIST_API_USAGE = "ip-reputation/blacklist/api-usage"
```

Repository pattern (diger repolardan):
```kotlin
class IpReputationRepository(private val client: HttpClient) {
    suspend fun getConfig(): Result<IpRepConfigDto> = runCatching {
        client.get(ApiRoutes.IP_REP_CONFIG).body()
    }
}
```

Koin DI pattern:
```kotlin
// AppModule.kt'de zaten kayitli:
viewModelOf(::IpReputationViewModel)
single { IpReputationRepository(get()) }
```

Web paneldeki ulke engelleme kullanimi (referans):
- PRESET_COUNTRIES listesi: CN, RU, KP, IR, NG, BR, IN, UA
- config.blocked_countries array'i ile yonetim
- Ekleme: PRESET_COUNTRIES dropdown + ozel kod girisi
- Cikarma: X butonu ile tek tek
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: DTO'lari backend API response format'ina tam uyumlu yap + ApiRoutes + Repository guncelle</name>
  <files>
    android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/IpReputationDtos.kt
    android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiRoutes.kt
    android/app/src/main/java/com/tonbil/aifirewall/data/repository/IpReputationRepository.kt
  </files>
  <action>
KRITIK: Mevcut DTO'lar backend response'lariyla HICBIR SEKILDE eslesmez. Tamamen yeniden yaz.

**IpReputationDtos.kt — Tum DTO'lari sil, asagidakilerle degistir:**

1. `IpRepConfigDto` — GET /ip-reputation/config response:
   - `enabled: Boolean`
   - `@SerialName("abuseipdb_key") abuseipdbKey: String = ""` (maskeli key gelir)
   - `@SerialName("abuseipdb_key_set") abuseipdbKeySet: Boolean = false`
   - `@SerialName("blocked_countries") blockedCountries: List<String> = emptyList()`
   - `@SerialName("check_interval") checkInterval: Int = 300`
   - `@SerialName("max_checks_per_cycle") maxChecksPerCycle: Int = 10`
   - `@SerialName("daily_limit") dailyLimit: Int = 900`

2. `IpRepConfigUpdateDto` — PUT /ip-reputation/config request body:
   - `enabled: Boolean? = null`
   - `@SerialName("abuseipdb_key") abuseipdbKey: String? = null` (tam key gonderilir)
   - `@SerialName("blocked_countries") blockedCountries: List<String>? = null`
   NOT: Backend sadece enabled, abuseipdb_key, blocked_countries kabul eder. Diger alanlar (check_interval vb.) backend'de sabit — gondermeye gerek yok.

3. `IpRepSummaryDto` — GET /ip-reputation/summary response:
   - `@SerialName("total_checked") totalChecked: Int = 0`
   - `@SerialName("flagged_critical") flaggedCritical: Int = 0`
   - `@SerialName("flagged_warning") flaggedWarning: Int = 0`
   - `@SerialName("daily_checks_used") dailyChecksUsed: Int = 0`
   - `@SerialName("daily_limit") dailyLimit: Int = 900`
   - `@SerialName("abuseipdb_remaining") abuseipdbRemaining: Int? = null`
   - `@SerialName("abuseipdb_limit") abuseipdbLimit: Int? = null`

4. `IpRepIpsResponseDto` — GET /ip-reputation/ips wrapper:
   - `ips: List<IpRepCheckDto> = emptyList()`
   - `total: Int = 0`

5. `IpRepCheckDto` — her IP entry:
   - `ip: String = ""`
   - `@SerialName("abuse_score") abuseScore: Int = 0`
   - `@SerialName("total_reports") totalReports: Int = 0`
   - `country: String = ""`
   - `city: String = ""`
   - `isp: String = ""`
   - `org: String = ""`
   - `@SerialName("checked_at") checkedAt: String = ""`

6. `IpRepBlacklistResponseDto` — GET /ip-reputation/blacklist wrapper:
   - `ips: List<IpRepBlacklistDto> = emptyList()`
   - `total: Int = 0`
   - `@SerialName("last_fetch") lastFetch: String = ""`
   - `@SerialName("total_count") totalCount: Int = 0`

7. `IpRepBlacklistDto` — her blacklist entry:
   - `ip: String = ""`
   - `@SerialName("abuse_score") abuseScore: Int = 0`
   - `country: String = ""`
   - `@SerialName("last_reported_at") lastReportedAt: String = ""`

8. `IpRepBlacklistConfigDto` — GET /ip-reputation/blacklist/config:
   - `@SerialName("auto_block") autoBlock: Boolean = true`
   - `@SerialName("min_score") minScore: Int = 100`
   - `limit: Int = 10000`
   - `@SerialName("daily_fetches") dailyFetches: Int = 0`
   - `@SerialName("daily_limit") dailyLimit: Int = 5`
   - `@SerialName("last_fetch") lastFetch: String = ""`
   - `@SerialName("total_count") totalCount: Int = 0`

9. `IpRepBlacklistConfigUpdateDto` — PUT /ip-reputation/blacklist/config:
   - `@SerialName("auto_block") autoBlock: Boolean? = null`
   - `@SerialName("min_score") minScore: Int? = null`
   - `limit: Int? = null`

10. `IpRepTestResponseDto` — POST /ip-reputation/test:
    - `status: String = ""`
    - `message: String = ""`
    - `data: IpRepTestDataDto? = null`

11. `IpRepTestDataDto`:
    - `@SerialName("tested_ip") testedIp: String = ""`
    - `@SerialName("abuse_score") abuseScore: Int = 0`
    - `@SerialName("total_reports") totalReports: Int = 0`
    - `country: String = ""`
    - `@SerialName("usage_type") usageType: String = ""`
    - `isp: String = ""`

12. `IpRepApiUsageResponseDto` — GET /ip-reputation/api-usage:
    - `status: String = ""`
    - `message: String = ""`
    - `data: IpRepApiUsageDataDto? = null`

13. `IpRepApiUsageDataDto`:
    - `limit: Int? = null`
    - `used: Int? = null`
    - `remaining: Int? = null`
    - `@SerialName("usage_percent") usagePercent: Double = 0.0`
    - `@SerialName("retry_after") retryAfter: String? = null`

14. `IpRepCacheClearResponseDto` — DELETE /ip-reputation/cache:
    - `status: String = ""`
    - `deleted: Int = 0`
    - `@SerialName("sql_deleted") sqlDeleted: Int = 0`
    - `message: String = ""`

15. `IpRepBlacklistApiUsageDto` — GET /ip-reputation/blacklist/api-usage:
    - `status: String = ""`
    - `data: IpRepBlacklistApiUsageDataDto? = null`

16. `IpRepBlacklistApiUsageDataDto`:
    - `limit: Int = 0`
    - `used: Int = 0`
    - `remaining: Int = 0`
    - `@SerialName("usage_percent") usagePercent: Double = 0.0`
    - `@SerialName("last_fetch") lastFetch: String = ""`
    - `@SerialName("total_ips") totalIps: Int = 0`

17. `IpRepBlacklistFetchResponseDto` — POST /ip-reputation/blacklist/fetch:
    - `status: String = ""`
    - `message: String = ""`
    - `@SerialName("new_ips") newIps: Int = 0`
    - `total: Int = 0`

Tum class'lara `@Serializable` annotation ekle. `import kotlinx.serialization.SerialName` ve `import kotlinx.serialization.Serializable` import et.

**ApiRoutes.kt — Eksik endpoint'leri ekle:**
IP Reputation bolumune 2 yeni constant ekle:
```kotlin
const val IP_REP_API_USAGE = "ip-reputation/api-usage"
const val IP_REP_BLACKLIST_API_USAGE = "ip-reputation/blacklist/api-usage"
```

**IpReputationRepository.kt — Tamamen yeniden yaz:**
Response wrapper'lari duzgun parse etmeli:

```kotlin
class IpReputationRepository(private val client: HttpClient) {

    suspend fun getConfig(): Result<IpRepConfigDto> = runCatching {
        client.get(ApiRoutes.IP_REP_CONFIG).body()
    }

    suspend fun updateConfig(dto: IpRepConfigUpdateDto): Result<Unit> = runCatching {
        client.put(ApiRoutes.IP_REP_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }
        Unit
    }

    suspend fun getSummary(): Result<IpRepSummaryDto> = runCatching {
        client.get(ApiRoutes.IP_REP_SUMMARY).body()
    }

    suspend fun getIps(minScore: Int? = null): Result<List<IpRepCheckDto>> = runCatching {
        val response: IpRepIpsResponseDto = client.get(ApiRoutes.IP_REP_IPS) {
            minScore?.let { url { parameters.append("min_score", it.toString()) } }
        }.body()
        response.ips
    }

    suspend fun clearCache(): Result<IpRepCacheClearResponseDto> = runCatching {
        client.delete(ApiRoutes.IP_REP_CACHE).body()
    }

    suspend fun test(): Result<IpRepTestResponseDto> = runCatching {
        client.post(ApiRoutes.IP_REP_TEST).body()
    }

    suspend fun getApiUsage(): Result<IpRepApiUsageResponseDto> = runCatching {
        client.get(ApiRoutes.IP_REP_API_USAGE).body()
    }

    suspend fun getBlacklist(): Result<IpRepBlacklistResponseDto> = runCatching {
        client.get(ApiRoutes.IP_REP_BLACKLIST).body()
    }

    suspend fun fetchBlacklist(): Result<IpRepBlacklistFetchResponseDto> = runCatching {
        client.post(ApiRoutes.IP_REP_BLACKLIST_FETCH).body()
    }

    suspend fun getBlacklistConfig(): Result<IpRepBlacklistConfigDto> = runCatching {
        client.get(ApiRoutes.IP_REP_BLACKLIST_CONFIG).body()
    }

    suspend fun updateBlacklistConfig(dto: IpRepBlacklistConfigUpdateDto): Result<Unit> = runCatching {
        client.put(ApiRoutes.IP_REP_BLACKLIST_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }
        Unit
    }

    suspend fun getBlacklistApiUsage(): Result<IpRepBlacklistApiUsageDto> = runCatching {
        client.get(ApiRoutes.IP_REP_BLACKLIST_API_USAGE).body()
    }
}
```

NOT: `updateConfig` ve `updateBlacklistConfig` artik `Result<Unit>` donduruyor cunku backend'in dondurdugu response body standart degil (sadece `{"status":"ok","updated":[...]}`). ViewModel'de config'i refresh ile yeniden yukleyecegiz.
  </action>
  <verify>
    <automated>cd android && ./gradlew compileDebugKotlin 2>&1 | tail -20</automated>
  </verify>
  <done>Tum DTO'lar backend API response format'iyla birebir eslesiyor. Repository tum endpoint'leri cagiriyor. Compile basarili.</done>
</task>

<task type="auto">
  <name>Task 2: ViewModel'i yeni DTO'lara uyarla + ulke engelleme + API usage state ekle</name>
  <files>
    android/app/src/main/java/com/tonbil/aifirewall/feature/ipreputation/IpReputationViewModel.kt
  </files>
  <action>
ViewModel'i tamamen yeniden yaz. Yeni DTO'lara gore UiState ve fonksiyonlari guncelle.

**IpReputationUiState — yeni field'lar:**

```kotlin
data class IpReputationUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val selectedTab: Int = 0,
    // Data
    val config: IpRepConfigDto? = null,
    val summary: IpRepSummaryDto? = null,
    val ips: List<IpRepCheckDto> = emptyList(),
    val blacklistResponse: IpRepBlacklistResponseDto? = null,
    val blacklistConfig: IpRepBlacklistConfigDto? = null,
    // IP list sort
    val ipSortField: IpSortField = IpSortField.SCORE,
    val ipSortAscending: Boolean = false,
    // Test result
    val lastTestResult: IpRepTestResponseDto? = null,
    val isBlacklistFetching: Boolean = false,
    // API Usage
    val apiUsage: IpRepApiUsageDataDto? = null,
    val isCheckingApiUsage: Boolean = false,
    val blacklistApiUsage: IpRepBlacklistApiUsageDataDto? = null,
    val isCheckingBlacklistApiUsage: Boolean = false,
)
```

**IpSortField enum — guncelle:**
```kotlin
enum class IpSortField { SCORE, IP, COUNTRY, LAST_CHECKED }
```

**loadAll() — paralel async, yeni DTO'lara uyumlu:**
- `repository.getConfig()` → `IpRepConfigDto`
- `repository.getSummary()` → `IpRepSummaryDto`
- `repository.getIps()` → `List<IpRepCheckDto>` (wrapper parse edilmis)
- `repository.getBlacklist()` → `IpRepBlacklistResponseDto`
- `repository.getBlacklistConfig()` → `IpRepBlacklistConfigDto`

**updateConfig(dto: IpRepConfigUpdateDto) — kaydet sonrasi refresh:**
```kotlin
fun updateConfig(dto: IpRepConfigUpdateDto) {
    viewModelScope.launch {
        _uiState.update { it.copy(isActionLoading = true) }
        repository.updateConfig(dto)
            .onSuccess {
                _uiState.update { it.copy(actionMessage = "Ayarlar kaydedildi", isActionLoading = false) }
                // Config'i yeniden yukle (backend maskeli key donduruyor)
                repository.getConfig().onSuccess { cfg ->
                    _uiState.update { it.copy(config = cfg) }
                }
            }
            .onFailure { e ->
                _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
            }
    }
}
```

**Yeni fonksiyon — checkApiUsage():**
```kotlin
fun checkApiUsage() {
    viewModelScope.launch {
        _uiState.update { it.copy(isCheckingApiUsage = true) }
        repository.getApiUsage()
            .onSuccess { resp ->
                _uiState.update { it.copy(apiUsage = resp.data, isCheckingApiUsage = false) }
            }
            .onFailure { e ->
                _uiState.update { it.copy(actionMessage = "API kullanim hatasi: ${e.message}", isCheckingApiUsage = false) }
            }
    }
}
```

**Yeni fonksiyon — checkBlacklistApiUsage():**
```kotlin
fun checkBlacklistApiUsage() {
    viewModelScope.launch {
        _uiState.update { it.copy(isCheckingBlacklistApiUsage = true) }
        repository.getBlacklistApiUsage()
            .onSuccess { resp ->
                _uiState.update { it.copy(blacklistApiUsage = resp.data, isCheckingBlacklistApiUsage = false) }
            }
            .onFailure { e ->
                _uiState.update { it.copy(actionMessage = "Blacklist API hatasi: ${e.message}", isCheckingBlacklistApiUsage = false) }
            }
    }
}
```

**sortIps — yeni field isimleriyle:**
```kotlin
private fun sortIps(list: List<IpRepCheckDto>, field: IpSortField, ascending: Boolean): List<IpRepCheckDto> {
    val comparator: Comparator<IpRepCheckDto> = when (field) {
        IpSortField.SCORE -> compareBy { it.abuseScore }
        IpSortField.IP -> compareBy { it.ip }
        IpSortField.COUNTRY -> compareBy { it.country }
        IpSortField.LAST_CHECKED -> compareBy { it.checkedAt }
    }
    return if (ascending) list.sortedWith(comparator) else list.sortedWith(comparator.reversed())
}
```

**clearCache — yeni response tipi:**
```kotlin
fun clearCache() {
    viewModelScope.launch {
        _uiState.update { it.copy(isActionLoading = true) }
        repository.clearCache()
            .onSuccess { resp ->
                _uiState.update { it.copy(actionMessage = resp.message, isActionLoading = false) }
                refresh()
            }
            .onFailure { e ->
                _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
            }
    }
}
```

**testApi — yeni response tipi:**
```kotlin
fun testApi() {
    viewModelScope.launch {
        _uiState.update { it.copy(isActionLoading = true, lastTestResult = null) }
        repository.test()
            .onSuccess { result ->
                val isOk = result.status == "ok"
                _uiState.update {
                    it.copy(
                        lastTestResult = result,
                        actionMessage = if (isOk) "API testi basarili" else "API testi basarisiz: ${result.message}",
                        isActionLoading = false,
                    )
                }
            }
            .onFailure { e ->
                _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
            }
    }
}
```

**fetchBlacklist — yeni response tipi:**
```kotlin
fun fetchBlacklist() {
    viewModelScope.launch {
        _uiState.update { it.copy(isBlacklistFetching = true) }
        repository.fetchBlacklist()
            .onSuccess { resp ->
                _uiState.update { it.copy(actionMessage = resp.message, isBlacklistFetching = false) }
                // Yeniden yukle
                repository.getBlacklist().onSuccess { bl ->
                    _uiState.update { it.copy(blacklistResponse = bl) }
                }
                repository.getBlacklistConfig().onSuccess { cfg ->
                    _uiState.update { it.copy(blacklistConfig = cfg) }
                }
            }
            .onFailure { e ->
                _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isBlacklistFetching = false) }
            }
    }
}
```

**updateBlacklistConfig — yeni response:**
```kotlin
fun updateBlacklistConfig(dto: IpRepBlacklistConfigUpdateDto) {
    viewModelScope.launch {
        _uiState.update { it.copy(isActionLoading = true) }
        repository.updateBlacklistConfig(dto)
            .onSuccess {
                _uiState.update { it.copy(actionMessage = "Kara liste ayarlari kaydedildi", isActionLoading = false) }
                repository.getBlacklistConfig().onSuccess { cfg ->
                    _uiState.update { it.copy(blacklistConfig = cfg) }
                }
            }
            .onFailure { e ->
                _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
            }
    }
}
```
  </action>
  <verify>
    <automated>cd android && ./gradlew compileDebugKotlin 2>&1 | tail -20</automated>
  </verify>
  <done>ViewModel tum yeni DTO'lari kullaniyor. Ulke engelleme, API usage, blacklist API usage fonksiyonlari mevcut. Compile basarili.</done>
</task>

<task type="auto">
  <name>Task 3: Screen UI'yi yeni state'e uyarla + Ayarlar'a ulke engelleme ekle</name>
  <files>
    android/app/src/main/java/com/tonbil/aifirewall/feature/ipreputation/IpReputationScreen.kt
  </files>
  <action>
IpReputationScreen.kt'yi tamamen yeniden yaz. 4-tab yapisi korunuyor ama icerik yeni DTO'lara gore degisiyor.

**Tab yapisi ayni:** `listOf("Ozet", "IP'ler", "Kara Liste", "Ayarlar")`

**Tab 0 — SummaryTab degisiklikleri:**
- Mevcut `totalClean`, `totalSuspicious`, `totalCritical`, `totalBlocked` KALDIRILACAK
- Yerine backend'in gercek field'lari:
  - "Toplam Kontrol" → `summary.totalChecked` (neonCyan)
  - "Kritik (80+)" → `summary.flaggedCritical` (neonRed, Warning icon)
  - "Supheli (50-79)" → `summary.flaggedWarning` (neonAmber, Warning icon)
  - "Temiz" → `summary.totalChecked - summary.flaggedCritical - summary.flaggedWarning` (neonGreen, CheckCircle icon)
- API Kota kismi:
  - `summary.dailyChecksUsed` / `summary.dailyLimit` seklinde goster
  - Eger `summary.abuseipdbRemaining` ve `summary.abuseipdbLimit` varsa, AbuseIPDB API gercek kota goster
- API Kullanim Kontrol butonu ekle:
  - "API Kullanimi Kontrol Et" butonu → `viewModel.checkApiUsage()` cagirir
  - `uiState.apiUsage` doluysa: limit, used, remaining, usage_percent goster
- ScoreDistributionBar: `clean` = totalChecked - flaggedCritical - flaggedWarning, `suspicious` = flaggedWarning, `critical` = flaggedCritical
- Son Kontrol satiri KALDIRILACAK (backend bu field'i gondermez)

**Tab 1 — IpsTab degisiklikleri:**
- `IpRepCheckDto` artik `ip` (ipAddress degil), `abuseScore` (score degil), `country` (countryName degil)
- `IpRepCheckCard` guncelle:
  - IP adresi: `ip.ip`
  - Skor badge: `ip.abuseScore`
  - Ulke: `ip.country` (countryCode yok, dogrudan country name gelir)
  - ISP: `ip.isp`
  - Sehir: `ip.city`
  - Rapor: `ip.totalReports`
  - Tarih: `ip.checkedAt`
  - TOR badge KALDIRILACAK (backend bu field'i gondermez)
  - Blocked badge KALDIRILACAK (backend bu field'i gondermez)
  - countryCodeToFlag kullanma — backend ulke kodu degil ulke adi gonderiyor. Eger country 2 harf ise flag goster, degilse sadece text olarak goster.
- LazyColumn `key` parametresi: `{ it.ip }` (ipAddress degil)

**Tab 2 — BlacklistTab degisiklikleri:**
- `uiState.blacklistResponse` kullan — `blacklistResponse.ips` listesi, `blacklistResponse.lastFetch`, `blacklistResponse.totalCount`
- `IpRepBlacklistDto` artik `ip` (ipAddress degil), `abuseScore` (score degil)
- Blacklist config toggles ayni kaliyor
- Blacklist API kullanim butonu ekle:
  - "Blacklist API Kontrol" butonu → `viewModel.checkBlacklistApiUsage()` cagirir
  - `uiState.blacklistApiUsage` doluysa: limit, used, remaining goster

**Tab 3 — SettingsTab degisiklikleri (EN BUYUK DEGISIKLIK):**
Config artik `IpRepConfigDto` tipi.

1. IP Reputation Aktif toggle: `config.enabled` → ayni
2. AbuseIPDB API Anahtari:
   - config.abuseipdbKeySet = true ise: maskeli goster (`config.abuseipdbKey`)
   - Yeni key girmek icin TextField acilir
   - Eger kullanici bos birakir ve key zaten set edilmisse, PUT'ta abuseipdb_key gonderme (sadece diger field'lar)
   - Bos string gonderirse key silinir
3. YENI: Ulke Engelleme bolumu ekle (web paneldeki gibi):
   - Baslik: "Engellenen Ulkeler"
   - Mevcut engelli ulke listesi: `config.blockedCountries` — her biri FlowRow'da Chip olarak gosterilir, X butonu ile cikarilabilir
   - Preset ulke ekleme: 8 hazir ulke butonu (CN Cin, RU Rusya, KP Kuzey Kore, IR Iran, NG Nijerya, BR Brezilya, IN Hindistan, UA Ukrayna)
     - Zaten eklenmis olanlar disabled/secili gosterilir
     - Tiklaninca blockedCountries listesine eklenir
   - Ozel ulke kodu ekleme: 2 harfli TextField + "Ekle" butonu
   - countryCodeToFlag fonksiyonu ile ulke bayraklari gosterilir
   - Kaydet butonuna basilinca `IpRepConfigUpdateDto(enabled=..., abuseipdbKey=..., blockedCountries=...)` gonderilir

4. Genel bilgiler GlassCard: check_interval (300s = 5dk), max_checks_per_cycle (10), daily_limit — sadece gosterim (backend sabit degerler)

5. Kaydet + Test Et + Cache Temizle butonlari ayni kaliyor

**Yeni SettingsTab yerel state'ler:**
```kotlin
var enabled by rememberSaveable { mutableStateOf(config.enabled) }
var apiKeyInput by rememberSaveable { mutableStateOf("") }  // Bos baslar — kullanici yeni key girmek isterse doldurur
var apiKeyVisible by remember { mutableStateOf(false) }
var blockedCountries by rememberSaveable { mutableStateOf(config.blockedCountries) }
var newCountryCode by rememberSaveable { mutableStateOf("") }
```

**Preset ulkeler sabiti (dosya basinda):**
```kotlin
private val PRESET_COUNTRIES = listOf(
    "CN" to "Cin",
    "RU" to "Rusya",
    "KP" to "Kuzey Kore",
    "IR" to "Iran",
    "NG" to "Nijerya",
    "BR" to "Brezilya",
    "IN" to "Hindistan",
    "UA" to "Ukrayna",
)
```

**Kaydet butonu mantigi:**
```kotlin
val updateDto = IpRepConfigUpdateDto(
    enabled = enabled,
    abuseipdbKey = apiKeyInput.takeIf { it.isNotBlank() },  // bos ise null → backend degistirmez
    blockedCountries = blockedCountries,
)
viewModel.updateConfig(updateDto)
```

**countryCodeToFlag — mevcut fonksiyon korunuyor, IpRepCheckCard'da country 2 harf ise kullan:**
```kotlin
// Eger ip.country uzunlugu 2 ise (ulke kodu), flag goster
// Degilse sadece text olarak goster
```

**Genel UI pattern'ler (degismeyen):**
- Scaffold + TopAppBar + pullToRefresh ayni
- GlassCard, CyberpunkTheme.colors, neonMagenta tema rengi ayni
- snackbarHost ayni
- Loading/Error state ayni
  </action>
  <verify>
    <automated>cd android && ./gradlew compileDebugKotlin 2>&1 | tail -20</automated>
  </verify>
  <done>
4-tab IP Reputation ekrani calisiyor:
- Ozet tab: totalChecked, flaggedCritical, flaggedWarning, gunluk kota, API kullanim kontrolu
- IP'ler tab: gercek IP listesi backend'den geliyor, skor/ulke/isp gosteriyor
- Kara Liste tab: blacklist IP'leri, config toggle, fetch butonu, API kullanim kontrolu
- Ayarlar tab: API key (maskeli gosterim + yeni key giris), ulke engelleme (preset + ozel), enabled toggle, test, cache temizle
  </done>
</task>

</tasks>

<verification>
1. `cd android && ./gradlew compileDebugKotlin` — hatasiz derleme
2. DTO field isimleri backend response'lariyla birebir eslesiyor (SerialName annotation'lar kontrol)
3. Repository tum 11 endpoint'i cagiriyor (config, summary, ips, cache, test, api-usage, blacklist, blacklist-fetch, blacklist-config, blacklist-api-usage, updateConfig, updateBlacklistConfig)
4. Ulke engelleme UI'da mevcut — preset ulkeler + ozel kod + cikarma
5. API key maskeli gosteriliyor, yeni key girilebiliyor
</verification>

<success_criteria>
- Android IP Reputation sayfasi acildiginda backend'den veri cekilip gosterilebiliyor
- Ozet tab: toplam kontrol, kritik, supheli sayilari dogru
- IP'ler tab: sorgulanan IP listesi skor sirali gorunuyor
- Kara Liste tab: AbuseIPDB blacklist IP'leri listeleniyor
- Ayarlar tab: API key maskeli gorunuyor, yeni key girilebiliyor, ulke ekleme/cikarma calisiyor
- Web panelden veya Android'den API key degistirildiginde ayni Redis key kullaniliyor (cakisma yok — backend ayni endpoint)
</success_criteria>

<output>
After completion, create `.planning/quick/27-android-ip-reputation-sayfasi-tam-uyarla/27-SUMMARY.md`
</output>
