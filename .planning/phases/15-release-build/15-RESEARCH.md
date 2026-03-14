# Phase 15: Release Build - Research

**Researched:** 2026-03-14
**Domain:** Android Release APK Signing + Sideload Deployment
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UX-03 | APK build — imzali release APK olusturma ve S24 Ultra'ya yukleme | Keystore olusturma + signingConfigs + assembleRelease + ADB sideload zinciri tamamen dokumanli |

</phase_requirements>

---

## Summary

Bu faz Android imzalama altyapisi kurarak production-ready release APK uretmek ve Samsung S24 Ultra'ya sideload ile yuklemeyi kapsayan tek bir is akisindan olusur. Proje halihazirda debug APK'si calisiyor (80MB, `android/app/build/outputs/apk/debug/app-debug.apk`). Release build icin yapilmasi gereken uc sey var: (1) keystore olusturmak, (2) `build.gradle.kts` dosyasina `signingConfigs` blogu eklemek, (3) `assembleRelease` gorevini calistirip cikan APK'yi ADB veya dosya aktarimi ile S24 Ultra'ya yuklemek.

Kritik bir bulgu: Proje FCM (Firebase Cloud Messaging) kullanmiyor. Push bildirimleri WebSocket uzerinden `NotificationHelper.showSecurityNotification()` ile gonderiliyor. Bu mimari, uygulama arka planda veya kapali olduğunda bildirimlerin gelip gelmeyeceğini dogrudan etkiler. Android Doze modu ve WorkManager kisitlari bu senaryoda onemli bir test konusudur.

AGP surumu 8.7.3, JDK 17 (Adoptium) ve Android SDK `C:\Android` konumunda kurulu. Gradle properties dosyasinda JVM yolu zaten tanimli. ProGuard/R8 varsayilan olarak release buildde aktif olacagi icin Ktor, OkHttp, Koin, Glance ve serialization icin keep kurallari gerekli.

**Birincil oneri:** Keystore'u proje disinda (git-ignore edilmis) sakla, sifreleri `keystore.properties` dosyasina yaz, `build.gradle.kts` bu dosyadan oku. `assembleRelease` sonrasi `app/build/outputs/apk/release/app-release.apk` uretilir.

---

## Standard Stack

### Core
| Arac | Versiyon | Amac | Neden Standart |
|------|---------|------|----------------|
| Gradle KTS | AGP 8.7.3 | Build sistemi | Proje zaten kullaniyor |
| keytool | JDK 17 (Adoptium) | Keystore uretimi | JDK ile birlikte geliyor, ayri kurulum yok |
| R8 (ProGuard yerine) | AGP 8.0+ default | Kod kucultme + obfuscation | AGP 8.0'dan beri varsayilan |
| ADB | Android SDK platform-tools | APK telefona yuklenme | `C:\Android\platform-tools\adb.exe` mevcut |

### Sideload Alternatifleri
| Yontem | Ne Zaman | Not |
|--------|---------|-----|
| ADB install | USB veya WiFi debug aktifse | En hizli, terminal tabanlı |
| Dosya aktarimi (MTP/USB) | ADB driver sorunu varsa | STATE.md'de Samsung S24 USB driver uyumsuzlugu belirtilmis |
| Bulut (Google Drive / Telegram) | Fiziksel baglanti yoksa | APK boyutu ~80MB, Telegram'in 2GB limiti yeterli |

---

## Architecture Patterns

### Keystore Yonetimi (Guvenli Yaklasim)

```
android/
├── keystore.properties        # GIT-IGNORED! Sifreleri iceriyor
├── tonbilaios.keystore        # GIT-IGNORED! Keystore dosyasi
└── app/
    └── build.gradle.kts       # keystore.properties'ten okuyor
```

### signingConfigs Konfigurasyonu (build.gradle.kts)

```kotlin
// Source: https://developer.android.com/build/building-cmdline + randombits.dev
import java.util.Properties

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("keystore.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(keystorePropertiesFile.inputStream())
}

android {
    signingConfigs {
        create("release") {
            storeFile = file(keystoreProperties["storeFile"] as String)
            storePassword = keystoreProperties["storePassword"] as String
            keyAlias = keystoreProperties["keyAlias"] as String
            keyPassword = keystoreProperties["keyPassword"] as String
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

### keystore.properties Icerigi

```properties
storeFile=../tonbilaios.keystore
storePassword=SIFRE_BURAYA
keyAlias=tonbilaios
keyPassword=SIFRE_BURAYA
```

### ProGuard Kurallari (proguard-rules.pro)

```pro
# Source: Ktor Slack community + OkHttp GitHub + Koin GitHub + kotlinlang docs

