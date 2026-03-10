---
phase: quick-30
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/v1/ws.py
autonomous: true
requirements: [QUICK-30]
must_haves:
  truths:
    - "Security event broadcast edildiginde istemcilere 3 saniye beklemeden aninda ulastiriliyor"
    - "asyncio.Event ile sleep dongusu event geldiginde erken uyandiriliyor"
    - "Backend WebSocket baglantilarina periyodik ping gonderiyor ve pong gelmezse kopuk baglantilari temizliyor"
    - "Kopuk baglantilar (zombie WS) birikmiyor, stale connection'lar otomatik kapatiliyor"
  artifacts:
    - path: "backend/app/api/v1/ws.py"
      provides: "asyncio.Event tabanli anlik broadcast + ping/pong keepalive"
      contains: "_wake_event"
  key_links:
    - from: "broadcast_security_event()"
      to: "websocket_endpoint while loop"
      via: "asyncio.Event.set() ile sleep'i erken uyandirma"
      pattern: "_wake_event\\.set\\(\\)"
    - from: "websocket_endpoint"
      to: "client WebSocket"
      via: "ping frame gondererek baglanti sagligini dogrulama"
      pattern: "websocket\\.send.*ping|ping_task"
---

<objective>
WebSocket security event broadcast'ini kuyruk+3s polling'den asyncio.Event tabanli anlik gonderime gecirmek ve baglanti kopma/birikmesini onlemek icin ping/pong keepalive eklemek.

Purpose: Mevcut sistemde security event'ler kuyruklara yaziliyor ama gercek gonderim 3 saniyelik sleep bitmesini bekliyor. Bu gecikme kritik guvenlik uyarilarinda kabul edilemez. Ayrica backend'de ping/pong yok, Nginx 60s timeout'u veya istemci tarafindaki ag sorunlari nedeniyle zombie baglantilar birikiyor.

Output: Guncelenmis ws.py — asyncio.Event ile anlik broadcast + ping/pong keepalive + stale connection temizligi
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@backend/app/api/v1/ws.py

<interfaces>
<!-- Mevcut ws.py yapisi (Quick-29 sonrasi) -->

# ConnectionManager singleton
class ConnectionManager:
    active_connections: list[WebSocket]
    _ip_counts: dict[str, int]
    _pending_events: dict[int, list[str]]  # ws id -> event list

    async connect(websocket, client_ip) -> bool
    disconnect(websocket, client_ip)
    queue_event(payload: str)              # Tum WS'lerin kuyruguna ekle
    drain_events(websocket) -> list[str]   # Bir WS'nin bekleyen event'lerini al+temizle

manager = ConnectionManager()  # module-level singleton

# broadcast_security_event() — module-level async fonksiyon
# Cagiranlar: telegram_service.py (4 hook), push.py (test endpoint)
# Mevcut davranis: manager.queue_event(payload) cagirir, ANINDA gondermez
# Event'ler websocket_endpoint() icindeki while True dongusunde 3s sleep sonrasi gonderilir

# websocket_endpoint() ana dongusu:
while True:
    pending = manager.drain_events(websocket)  # Kuyruktaki event'leri al
    for event_payload in pending:
        await websocket.send_text(event_payload)
    data = await _get_realtime_data()          # DB+Redis sorgusu (~50-200ms)
    await websocket.send_json(data)
    await asyncio.sleep(3)                     # <-- SORUN: Event gelse bile 3s bekler

# Frontend useWebSocket.ts:
# - Basit reconnect (exponential backoff 2s->30s)
# - Disconnect debounce (5s)
# - Ping/pong YOK

# Bilinen sorunlar (STATE.md):
# - "WebSocket baglanti birikimi: Ayni tarayicidan 10-15 WS baglantisi acilebiliyor (backend pong timeout eksik)"
# - Per-IP limit 5 zaten var ama stale baglantilar temizlenmedigi icin yeni baglantilar reddediliyor
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: asyncio.Event ile anlik security event broadcast + ping/pong keepalive</name>
  <files>backend/app/api/v1/ws.py</files>
  <action>
ws.py dosyasini guncelleyerek iki kritik sorunu coz:

**1) asyncio.Event ile anlik event broadcast:**

ConnectionManager sinifina `_wake_event: asyncio.Event` ekle:

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._ip_counts: dict[str, int] = {}
        self._pending_events: dict[int, list[str]] = {}
        self._wake_event = asyncio.Event()  # YENi: donguyu uyandirmak icin
```

`queue_event()` metodunun sonuna `self._wake_event.set()` ekle — event kuyruga girince tum donguleri uyandir:

```python
def queue_event(self, payload: str):
    """Tum bagli istemcilerin kuyruklarina event ekle ve donguleri uyandir."""
    for ws in self.active_connections:
        events = self._pending_events.get(id(ws))
        if events is not None:
            events.append(payload)
    self._wake_event.set()  # Bekleyen donguleri uyandir
```

`websocket_endpoint()` icindeki `asyncio.sleep(3)` satirini `asyncio.wait_for` ile degistir. Mevcut dongu:

```python
# ESKISI:
while True:
    pending = manager.drain_events(websocket)
    for event_payload in pending:
        await websocket.send_text(event_payload)
    data = await _get_realtime_data()
    await websocket.send_json(data)
    await asyncio.sleep(3)
```

Yeni dongu yapisi — `_wake_event` kullanarak sleep'i erken uyandirma + ping/pong:

```python
PING_INTERVAL = 30   # Her 30 saniyede bir ping gonder
PONG_TIMEOUT = 10    # Pong icin 10 saniye bekle
DATA_INTERVAL = 3    # Normal realtime data interval

# ...websocket_endpoint() icinde, while True icinden once:
    last_ping = asyncio.get_event_loop().time()
    last_data = 0.0  # Hemen ilk data gondermek icin 0

    try:
        while True:
            now = asyncio.get_event_loop().time()

            # 1) Bekleyen security event'leri ANINDA gonder
            pending = manager.drain_events(websocket)
            for event_payload in pending:
                await websocket.send_text(event_payload)

            # 2) Realtime data gonder (her DATA_INTERVAL saniyede bir)
            if now - last_data >= DATA_INTERVAL:
                data = await _get_realtime_data()
                await websocket.send_json(data)
                last_data = now

            # 3) Ping gonder (her PING_INTERVAL saniyede bir)
            if now - last_ping >= PING_INTERVAL:
                try:
                    # Starlette WebSocket ping (dusuk seviye)
                    await asyncio.wait_for(
                        websocket.send_bytes(b"__ping__"),
                        timeout=PONG_TIMEOUT,
                    )
                    last_ping = now
                except (asyncio.TimeoutError, Exception):
                    logger.warning(f"WebSocket ping timeout, baglanti kapatiliyor: {client_ip}")
                    break

            # 4) _wake_event veya DATA_INTERVAL kadar bekle (hangisi once gelirse)
            manager._wake_event.clear()
            try:
                await asyncio.wait_for(
                    manager._wake_event.wait(),
                    timeout=DATA_INTERVAL,
                )
                # Event geldi — dongude hemen drain_events calisacak
            except asyncio.TimeoutError:
                # Normal timeout — dongude realtime data gonderilecek
                pass
```

ONEMLI NOTLAR:
- `_wake_event.clear()` SONRA `wait()` yapilmali — yoksa onceki set() kalintisi hemen uyandirir
- `send_bytes(b"__ping__")` Starlette'in dusuk seviye WS mesajidir. FastAPI/Starlette icinde gercek WS ping frame gondermek icin `websocket.send({"type": "websocket.ping"})` KULLANILMAMALI cunku Starlette bunu desteklemez. Bunun yerine application-level ping kullan: `await websocket.send_text('{"type":"ping"}')`
- Application-level ping daha guvenilir: JSON mesaj gonderir, istemci almazsa connection broken demektir
- Frontend tarafindaki useWebSocket.ts'ye mudahale GEREKMIYOR — ping mesaji sadece parse edilemezse console.error basacak (mevcut try/catch), veri akisini bozmuyor

**GUNCELLENMIS YAKLASIM — Application-level ping:**

Ping icin basit JSON mesaj kullan (WebSocket protocol-level ping yerine). Bu Starlette ile uyumlu ve frontend tarafinda sorunsuz:

```python
# Ping kontrolu:
if now - last_ping >= PING_INTERVAL:
    try:
        await asyncio.wait_for(
            websocket.send_json({"type": "ping", "ts": int(now)}),
            timeout=PONG_TIMEOUT,
        )
        last_ping = now
    except (asyncio.TimeoutError, Exception):
        logger.warning(f"WebSocket ping timeout, baglanti kapatiliyor: {client_ip}")
        break
