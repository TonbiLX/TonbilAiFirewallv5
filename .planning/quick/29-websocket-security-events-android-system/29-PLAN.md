---
phase: quick-29
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/v1/ws.py
  - backend/app/services/telegram_service.py
  - backend/app/api/v1/push.py
  - android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/WebSocketDto.kt
  - android/app/src/main/java/com/tonbil/aifirewall/data/remote/WebSocketManager.kt
  - android/app/src/main/java/com/tonbil/aifirewall/util/NotificationHelper.kt
  - android/app/src/main/java/com/tonbil/aifirewall/TonbilApp.kt
  - android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt
autonomous: true
requirements: [QUICK-29]
must_haves:
  truths:
    - "Backend guvenlik olaylari (DDoS, yeni cihaz, IP engelleme, AI insight) WebSocket uzerinden tum bagli istemcilere broadcast ediliyor"
    - "Android uygulama WS security_event mesajlarini parse edip sistem bildirimi (NotificationManager) olarak gosteriyor"
    - "Test endpoint POST /api/v1/push/test-notification ile sahte guvenlik olayi tetiklenebiliyor"
  artifacts:
    - path: "backend/app/api/v1/ws.py"
      provides: "broadcast_security_event() fonksiyonu"
      contains: "broadcast_security_event"
    - path: "backend/app/services/telegram_service.py"
      provides: "Her bildirim fonksiyonundan WS broadcast hook"
      contains: "broadcast_security_event"
    - path: "backend/app/api/v1/push.py"
      provides: "POST /api/v1/push/test-notification endpoint"
      contains: "test-notification"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/WebSocketDto.kt"
      provides: "SecurityEventDto data class"
      contains: "SecurityEventDto"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/data/remote/WebSocketManager.kt"
      provides: "securityEvents SharedFlow"
      contains: "securityEvents"
    - path: "android/app/src/main/java/com/tonbil/aifirewall/util/NotificationHelper.kt"
      provides: "NotificationChannel olusturma + bildirim gosterme"
      contains: "showSecurityNotification"
  key_links:
    - from: "backend/app/services/telegram_service.py"
      to: "backend/app/api/v1/ws.py"
      via: "broadcast_security_event() import and call"
      pattern: "broadcast_security_event"
    - from: "android WebSocketManager"
      to: "android NotificationHelper"
      via: "securityEvents flow collect -> showSecurityNotification"
      pattern: "securityEvents"
---

<objective>
WebSocket uzerinden Android'e gercek zamanli guvenlik bildirimi sistemi.

Purpose: Mevcut Telegram bildirim altyapisina paralel olarak, WebSocket bagli tum istemcilere (ozellikle Android uygulamaya) anlik guvenlik olaylari gondermek. Android tarafinda bu olaylar sistem bildirimi (NotificationManager) olarak gosterilecek.

Output: Backend broadcast fonksiyonu + Telegram hook'lari + test endpoint + Android SecurityEventDto + NotificationHelper + WS entegrasyonu
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@backend/app/api/v1/ws.py
@backend/app/services/telegram_service.py
@backend/app/api/v1/push.py
@android/app/src/main/java/com/tonbil/aifirewall/data/remote/WebSocketManager.kt
@android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/WebSocketDto.kt
@android/app/src/main/java/com/tonbil/aifirewall/TonbilApp.kt
@android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt
@android/app/src/main/AndroidManifest.xml

<interfaces>
<!-- Backend: ws.py ConnectionManager (broadcast hedefi) -->
class ConnectionManager:
    active_connections: list[WebSocket]
    async connect(websocket, client_ip) -> bool
    disconnect(websocket, client_ip)

manager = ConnectionManager()  # module-level singleton

<!-- Backend: telegram_service.py bildirim fonksiyonlari (hook noktasi) -->
async def notify_new_device(ip, hostname, manufacturer, device_type, detected_os)
async def notify_ip_blocked(ip, reason)
async def notify_trusted_ip_threat(ip, reason)
async def notify_ai_insight(severity, message, category)
# DDoS: ddos_service.py -> _send_ddos_telegram_alert(alerts) icinde notify_ai_insight cagrilir

