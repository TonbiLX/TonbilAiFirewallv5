# Phase 10: DNS Filtering - Research

**Researched:** 2026-03-13
**Domain:** Android Jetpack Compose — DNS Filtreleme + Guvenlik Katmanlari
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- DNS Ozet Ekrani: Toplam sorgu, engelleme sayisi, engelleme orani gosterilmeli
- DNS Ozet Ekrani: En cok sorgulanan ve engellenen domain listesi
- DNS Ozet Ekrani: DNS guvenlik katmanlari durumu (DNSSEC, Tunneling, DoH, DGA)
- DNS Ozet Ekrani: Kaynak tipi dagilimi (INTERNAL/EXTERNAL/DOT)
- DNS Filtreleme Toggle: Tek dokunusla global DNS filtreleme ac/kapa
- DNS Filtreleme Toggle: SecuritySettings API uzerinden hot-reload (backend destekliyor)
- Icerik Kategorileri: Kategori listesi (ikon, renk, domain sayisi)
- Icerik Kategorileri: Blocklist baglama yonetimi (multi-select)
- Icerik Kategorileri: Ozel domain ekleme (custom_domains textarea)
- Profil Yonetimi: Profil CRUD (isim, ikon, bandwidth limiti)
- Profil Yonetimi: Kategori secimi (content_filters JSON array)
- Profil Yonetimi: Profil bazli domain sayisi gosterimi
- DNS Guvenlik Katmanlari (YENi): DNSSEC dogrulama durumu (enforce/log_only/disabled)
- DNS Guvenlik Katmanlari (YENi): DNS Tunneling dedektoru durumu (aktif/pasif, istatistikler)
- DNS Guvenlik Katmanlari (YENi): DoH endpoint durumu (guard.tonbilx.com)
- DNS Guvenlik Katmanlari (YENi): DGA tespiti durumu
- DNS Guvenlik Katmanlari (YENi): Rate limiting ayarlari
- DNS Guvenlik Katmanlari (YENi): Engelli sorgu tipleri (ANY, AXFR, vb.)
- DNS Guvenlik Katmanlari (YENi): Sinkhole IP

### Claude's Discretion
- Ekran tab yapisi (DNS Ozet / Kategoriler / Profiller / Guvenlik)
- DTO yapisi ve Kotlin data class'lari
- Repository pattern organizasyonu
- ViewModel state management detaylari
- Pull-to-refresh davranisi

### Deferred Ideas (OUT OF SCOPE)
- DNS sorgu gecmisi detayli filtreleme (zaman araliqi, cihaz bazli) — Phase 12 ile birlikte
- DNS analytics grafikleri (saatlik trend) — AI Insights sayfasiyla birlikte
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DNS-01 | DNS ozet ekrani — toplam sorgu, engelleme sayisi, en cok sorgulanan/engellenen domainler | GET /api/v1/dns/stats mevcut; DnsStatsDto hazir (topBlockedDomains + topQueriedDomains iceriyor) |
| DNS-02 | DNS filtreleme hizli toggle (tek dokunusla ac/kapa) | GET/PUT /api/v1/security-settings/config; SecurityConfigDto + SecurityConfigUpdateDto hazir; hot-reload destekli |
| DNS-03 | Icerik kategorileri goruntuleme + blocklist baglama yonetimi | ContentCategoriesScreen + ContentCategoriesViewModel + ContentCategoryRepository tamamen mevcut |
| DNS-04 | Profil yonetimi — profil olusturma/duzenleme, kategori secimi, bandwidth limiti | ProfilesScreen + ProfilesViewModel mevcut; ProfileCreateDto kategori secimi desteklemiyor (eksik) |
</phase_requirements>

---

## Summary

Phase 10, Android uygulamasinda DNS filtreleme sisteminin tam yonetimini kapsar. Arastirma, bu phase'in buyuk olcude mevcut kod temeli uzerine insa edilecegini ortaya koymustur. `DnsBlockingScreen`, `ContentCategoriesScreen` ve `ProfilesScreen` zaten mevcuttur ve temel islevleri calisir durumdadir.

