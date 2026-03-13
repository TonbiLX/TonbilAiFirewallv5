# Phase 13: Communication & Config - Research

**Researched:** 2026-03-13
**Domain:** Android Kotlin/Compose — Push Notifications, AI Chat, Telegram, WiFi AP, DHCP, Security Settings
**Confidence:** HIGH

## Summary

Bu faz esas olarak **bağlantı ve yapılandırma** işlevlerini kapsamaktadır: FCM push bildirim altyapısı, AI sohbet ekranı, Telegram bot yapılandırması, WiFi AP yönetimi, DHCP yönetimi ve güvenlik eşik ayarları. Kritik bulgu: **tüm ekranlar zaten mevcut** — `ChatScreen`, `TelegramScreen`, `WifiScreen`, `DhcpScreen`, `SecuritySettingsScreen`, `PushNotificationsScreen` dosyaları Android projesinde yazılmış ve `AppNavHost`'a bağlanmıştır. `SettingsHubScreen` ve `NetworkHubScreen` da bu ekranlara referans vermektedir.

**Temel sorun:** Mevcut ekranlar çalışıyor ancak bazı özellikler eksik veya tamamlanmamış. NOTIF-01/02 için FCM gerçek entegrasyonu placeholder durumunda. CHAT-03 yapılandırılmış yanıt (JSON/tablo) görüntüleme eksik. Diğer ekranlar (Telegram, WiFi, DHCP, SecuritySettings) büyük ölçüde tamamlanmış görünüyor.

**Birincil öneri:** Mevcut ekranları sıfırdan yazmak yerine gap analizi yap ve eksik özellikleri tamamla. FCM entegrasyonu en büyük çalışma gerektirecek alan.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| NOTIF-01 | FCM push notification altyapisi — backend token kayit endpoint | Backend `push.py` endpoint mevcut ama token gerçekten kaydedilmiyor (placeholder). FCM token'ı Firebase'e kaydetmek ve Pi backend'e bildirmek gerekiyor. |
| NOTIF-02 | Backend bildirim dispatch servisi (yeni cihaz, DDoS, DNS, VPN durum degisikligi) | WebSocket üzerinden `broadcast_security_event()` mevcut. FCM dispatch için `telegram_service` benzeri bir mekanizma gerekiyor. |
| NOTIF-03 | Android bildirim kanallari (Guvenlik, Cihaz, Trafik, Sistem) | `PushNotificationsScreen` kanal listesi gösteriyor. Android `NotificationChannel` oluşturma `Application` sınıfında yapılmalı. |
| NOTIF-04 | Bildirim ayarlari ekrani — kanal bazli ac/kapa | `PushNotificationsScreen` + `PushNotificationsViewModel` mevcut. Kanal toggle çalışıyor (backend `push/channels/{id}/toggle`). |
| CHAT-01 | Mobil AI sohbet ekrani — mevcut /api/v1/chat endpoint kullanimi | `ChatScreen` + `ChatViewModel` mevcut. `SecurityRepository.sendChat()` ve `getChatHistory()` entegre. |
| CHAT-02 | Mesaj gecmisi goruntuleme | `ChatViewModel.loadHistory()` → `GET /chat/history`. `LazyColumn` ile mesaj listesi mevcut. |
| CHAT-03 | Yapilandirilmis yanit goruntuleme (JSON/tablo formati) | Mevcut `ChatBubble` sadece düz metin gösteriyor. JSON yanıtları parse edip tablo/liste halinde render etmek gerekiyor. |
| TELE-01 | Telegram bot yapilandirma ekrani (token, chat ID) | `TelegramScreen` tam fonksiyonel — bot token, chat ID alanları, kaydet butonu mevcut. |
| TELE-02 | Telegram bildirim ayarlari | `TelegramScreen` notify_threats, notify_devices, notify_ddos toggle'ları mevcut. |
| WIFI-01 | WiFi erisim noktasi durumu goruntuleme | `WifiScreen` → `WifiStatusCard` ile SSID, kanal, frekans, bağlı istemci sayısı gösteriliyor. |
| WIFI-02 | SSID, sifre, kanal degistirme | `WifiScreen` → `WifiConfigCard` edit mode ile SSID/şifre/kanal düzenleme mevcut. |
| WIFI-03 | WiFi AP acma/kapatma | `WifiScreen` → `WifiStatusCard` Switch toggle ile enable/disable mevcut. |
| DHCP-01 | DHCP havuz bilgileri goruntuleme | `DhcpScreen` → `DhcpStatsRow` + pool listesi mevcut. |
| DHCP-02 | Statik IP atamalari yonetimi | `DhcpScreen` → `AddStaticLeaseDialog` + lease listesi + silme mevcut. |
| SEC-01 | Guvenlik ayarlari ekrani — tehdit/DNS/DDoS esik degerleri | `SecuritySettingsScreen` + `SecuritySettingsViewModel` mevcut. |
| SEC-02 | Ayar degistirme ve kaydetme (hot-reload backend) | `SecurityConfigUpdateDto` ile partial update, `PUT /security/config` + `POST /security/reload` mevcut. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kotlin | 2.0+ | Dil | Proje standardı |
| Jetpack Compose | BOM 2024.x | UI | Proje standardı |
| Koin | 4.x | DI | Proje standardı (Hilt değil) |
| Ktor Client | 3.4.0 | HTTP + WebSocket | Proje standardı |
| kotlinx.serialization | 1.7+ | JSON | Proje standardı |
| Firebase Messaging | 24.x | FCM push | Push bildirim standardı |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| firebase-bom | 33.x | Firebase BOM | FCM eklendiğinde |
| google-services plugin | 4.4.x | google-services.json okuma | FCM için zorunlu |
| AndroidX Core | 1.13+ | NotificationCompat, NotificationChannel | NOTIF-03 için |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FCM gerçek entegrasyonu | WebSocket sistem bildirimleri (mevcut) | WebSocket zaten çalışıyor; FCM uygulama kapalıyken de bildirim getirir |
| JSON tablo render (CHAT-03) | Markdown renderer kütüphanesi | Dependency ağırlığı; basit tablo regex parse daha hafif |