<!-- Android: WebSocketManager (genisletme noktasi) -->
class WebSocketManager(client, serverDiscovery, tokenManager, networkMonitor):
    val messages: SharedFlow<RealtimeUpdateDto>  # mevcut realtime_update akisi
    val connectionState: StateFlow<WebSocketState>
    # incoming frame loop: sadece type=="realtime_update" parse ediliyor

<!-- Android: WebSocketDto.kt (yeni DTO eklenecek) -->
@Serializable data class RealtimeUpdateDto(type, deviceCount, devices, dns, bandwidth, vpn, vpnClient)

<!-- Android: Manifest POST_NOTIFICATIONS permission zaten mevcut -->
<!-- Android: TonbilApp.kt -> startKoin { modules(appModule, featureModules) } -->
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend - WS security event broadcast + Telegram hook + test endpoint</name>
  <files>
    backend/app/api/v1/ws.py
    backend/app/services/telegram_service.py
    backend/app/api/v1/push.py
  </files>
  <action>
**ws.py - broadcast_security_event() fonksiyonu ekle:**

`manager` singleton'u kullanarak `broadcast_security_event()` async fonksiyonu ekle (modul seviyesinde, ConnectionManager disinda):

```python
async def broadcast_security_event(
    event_type: str,       # "ddos_attack" | "new_device" | "ip_blocked" | "trusted_ip_threat" | "ai_insight"
    severity: str,         # "info" | "warning" | "critical"
    title: str,
    message: str,
    data: dict | None = None,
):
    """Tum bagli WS istemcilerine guvenlik olayi broadcast et."""
    if not manager.active_connections:
        return
    payload = json.dumps({
        "type": "security_event",
        "event_type": event_type,
        "severity": severity,
        "title": title,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "data": data or {},
    })
    disconnected = []
    for ws in manager.active_connections[:]:  # copy to avoid mutation during iteration
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        manager.disconnect(ws)
```

`datetime` import'u zaten mevcut (line 9). `json` import'u zaten mevcut (line 2).

**telegram_service.py - Her bildirim fonksiyonuna WS broadcast hook ekle:**

Her bildirim fonksiyonunun SONUNA (Telegram mesaji gonderdikten sonra) WS broadcast cagrisini ekle. Import lazy yapilacak (circular import onleme):

`notify_new_device()` sonuna (line 146 `await send_message(text)` SONRASINA):
```python
    try:
        from app.api.v1.ws import broadcast_security_event
        await broadcast_security_event(
            event_type="new_device",
            severity="info",
            title="Yeni Cihaz Algilandi",
            message=f"{hostname or 'Bilinmiyor'} ({ip})",
            data={"ip": ip, "hostname": hostname, "manufacturer": manufacturer},
        )
    except Exception:
        pass
```

`notify_ip_blocked()` sonuna (line 165 sonrasina):
```python
    try:
        from app.api.v1.ws import broadcast_security_event
        await broadcast_security_event(
            event_type="ip_blocked",
            severity="critical",
            title="IP Engellendi",
            message=f"{ip} - {reason or 'Bilinmiyor'}",
            data={"ip": ip, "reason": reason},
        )
    except Exception:
        pass
```

`notify_trusted_ip_threat()` sonuna (line 187 sonrasina):
```python
    try:
        from app.api.v1.ws import broadcast_security_event
        await broadcast_security_event(
            event_type="trusted_ip_threat",
            severity="warning",
            title="Guvenilir IP Tehdit Uyarisi",
            message=f"{ip} - {reason}",
            data={"ip": ip, "reason": reason},
        )
    except Exception:
        pass
```

`notify_ai_insight()` sonuna (line 268 sonrasina):
```python
    try:
        from app.api.v1.ws import broadcast_security_event
        await broadcast_security_event(
            event_type="ai_insight",
            severity=severity,
            title=f"AI Uyari ({severity.upper()})",
            message=message,
            data={"category": category},
        )
    except Exception:
        pass
```