```

Frontend'de `{"type": "ping"}` mesaji gelince `setData(parsed)` ile state'e yazilir ama `type === "realtime_update"` degilse dashboard'da hicbir sey yapmaz. Dashboard zaten sadece `data?.dns`, `data?.bandwidth` gibi alanlari okur. Dolayisiyla ek bir frontend degisikligi GEREKMEZ.

**2) Stale baglanti temizligi:**

ConnectionManager'a `cleanup_stale()` metodu ekle:

```python
async def cleanup_stale(self):
    """Gonderim yapilamayan baglantilari temizle."""
    stale = []
    for ws in self.active_connections[:]:
        try:
            # Kucuk test mesaji gonder
            await asyncio.wait_for(
                ws.send_json({"type": "ping"}),
                timeout=5,
            )
        except Exception:
            stale.append(ws)
    for ws in stale:
        client_ip = ""
        # IP'yi bulmak icin ip_counts'u taramak gerekiyor ama basit tutmak icin
        # disconnect'e bos string ver — loglarda "unknown" cikacak
        self.disconnect(ws, client_ip="stale")
        try:
            await ws.close(code=1001, reason="Stale connection")
        except Exception:
            pass
    if stale:
        logger.info(f"Stale WebSocket temizlendi: {len(stale)} baglanti")
```

Ancak cleanup_stale() ayri bir coroutine olarak calistirilMAYACAK. Her WebSocket baglantisi kendi dongusunde ping gonderir, kendi stale durumunu yakalar. Bu metod gelecekte ihtiyac olursa hazir bekler.

Mevcut `disconnect()` metodunda `client_ip` parametresi opsiyonel tutulmali — eger "stale" gelirse IP count dusurulmemeli:

```python
def disconnect(self, websocket: WebSocket, client_ip: str = ""):
    if websocket in self.active_connections:
        self.active_connections.remove(websocket)
    self._pending_events.pop(id(websocket), None)
    if client_ip and client_ip != "stale" and client_ip in self._ip_counts:
        self._ip_counts[client_ip] = max(0, self._ip_counts[client_ip] - 1)
        if self._ip_counts[client_ip] == 0:
            del self._ip_counts[client_ip]
    logger.info(
        f"WebSocket koptu: {client_ip}. "
        f"Aktif: {len(self.active_connections)}"
    )