**Kurulum (FCM için):**
```bash
# android/app/build.gradle.kts
implementation(platform("com.google.firebase:firebase-bom:33.x"))
implementation("com.google.firebase:firebase-messaging-ktx")
```

## Architecture Patterns

### Mevcut Proje Yapısı (Phase 13 ilgili kısımlar)
```
android/app/src/main/java/com/tonbil/aifirewall/
├── feature/
│   ├── notifications/        # PushNotificationsScreen + ViewModel — MEVCUT
│   ├── chat/                 # ChatScreen + ViewModel — MEVCUT, CHAT-03 eksik
│   ├── telegram/             # TelegramScreen + ViewModel — MEVCUT, tam fonksiyonel
│   ├── wifi/                 # WifiScreen + ViewModel — MEVCUT, tam fonksiyonel
│   ├── dhcp/                 # DhcpScreen + ViewModel — MEVCUT, tam fonksiyonel
│   └── securitysettings/     # SecuritySettingsScreen + ViewModel — MEVCUT
├── data/remote/dto/
│   ├── PushDtos.kt           # PushTokenDto, PushChannelDto — MEVCUT
│   └── SecurityConfigDtos.kt # SecurityConfigDto, SecurityConfigUpdateDto — MEVCUT
├── di/AppModule.kt           # Tüm ViewModel'lar kayıtlı — MEVCUT
└── ui/navigation/AppNavHost.kt  # Tüm rotalar bağlı — MEVCUT
```

### Pattern 1: FCM Token Kayıt Akışı
**What:** Uygulama açıldığında FCM token alınır, backend'e kaydedilir
**When to use:** NOTIF-01/02 için
**Example:**
```kotlin
// FirebaseMessagingService override
class TonbilFirebaseService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        // Koin ile HttpClient inject edilemez, coroutine scope gerekir
        CoroutineScope(Dispatchers.IO).launch {
            // POST /push/register {token, platform: "android", device_name: Build.MODEL}
        }
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        // Mesajı Android bildirim olarak göster
        val channelId = remoteMessage.data["channel"] ?: "system_notifications"
        showNotification(channelId, remoteMessage.notification?.title, remoteMessage.notification?.body)
    }
}
```

