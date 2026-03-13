# Phase 11: Network Security - Research

**Researched:** 2026-03-13
**Domain:** Android Kotlin/Compose - Firewall/VPN/DDoS management screens
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Mevcut SecurityScreen Firewall tab'i genisletilecek
- Kural siralama: drag-and-drop veya up/down butonlari
- Edit dialog: mevcut Add dialog'a duzenleme modu ekleme
- Backend: /api/v1/firewall/* endpoint'leri
- Mevcut SecurityScreen VPN tab'i genisletilecek
- QR kod goruntuleme + paylasma (ShareSheet)
- VPN global durum gostergesi
- Backend: /api/v1/vpn/* endpoint'leri
- DDoS durumu: aktif/pasif, savunma metrikleri
- Basitlestirilmis saldiri haritasi (mobil optimize — SVG dunya haritasi yerine liste/kart bazli)
- Canli saldiri akisi (son N saldiri)
- Backend: /api/v1/ddos/* endpoint'leri

### Claude's Discretion
- Saldiri haritasi mobil implementasyonu (SVG harita vs basit liste)
- Kural oncelik duzenleme UX'i (drag vs buton)
- DTO ve Repository organizasyonu
- Tab yapisi (mevcut SecurityScreen tab'lari icinde mi, ayri ekran mi)

### Deferred Ideas (OUT OF SCOPE)
- Full SVG dunya haritasi (web versiyonu gibi) — mobil icin performans sorunu, basit liste yeterli
- VPN tunel istatistikleri (per-peer bandwidth) — ileride
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FW-01 | Firewall kural listesi goruntuleme | FirewallTab mevcut SecurityScreen'de — genisletme gerekli (priority, description alanlari eksik) |
| FW-02 | Kural ekleme/duzenleme/silme | Ekleme+silme mevcut, DUZENLEME (edit) yok — updateFirewallRule repository metodu var ama UI yok |
| FW-03 | Kural siralama (oncelik) yonetimi | priority alani backend'de var (0-10000) — UI'da up/down buton ile PATCH /rules/{id} |
| VPN-01 | WireGuard peer listesi goruntuleme | VpnTab mevcut SecurityScreen'de — yeterli, ufak iyilestirme yeterli |
| VPN-02 | Peer ekleme/silme | Mevcut SecurityScreen'de var (FAB + AddVpnPeerDialog + silme) |
| VPN-03 | VPN durumu gostergesi (aktif/pasif) | Mevcut VpnTab'da var (serverEnabled flag) — global durum gostergesi eksik |
| VPN-04 | Peer QR kodu goruntuleme/paylasma | QR goruntuleme mevcut (Base64 decode) — PAYLASMA (Android ShareSheet) eksik |
| DDOS-01 | DDoS koruma durumu ekrani | DdosTab mevcut SecurityScreen'de — yeterli temel bilgi, genisletme gerekli |
| DDOS-02 | Basitlestirilmis saldiri haritasi (mobil optimized) | DdosMapScreen AYRI ekran olarak mevcut — tab icine tasima veya direkt link |
| DDOS-03 | Canli saldiri akisi (son tehditler) | DdosMapScreen attack listesi var — DdosTab icine eklenebilir veya DdosMapScreen yeterli |
</phase_requirements>

---

## Summary

Bu phase, mevcut Android uygulamasindaki ag guvenligi ekranlarini tamamlamaya odaklanmaktadir. Kritik bir bulgu sudur: cogu altyapi ZATEN MEVCUT. SecurityScreen.kt'de Firewall tab (kural listesi, toggle, silme, FAB ekleme), VPN tab (peer listesi, start/stop, QR goruntuleme) ve DDoS tab (temel sayaclar, koruma modulleri) bulunmaktadir. Ayrica FirewallScreen.kt, VpnServerScreen.kt, DdosScreen.kt, DdosMapScreen.kt gibi ayri tam ekranlar da vardir.

Eksiklerin buyuk cogunlugu kucuk eklentilerdir: Firewall icin edit dialog + priority up/down butonlari; VPN icin Android ShareSheet entegrasyonu (Intent.createChooser); DDoS icin DdosTab'a saldiri listesi veya DdosMapScreen'e navigasyon linki. SecurityHubScreen zaten FirewallRoute, DdosRoute, DdosMapRoute gostermektedir.

**Primary recommendation:** Mevcut SecurityScreen'deki tab'lari genislet. Firewall edit dialog + priority siralama, VPN ShareSheet, DdosTab'a saldiri akisi ekle.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jetpack Compose | BOM 2024.x | UI framework | Proje standardı |
| Material3 | BOM ile gelir | AlertDialog, Switch, FAB | Mevcut tum diyaloglarda kullaniliyor |
| Koin | 4.x (BOM) | DI — ViewModel injection | Proje standardı |
| Ktor | 3.4.0 | API client (PATCH /rules/{id}) | Proje standardı |

### QR Paylasma (VPN-04 icin)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Android Intent.ACTION_SEND | Built-in | ShareSheet — metin veya gorsel paylas | QR config text paylasmak icin |
| FileProvider | Built-in (AndroidX) | Gerekirse bitmap dosyasi paylasmak icin | Gorsel olarak paylasma gerekirse |

**QR Paylasma — build.gradle degisiklik gerektirmiyor:** Android standart `Intent.createChooser` kullanilir, disaridan kutuphane eklenmez.

### Kural Siralama (FW-03 icin)
| Approach | Kutuphane | Not |
|----------|-----------|-----|
| Up/Down buton | Yok (pure Compose) | Tercih edilen — basit, guvenceli |
| Drag-and-drop | `compose-reorderable` (3rd party) veya `LazyColumn.reorderable` (deneysel) | Proje basit tutsun, buton yeterli |

**Karar:** Up/down buton (Claude'a birakilan UX). Ek kutuphane gerektirmiyor.

**Installation (yeni bagimlilık yok):**
```bash
# Degisiklik yok — mevcut dependencies yeterli
```

---

## Architecture Patterns

### Mevcut Mimari (Aynisinı Kullan)

```
SecurityScreen.kt (ana ekran — tab bazli)
├── FirewallTab()       ← genisletilecek (edit + priority)
├── VpnTab()            ← genisletilecek (ShareSheet)
├── DdosTab()           ← genisletilecek (saldiri listesi linki)
└── ...diger tablar

SecurityViewModel.kt    ← genisletilecek (editFirewallRule, reorderRule)
SecurityRepository.kt   ← mevcut, tam eksiksiz
SecurityDtos.kt         ← FirewallRuleDto priority alani EKSIK — guncellenecek
```

### Pattern 1: Firewall Edit Dialog (Mevcut Add Dialog'a Mod Ekleme)
**What:** AddFirewallRuleDialog'a `editingRule: FirewallRuleDto?` parametresi ekle. null = ekleme, non-null = duzenleme.
**When to use:** FW-02 gereği
**Example:**
```kotlin
// SecurityScreen.kt'deki mevcut dialog cagrisini genislet
if (uiState.showAddFirewallRuleDialog) {
    AddFirewallRuleDialog(
        onDismiss = { viewModel.hideAddFirewallRuleDialog() },
        onCreate = { dto -> viewModel.createFirewallRule(dto) },
        editingRule = uiState.editingFirewallRule, // yeni alan
        onUpdate = { id, dto -> viewModel.updateFirewallRule(id, dto) }, // yeni callback
    )
}
```

### Pattern 2: Priority Up/Down Butonlari (FW-03)
**What:** Her FirewallRuleItem'a yukarı/asagi buton ekle. Backend priority degeri PATCH ile guncellenir.
**When to use:** Kural siralama gerektigi durumda

**Siralama mantigi:**
```kotlin
// ViewModel'da
fun moveRuleUp(rule: FirewallRuleDto) {
    val rules = uiState.value.firewallRules
    val idx = rules.indexOfFirst { it.id == rule.id }
    if (idx <= 0) return
    val above = rules[idx - 1]
    // Priority degerlerini swap et
    viewModelScope.launch {
        repository.updateFirewallRule(rule.id, FirewallRuleCreateDto(..., priority = above.priority))
        repository.updateFirewallRule(above.id, FirewallRuleCreateDto(..., priority = rule.priority))
        refresh()
    }
}
```

**Kritik not:** Backend PATCH `/firewall/rules/{id}` mevcuttur ve `priority` alani `FirewallRuleUpdate` schema'sinda vardir (0-10000 arasi). FirewallRuleCreateDto'ya `priority: Int = 100` alani eklenmeli.

### Pattern 3: VPN QR Paylasma — Android ShareSheet (VPN-04)
**What:** VpnPeerConfigDialog'da "Paylas" butonu ile config_text'i ShareSheet'e aktar.
**When to use:** Kullanici QR dialog'da paylasma butonu tikladiginda

```kotlin
// Composable icinde
val context = LocalContext.current

Button(onClick = {
    val sendIntent = Intent(Intent.ACTION_SEND).apply {
        putExtra(Intent.EXTRA_TEXT, config.configText)
        type = "text/plain"
    }
    val shareIntent = Intent.createChooser(sendIntent, "WireGuard Config Paylas")
    context.startActivity(shareIntent)
}) {
    Icon(Icons.Outlined.Share, contentDescription = "Paylas")
    Text("Paylas")
}
```

**Manifest degisikligi gerekmez.** `android.permission.SEND` izni gerektirmez.

### Pattern 4: DDoS Tab Genisletme (DDOS-01/02/03)
**What:** Mevcut DdosTab'a DdosMapScreen'e yonlendiren bir kart/buton ekle. Canli saldiri akisi icin DdosAttackMapDto verisini SecurityViewModel'a ekle.

**Secenekler:**
- A) DdosTab icine getDdosAttackMap() cagirarak saldiri listesi goster (SecurityViewModel genisletme)
- B) DdosTab'da "Saldiri Haritasina Git" butonu goster (SecurityHubScreen'deki gibi)

**Tavsiye: Secenek A** — SecurityViewModel'a `ddosAttackMap: DdosAttackMapDto` ekle, DdosTab icinde son N saldiriyi liste olarak goster. DdosMapScreen zaten tam ekran harita icin mevcut.

### Anti-Patterns to Avoid
- **Yeni ayri ViewModel olusturma:** SecurityViewModel zaten tum guvenlik verisini yukluyor. Yeni ViewModel yerine mevcut genisletilmeli.
- **Kural siralama icin drag-and-drop kutuphanesi:** Ek bagimlilik, proje standardini bozar. Up/down buton yeterli.
- **QR paylasma icin bitmap encoding:** config_text plain text olarak paylasilabilir. Zorla gorsel yapmaya gerek yok.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Android ShareSheet | Ozel paylasma ekrani | `Intent.createChooser(ACTION_SEND)` | Platform standart, tum uygulamalar destekler |
| Kural siralama | Drag-drop sistemi | Up/down IconButton + priority PATCH | Proje kapsamina uygun, hata payı az |
| QR kod olusturma | Kotlin QR kutuphanesi | Backend zaten `qr_code_base64` donuyor | Sunucu tarafli zaten cozulmus |

---

## Common Pitfalls

### Pitfall 1: FirewallRuleDto'da priority Alani Yok
**What goes wrong:** Mevcut `FirewallRuleDto` (SecurityDtos.kt satir 140) `priority` alanini icermiyor. Up/down siralama yapildiginda priority degeri bilinmiyor.
**Why it happens:** DTO backend'in tum alanlarini yansıtmıyor.
**How to avoid:** `FirewallRuleDto`'ya `val priority: Int = 100` ekle. `FirewallRuleCreateDto`'ya da `val priority: Int = 100` ekle.
**Warning signs:** Kural siralamasinda "hangi priority degeri gonderecegim?" sorusu

### Pitfall 2: VPN QR Dialog'da Context Erismek
**What goes wrong:** `LocalContext.current` Composable scope disinda cagilirsa crash.
**How to avoid:** `val context = LocalContext.current` satiri Composable fonksiyon icinde tanimla, lambda icinde kullan.
**Warning signs:** "Cannot use LocalContext outside Composable" derleme hatasi

### Pitfall 3: SecurityViewModel'in Cok Buyumesi
**What goes wrong:** DdosAttackMap eklendikce loadAll() coroutine yavalayabilir (13+ paralel async).
**How to avoid:** DDoS attack map verisini lazy yukle (sadece DdosTab secildiginde). `LaunchedEffect(uiState.selectedTab)` ile tetikle.
**Warning signs:** Ilk yukleme 3+ saniye suruyorsa

### Pitfall 4: Edit Dialog'da Mevcut Kural Priority Degeri
**What goes wrong:** Edit dialog acildiginda priority alani gozukmuyorsa, guncelleme onceki degeri sifirliyor.
**How to avoid:** `editingRule` ile dialog acilirken butun alanlari (priority dahil) pre-populate et.

---

## Code Examples

### FirewallRuleDto Guncelleme (priority alani ekleme)
```kotlin
// SecurityDtos.kt — FirewallRuleDto'ya ekle
@Serializable
data class FirewallRuleDto(
    val id: Int = 0,
    val name: String = "",
    val direction: String = "",
    val protocol: String = "",
    val port: String? = null,
    @SerialName("source_ip") val sourceIp: String? = null,
    @SerialName("dest_ip") val destIp: String? = null,
    val action: String = "",
    val enabled: Boolean = true,
    val priority: Int = 100,        // YENİ
    val description: String? = null, // YENİ (backend'de var)
)
```

### SecurityUiState Guncelleme
```kotlin
// SecurityViewModel.kt — yeni state alanlari
data class SecurityUiState(
    // ... mevcut alanlar ...
    val editingFirewallRule: FirewallRuleDto? = null,   // edit modu
    val ddosAttackMap: DdosAttackMapDto = DdosAttackMapDto(), // saldiri haritasi
)
```

### ViewModel'a Edit + Reorder Fonksiyonlari
```kotlin
fun showEditFirewallRuleDialog(rule: FirewallRuleDto) =
    _uiState.update { it.copy(showAddFirewallRuleDialog = true, editingFirewallRule = rule) }

fun hideAddFirewallRuleDialog() =
    _uiState.update { it.copy(showAddFirewallRuleDialog = false, editingFirewallRule = null) }

fun updateFirewallRule(id: Int, dto: FirewallRuleCreateDto) {
    viewModelScope.launch {
        _uiState.update { it.copy(isActionLoading = true, showAddFirewallRuleDialog = false, editingFirewallRule = null) }
        securityRepository.updateFirewallRule(id, dto)
            .onSuccess {
                _uiState.update { it.copy(actionMessage = "Firewall kurali guncellendi", isActionLoading = false) }
                refresh()
            }
            .onFailure { e ->
                _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
            }
    }
}

fun moveRuleUp(rule: FirewallRuleDto) {
    val rules = _uiState.value.firewallRules.sortedBy { it.priority }
    val idx = rules.indexOfFirst { it.id == rule.id }
    if (idx <= 0) return
    val above = rules[idx - 1]
    viewModelScope.launch {
        // Priority degerlerini swap et
        securityRepository.updateFirewallRule(rule.id, buildUpdateDto(rule, priority = above.priority))
        securityRepository.updateFirewallRule(above.id, buildUpdateDto(above, priority = rule.priority))
        refresh()
    }
}
```

### Android ShareSheet Kullanimi
```kotlin
// VpnPeerConfigDialog icinde
val context = LocalContext.current
TextButton(
    onClick = {
        val intent = Intent(Intent.ACTION_SEND).apply {
            putExtra(Intent.EXTRA_TEXT, config.configText)
            type = "text/plain"
        }
        context.startActivity(Intent.createChooser(intent, "WireGuard Config"))
    }
) {
    Text("Paylas", color = colors.neonGreen)
}
```

---

## Mevcut Durum Analizi

### Zaten Tamam (dokunma yok):
| Ozellik | Nerede | Durum |
|---------|--------|-------|
| Firewall kural listesi | SecurityScreen.kt FirewallTab + FirewallScreen.kt | Calisıyor |
| Firewall kural ekleme | AddFirewallRuleDialog mevcut | Calisıyor |
| Firewall kural silme | deleteFirewallRule ViewModel + UI | Calisıyor |
| Firewall kural toggle | toggleFirewallRule mevcut | Calisıyor |
| VPN peer listesi | VpnTab mevcut | Calisıyor |
| VPN peer ekleme | AddVpnPeerDialog mevcut | Calisıyor |
| VPN peer silme | deleteVpnPeer mevcut | Calisıyor |
| VPN start/stop | startVpn/stopVpn mevcut | Calisıyor |
| VPN QR goruntuleme | VpnPeerConfigDialog, Base64 decode | Calisıyor |
| DDoS koruma modulleri | DdosTab + DdosScreen.kt | Calisıyor |
| DDoS saldiri haritasi | DdosMapScreen.kt (ayri ekran) | Calisıyor |
| DDoS saldiri listesi | DdosMapScreen'de AttackPointCard | Calisıyor |

### Eksik (bu phase'de eklenecek):
| Eksik | Nerede Eklenmeli | Kod Buyuklugu |
|-------|-----------------|---------------|
| Firewall kural duzenleme (edit) | AddFirewallRuleDialog'a mod + ViewModel | Kucuk |
| Firewall priority siralama (up/down) | FirewallRuleItem'a butonlar + ViewModel | Kucuk |
| FirewallRuleDto priority alani | SecurityDtos.kt + FirewallRuleCreateDto | Satirlik |
| VPN QR paylasma (ShareSheet) | VpnPeerConfigDialog'a buton | Satirlik |
| DdosTab'da saldiri akisi ozeti | DdosTab icine mini liste veya navigasyon linki | Kucuk |
| DDoS global durum ozeti kartı | DdosTab iyilestirme | Kucuk |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SecurityScreen tek monolitik tab | Ayri FirewallScreen/VpnServerScreen/DdosScreen + SecurityScreen tab | Onceki phase'ler | Her iki yaklasim mevcut — SecurityScreen tab'i tercih edilen |
| QR kod olusturma Android tarafında | Backend `qr_code_base64` donuyor | Phase 6-7 | Android sadece display ediyor |

---

## Open Questions

1. **SecurityScreen mi, SecurityHubScreen mi kullanilmali?**
   - What we know: SecurityHubScreen FirewallRoute, DdosRoute, DdosMapRoute'u ayri ekranlara yonlendiriyor. SecurityScreen tab-bazli yaklasim sunuyor.
   - What's unclear: Kullanici deneyimi acisından hangisi tercih edilmeli.
   - Recommendation: CONTEXT.md'de "SecurityScreen tab'i genisletilecek" yazıyor — bu kararı uygula. Ayri ekranlar (FirewallScreen, VpnServerScreen, DdosScreen) zaten var ve SecurityHubScreen'den de erisilebilir — ikiside korunsun.

2. **DdosTab'da saldiri listesi mi, yoksa DdosMapScreen linki mi?**
   - What we know: DdosMapScreen eksiksiz saldiri haritasi + liste sunuyor. DdosTab temel sayaclar goruyor.
   - Recommendation: DdosTab'a "DDoS Haritasini Goster" butonu + en son 3-5 saldiriyi mini kart olarak ekle. Bu en az kodla DDOS-02/03'u karsilar.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Android instrumented test / Compose UI test |
| Config file | android/app/src/androidTest/ |
| Quick run command | `./gradlew :app:connectedDebugAndroidTest` (Pi'de APK kurulmasi gerekir) |
| Full suite command | `./gradlew :app:connectedDebugAndroidTest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FW-01 | Firewall kural listesi goruntuleme | UI smoke | APK build + manuel | ❌ Wave 0 |
| FW-02 | Kural ekleme/duzenleme/silme | Integration (repository mock) | Unit test | ❌ Wave 0 |
| FW-03 | Kural priority siralama | Unit (ViewModel moveRuleUp/Down) | `./gradlew :app:testDebugUnitTest` | ❌ Wave 0 |
| VPN-01 | Peer listesi goruntuleme | UI smoke | Manuel | ❌ Wave 0 |
| VPN-02 | Peer ekleme/silme | Integration | Manuel | ❌ Wave 0 |
| VPN-03 | VPN durum gostergesi | UI smoke | Manuel | ❌ Wave 0 |
| VPN-04 | QR paylas ShareSheet | Manual-only | Manuel | N/A |
| DDOS-01 | DDoS durum ekrani | UI smoke | Manuel | ❌ Wave 0 |
| DDOS-02 | Saldiri haritasi (liste) | UI smoke | Manuel | ❌ Wave 0 |
| DDOS-03 | Canli saldiri akisi | UI smoke | Manuel | ❌ Wave 0 |

**Not:** Bu proje Android APK — jest/pytest gibi hizli unit test yerine build + manuel test tercih ediliyor. ViewModel logikleri (moveRuleUp, updateFirewallRule) JVM unit test ile test edilebilir.

### Sampling Rate
- **Per task commit:** `./gradlew :app:compileDebugKotlin` (derleme hatasi olmadigi dogrulama)
- **Per wave merge:** APK build (`./gradlew :app:assembleDebug`)
- **Phase gate:** APK Pi'ye deploy edilip manuel test

### Wave 0 Gaps
- [ ] `android/app/src/test/java/.../SecurityViewModelTest.kt` — FW-03 moveRuleUp/Down unit testi
- [ ] `android/app/src/test/java/.../FirewallRuleDtoTest.kt` — priority serialization dogrulama

*(Zorunlu degil — proje manuel test odakli. Derleme hatası = en önemli dogrulama.)*

---

## Sources

### Primary (HIGH confidence)
- Mevcut `SecurityScreen.kt` (97KB) — Firewall/VPN/DDoS tab kodu dogrudan incelendi
- Mevcut `SecurityViewModel.kt` — State ve action metodlari incelendi
- Mevcut `SecurityRepository.kt` — Tum CRUD metodlari mevcut dogrulandi
- Mevcut `SecurityDtos.kt` — FirewallRuleDto, VpnPeerConfigDto, FirewallRuleCreateDto
- Backend `firewall.py` — PATCH /rules/{id}, priority alani dogrulandi
- Backend `firewall_rule.py` (schema) — priority 0-10000, FirewallRuleUpdate nullable alanlar
- `FirewallScreen.kt`, `VpnServerScreen.kt`, `DdosScreen.kt`, `DdosMapScreen.kt` — Ayri ekranlar mevcut
- `SecurityHubScreen.kt` — Navigation linkleri mevcut
- `DdosFullDtos.kt` — DdosAttackMapDto, DdosAttackPointDto

### Secondary (MEDIUM confidence)
- Android docs: Intent.ACTION_SEND ShareSheet pattern — standart Android pratigi

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH - mevcut proje bagimlilikları incelendi, yeni kutuphane yok
- Architecture: HIGH - tum ilgili dosyalar okundu, bosluklar net sekilde tanimlandi
- Pitfalls: HIGH - gerçek kod okunarak tanimlandi (priority alani eksikligi gibi)

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 gun — stable Android codebase)