Ancak `CONTEXT.md`'de tanimlanmis gereksinimleri karsilamak icin uc kritik bosluk bulunmustur: (1) DnsBlockingScreen mevcut haliyle blocklist/kural yonetimi yapabilmektedir ama DNS ozet ekranini, guvenlik katmanlari durumunu ve global toggle'i icermez; bunlari tasiyacak yeni bir `DnsHubScreen` veya genisletilmis sekme yapisi gereklidir. (2) `ProfilesViewModel`, profil olusturma/duzenleme sirasinda `content_filters` (kategori secimi) desteklememektedir — `AddProfileDialog` sadece isim ve bandwidth ister. (3) DNS guvenlik katmanlari (DNSSEC, Tunneling, DoH) `SecurityConfigDto`'da mevcut ama Android'de goruntuleme/duzenlemesi bulmamak icin yeni bir tab veya kart gerekmektedir.

**Birincil oneri:** DNS Filtering sayfasini 4-tab yapiyla uretin: `Ozet` (stats + toggle + guvenlik katmanlari), `Kategoriler` (mevcut ContentCategoriesScreen), `Profiller` (genisletilmis ProfilesScreen), `Guvenlik` (SecurityConfig DNS tab). Kategoriler ve Profiller ekranlari buyuk olcude yeniden kullanilabilir; sadece Ozet ve guvenlik katmanlari bolumleri yeniden yazilmalidir.

---

## Standard Stack

### Core (Mevcut — Degisiklik Yok)

| Kutphane | Versiyon | Amac | Neden Standart |
|----------|---------|------|----------------|
| Kotlin + Jetpack Compose | AGP 9.0.1 | UI framework | Proje geneli standart |
| Ktor Client 3.4.0 | 3.4.0 | REST API | OkHttp engine, proje geneli |
| Koin 4.1.0 | 4.1.0 | Dependency Injection | viewModelOf pattern, proje geneli |
| kotlinx.serialization | BOM | DTO serializasyon | @Serializable + @SerialName pattern |
| Material 3 | Compose BOM | UI komponentleri | Switch, Tab, FilterChip, AlertDialog |

### Mevcut ve Yeniden Kullanilabilir Dosyalar

| Dosya | Durum | Phase 10 Kullanimi |
|-------|-------|-------------------|
| `ContentCategoriesScreen.kt` | TAMAM | Dogrudan yeniden kullan |
| `ContentCategoriesViewModel.kt` | TAMAM | Dogrudan yeniden kullan |
| `ContentCategoryRepository.kt` | TAMAM | Dogrudan yeniden kullan |
| `ContentCategoryDtos.kt` | TAMAM | Dogrudan yeniden kullan |
| `ProfilesScreen.kt` | KISMI | Kategori secimi eklenmeli |
| `ProfilesViewModel.kt` | KISMI | content_filters destegi eklenmeli |
| `DnsBlockingScreen.kt` | KISMI | Sadece blocklist/kural UI'i mevcuttur; Ozet tab'i eksik |
| `DnsBlockingViewModel.kt` | KISMI | Global toggle + guvenlik katmanlari state eksik |
| `SecurityRepository.kt` | KISMI | getSecurityConfig + updateSecurityConfig mevcut; DNS toggle logic eksik |
| `SecurityConfigDto.kt` / `SecurityConfigDtos.kt` | TAMAM | DnsSecurityConfigDto tamamen mevcut |
| `DnsStatsDto` (SecurityDtos.kt) | TAMAM | topBlockedDomains + topQueriedDomains mevcut |
| `ApiRoutes.kt` | TAMAM | DNS_STATS, SECURITY_CONFIG endpoint'leri mevcut |

### Eksik / Olusturulmasi Gereken Dosyalar