```

**3) websocket_endpoint disconnect'inde client_ip gecisini duzelt:**

Mevcut `except WebSocketDisconnect` ve `except Exception` bloklarinda `client_ip` zaten dogru geciliyor — degisiklik gerekmez.

**Tam websocket_endpoint() fonksiyonu (yeniden yazim):**

```python
PING_INTERVAL = 30   # saniye
PONG_TIMEOUT = 10    # saniye
DATA_INTERVAL = 3    # saniye

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default=None)):
    """Her 3 saniyede gercek DNS ve cihaz verisi push et.
    Security event gelince asyncio.Event ile aninda gonder.
    Periyodik ping ile stale baglantilar tespit edilir.
    Token dogrulama: ?token=xxx query parametresi veya cookie."""
    # Token kontrolu: query param > cookie
    ws_token = token or websocket.cookies.get("tonbilai_session")
    client_ip = _get_ws_client_ip(websocket)
    is_authenticated = _validate_ws_token(ws_token, client_ip)
    if not is_authenticated:
        is_authenticated = _validate_ws_token(ws_token, "")
    if not is_authenticated:
        logger.warning(f"WebSocket auth basarisiz, baglanti reddedildi: {client_ip}")
        await websocket.close(code=1008, reason="Unauthorized")
        return
    connected = await manager.connect(websocket, client_ip=client_ip)
    if not connected:
        return
    try:
        loop_time = asyncio.get_event_loop().time
        last_ping = loop_time()
        last_data = 0.0  # Ilk data hemen gonderilsin

        while True:
            now = loop_time()

            # 1) Bekleyen security event'leri ANINDA gonder
            pending = manager.drain_events(websocket)
            for event_payload in pending:
                await websocket.send_text(event_payload)

            # 2) Realtime data (her DATA_INTERVAL saniyede)
            if now - last_data >= DATA_INTERVAL:
                data = await _get_realtime_data()
                await websocket.send_json(data)
                last_data = now

            # 3) Application-level ping (her PING_INTERVAL saniyede)
            if now - last_ping >= PING_INTERVAL:
                try:
                    await asyncio.wait_for(
                        websocket.send_json({"type": "ping", "ts": int(now)}),
                        timeout=PONG_TIMEOUT,
                    )
                    last_ping = now
                except (asyncio.TimeoutError, Exception):
                    logger.warning(
                        f"WebSocket ping timeout, baglanti kapatiliyor: {client_ip}"
                    )
                    break

            # 4) Event veya timeout bekle
            manager._wake_event.clear()
            try:
                await asyncio.wait_for(
                    manager._wake_event.wait(),
                    timeout=DATA_INTERVAL,
                )
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket, client_ip=client_ip)
    except Exception as e:
        logger.error(f"WebSocket hatasi: {e}")
        manager.disconnect(websocket, client_ip=client_ip)
```

**DIKKAT — asyncio.Event paylasim sorunu:**
Birden fazla WS baglantisi ayni `_wake_event` nesnesini paylasiyor. `clear()` cagirildiginda DIGER coroutine'ler de etkilenir. Bu sorun degil cunku:
- Her coroutine kendi dongusunde `clear()` + `wait()` yapar
- `set()` cagirildiginda TUM bekleyen coroutine'ler uyanir (istedigimiz davranis)
- Bir coroutine `clear()` yaptiginda diger coroutine zaten `drain_events` veya `_get_realtime_data` ile mesguldur
- En kotu durumda bir coroutine extra bir tur yapar — bu kabul edilebilir

ALTERNATIF: Her WS icin ayri Event olusturmak daha temiz ama karmasiklik ekler. Mevcut yaklasim yeterli.
  </action>
  <verify>
    <automated>cd /c/Nextcloud2/TonbilAiFirevallv5 && python3 -c "
import ast
with open('backend/app/api/v1/ws.py') as f:
    content = f.read()
    tree = ast.parse(content)

# 1) _wake_event must exist
assert '_wake_event' in content, '_wake_event not found in ws.py'
assert 'asyncio.Event' in content, 'asyncio.Event not found'

# 2) queue_event must call set()
assert '_wake_event.set()' in content, '_wake_event.set() not in queue_event'

# 3) wait_for pattern must exist (sleep replacement)
assert 'wait_for' in content, 'asyncio.wait_for not found (sleep replacement)'

# 4) PING_INTERVAL constant
assert 'PING_INTERVAL' in content, 'PING_INTERVAL not defined'

# 5) No bare asyncio.sleep(3) in websocket_endpoint (should use wait_for)
# Find websocket_endpoint function and check no sleep(3) inside
import re
ws_func_match = re.search(r'async def websocket_endpoint.*?(?=\nasync def |\nclass |\Z)', content, re.DOTALL)
if ws_func_match:
    ws_body = ws_func_match.group(0)
    assert 'asyncio.sleep(3)' not in ws_body, 'asyncio.sleep(3) still in websocket_endpoint — should use wait_for'

# 6) ping mechanism present
assert '\"type\": \"ping\"' in content or '\"type\":\"ping\"' in content or 'type.*ping' in content.replace(' ',''), 'ping type not found'

print('ALL WS CHECKS PASSED')
" 2>&1 || echo "VERIFY FAILED"</automated>
  </verify>
  <done>
    - asyncio.Event tabanli anlik broadcast: security event geldiginde _wake_event.set() ile tum WS donguleri 3s beklemeden hemen uyanir
    - Application-level ping: 30s aralikla JSON ping mesaji gonderilir, 10s icerisinde gonderilemezse baglanti stale kabul edilip kapatilir
    - Zombie/stale baglantilar otomatik tespit ve temizleniyor
    - asyncio.sleep(3) kaldirildi, yerine wait_for(_wake_event.wait(), timeout=3) kullaniliyor
  </done>
</task>

<task type="auto">
  <name>Task 2: Pi'ye deploy + test endpoint ile anlik broadcast dogrulama</name>
  <files>deploy_quick30.py</files>
  <action>
Paramiko SFTP ile guncelenmis backend dosyasini Pi'ye deploy et.

deploy_quick30.py scripti olustur. Mevcut deploy_quick29.py pattern'ini takip et:

1. **Deploy dosyasi:**
   - `backend/app/api/v1/ws.py` -> `/opt/tonbilaios/backend/app/api/v1/ws.py`

2. **Backend restart:** `sudo systemctl restart tonbilaios-backend`

3. **5 saniye bekle** (uvicorn startup)

4. **Dogrulama adimlari (SSH uzerinden):**
   a. Backend servis durumu: `sudo systemctl is-active tonbilaios-backend` -> "active" olmali
   b. Import kontrolu: `python3 -c "from app.api.v1.ws import manager; print('wake_event:', hasattr(manager, '_wake_event'))"` (cwd: `/opt/tonbilaios/backend`)
   c. Test notification endpoint'i cagir:
      - Once JWT al: `curl -s -X POST http://localhost/api/v1/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"benbuyum9087"}'`
      - Token'la test et: `curl -s -X POST http://localhost/api/v1/push/test-notification -H 'Authorization: Bearer <token>' -H 'Content-Type: application/json' -d '{"title":"Quick30 Test","message":"Anlik broadcast testi"}'`
      - 200 donmeli
   d. Backend log'larinda "Security event queued" mesaji kontrol et: `sudo journalctl -u tonbilaios-backend --since '30 seconds ago' --no-pager | grep -i 'security\|wake\|ping'`

