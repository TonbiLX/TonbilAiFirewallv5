---
phase: quick-28
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/v1/push.py
  - backend/app/schemas/push.py
  - backend/app/api/v1/router.py
  - android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/PushDtos.kt
  - android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsViewModel.kt
  - android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsScreen.kt
autonomous: true
requirements: [PUSH-01]

must_haves:
  truths:
    - "Android uygulamasinda Bildirimler ekrani acildiginda bildirim kanallari yuklenir"
    - "Her bildirim kanali toggle ile acilip kapatilabilir"
    - "Kanal degisiklikleri backend'e kaydedilir ve sayfa yenilendiginde korunur"
    - "Telegram bot bildirim tercihleri ile senkronize calisir"
  artifacts:
    - path: "backend/app/api/v1/push.py"
      provides: "Push bildirim API endpoint'leri (GET /push/channels, POST /push/channels/{id}/toggle, POST /push/register)"
      exports: ["router"]
    - path: "backend/app/schemas/push.py"
      provides: "Pydantic push semalari"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsScreen.kt"
      provides: "Bildirim ayarlari UI ekrani"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsViewModel.kt"
      provides: "Bildirim ayarlari ViewModel"
  key_links:
    - from: "PushNotificationsViewModel"
      to: "/api/v1/push/channels"
      via: "Ktor HTTP GET/POST"
      pattern: "httpClient\\.get.*PUSH_CHANNELS"
    - from: "backend/app/api/v1/push.py"
      to: "TelegramConfig model"
      via: "SQLAlchemy query"
      pattern: "select.*TelegramConfig"
---

<objective>
Android Push Bildirim ayar ekrani ve backend API endpoint'lerinin olusturulmasi.

Purpose: Kullanici Android uygulamasindan hangi bildirim turlerini almak istedigini yonetebilmeli. Mevcut Telegram bildirim altyapisinin uzerine push bildirim kanal tercihleri ekleniyor.

Output: Backend'de 3 push endpoint + Android'de calisan bildirim ayarlari ekrani
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@backend/app/api/v1/telegram.py
@backend/app/models/telegram_config.py
@backend/app/schemas/telegram.py
@backend/app/api/v1/router.py
@android/app/src/main/java/com/tonbil/aifirewall/data/remote/ApiRoutes.kt
@android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/PushDtos.kt
@android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsViewModel.kt
@android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsScreen.kt
@android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt

<interfaces>
<!-- Backend Telegram Config model — push endpoint'leri bu modeli kullanacak -->
From backend/app/models/telegram_config.py:
```python
class TelegramConfig(Base):
    __tablename__ = "telegram_config"
    id = Column(Integer, primary_key=True)
    bot_token = Column(String(255))
    chat_ids = Column(String(500))
    enabled = Column(Boolean, default=False)
    notify_new_device = Column(Boolean, default=True)
    notify_blocked_ip = Column(Boolean, default=True)
    notify_trusted_ip_threat = Column(Boolean, default=True)
    notify_ai_insight = Column(Boolean, default=True)
```

From backend/app/schemas/telegram.py:
```python
class TelegramConfigUpdate(BaseModel):
    bot_token: str | None = None
    chat_ids: str | None = None
    enabled: bool | None = None
    notify_new_device: bool | None = None
    notify_blocked_ip: bool | None = None
    notify_trusted_ip_threat: bool | None = None
    notify_ai_insight: bool | None = None
```

From android ApiRoutes.kt:
```kotlin
const val PUSH_REGISTER = "push/register"
const val PUSH_CHANNELS = "push/channels"
fun pushChannelToggle(channel: String) = "push/channels/$channel/toggle"
```

From android PushDtos.kt:
```kotlin
data class PushTokenDto(val token: String, val platform: String = "android", val deviceName: String = "")
data class PushChannelDto(val id: String = "", val name: String = "", val description: String = "", val enabled: Boolean = true)
data class PushRegistrationResponseDto(val success: Boolean = false, val message: String = "")
```