| Dosya | Neden Olusturulmali |
|-------|---------------------|
| `DnsFilteringScreen.kt` (yeni) | 4-tab hub ekrani (Ozet, Kategoriler, Profiller, Guvenlik) |
| `DnsFilteringViewModel.kt` (yeni) | DNS stats + toggle + guvenlik katmanlari state yonetimi |
| `DnsSecurityLayersCard.kt` (yeni bilesem) | DNSSEC/Tunneling/DoH/DGA kart gosterimi |
| `ProfileEditDialog.kt` (genisletme) | Mevcut AddProfileDialog'a content_filters secimi ekle |
| `NavRoutes.kt` (guncelleme) | DnsFilteringRoute ekle |
| `AppNavHost.kt` (guncelleme) | DnsFilteringRoute composable ekle |
| `NetworkHubScreen.kt` (guncelleme) | DnsBlockingRoute → DnsFilteringRoute degistir |

---

## Architecture Patterns

### Onaylanan Mimari (Proje Geneli)

```
ViewModel (StateFlow<UiState>)
    ↓
Repository (suspend fun → Result<T>)
    ↓
Ktor HttpClient → ApiRoutes → Backend
```

### Onaylanan ViewModel Paterni

```kotlin
// Proje geneli standart pattern (Phase 8-9 orneklerinden)
data class DnsFilteringUiState(
    val stats: DnsStatsDto? = null,
    val securityConfig: SecurityConfigResponseDto? = null,
    val isLoading: Boolean = true,
    val isTogglingFilter: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val selectedTab: Int = 0,
)

class DnsFilteringViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(DnsFilteringUiState())
    val uiState: StateFlow<DnsFilteringUiState> = _uiState.asStateFlow()

    init { loadAll() }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val statsDeferred = async { securityRepository.getDnsStats() }
                    val configDeferred = async { securityRepository.getSecurityConfig() }
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            stats = statsDeferred.await().getOrNull(),
                            securityConfig = configDeferred.await().getOrNull(),
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = e.message) }
            }
        }
    }
}
```

### 4-Tab Yapisi (Claude's Discretion)

Tab yapisinin nedeni: DNS Filtering'in 4 farkli alan kapsadigini ve her birinin bagimsiz bir sayfa olacak kadar karmasik oldugunu kodun arastirmasi ortaya koymustur. Kategori ve Profil ekranlari hali hazirda mevcut oldugundan yeniden yazim gereksizdir.

```
DnsFilteringScreen (ScrollableTabRow)
├── Tab 0: "Ozet"
│   ├── DnsStatsCard (totalQueries24h, blockedQueries24h, blockPercentage, activeBlocklists)
│   ├── GlobalFilterToggle (Switch → PUT /security-settings/config)
│   ├── SourceTypeRow (INTERNAL / EXTERNAL / DOT dagilimi)
│   ├── TopDomainsList (top_blocked + top_queried)
│   └── DnsSecurityLayersCard (DNSSEC / Tunneling / DoH / DGA durumu)
│
├── Tab 1: "Kategoriler"
│   └── ContentCategoriesScreen (MEVCUT — yeniden kullan)
│
├── Tab 2: "Profiller"
│   └── ProfilesScreen (MEVCUT + content_filters secimi eklenmeli)
│
└── Tab 3: "Guvenlik"
    └── DnsSecuritySettingsCard (DNSSEC mode, rate limit, blocked qtypes, sinkhole IP)
```

### DNS Global Toggle Mantigi

Backend'de global DNS filtreleme toggle'i bulmak icin `SecurityConfigDto` incelendi. Dogrudan bir `dns_filtering_enabled` boolean alani yoktur. Toggle, proxy/blocklist sistemi uzerinden calisir. En temiz mobil toggle secenegi `dns_rate_limit_per_sec` sifirlamak veya DNS proxy servisinin systemd toggle'i kullanmak olabilir.

**Kritik bulgu:** `SecurityConfigDto`'da global DNS filtering toggle'i olarak kullanilabilecek bir alan mevcut degil. Ancak `dga_detection_enabled`, `dns_tunneling_enabled`, `dnssec_enabled` bireysel toggle'lardir. Web frontend incelenmeli — orada global toggle nasil calistiyor?

### Mevcut SecurityConfigDto DNS alanlari (SecurityConfigDtos.kt):