### Pattern 2: Android Bildirim Kanalları (NOTIF-03)
**What:** Android 8+ için NotificationChannel oluşturma — Application sınıfında yapılmalı
**When to use:** Uygulama ilk çalıştığında, kanallar yeniden oluşturmak idempotent
```kotlin
// Application.onCreate() içinde
class TonbilApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        createNotificationChannels()
        startKoin { ... }
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channels = listOf(
                NotificationChannel("security_threats", "Tehdit Bildirimleri", IMPORTANCE_HIGH),
                NotificationChannel("device_events", "Cihaz Bildirimleri", IMPORTANCE_DEFAULT),
                NotificationChannel("traffic_alerts", "Trafik Uyarilari", IMPORTANCE_DEFAULT),
                NotificationChannel("system_notifications", "Sistem", IMPORTANCE_LOW),
            )
            val manager = getSystemService(NotificationManager::class.java)
            channels.forEach { manager.createNotificationChannel(it) }
        }
    }
}
```

### Pattern 3: ChatBubble Yapılandırılmış Yanıt (CHAT-03)
**What:** AI yanıtındaki JSON/tablo içeriğini ayrıştırıp görsel olarak render etmek
**When to use:** `message.role == "assistant"` ve içerik `{` ile başlıyor veya `|` tablo formatı içeriyorsa
```kotlin
@Composable
private fun AssistantMessageContent(content: String) {
    when {
        content.trimStart().startsWith("{") || content.trimStart().startsWith("[") -> {
            // JSON → key-value liste
            JsonContentBlock(content)
        }
        content.contains("| ") && content.contains("\n|") -> {
            // Markdown tablo → LazyColumn table
            TableContentBlock(content)
        }
        else -> Text(content, color = TextPrimary, fontSize = 13.sp)
    }
}
```

### Anti-Patterns to Avoid
- **FirebaseApp.initializeApp() manuel çağrısı:** `google-services` plugin varsa otomatik yapılır, çift çağrı hata verir
- **FCM token'ı Application scope'ta sync çağrıyla alma:** `FirebaseMessaging.getInstance().token` suspend değil, `.await()` ile coroutine içinde kullan
- **NotificationChannel'ı Activity'de oluşturma:** Application sınıfında bir kere oluşturmak yeterli; Activity her açılışta tekrar çalışır
- **Koin inject FirebaseMessagingService içinde:** `FirebaseMessagingService` Android lifecycle dışında yaratılır, `KoinComponent` implement et
- **google-services.json olmadan FCM build:** Build-time hata verir; placeholder dosya veya `FirebaseOptions` ile programmatic init gerekir

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Android push bildirim gönderme | Custom HTTP long-polling | Firebase Cloud Messaging | Battery optimizer, doze mode, Doze exceptions, WakeLock yönetimi çok karmaşık |
| Token yenileme | Manuel token takibi | FCM SDK `onNewToken` callback | FCM token TTL yönetimi platform sorumluluğu |
| JSON parse mesajda | Regex string manipulation | `kotlinx.serialization` + try/catch | Edge case'ler çok |
| Bildirim kanalı görünürlüğü | Custom Settings UI | `Settings.ACTION_APP_NOTIFICATION_SETTINGS` intent | System UI standart davranış bekler |

**Key insight:** FCM ile ilgili tüm platform özellikleri (Doze, background restrictions, token rotation) Firebase SDK tarafından yönetilir. Kendin yazmak Android batarya optimizasyonuna takılır.

## Common Pitfalls

### Pitfall 1: google-services.json olmadan FCM
**What goes wrong:** `FirebaseApp` init sırasında `IllegalStateException` veya build hatası
**Why it happens:** `google-services` Gradle plugin JSON dosyasını arar
**How to avoid:** Firebase Console'dan `google-services.json` indir, `android/app/` dizinine koy
**Warning signs:** `Default FirebaseApp is not initialized` runtime hatası