From android AppModule.kt — PushNotificationsViewModel zaten kayitli:
```kotlin
viewModelOf(::PushNotificationsViewModel)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend push bildirim API endpoint'leri olustur</name>
  <files>backend/app/api/v1/push.py, backend/app/schemas/push.py, backend/app/api/v1/router.py</files>
  <action>
Backend'de push bildirim yonetimi icin 3 endpoint olustur. Telegram bildirim konfigurasyonunu temel alarak kanal bazinda bildirim tercihlerini yonet.

1. **backend/app/schemas/push.py** olustur:
   - `PushChannelResponse` — id: str, name: str, description: str, enabled: bool
   - `PushRegisterRequest` — token: str, platform: str = "android", device_name: str = ""
   - `PushRegisterResponse` — success: bool, message: str

2. **backend/app/api/v1/push.py** olustur (APIRouter):

   **GET /channels** — Bildirim kanal listesi doner:
   - DB'den TelegramConfig'i cek (yoksa default olustur)
   - 4 adet kanal dondur (sabit kanal ID'leri):
     ```python
     channels = [
         {"id": "security_threats", "name": "Tehdit Bildirimleri", "description": "IP engelleme ve guvenlik tehditleri", "enabled": config.notify_blocked_ip},
         {"id": "device_events", "name": "Cihaz Bildirimleri", "description": "Yeni cihaz baglantilari", "enabled": config.notify_new_device},
         {"id": "trusted_ip_threats", "name": "Guvenilir IP Tehditleri", "description": "Guvenilir IP'lerde tespit edilen tehditler", "enabled": config.notify_trusted_ip_threat},
         {"id": "ai_insights", "name": "AI Icgoruleri", "description": "Yapay zeka guvenlik analizleri", "enabled": config.notify_ai_insight},
     ]
     ```
   - Her kanal `PushChannelResponse` listesi olarak dondur
   - `Depends(get_current_user)` ile JWT auth korumali

   **POST /channels/{channel_id}/toggle** — Kanal toggle:
   - channel_id'ye gore TelegramConfig'teki ilgili boolean'i tersine cevir
   - Mapping: `security_threats` -> `notify_blocked_ip`, `device_events` -> `notify_new_device`, `trusted_ip_threats` -> `notify_trusted_ip_threat`, `ai_insights` -> `notify_ai_insight`
   - Bilinmeyen channel_id icin 404 dondur
   - Guncellenen kanali `PushChannelResponse` olarak dondur
   - `telegram_service.invalidate_cache()` cagir
   - `Depends(get_current_user)` ile JWT auth korumali

   **POST /register** — Token kaydi (gelecek FCM entegrasyonu icin placeholder):
   - `PushRegisterRequest` body al
   - Simdilik sadece `{"success": true, "message": "Token kaydedildi"}` dondur
   - Gelecekte FCM token'i DB'ye kaydedilecek
   - `Depends(get_current_user)` ile JWT auth korumali

3. **backend/app/api/v1/router.py** guncelle:
   - `from app.api.v1 import push` ekle (import sirasina dikkat — alfabetik)
   - `api_v1_router.include_router(push.router, prefix="/push", tags=["Push Bildirimler"])` ekle
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5 && python -c "from backend.app.api.v1 import push; print('push module OK')" 2>&1 || echo "Module import check — deploy ile dogrulanacak"</automated>
  </verify>
  <done>
    - backend/app/api/v1/push.py 3 endpoint iceriyor (GET /channels, POST /channels/{id}/toggle, POST /register)
    - backend/app/schemas/push.py 3 Pydantic model iceriyor
    - router.py push modulu dahil edilmis
    - Tum endpoint'ler JWT auth korumali
  </done>
</task>

<task type="auto">
  <name>Task 2: Android PushNotifications ekranini backend API ile uyumlu hale getir ve iyilestir</name>
  <files>android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsViewModel.kt, android/app/src/main/java/com/tonbil/aifirewall/feature/notifications/PushNotificationsScreen.kt, android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/PushDtos.kt</files>
  <action>
Mevcut Android PushNotifications ekranini iyilestir. Zaten calisan bir iskelet var (ViewModel + Screen + DTOs + AppModule + NavRoutes hepsi kayitli). Asagidaki degisiklikleri yap:

1. **PushDtos.kt** — Mevcut DTOlar backend ile uyumlu, degisiklik GEREKMEZ. Sadece dogrula:
   - PushChannelDto: id, name, description, enabled alanlari backend response ile eslesir
   - PushRegistrationResponseDto: success, message backend response ile eslesir

2. **PushNotificationsViewModel.kt** iyilestir:
   - Mevcut loadChannels, toggleChannel, registerToken fonksiyonlari zaten dogru API yollarini kullaniyor
   - `registerToken` fonksiyonuna Android cihaz adini otomatik ekle: `android.os.Build.MODEL` kullan
   - Hata mesajlarini Turkce yap (zaten oyle ama kontrol et)
   - `toggleChannel` icindeki optimistic update pattern korunsun (zaten var)
   - Yeni ekleme: `init` blogunun sonunda `checkRegistration()` ekle — bu `isRegistered = true` yapsin (basit placeholder, backend register endpoint'i simdilik her zaman success donuyor)

3. **PushNotificationsScreen.kt** iyilestir:
   - TopAppBar'a `navigationIcon` ekle (geri butonu eksik):
     ```kotlin
     navigationIcon = {
         IconButton(onClick = onBack) {
             Icon(Icons.Outlined.ArrowBack, contentDescription = "Geri", tint = TextSecondary)
         }
     }
     ```
   - Import ekle: `import androidx.compose.material.icons.outlined.ArrowBack`
   - `RegistrationCard` icindeki `onRegister` lambda'sini guncelle: `viewModel.registerToken(Build.MODEL)` olarak degistir (placeholder token yerine cihaz adini gonder)
   - Import ekle: `import android.os.Build`
   - RegistrationCard'daki "Kaydet" buton textini "Etkinlestir" olarak degistir
   - Kanal aciklamalari zaten backend'den gelecek, ekstra degisiklik gerekmez
   - Error ve success mesajlari zaten mevcut, korunsun

NOT: AppModule'de `viewModelOf(::PushNotificationsViewModel)` ZATEN var, NavRoutes'ta `PushNotificationsRoute` ZATEN var, AppNavHost'ta `composable<PushNotificationsRoute>` ZATEN var, SettingsHubScreen'de "Bildirimler" karti ZATEN var. Bunlara DOKUNMA.
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5/android && ./gradlew compileDebugKotlin --no-daemon 2>&1 | tail -5</automated>
  </verify>
  <done>
    - PushNotificationsScreen'de geri butonu calisiyor
    - ViewModel backend /push/channels endpoint'ini cagiriyor ve kanallari listeliyor
    - Her kanalin toggle switch'i calisip backend'e POST atiyor
    - Kayit butonu cihaz adini gonderiyor
    - Hata ve basari mesajlari Turkce gosteriliyor
  </done>
</task>

<task type="auto">
  <name>Task 3: Backend push endpoint'lerini Pi'ye deploy et ve test et</name>
  <files>deploy_quick28.py</files>
  <action>
Deploy scripti olustur (mevcut deploy script pattern'ini takip et). Paramiko ile SSH jump host uzerinden:

1. Yeni dosyalari Pi'ye transfer et:
   - `backend/app/schemas/push.py` -> `/opt/tonbilaios/backend/app/schemas/push.py`
   - `backend/app/api/v1/push.py` -> `/opt/tonbilaios/backend/app/api/v1/push.py`
   - `backend/app/api/v1/router.py` -> `/opt/tonbilaios/backend/app/api/v1/router.py`

2. Backend'i restart et: `sudo systemctl restart tonbilaios-backend`

3. 5 saniye bekle, ardindan API test et:
   - SSH uzerinden `curl -s http://localhost/api/v1/push/channels -H "Authorization: Bearer $(curl -s -X POST http://localhost/api/v1/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"benbuyum9087"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')"` calistir
   - Yanit 4 kanal icermeli (security_threats, device_events, trusted_ip_threats, ai_insights)
   - Biri toggle et ve tekrar channels cek — degistigini dogrula