NOT: DDoS uyarilari zaten `notify_ai_insight()` uzerinden geciyor (`_send_ddos_telegram_alert` -> `notify_ai_insight`), ayrica hook gerekmez.

NOT: `notify_device_isolation_suggestion()` ve `notify_hourly_summary()` daha az kritik, bunlara hook eklenmeyecek (scope kucuk tutmak icin).

NOT: Her hook try/except icinde — WS hatasi Telegram bildirimini ASLA engellemeyecek.

**push.py - Test endpoint ekle:**

Dosyanin sonuna yeni endpoint ekle:

```python
from pydantic import BaseModel

class TestNotificationRequest(BaseModel):
    event_type: str = "ip_blocked"
    severity: str = "critical"
    title: str = "Test Bildirimi"
    message: str = "Bu bir test guvenlik bildirimidir"

@router.post("/test-notification")
async def test_notification(
    data: TestNotificationRequest | None = None,
    current_user: User = Depends(get_current_user),
):
    """Test amacli sahte guvenlik olayi gonderer. Tum WS istemcilerine broadcast eder."""
    from app.api.v1.ws import broadcast_security_event
    req = data or TestNotificationRequest()
    await broadcast_security_event(
        event_type=req.event_type,
        severity=req.severity,
        title=req.title,
        message=req.message,
        data={"test": True},
    )
    return {"success": True, "message": "Test bildirimi gonderildi"}
```

`BaseModel` import'u dosyanin basina eklenmeli. `User` ve `Depends`, `get_current_user` zaten import edilmis.
  </action>
  <verify>
    <automated>cd /c/Nextcloud2/TonbilAiFirevallv5 && python3 -c "
import ast, sys
# Check ws.py has broadcast_security_event
with open('backend/app/api/v1/ws.py') as f:
    tree = ast.parse(f.read())
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    assert 'broadcast_security_event' in funcs, 'broadcast_security_event not found in ws.py'

# Check telegram_service.py has broadcast hooks
with open('backend/app/services/telegram_service.py') as f:
    content = f.read()
    assert content.count('broadcast_security_event') >= 4, 'Expected 4+ broadcast hooks in telegram_service.py'

# Check push.py has test-notification endpoint
with open('backend/app/api/v1/push.py') as f:
    content = f.read()
    assert 'test-notification' in content, 'test-notification endpoint not found in push.py'
    assert 'TestNotificationRequest' in content, 'TestNotificationRequest not found in push.py'

print('ALL BACKEND CHECKS PASSED')
" 2>&1 || echo "VERIFY FAILED"</automated>
  </verify>
  <done>
    - broadcast_security_event() fonksiyonu ws.py'de tanimli ve tum bagli WS istemcilerine JSON mesaj gonderiyor
    - notify_new_device, notify_ip_blocked, notify_trusted_ip_threat, notify_ai_insight fonksiyonlarinin her biri Telegram mesajindan sonra WS broadcast cagiriyor
    - POST /api/v1/push/test-notification endpoint'i JWT auth ile korunmus ve sahte guvenlik olayi broadcast ediyor
  </done>
</task>

<task type="auto">
  <name>Task 2: Android - SecurityEventDto + WebSocketManager + NotificationHelper + sistem bildirimi</name>
  <files>
    android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/WebSocketDto.kt
    android/app/src/main/java/com/tonbil/aifirewall/data/remote/WebSocketManager.kt
    android/app/src/main/java/com/tonbil/aifirewall/util/NotificationHelper.kt
    android/app/src/main/java/com/tonbil/aifirewall/TonbilApp.kt
    android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt
  </files>
  <action>
**WebSocketDto.kt - SecurityEventDto ekle:**

Dosyanin sonuna yeni DTO ekle:

```kotlin
@Serializable
data class SecurityEventDto(
    val type: String = "",
    @SerialName("event_type") val eventType: String = "",
    val severity: String = "info",
    val title: String = "",
    val message: String = "",
    val timestamp: String = "",
    val data: Map<String, String> = emptyMap(),
)
```

Ayrica WebSocket frame'lerin genel type tespiti icin minimal wrapper:

```kotlin
@Serializable
data class WsMessageType(
    val type: String = "",
)
```

**WebSocketManager.kt - security_event parse + securityEvents flow ekle:**

Yeni SharedFlow ekle (mevcut `_messages` yanina):

```kotlin
private val _securityEvents = MutableSharedFlow<SecurityEventDto>(
    replay = 1,
    extraBufferCapacity = 10,
    onBufferOverflow = BufferOverflow.DROP_OLDEST,
)
val securityEvents: SharedFlow<SecurityEventDto> = _securityEvents.asSharedFlow()
```

Import ekle: `com.tonbil.aifirewall.data.remote.dto.SecurityEventDto` ve `com.tonbil.aifirewall.data.remote.dto.WsMessageType`

Incoming frame loop'u guncelle (mevcut lines 132-143). Mevcut `if (update.type == "realtime_update")` kontrolunu genislet:

```kotlin
for (frame in incoming) {
    if (frame is Frame.Text) {
        try {
            val raw = frame.readText()
            // Once type'i belirle
            val msgType = json.decodeFromString<WsMessageType>(raw)
            when (msgType.type) {
                "realtime_update" -> {
                    val update = json.decodeFromString<RealtimeUpdateDto>(raw)
                    _messages.emit(update)
                }
                "security_event" -> {
                    val event = json.decodeFromString<SecurityEventDto>(raw)
                    _securityEvents.emit(event)
                    Log.d(TAG, "Security event received: ${event.eventType} - ${event.title}")
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to parse WS frame: ${e.message}")
        }
    }
}
```

**NotificationHelper.kt - Yeni dosya olustur:**

Path: `android/app/src/main/java/com/tonbil/aifirewall/util/NotificationHelper.kt`

```kotlin
package com.tonbil.aifirewall.util

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.tonbil.aifirewall.R
import com.tonbil.aifirewall.data.remote.dto.SecurityEventDto
import java.util.concurrent.atomic.AtomicInteger

class NotificationHelper(private val context: Context) {

    private val notificationId = AtomicInteger(1000)

    fun createChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Guvenlik Bildirimleri",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "DDoS, IP engelleme, yeni cihaz ve AI guvenlik uyarilari"
                enableVibration(true)
                enableLights(true)
            }
            val nm = context.getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)
        }
    }

    fun showSecurityNotification(event: SecurityEventDto) {
        val icon = when (event.eventType) {
            "ddos_attack" -> android.R.drawable.ic_dialog_alert
            "ip_blocked" -> android.R.drawable.ic_lock_lock
            "new_device" -> android.R.drawable.ic_menu_add
            "trusted_ip_threat" -> android.R.drawable.ic_dialog_info
            "ai_insight" -> android.R.drawable.ic_menu_info_details
            else -> android.R.drawable.ic_dialog_info
        }

        val priority = when (event.severity) {
            "critical" -> NotificationCompat.PRIORITY_HIGH
            "warning" -> NotificationCompat.PRIORITY_DEFAULT
            else -> NotificationCompat.PRIORITY_LOW
        }

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(icon)
            .setContentTitle(event.title)
            .setContentText(event.message)
            .setPriority(priority)
            .setAutoCancel(true)
            .setStyle(NotificationCompat.BigTextStyle().bigText(event.message))
            .build()

        try {
            NotificationManagerCompat.from(context).notify(
                notificationId.getAndIncrement(),
                notification,
            )
        } catch (e: SecurityException) {
            // POST_NOTIFICATIONS izni verilmemis olabilir
        }
    }

    companion object {
        const val CHANNEL_ID = "security_alerts"
    }
}
```

**TonbilApp.kt - NotificationHelper channel olusturma + security event collection:**

`onCreate()` icinde, `startKoin` blogundan SONRA:

```kotlin
// Notification channels
val notificationHelper = NotificationHelper(this)
notificationHelper.createChannels()
```

Import ekle: `com.tonbil.aifirewall.util.NotificationHelper`

**AppModule.kt - NotificationHelper singleton ekle:**