### Pitfall 2: FCM token backend'e kaydedilmiyor
**What goes wrong:** Backend `push.py` `register` endpoint placeholder — gerçek kayıt yok
**Why it happens:** Mevcut kodda `PushRegistrationResponseDto(success=True)` ama token kaydedilmiyor
**How to avoid:** Backend'e FCM token saklama ve dispatch mekanizması eklemek gerekiyor. Pi'den Firebase Admin SDK ile push gönderilebilir VEYA WebSocket events yeterli kabul edilebilir (uygulama açıkken)
**Warning signs:** `register` endpoint çağrılıyor ama bildirim gelmiyor

### Pitfall 3: ChatViewModel SecurityRepository bağımlılığı
**What goes wrong:** `ChatViewModel` `SecurityRepository` bekliyor; `sendChat` ve `getChatHistory` metotları bu repository'de
**Why it happens:** Mevcut DI konfigürasyonunda `viewModelOf(::ChatViewModel)` kullanılıyor ama `ChatViewModel(private val repo: SecurityRepository)` constructor imzası var
**How to avoid:** AppModule'daki `viewModelOf(::ChatViewModel)` satırı doğru çalışıyor, SecurityRepository zaten single olarak kayıtlı. CHAT-03 için sadece UI katmanı değişecek.
**Warning signs:** `ChatViewModel` koin inject hatası → constructor imzasını kontrol et

### Pitfall 4: DHCP static lease silme MAC format
**What goes wrong:** `dhcpStaticLeaseDelete(mac)` URL path'te MAC adresi var; `:` karakterleri URL encode sorununa yol açar
**Why it happens:** MAC `AA:BB:CC:DD:EE:FF` path segment olarak decode sorunu
**How to avoid:** Backend endpoint'ini kontrol et — `linux_dhcp_driver.py`'de MAC normalize ediliyorsa Ktor ile doğru iletilir; gerekirse `encodeURLPathPart(mac)` kullan
**Warning signs:** 404 veya backend'de MAC bulunamıyor hatası

### Pitfall 5: SecuritySettings Slider tam sayı alanları
**What goes wrong:** `Slider` float değer döndürür, backend Int bekler
**Why it happens:** Compose `Slider` `value: Float` kullanır
**How to avoid:** `onValueChange = { value -> viewModel.updateThreshold(value.roundToInt()) }` kullan
**Warning signs:** Backend 422 validation error

## Code Examples

Verified patterns from official sources:

### FCM Token Alma (Kotlin Coroutines)
```kotlin
// Source: Firebase Android SDK docs
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.tasks.await

suspend fun getFcmToken(): String? {
    return try {
        FirebaseMessaging.getInstance().token.await()
    } catch (e: Exception) {
        null
    }
}
```

### PushNotificationsViewModel — FCM Token Kayıt Entegrasyonu
```kotlin
// Mevcut ViewModel'a eklenecek — uygulama açılışında çağrılacak
fun initFcmToken(context: Context) {
    viewModelScope.launch {
        try {
            val token = FirebaseMessaging.getInstance().token.await()
            registerToken(token, Build.MODEL)
        } catch (e: Exception) {
            // FCM yoksa veya google-services.json yoksa sessizce geç
        }
    }
}
```

### ChatBubble — Yapılandırılmış Yanıt Tespiti
```kotlin
// Mevcut ChatBubble içine eklenecek
@Composable
private fun ChatMessageContent(content: String, isUser: Boolean) {
    if (!isUser && content.trimStart().startsWith("[") || content.contains("| ---")) {
        // Yapılandırılmış veri — ayrı render
        StructuredResponseView(content)
    } else {
        Text(
            text = content,
            color = if (isUser) NeonCyan else TextPrimary,
            fontSize = 13.sp,
            lineHeight = 18.sp,
        )
    }
}
```