# Ktor
-keep class io.ktor.** { *; }
-dontwarn io.ktor.**

# OkHttp + Okio
-keep class okhttp3.** { *; }
-dontwarn okhttp3.**
-keep class okio.** { *; }
-dontwarn okio.**

# Kotlinx Serialization — DTO siniflarini koru
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class com.tonbil.aifirewall.data.remote.dto.** { *; }

# Koin — DI framework
-keep class org.koin.** { *; }
-dontwarn org.koin.**

# Glance App Widget
-keep class androidx.glance.** { *; }
-dontwarn androidx.glance.**

# WorkManager
-keep class androidx.work.** { *; }

# EncryptedSharedPreferences / Security Crypto
-keep class androidx.security.crypto.** { *; }

# Biometric
-keep class androidx.biometric.** { *; }

# Genel — Kotlin metadata koru
-keepattributes Signature
-keepattributes SourceFile,LineNumberTable
-keepattributes RuntimeVisibleAnnotations
```

### Keystore Olusturma Komutu

```bash
# Source: developer.android.com/studio/publish/app-signing
keytool -genkey -v \
  -keystore tonbilaios.keystore \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -alias tonbilaios
```

Windows'ta (JDK 17 Adoptium):
```cmd
"C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot\bin\keytool.exe" -genkey -v -keystore tonbilaios.keystore -keyalg RSA -keysize 2048 -validity 10000 -alias tonbilaios
```

### Release APK Build Komutu

```bash
# Windows'ta android/ dizininden
cd android
gradlew.bat assembleRelease
# Cikti: app/build/outputs/apk/release/app-release.apk
```

### ADB Sideload

```bash
# USB debug aktifse
adb install app/build/outputs/apk/release/app-release.apk