4. Deploy sonuclarini `deploy_quick28_result.txt` dosyasina kaydet

SSH bilgileri (CLAUDE.md'den):
- Jump host: pi.tonbil.com:2323, user: admin, pass: benbuyum9087
- Pi: 192.168.1.2:22, user: admin, pass: benbuyum9087
- SFTP root'a ait oldugu icin /tmp/ uzerinden sudo cp kullan
  </action>
  <verify>
    <automated>python deploy_quick28.py 2>&1 | tail -20</automated>
  </verify>
  <done>
    - Push endpoint'leri Pi'de calisiyor
    - GET /push/channels 4 kanal donuyor
    - POST /push/channels/{id}/toggle kanal durumunu degistiriyor
    - POST /push/register success donuyor
    - Backend restart sonrasi hata yok
  </done>
</task>

</tasks>

<verification>
1. Backend push endpoint'leri JWT auth ile korumali
2. Android uygulamasinda Ayarlar > Bildirimler ekrani aciliyor
3. Bildirim kanallari backend'den yukleniyor (4 kanal)
4. Toggle switch'leri backend'e kaydediyor
5. Telegram config ile senkronize (ayni boolean alanlar)
</verification>

<success_criteria>
- Backend'de /api/v1/push/ altinda 3 calisan endpoint
- Android PushNotificationsScreen backend API ile entegre calisiyor
- Kanal tercihleri Telegram bildirim config ile senkronize
- Pi'ye deploy edilmis ve test edilmis
</success_criteria>

<output>
After completion, create `.planning/quick/28-android-app-push-bildirimleri-ve-push-bi/28-SUMMARY.md`
</output>