`appModule` icine (Core bolumune):

```kotlin
single { NotificationHelper(androidContext()) }
```

Import ekle: `com.tonbil.aifirewall.util.NotificationHelper`

**TonbilApp.kt - Security events collect ve bildirim goster:**

`onCreate()` icinde, notification channels'dan sonra, WebSocketManager'dan security events flow'unu collect edecek global coroutine scope baslat:

```kotlin
// Collect security events from WebSocket and show system notifications
val processScope = kotlinx.coroutines.CoroutineScope(
    kotlinx.coroutines.Dispatchers.Main + kotlinx.coroutines.SupervisorJob()
)
processScope.launch {
    // Koin hazir olduktan sonra WebSocketManager'i al
    val wsManager = org.koin.java.KoinJavaComponent.get<WebSocketManager>(WebSocketManager::class.java)
    val helper = org.koin.java.KoinJavaComponent.get<NotificationHelper>(NotificationHelper::class.java)
    wsManager.securityEvents.collect { event ->
        helper.showSecurityNotification(event)
    }
}
```

Import'lar: `kotlinx.coroutines.CoroutineScope`, `kotlinx.coroutines.Dispatchers`, `kotlinx.coroutines.SupervisorJob`, `kotlinx.coroutines.launch`, `com.tonbil.aifirewall.data.remote.WebSocketManager`, `com.tonbil.aifirewall.util.NotificationHelper`, `org.koin.java.KoinJavaComponent`

NOT: ProcessLifecycleOwner yerine basit CoroutineScope kullaniliyor — uygulama process'i oldurunce scope otomatik olarak biter. WebSocketManager zaten bagimsiz scope ile calisiyor, burada sadece event collection yapiliyor.
  </action>
  <verify>
    <automated>cd /c/Nextcloud2/TonbilAiFirevallv5 && python3 -c "
import os

# Check SecurityEventDto in WebSocketDto.kt
dto_path = 'android/app/src/main/java/com/tonbil/aifirewall/data/remote/dto/WebSocketDto.kt'
with open(dto_path) as f:
    c = f.read()
    assert 'SecurityEventDto' in c, 'SecurityEventDto not found'
    assert 'WsMessageType' in c, 'WsMessageType not found'
    assert 'event_type' in c, 'event_type field not found'

# Check WebSocketManager has securityEvents
ws_path = 'android/app/src/main/java/com/tonbil/aifirewall/data/remote/WebSocketManager.kt'
with open(ws_path) as f:
    c = f.read()
    assert 'securityEvents' in c, 'securityEvents flow not found'
    assert 'security_event' in c, 'security_event type check not found'
    assert 'SecurityEventDto' in c, 'SecurityEventDto import not found'

# Check NotificationHelper exists
helper_path = 'android/app/src/main/java/com/tonbil/aifirewall/util/NotificationHelper.kt'
assert os.path.exists(helper_path), 'NotificationHelper.kt not created'
with open(helper_path) as f:
    c = f.read()
    assert 'showSecurityNotification' in c, 'showSecurityNotification not found'
    assert 'CHANNEL_ID' in c, 'CHANNEL_ID not found'
    assert 'security_alerts' in c, 'security_alerts channel ID not found'

# Check TonbilApp has notification setup
app_path = 'android/app/src/main/java/com/tonbil/aifirewall/TonbilApp.kt'
with open(app_path) as f:
    c = f.read()
    assert 'NotificationHelper' in c, 'NotificationHelper not in TonbilApp'
    assert 'createChannels' in c, 'createChannels not called in TonbilApp'
    assert 'securityEvents' in c, 'securityEvents collection not in TonbilApp'

# Check AppModule has NotificationHelper
mod_path = 'android/app/src/main/java/com/tonbil/aifirewall/di/AppModule.kt'
with open(mod_path) as f:
    c = f.read()
    assert 'NotificationHelper' in c, 'NotificationHelper not in AppModule'

