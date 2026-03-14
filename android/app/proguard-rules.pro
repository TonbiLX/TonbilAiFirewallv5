# TonbilAiOS ProGuard / R8 Keep Rules
# Source: Ktor Slack + OkHttp GitHub + Koin GitHub + kotlinlang docs

# ---- Ktor ----
-keep class io.ktor.** { *; }
-dontwarn io.ktor.**

# ---- OkHttp + Okio ----
-keep class okhttp3.** { *; }
-dontwarn okhttp3.**
-keep class okio.** { *; }
-dontwarn okio.**

# ---- Kotlinx Serialization — DTO siniflarini koru ----
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class com.tonbil.aifirewall.data.remote.dto.** { *; }

# ---- Koin — DI framework ----
-keep class org.koin.** { *; }
-dontwarn org.koin.**

# ---- Glance App Widget ----
-keep class androidx.glance.** { *; }
-dontwarn androidx.glance.**

# ---- WorkManager ----
-keep class androidx.work.** { *; }

# ---- EncryptedSharedPreferences / Security Crypto ----
-keep class androidx.security.crypto.** { *; }

# ---- Biometric ----
-keep class androidx.biometric.** { *; }

# ---- Google Tink / ErrorProne (security-crypto bağımlılığı) ----
-dontwarn com.google.errorprone.annotations.CanIgnoreReturnValue
-dontwarn com.google.errorprone.annotations.CheckReturnValue
-dontwarn com.google.errorprone.annotations.Immutable
-dontwarn com.google.errorprone.annotations.RestrictedApi

# ---- Genel — Kotlin metadata koru ----
-keepattributes Signature
-keepattributes SourceFile,LineNumberTable
-keepattributes RuntimeVisibleAnnotations