```kotlin
// DnsSecurityConfigDto (mevcut — /security/config endpoint'i icin)
data class DnsSecurityConfigDto(
    val rateLimitEnabled: Boolean = true,
    val rateLimitPerSecond: Int = 50,
    val blockedQueryTypes: List<String> = emptyList(),
    val sinkholeEnabled: Boolean = true,
    val sinkholeIp: String = "0.0.0.0",
)

// SecurityConfigResponse (backend schema) — yeni bir Android DTO gerekli:
data class SecurityConfigResponseDto(
    // Tehdit analizi, DNS guvenlik, uyari ayarlari yaninda:
    val dnssecEnabled: Boolean = true,
    val dnssecMode: String = "log_only",  // "enforce", "log_only", "disabled"
    val dnsTunnelingEnabled: Boolean = true,
    val dohEnabled: Boolean = true,
    val dgaDetectionEnabled: Boolean = true,
    val rateLimitEnabled: Boolean = true,  // NOTE: /security/config'den
    val dns_rate_limit_per_sec: Int = 5,
    ...
)
```

**Dikkat:** Mevcut `SecurityConfigDtos.kt`'deki `DnsSecurityConfigDto`, `/security/config` endpoint'iyle degil, daha eski bir endpoint yapisiyla eslesiyor. Gercek backend endpoint `/api/v1/security-settings/config` ve `SecurityConfigResponse` schema'si cok daha kapsamlidir. Yeni bir `SecuritySettingsDto` olusturulmasi gerekebilir veya mevcut `SecurityConfigDto` yeniden haritalanmali.

### Anti-Patterns

- **Mevcut ekranlari silip yeniden yazmak:** ContentCategoriesScreen ve ProfilesScreen calisir durumda. Sadece genislet.
- **Ayri repository olusturmak:** DNS ile ilgili her sey SecurityRepository'de. Yeni bir DNS repository gereksiz.
- **Toggle icin ozel endpoint istemek:** Backend zaten PUT /security-settings/config ile hot-reload destekliyor.

---

## Don't Hand-Roll