print('ALL ANDROID CHECKS PASSED')
" 2>&1 || echo "VERIFY FAILED"</automated>
  </verify>
  <done>
    - SecurityEventDto ve WsMessageType WebSocketDto.kt'ye eklenmis
    - WebSocketManager incoming frame loop'u security_event type'ini parse edip securityEvents flow'una emit ediyor
    - NotificationHelper.kt olusturulmus: channel creation + severity bazli icon + sistem bildirimi
    - TonbilApp.kt notification channel'lari olusturuyor ve security events flow'unu collect edip bildirim gosteriyor
    - AppModule'de NotificationHelper Koin singleton olarak kayitli
  </done>
</task>

<task type="auto">
  <name>Task 3: Pi'ye deploy + test bildirimi tetikle + dogrulama</name>
  <files>
    deploy_quick29.py
  </files>
  <action>
Paramiko SFTP ile degistirilmis backend dosyalarini Pi'ye deploy et:

1. **Deploy dosyalari:**
   - `backend/app/api/v1/ws.py` -> `/opt/tonbilaios/backend/app/api/v1/ws.py`
   - `backend/app/services/telegram_service.py` -> `/opt/tonbilaios/backend/app/services/telegram_service.py`
   - `backend/app/api/v1/push.py` -> `/opt/tonbilaios/backend/app/api/v1/push.py`

2. **Backend restart:** `sudo systemctl restart tonbilaios-backend`

3. **3 saniye bekle** (uvicorn startup)

4. **Test endpoint'i cagir:**
   ```
   curl -X POST http://192.168.1.2/api/v1/push/test-notification \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"event_type": "ip_blocked", "severity": "critical", "title": "Test: IP Engellendi", "message": "1.2.3.4 test engelleme"}'
   ```
   (Token icin once `/api/v1/auth/login` ile JWT al)

5. **Dogrula:** Backend log'larinda `broadcast_security_event` cagrisinin basarili oldugunu kontrol et.

Deploy script pattern: Mevcut deploy_quick28.py pattern'ini takip et (Paramiko SSH jump host -> SFTP -> sudo cp -> systemctl restart).

SSH bilgileri: Jump host `pi.tonbil.com:2323`, hedef `192.168.1.2:22`, kullanici `admin`, sifre `benbuyum9087`.
SFTP: `/tmp/` uzerinden upload, `sudo cp` ile `/opt/tonbilaios/` altina kopyala.
  </action>
  <verify>
    <automated>cd /c/Nextcloud2/TonbilAiFirevallv5 && python3 deploy_quick29.py 2>&1 | tail -20</automated>
  </verify>
  <done>
    - Backend dosyalari Pi'ye deploy edilmis
    - tonbilaios-backend servisi basariyla yeniden baslatilmis
    - Test bildirimi endpoint'i cagirilmis ve basarili yanit dondurmus
    - WebSocket bagli istemcilere security_event mesaji broadcast edilmis
  </done>
</task>

</tasks>

<verification>
1. Backend: `broadcast_security_event()` ws.py'de tanimli
2. Backend: 4 Telegram bildirim fonksiyonunda WS broadcast hook mevcut
3. Backend: POST /api/v1/push/test-notification endpoint JWT auth ile calisiyor
4. Android: SecurityEventDto parse ediliyor, securityEvents flow yayinlaniyor
5. Android: NotificationHelper sistem bildirimi gosteriyor (channel: security_alerts)
6. Android: TonbilApp'da securityEvents collect -> showSecurityNotification wiring'i var
7. Pi: Deploy sonrasi backend ayakta ve test bildirimi basariyla broadcast ediliyor
</verification>

<success_criteria>
- Pi'de test endpoint cagirildiginda tum WS bagli istemcilere `{"type": "security_event", ...}` mesaji ulastiriliyor
- Android uygulama acikken test bildirimi sistem bildirim cubugunda gorunuyor
- Gercek guvenlik olaylari (DDoS, IP engelleme, yeni cihaz, AI insight) tetiklendiginde hem Telegram hem WS uzerinden bildirim gidiyor
</success_criteria>

<output>
After completion, create `.planning/quick/29-websocket-security-events-android-system/29-SUMMARY.md`
</output>