### Backend SecurityRepository — sendChat ve getChatHistory
```kotlin
// Mevcut SecurityRepository'deki metotlar (değişiklik gerekmez)
// GET /chat/history → List<ChatMessageDto>
// POST /chat/send {message: String} → ChatResponseDto {reply: String}
// DELETE /chat/history → success
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Firebase legacy SDK | Firebase BOM 33+ | 2024 | `firebase-bom` sürüm yönetimi; `ktx` uzantıları zorunlu |
| `FirebaseInstanceId` | `FirebaseMessaging.getInstance().token` | Firebase SDK 21+ | `getInstanceId()` deprecated |
| Notification compat builder her yerde | NotificationChannel + channelId | Android 8.0 (API 26) | API 26+ için channelId zorunlu, yoksa bildirim gösterilmez |

**Deprecated/outdated:**
- `FirebaseInstanceId.getInstance().instanceId`: Kaldırıldı — `FirebaseMessaging.getInstance().token.await()` kullan
- `NotificationCompat.Builder` channelId olmadan: API 26+ sessizce yok sayılır

## Open Questions

1. **FCM için google-services.json mevcut mu?**
   - What we know: Proje Firebase Console'a kayıtlı değil; `push.py` placeholder
   - What's unclear: Gerçek FCM dispatch Pi'den yapılacak mı yoksa WebSocket yeterli mi sayılacak?
   - Recommendation: Mevcut WebSocket security events zaten `NotificationHelper` üzerinden sistem bildirimleri gösteriyor (Quick 29). FCM tam entegrasyonu olmadan NOTIF-01/02 kısmen karşılanabilir. `google-services.json` yoksa FCM skip edilip WebSocket bildirimleri yeterli sayılabilir.

2. **CHAT-03 yapılandırılmış format ne kadar karmaşık?**
   - What we know: Backend `chat_formatter.py` servisi var; AI yanıtları markdown veya JSON içerebilir
   - What's unclear: Hangi format tipleri destekleniyor? Tablo, JSON, kod bloğu?
   - Recommendation: Basit string analizi yeterli — `|` tablo satırı, `{` JSON başlangıcı, ` ``` ` kod bloğu detect et. Tam markdown renderer ekleme gerek yok.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Manuel test (Android APK) — birim testi yok |
| Config file | none |
| Quick run command | `./gradlew assembleDebug` |
| Full suite command | `./gradlew assembleDebug` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOTIF-01 | FCM token backend'e kaydedilir | smoke | `./gradlew assembleDebug` + manuel Pi log | ❌ Wave 0 |
| NOTIF-02 | DDoS alarmı geldiğinde bildirim görünür | manual | Manuel — Pi event tetikle | N/A |
| NOTIF-03 | 4 kanal Android Ayarlar'da görünür | manual | Manuel — telefon Ayarlar > Bildirimler | N/A |
| NOTIF-04 | Kanal toggle ekranda çalışır | smoke | `./gradlew assembleDebug` + UI test | ❌ Wave 0 |
| CHAT-01 | Mesaj gönderilir, yanıt gelir | smoke | `./gradlew assembleDebug` + manuel test | ❌ Wave 0 |
| CHAT-02 | Sohbet geçmişi yüklenir | smoke | `./gradlew assembleDebug` + manuel test | ❌ Wave 0 |
| CHAT-03 | JSON/tablo yanıtlar görsel gösterilir | manual | Manuel — AI'ye yapılandırılmış soru sor | N/A |
| TELE-01 | Token/chat ID kaydedilir | smoke | `./gradlew assembleDebug` + Pi log | ❌ Wave 0 |
| TELE-02 | Telegram bildirim toggle çalışır | smoke | `./gradlew assembleDebug` + Pi Telegram | ❌ Wave 0 |
| WIFI-01 | WiFi durumu ekranda görünür | smoke | `./gradlew assembleDebug` + Pi wifi status | ❌ Wave 0 |
| WIFI-02 | SSID/kanal değiştirilebilir | manual | Manuel — edit + save + Pi kontrol | N/A |
| WIFI-03 | AP açma/kapama çalışır | manual | Manuel — toggle + Pi hostapd kontrol | N/A |
| DHCP-01 | DHCP havuz bilgileri görünür | smoke | `./gradlew assembleDebug` + Pi dhcp status | ❌ Wave 0 |
| DHCP-02 | Statik lease ekle/sil çalışır | manual | Manuel — dialog + Pi dnsmasq kontrol | N/A |
| SEC-01 | Ayarlar ekranı yüklenir | smoke | `./gradlew assembleDebug` + Pi /security/config | ❌ Wave 0 |
| SEC-02 | Ayar değişikliği kaydedilir | manual | Manuel — değer değiştir + Pi reload | N/A |

### Sampling Rate
- **Per task commit:** `./gradlew assembleDebug` (APK üretimi)
- **Per wave merge:** `./gradlew assembleDebug` + Pi'ye deploy + temel akış testi
- **Phase gate:** Tüm smoke testler green, manuel testler Pi'de doğrulanmış

### Wave 0 Gaps
- [ ] FCM entegrasyonu için `google-services.json` — Firebase Console karar gerekiyor
- [ ] `TonbilApplication.kt` — `NotificationChannel` oluşturma (uygulama sınıfı eksik veya kanallar eklenmemiş)
- [ ] `FirebaseMessagingService` subclass — `onNewToken` + `onMessageReceived` handler

*(Mevcut test altyapısı yok — Android projesi sadece build + manuel test ile doğrulanıyor)*

## Sources

### Primary (HIGH confidence)
- Kaynak kodu doğrudan incelendi: `android/app/src/main/java/com/tonbil/aifirewall/` (134 .kt dosyası)
- Backend API: `backend/app/api/v1/push.py`, `chat.py`, `telegram.py`, `wifi.py`, `dhcp.py`, `security_settings.py`
- `AppNavHost.kt` — tüm rotaların bağlı olduğu doğrulandı
- `AppModule.kt` — tüm ViewModel'ların Koin'e kayıtlı olduğu doğrulandı

### Secondary (MEDIUM confidence)
- Firebase Android SDK patterns — genel FCM entegrasyon akışı (training data, 2024 itibariyle stabil)

### Tertiary (LOW confidence)
- FCM tam entegrasyonu için `google-services.json` gereksinimi — Firebase Console durumu bilinmiyor

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — mevcut proje bağımlılıkları doğrudan okundu
- Architecture: HIGH — tüm ekranlar ve ViewModel'lar kaynak koddan doğrulandı
- Pitfalls: HIGH — mevcut kodun analizi ile tespit edildi; FCM kısmı MEDIUM (Firebase docs)

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (kararlı stack, 30 gün)

---

## Kritik Özet: Mevcut Durum Analizi

### Zaten Tamamlanmış (dokunmak gerekmez)
- `TelegramScreen` + `TelegramViewModel` — TELE-01, TELE-02 tam karşılanıyor
- `WifiScreen` + `WifiViewModel` — WIFI-01, WIFI-02, WIFI-03 tam karşılanıyor
- `DhcpScreen` + `DhcpViewModel` — DHCP-01, DHCP-02 tam karşılanıyor
- `SecuritySettingsScreen` + `SecuritySettingsViewModel` — SEC-01, SEC-02 tam karşılanıyor
- `ChatScreen` + `ChatViewModel` — CHAT-01, CHAT-02 karşılanıyor
- `PushNotificationsScreen` + kanal toggle — NOTIF-04 karşılanıyor
- `AppNavHost` — tüm rotalar bağlı
- `AppModule` — tüm ViewModel'lar Koin'e kayıtlı

### Eksik / Tamamlanması Gereken
| Eksiklik | İlgili Req | Tahmini İş |
|----------|-----------|------------|
| FCM `NotificationChannel` oluşturma (Application sınıfı) | NOTIF-03 | Küçük |
| FCM `FirebaseMessagingService` subclass | NOTIF-01, NOTIF-03 | Orta (google-services.json gerekiyor) |
| Backend FCM token kayıt (gerçek, placeholder değil) | NOTIF-01, NOTIF-02 | Orta |
| `ChatBubble` yapılandırılmış yanıt render | CHAT-03 | Küçük-Orta |

### Plan Önerisi
Bu faz için **1 plan** yeterli:
- **Plan 13-01:** NOTIF (FCM altyapısı + kanallar) + CHAT-03 (yapılandırılmış yanıt) — diğer ekranlar zaten tamamlandığı için doğrulama + varsa ince ayar