# Guncelleme (ayni paket ismi mevcut APK uzerine)
adb install -r app/build/outputs/apk/release/app-release.apk
```

---

## Don't Hand-Roll

| Problem | Yapma | Kullan |
|---------|-------|--------|
| APK imzalama | Manuel apksigner calistirma | Gradle signingConfigs — build sirasinda otomatik imzalar |
| Kod kucultme | Manuel sinif silme | R8/ProGuard — release buildde otomatik aktif |
| ADB driver | Samsung-ozel surucu arama | Universal ADB Driver veya dosya aktarimi yontemi |

---

## Common Pitfalls

### Pitfall 1: ProGuard DTO Siniflarini Siliyor
**Ne olur:** Release APK'de API yanitleri parcalanamaz (JSON parse hatasi), debug APK'de calisiyor
**Neden olur:** R8 serialization DTO'larini kullanilmiyor sanip siliyor
**Nasil onlenir:** `proguard-rules.pro` icinde `com.tonbil.aifirewall.data.remote.dto.**` siniflarini `keepclasseswithmembers` ile koru
**Uyari isaretleri:** Release buildde API cagrisi sonrasi `JsonDecodingException` veya bos ekran

### Pitfall 2: Koin DI Release'de Cozumleme Hatasi
**Ne olur:** `NoBeanDefFoundException` veya `ClassNotFoundException` — debug'da calisiyor, release'de patliyor
**Neden olur:** R8 Koin'in runtime yansima (reflection) ile cozumledigini bilmiyor, sinifi siliyor
**Nasil onlenir:** `-keep class org.koin.** { *; }` kuralini ekle
**Uyari isaretleri:** Uygulama acilirken splash sonrasi aninda kapaniyor

### Pitfall 3: keystore Dosyasinin Git'e Commitlennmesi
**Ne olur:** Ozel anahtar GitHub'a gidiyor — guvenlik acigi
**Neden olur:** `.gitignore` unutuluyor
**Nasil onlenir:** `.gitignore` dosyasina `*.keystore`, `*.jks`, `keystore.properties` ekle. Build ONCESINDE kontrol et.

### Pitfall 4: Samsung S24 USB Driver Uyumsuzlugu
**Ne olur:** ADB cihazi goremez (STATE.md'de belirtilmis)
**Neden olur:** Samsung Galaxy S24 icin standart USB surucu cihazi tanımiyor
**Nasil onlenir:** ADB yerine dosya aktarim yontemini kullan (MTP, Google Drive, Telegram) veya Samsung USB Driver'i manuel indir
**Uyari isaretleri:** `adb devices` cikti bos

### Pitfall 5: Arka Planda Bildirim Calismamasi (Doze Modu)
**Ne olur:** Uygulama kapatildiginda push bildirimleri gelmiyor (Basari Kriteri #3)
**Neden olur:** Proje FCM kullanmiyor — WebSocket-tabanlı bildirimler Doze modunda duzgun calismiyor
**Nasil onlenir:**
- WorkManager periyodik gorev halihazirda var (15 dk widget yenilemesi) — bildirim kontrolu buraya eklenebilir
- Ya da kullanicidan "Pil Optimizasyonu" muafiyeti talep edilebilir (`REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`)
- Kabul edilebilir cozum: Bildirimler uygulama ACIKKEN guvenilir; tamamen kapali iken sinirli
**Uyari isaretleri:** Telefon bekleme modunda bildirim gelmiyor

### Pitfall 6: versionCode Guncellenmeden Kurulum
**Ne olur:** `adb install` "INSTALL_FAILED_VERSION_DOWNGRADE" hatasi
**Neden olur:** Release APK'nin versionCode debug APK'den kucuk veya esit
**Nasil onlenir:** `build.gradle.kts` icinde `versionCode = 1` zaten ayarli — ilk release icin sorun yok. Ama ileride guncellemelerde artir.

---

## Code Examples

### Mevcut Proje Durumu (Debug APK)

```
android/app/build/outputs/apk/debug/app-debug.apk
Boyut: 80,449,510 byte (~77MB)
Build tarihi: 2026-03-14
Build tipi: DEBUG (imzasiz / debug keystore)
versionCode: 1, versionName: "1.0.0"
minSdk: 31 (Android 12), targetSdk: 35 (Android 15)
applicationId: com.tonbil.aifirewall
```

### Manifest'te Cleartext Traffic Uyarisi

```xml
<!-- AndroidManifest.xml icinde mevcut: -->
android:usesCleartextTraffic="true"
```

Bu ayar release buildde guvenlik uyarisi dogurabilir. 192.168.1.2 HTTP ile konusuldugu icin (HTTPS degil) bu gerekli. Release icin oldugun gibi birakmak kabul edilebilir (kisisel kullanim, ic ag).

### .gitignore Eklemeleri

```gitignore
# Android keystore — ASLA commit etme
*.keystore
*.jks
android/keystore.properties
android/local.properties
```

---

## State of the Art

| Eski Yaklasim | Mevcut Yaklasim | Ne Zaman Degisti | Etkisi |
|---------------|-----------------|-----------------|--------|
| ProGuard | R8 (tam mod) | AGP 8.0 (2023) | Daha agresif optimizasyon, daha fazla ProGuard kural gerekebilir |
| Global "Unknown Sources" | Per-app "Install Unknown Apps" | Android 8.0+ | S24'te ayar: Ayarlar > Uygulamalar > Ozel Uygulama Erisimi > Bilinmeyen Uygulama Yukle |
| `draggableHandle` (react-grid-layout) | Android'le alakali degil | - | - |

---

## Open Questions

1. **Arka Planda Bildirim Guvenirligi**
   - Bildiklerimiz: Uygulama WebSocket kullanıyor, FCM yok; TonbilApp.observeSecurityEvents() WebSocket event dinliyor
   - Belirsiz olan: Android Doze modu WebSocket baglantisini olduruyor, uygulama tamamen kapali oldugunda hic bildirim gelmiyor
   - Oneri: Planlama asamasinda "Basari Kriteri #3"u yeniden tanimla — "uygulama arka planda (minimize edilmis, foreground service degil)" olarak sinirla; tamamen kapali iken garanti verilmez. Alternatif: WorkManager icinde periyodik kontrol ve local notification pattern. Bu faz kapsami icinde derin bildirim mimarisi degisikligi gerekmez; kabul edilebilir siniri olusturdurmak yeterli.

2. **keystore Sifresi Yonetimi**
   - Bildiklerimiz: Kisisel kullanim, tek gelistirici
   - Oneri: Basit sifre belirle, `keystore.properties` dosyasini Windows'ta guvenli yerde sakla (Nextcloud sifre kasasi veya BitLocker'li disk)

---

## Validation Architecture

> `workflow.nyquist_validation` anahtari `.planning/config.json` dosyasinda yok — etkin sayilir.

### Test Framework

| Ozellik | Deger |
|---------|-------|
| Framework | Manuel test (otomatik Android UI test altyapisi yok — Espresso/Compose test bagimliligi mevcut degil) |
| Config dosyasi | Yok |
| Hizli test | `./gradlew assembleRelease` basariyla tamamlandi mi? |
| Tam suite | Manuel S24 Ultra dogrulama listesi (asagida) |

### Phase Requirements → Test Map

| Req ID | Davranis | Test Tipi | Komut | Var mi? |
|--------|----------|-----------|-------|---------|
| UX-03-A | Release APK uretildi | Build | `gradlew.bat assembleRelease` | Wave 0 sonrasi |
| UX-03-B | APK S24 Ultra'ya yuklendi | Manuel | `adb install -r app-release.apk` veya dosya aktarimi | Wave 0 sonrasi |
| UX-03-C | Uygulama acilista giris ekranini gosteriyor | Manuel | Telefonda acilis kontrol | Wave 0 sonrasi |
| UX-03-D | Tum ekranlar giris sonrasi erisilebilir | Manuel | Nav bar ile tum ekranlara gec | Wave 0 sonrasi |
| UX-03-E | Arka planda bildirim calisiyor | Manuel | Uygulama minimize, Pi'de test olayı tetikle | Wave 0 sonrasi |

### Sampling Rate
- **Her gorev commit sonrasi:** `gradlew.bat assembleRelease` basarili mi? (R8 hata olmadan tamamlandi mi?)
- **Dalga birlestirme:** Telefona yukle + ilk acilis testi
- **Faz kapisinda:** Tum manuel test maddelerini gec

### Wave 0 Gaps
- [ ] `android/app/proguard-rules.pro` — Ktor/Koin/DTO keep kurallari (dosya mevcut degil, olusturulacak)
- [ ] `android/keystore.properties` — Keystore sifreleri (git-ignore edilmis, Wave 0'da olusturulacak)
- [ ] `android/tonbilaios.keystore` — Keystore dosyasi (Wave 0'da keytool ile uretilecek)
- [ ] `android/.gitignore` — keystore ve properties dosyalarini disla
- [ ] `build.gradle.kts` signingConfigs blogu — release signing konfigurasyonu

---

## Sources

### Birincil (HIGH guven)
- [Android Developer — Sign your app](https://developer.android.com/studio/publish/app-signing) — Keystore olusturma, Gradle signingConfigs
- [Android Developer — Build from command line](https://developer.android.com/build/building-cmdline) — assembleRelease, Gradle gorevleri
- [Android Developer — R8 / Shrink code](https://developer.android.com/build/shrink-code) — minifyEnabled, proguardFiles

### Ikincil (MEDIUM guven)
- [randombits.dev — Signing with Gradle](https://randombits.dev/articles/android/signing-with-gradle) — Kotlin DSL signingConfigs ornegi
- [Medium — Keystore.properties KTS pattern](https://medium.com/@omkartenkale/example-of-declaring-android-signing-configs-using-gradle-kotlin-dsl-with-gitignored-keystore-proper-6058433985a2) — keystore.properties guvenli yaklasim
- [The GalaxyS24 Guide — Install Unknown Apps](https://thegalaxys24guide.com/how-to-allow-install-unknown-apps-on-samsung-galaxy-s24/) — S24 sideload adimları
- [Ktor Slack — ProGuard rules](https://slack-chats.kotlinlang.org/t/18845808/hi-does-ktor-client-library-need-some-rules-in-order-to-work) — Ktor ProGuard gereksinimleri
- [Kotzilla — Koin ProGuard](https://doc.kotzilla.io/docs/settings/proguard/) — Koin R8 keep kurallari

### Ucuncul (LOW guven — dogrulama gerekir)
- [Mobile Push vs WebSocket (Curiosum)](https://www.curiosum.com/blog/mobile-push-notifications-description-and-comparison-with-web-sockets) — WebSocket-tabanlı bildirim sinirlamalari

---

## Metadata

**Guven dagilimi:**
- Standard Stack: HIGH — AGP 8.7.3, JDK 17, ADB — proje config'inden dogrudan okundu
- Architecture: HIGH — Gradle KTS signingConfigs resmi Android dokumaninda
- Pitfalls: HIGH (ProGuard/Doze) — yaygin, bircok kaynakla teyit edildi; MEDIUM (Samsung USB driver) — STATE.md'den proje deneyimiyle teyit edildi
- Bildirim kisitlamalari: MEDIUM — WebSocket+Doze davranisi belgelenmis ama test gerektirir

**Arastirma tarihi:** 2026-03-14
**Gecerlilik suresi:** 90 gun (Android release sureci stabil)