| Problem | Yapilmasin | Kullanilsin | Neden |
|---------|-----------|-------------|-------|
| DNS stats gosterimi | Ozel sayac komponenti | Mevcut `StatItem` bileseni (DnsBlockingScreen'den) | Zaten var ve stilize |
| Tab navigasyon | Ozel tab bar | Material3 `ScrollableTabRow` + `Tab` | Proje genelinde kullaniliyor (SecuritySettingsScreen ornegi) |
| Kategori listesi | Yeniden yaz | Mevcut `ContentCategoriesScreen` | Tam CRUD hazir |
| Profil listesi | Yeniden yaz | Mevcut `ProfilesScreen` (genislet) | Temel yapi hazir |
| Renk parsing | Ozel | Mevcut `parseHexColor()` (ContentCategoriesScreen) | Proje geneli util |
| Snackbar mesajlari | Toast kullanim | `SnackbarHostState` pattern | Proje geneli standart |
| Swipe-to-delete | Ozel gesture | `SwipeToDismissBox` (ContentCategoriesScreen ornegi) | Material3 built-in |

---

## Common Pitfalls

### Pitfall 1: SecurityConfigDto vs SecurityConfigResponse Uyumsuzlugu

**Neden olur:** Android'deki `SecurityConfigDto` (SecurityConfigDtos.kt dosyasinda), `/security/config` (security_settings API) ile degil, daha eski `/security/config` (guvenlik ayarlari) ile eslesiyor. Backend `SecurityConfigResponse` schema'si `dnssec_enabled`, `dns_tunneling_enabled`, `doh_enabled` alanlarini iceriyor; Android DTO'su icermiyor.

**Onleme:** `SecurityConfigDtos.kt`'deki `DnsSecurityConfigDto`'yu KULLANMA. Bunun yerine yeni bir `FullSecurityConfigDto` data class'i olustur ve `/api/v1/security-settings/config` GET/PUT endpoint'lerini kullanan `SecurityRepository.getSecurityConfig()` / `updateSecurityConfig()` metodlarini kullan (bunlar zaten mevcut).

**Uyari isaretleri:** Backend'den 422 validation error veya eksik alan gelmesi.

### Pitfall 2: ProfileCreateDto Kategori Secimi Eksikligi

**Neden olur:** Mevcut `AddProfileDialog`, sadece `name` ve `bandwidthLimitMbps` ister. `ProfileCreateDto`'da `contentFilters: List<String>` alani var ama UI'da girmek icin alan yok.

**Onleme:** `AddProfileDialog`'u genislet ve `ContentCategoriesScreen`'deki checkbox paterni gibi kategori listesi ekle. Kategorileri yukleme icin `ContentCategoryRepository.getCategories()` kullan.

**Uyari isaretleri:** Yeni profil olusturuldugunda `content_filters` her zaman bos liste.

### Pitfall 3: Global DNS Toggle Backend Alani Eksik

**Neden olur:** `SecurityConfig` modelinde `dns_filtering_enabled` gibi tek bir global toggle yok. Web frontend incelenmesi gerekiyor.

**Onleme:** Web frontend `DnsBlockingPage.tsx` ve `SecuritySettingsPage.tsx` incelenerek global toggle'in nasil uygulandigini anla. Muhtemelen blocklist'lerin `enabled` durumu uzerinden veya systemd servis stop/start ile yapiliyor. Alternatif: `dns_rate_limit_per_sec` 0 yaparak filtrelemeyi etkisiz kilmak.

**Uyari isaretleri:** Toggle sonrasi DNS filtrelemesi hala calisiyorsa veya duruyorsa.

### Pitfall 4: DnsStatsDto `externalQueries24h` Alani Eksik

**Neden olur:** Mevcut Android `DnsStatsDto`'sunda `externalQueries24h` alani yok, ama backend `DnsStatsResponse` bu alani donduruyor.

**Onleme:** `DnsStatsDto`'ya `@SerialName("external_queries_24h") val externalQueries24h: Int = 0` ekle.

### Pitfall 5: Profil Duzenleme (Edit) Destegi Yok

**Neden olur:** `ProfilesViewModel` sadece create ve delete destekliyor. Update (PATCH) endpoint'i backend'de mevcut (`updateProfile` SecurityRepository'de var) ama UI yok.

**Onleme:** ProfileCard'a "Duzenle" butonu ekle ve `ProfileEditDialog` (veya mevcut `AddProfileDialog`'u modal olarak tekrar kullan) ekle.

---

## Code Examples

### DNS Stats Yukleme (Paralel async pattern — proje standardi)

```kotlin
// Kaynak: DeviceDetailViewModel.kt (Phase 9 ornegi)
fun loadAll() {
    viewModelScope.launch {
        _uiState.update { it.copy(isLoading = true, error = null) }
        try {
            coroutineScope {
                val statsDeferred = async { securityRepository.getDnsStats() }
                val configDeferred = async { securityRepository.getSecurityConfig() }
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        stats = statsDeferred.await().getOrNull(),
                        securityConfig = configDeferred.await().getOrNull(),
                    )
                }
            }
        } catch (e: Exception) {
            _uiState.update { it.copy(isLoading = false, error = e.message) }
        }
    }
}
```

### SecurityConfig Guncelleme (Toggle icin)

```kotlin
// Kaynak: SecurityRepository.kt (mevcut)
fun toggleDnsSecurityLayer(field: String, value: Boolean) {
    viewModelScope.launch {
        _uiState.update { it.copy(isTogglingFilter = true) }
        // Ornek: DNSSEC toggle
        val update = FullSecurityConfigUpdateDto(dnssecEnabled = value)
        securityRepository.updateFullSecurityConfig(update)
            .onSuccess { updated ->
                _uiState.update { it.copy(isTogglingFilter = false, securityConfig = updated, actionMessage = "Ayar guncellendi") }
            }
            .onFailure { e ->
                _uiState.update { it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}") }
            }
    }
}
```

### ScrollableTabRow (SecuritySettingsScreen ornegi)

```kotlin
// Kaynak: SecuritySettingsScreen.kt (mevcut)
ScrollableTabRow(
    selectedTabIndex = uiState.selectedTab,
    containerColor = Color.Transparent,
    contentColor = colors.neonCyan,
    edgePadding = 0.dp,
) {
    listOf("Ozet", "Kategoriler", "Profiller", "Guvenlik").forEachIndexed { index, title ->
        Tab(
            selected = uiState.selectedTab == index,
            onClick = { viewModel.selectTab(index) },
            text = { Text(title, fontSize = 13.sp) },
        )
    }
}
```

### DNS Guvenlik Katmanlari Karti (Yeni bilesem)

```kotlin
// Oneri: Her katman icin StatusRow widget
@Composable
private fun SecurityLayerRow(
    label: String,
    isActive: Boolean,
    detail: String? = null,
    colors: CyberpunkColors,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(if (isActive) colors.neonGreen else colors.neonRed)
        )
        Spacer(Modifier.width(10.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(label, color = TextPrimary, fontSize = 13.sp)
            detail?.let { Text(it, color = TextSecondary, fontSize = 11.sp) }
        }
    }
}
```

### Content Filters Secimi (Profil dialog icin)

```kotlin
// Kaynak: ContentCategoriesScreen.kt checkbox pattern
categories.forEach { category ->
    val isChecked = category.key in selectedFilters
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable {
                selectedFilters = if (isChecked) selectedFilters - category.key
                                  else selectedFilters + category.key
            }
    ) {
        Checkbox(
            checked = isChecked,
            onCheckedChange = { checked ->
                selectedFilters = if (checked) selectedFilters + category.key
                                  else selectedFilters - category.key
            },
            colors = CheckboxDefaults.colors(checkedColor = colors.neonCyan)
        )
        Text(category.name, color = TextPrimary)
    }
}
```

---

## State of the Art

| Eski Yaklasim | Yeni Yaklasim | Ne Zaman Degisti | Etki |
|---------------|---------------|-----------------|------|
| DnsBlockingScreen tek sayfa (blocklist + kurallar) | 4-tab hub (ozet + kategoriler + profiller + guvenlik) | Phase 10 ile | Daha iyi organizasyon, tum DNS ozelliklerine tek noktadan erisim |
| ProfilesScreen sadece create/delete | ProfilesScreen + kategori secimi + edit dialog | Phase 10 ile | DNS-03 ve DNS-04 gereksinimlerini karsilar |
| SecurityConfig sadece tehdit analizi | SecurityConfig DNSSEC/DoH/Tunneling degerlerini de iceriyor | 2026-03-13 sistem guncellemesi ile | 12 guvenlik katmani gorunurlugu mobilde saglanacak |

**Deprecated/eskimis:**
- `DnsBlockingRoute` → `DnsFilteringRoute` ile degistirilecek (veya DnsBlockingScreen, yeni hub icine tab olarak tasınacak)

---

## Open Questions

1. **Global DNS Filtering Toggle — Backend Destegi**
   - Bildiklerimiz: `SecurityConfig`'de tek bir `dns_filtering_enabled` boolean yok
   - Belirsiz olan: Web frontend global toggle'i nasil yapiyor? `sinkhole_enabled` toggle'i mi kullaniliyor?
   - Oneri: Web frontend `SecuritySettingsPage.tsx` ve `DnsBlockingPage.tsx` incelenerek global toggle mantigi anlasilmali; yoksa `dga_detection_enabled + dns_tunneling_enabled + dnssec_enabled` kombinasyonu "hepsi kapat" olarak sunulabilir

2. **DnsStatsDto `external_queries_24h` Alani**
   - Bildiklerimiz: Backend `DnsStatsResponse` bu alani donduruyor
   - Belirsiz olan: Mevcut `DnsStatsDto`'ya eklenmeli mi yoksa yeni DTO mu olusturulmali?
   - Oneri: Mevcut `DnsStatsDto`'ya alan ekle (`ignoreUnknownKeys = true` zaten ayarli oldugu icin geri uyumluluk sorunu yok)

3. **Profil Duzenleme (Edit) Kapsamı**
   - Bildiklerimiz: Backend PATCH /profiles/{id} destekliyor, SecurityRepository.updateProfile() mevcut
   - Belirsiz olan: DNS-04 gereksinimine gore sadece "olusturma ve duzenleme" deniyor — edit in scope mi?
   - Oneri: DNS-04 "profil olusturulabiliyor/duzenlenebiliyor" diyor → edit kesinlikle scope icinde

---

## Validation Architecture

### Test Framework

| Ozellik | Deger |
|---------|-------|
| Framework | Manuel test (APK deploy + Pi SSH) |
| Config dosyasi | N/A |
| Hizli test komutu | `./gradlew assembleDebug` |
| Tam suite komutu | `./gradlew assembleDebug` + Pi deploy + manuel dogrulama |

### Phase Requirements → Test Map

| Req ID | Davranis | Test Tipi | Otomatik Komut | Dosya Mevcut? |
|--------|---------|-----------|----------------|---------------|
| DNS-01 | DNS ozet ekrani: stats, top domainler gosteriliyor | Smoke | `./gradlew assembleDebug` + manuel | Hayir — Wave 0 |
| DNS-02 | Toggle sonrasi DNS filtreleme degisiyor | Integration | Manuel (Pi SSH ile verify) | Hayir — Wave 0 |
| DNS-03 | Kategori goruntulenebiliyor, blocklist baglama yapilabiliyor | Smoke | `./gradlew assembleDebug` + manuel | Kismi (ContentCategoriesScreen mevcut) |
| DNS-04 | Profil olusturma, kategori secimi, bandwidth ayari calisiyor | Smoke | `./gradlew assembleDebug` + manuel | Kismi (ProfilesScreen mevcut, content_filters eksik) |

### Sampling Rate

- Her task commit sonrasi: `./gradlew assembleDebug` (derleme hatasi yok)
- Her wave merge sonrasi: APK Pi'ye deploy + manuel smoke test
- Phase gate: Tum 4 requirement manuel olarak dogrulanmis, APK derlemesi temiz

### Wave 0 Gaps

- [ ] `DnsFilteringScreen.kt` — DNS-01, DNS-02 kapsami
- [ ] `DnsFilteringViewModel.kt` — DNS-01, DNS-02 kapsami
- [ ] `FullSecurityConfigDto.kt` (veya mevcut SecurityConfigDtos.kt guncellemesi) — DNS-02, Guvenlik tab
- [ ] `ProfilesScreen.kt` content_filters guncelleme — DNS-04 kapsami
- [ ] `NavRoutes.kt` + `AppNavHost.kt` + `NetworkHubScreen.kt` guncelleme — routing

*(Mevcut test altyapisi yok; proje Android APK sideload + manuel dogrulama kullaniyor)*

---

## Sources

### Primary (HIGH confidence)
- Kaynak kod: `/android/app/src/main/java/com/tonbil/aifirewall/` — Tum mevcut Kotlin dosyalari dogrudan okundu
- Backend: `/backend/app/api/v1/dns.py`, `security_settings.py` — Endpoint ve schema yapisi dogrudan incelendi
- Backend: `/backend/app/models/security_config.py` — `dnssec_enabled`, `dns_tunneling_enabled`, `doh_enabled` alanlari dogrulandi
- Backend: `/backend/app/schemas/security_config.py` — `SecurityConfigResponse` schema tam listelendi

### Secondary (MEDIUM confidence)
- `SecurityRepository.kt` — `getSecurityConfig()` + `updateSecurityConfig()` metodlari mevcut; backend endpoint ile eslestigi onaylandi
- `SecuritySettingsScreen.kt` — `ScrollableTabRow` pattern dogrudan kopyalanabilir

### Tertiary (LOW confidence)
- Global DNS filtering toggle mekanizmasi — Tam olarak dogrulanamadi; web frontend incelemesi oneriliyor

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — Tum dosyalar dogrudan okundu
- Architecture: HIGH — Mevcut pattern'ler incelendi, bosluklar belirlendi
- Pitfalls: HIGH — Kod incelemesinden direkt cikartildi

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (backend schema degismedikce gecerli)