SSH bilgileri: Jump host `pi.tonbil.com:2323`, hedef `192.168.1.2:22`, kullanici `admin`, sifre `benbuyum9087`.
SFTP: `/tmp/` uzerinden upload, `sudo cp` ile `/opt/tonbilaios/` altina kopyala.
  </action>
  <verify>
    <automated>cd /c/Nextcloud2/TonbilAiFirevallv5 && python3 deploy_quick30.py 2>&1 | tail -30</automated>
  </verify>
  <done>
    - ws.py Pi'ye deploy edilmis ve backend basariyla yeniden baslatilmis
    - Test endpoint cagirildiginda security event aninda broadcast ediliyor (kuyruk+3s gecikme yok)
    - Backend loglari ping/pong mekanizmasinin aktif oldugunu dogruluyor
  </done>
</task>

</tasks>

<verification>
1. Backend ws.py: `_wake_event` asyncio.Event tabanli — `queue_event()` set(), `websocket_endpoint()` wait()
2. Backend ws.py: `asyncio.sleep(3)` kaldirildi, yerine `wait_for(_wake_event.wait(), timeout=3)` kullaniliyor
3. Backend ws.py: PING_INTERVAL=30s application-level ping, PONG_TIMEOUT=10s ile stale tespit
4. Backend ws.py: Stale baglanti tespit edildiginde disconnect + log
5. Pi: Deploy sonrasi backend ayakta, test endpoint basarili
</verification>

<success_criteria>
- Security event broadcast edildiginde istemcilere <100ms icerisinde ulastiriliyor (3s polling yerine)
- 30s aralikla ping gonderiliyor, yanit gelmezse baglanti kapatiliyor
- Zombie baglantilar birikimiyor — 40s icerisinde (30s interval + 10s timeout) stale baglantilar tespit ve temizleniyor
- Pi'de deploy sonrasi test notification endpoint basarili calisiyor
</success_criteria>

<output>
After completion, create `.planning/quick/30-ws-security-event-an-nda-g-nderim-asynci/30-SUMMARY.md`
</output>
