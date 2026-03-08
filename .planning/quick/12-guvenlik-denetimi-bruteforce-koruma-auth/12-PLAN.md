---
phase: quick-12
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/v1/system_management.py
  - backend/app/api/v1/auth.py
  - backend/app/schemas/auth.py
  - backend/app/api/v1/ws.py
autonomous: true
requirements: [SEC-01, SEC-02, SEC-03]

must_haves:
  truths:
    - "Reboot/shutdown endpointleri confirmation parametresi olmadan calismiyor"
    - "Ayni kullanici adi ile brute force yapilamiyor (username+IP rate limiting)"
    - "Sifre degistirildikten sonra eski oturumlar gecersiz oluyor"
    - "Yeni sifreler ozel karakter icermek zorunda"
    - "Tek IP'den 5'ten fazla WebSocket baglantisi acilamiyor"
  artifacts:
    - path: "backend/app/api/v1/system_management.py"
      provides: "Reboot/shutdown confirmation kontrolu"
      contains: "confirm"
    - path: "backend/app/api/v1/auth.py"
      provides: "Username+IP rate limiting + session invalidation on password change"
      contains: "auth:failed:user:"
    - path: "backend/app/schemas/auth.py"
      provides: "Ozel karakter zorunlulugu"
      contains: "ozel karakter"
    - path: "backend/app/api/v1/ws.py"
      provides: "Per-IP WebSocket limiti"
      contains: "MAX_CONNECTIONS_PER_IP"
  key_links:
    - from: "backend/app/api/v1/auth.py"
      to: "Redis auth:failed:user:*"
      via: "username bazli rate limit key"
      pattern: "auth:failed:user:"
    - from: "backend/app/api/v1/auth.py"
      to: "Redis auth:session:*"
      via: "SCAN + delete on password change"
      pattern: "auth:session:"
    - from: "backend/app/api/v1/ws.py"
      to: "ConnectionManager._ip_counts"
      via: "per-IP counter dict"
      pattern: "_ip_counts"
---

<objective>
Ev agi guvenlik denetimi sonucu bulunan 3 guvenlik acigini kapat:
1. Reboot/shutdown confirmation kontrolu (service whitelist zaten mevcut)
2. Auth guclendirme (username rate limit + session invalidation + ozel karakter)
3. WebSocket per-IP baglanti limiti

Purpose: Brute force, DoS ve yetkisiz sistem kontrolune karsi koruma katmanlari
Output: 4 dosyada guvenlik iyilestirmeleri, Pi'ye deploy
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/api/v1/system_management.py
@backend/app/api/v1/auth.py
@backend/app/schemas/auth.py
@backend/app/api/v1/ws.py
@backend/app/services/system_management_service.py

<interfaces>
<!-- system_management_service.py zaten whitelist iceriyor: -->
MANAGED_SERVICES = [{"name": "tonbilaios-backend", ...}, ...]
_ALLOWED_NAMES = {s["name"] for s in MANAGED_SERVICES}
def _validate_service_name(name: str) -> str  # ValueError if not in whitelist
async def reboot_system() -> dict   # {"success": bool, "message": str}
async def shutdown_system() -> dict # {"success": bool, "message": str}

<!-- auth.py mevcut rate limiting yapisi: -->
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 900
async def check_rate_limit(redis, client_ip)     # key: auth:failed:{client_ip}
async def record_failed_attempt(redis, client_ip) # INCR + EXPIRE
async def clear_failed_attempts(redis, client_ip)  # DELETE
# Session key format: auth:session:{user_id}:{client_ip}

<!-- schemas/auth.py mevcut sifre validasyonu: -->
def _validate_password_strength(password: str) -> str
# Mevcut: 8 char min, buyuk harf, kucuk harf, rakam
# EKSIK: ozel karakter

<!-- ws.py mevcut yapisi: -->
MAX_WS_CONNECTIONS = 100
class ConnectionManager:
    active_connections: list[WebSocket]
    async def connect(websocket) -> bool
    def disconnect(websocket)
def _get_ws_client_ip(websocket: WebSocket) -> str
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Reboot/Shutdown Confirmation + Auth Guclendirme (rate limit + session + sifre)</name>
  <files>
    backend/app/api/v1/system_management.py
    backend/app/api/v1/auth.py
    backend/app/schemas/auth.py
  </files>
  <action>
**NOT: Service name whitelist ZATEN MEVCUT (`system_management_service.py` icinde `_validate_service_name`). Bu adim atlanir.**

**1) system_management.py — Reboot/Shutdown confirmation:**

`reboot_system` ve `shutdown_system` endpoint'lerine `confirm: bool = False` body parametresi ekle (Pydantic model veya Query). `confirm=True` olmadan 400 don:

```python
from pydantic import BaseModel

class ConfirmAction(BaseModel):
    confirm: bool = False

@router.post("/reboot")
async def reboot_system(
    data: ConfirmAction,
    current_user: User = Depends(get_current_user),
):
    if not data.confirm:
        raise HTTPException(
            status_code=400,
            detail="Onay gerekli: confirm=true gonderilmelidir"
        )
    result = await sms.reboot_system()
    ...

@router.post("/shutdown")
async def shutdown_system(
    data: ConfirmAction,
    current_user: User = Depends(get_current_user),
):
    if not data.confirm:
        raise HTTPException(
            status_code=400,
            detail="Onay gerekli: confirm=true gonderilmelidir"
        )
    result = await sms.shutdown_system()
    ...
```

**2) auth.py — Username+IP rate limiting:**

`check_rate_limit` fonksiyonuna username parametresi ekle. IP bazli kontrole EK OLARAK `auth:failed:user:{username}` key'i de kontrol et ve artir. Her iki key de MAX_LOGIN_ATTEMPTS'a tabi. Login endpoint'inde cagriyi guncelle:

```python
async def check_rate_limit(redis, client_ip, username: str | None = None):
    # Mevcut IP bazli kontrol (degistirme)
    ...
    # Ek: username bazli kontrol
    if username:
        user_key = f"auth:failed:user:{username}"
        attempts = await redis.get(user_key)
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
            ttl = await redis.ttl(user_key)
            raise HTTPException(429, ...)

async def record_failed_attempt(redis, client_ip, username: str | None = None):
    # Mevcut IP bazli kayit (degistirme)
    ...
    # Ek: username bazli kayit
    if username:
        user_key = f"auth:failed:user:{username}"
        pipe = redis.pipeline()
        pipe.incr(user_key)
        pipe.expire(user_key, LOCKOUT_SECONDS)
        await pipe.execute()

async def clear_failed_attempts(redis, client_ip, username: str | None = None):
    # Mevcut IP bazli temizlik (degistirme)
    ...
    # Ek: username bazli temizlik
    if username:
        await redis.delete(f"auth:failed:user:{username}")
```

Login endpoint cagrilarini guncelle:
```python
await check_rate_limit(redis, client_ip, username=data.username)
await record_failed_attempt(redis, client_ip, username=data.username)
await clear_failed_attempts(redis, client_ip, username=data.username)
```

In-memory fallback fonksiyonlarini da username destekleyecek sekilde guncelle — `_check_memory_rate_limit` ve `_record_memory_attempt` username key'i de eklesin.

**3) auth.py — Sifre degistirmede tum oturumlari kapat:**

`change-password` endpoint'ine Redis dependency ekle. Basarili degisiklikten sonra `auth:session:{user_id}:*` pattern'ini SCAN ile tara ve sil:

```python
@router.post("/change-password")
async def change_password(
    data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    if not current_user.verify_password(data.current_password):
        raise HTTPException(400, "Mevcut sifre hatali")

    current_user.password_hash = User.hash_password(data.new_password)
    await db.flush()

    # Tum aktif oturumlari kapat
    pattern = f"auth:session:{current_user.id}:*"
    deleted = 0
    async for key in redis.scan_iter(match=pattern, count=100):
        await redis.delete(key)
        deleted += 1

    logger.info(f"Sifre degistirildi, {deleted} oturum kapatildi: {current_user.username}")
    return {"message": f"Sifre degistirildi, {deleted} aktif oturum kapatildi"}
```

**4) schemas/auth.py — Ozel karakter zorunlulugu:**

`_validate_password_strength` fonksiyonuna ozel karakter kontrolu ekle:

```python
if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
    raise ValueError("Sifre en az bir ozel karakter icermelidir (!@#$%^&* vb.)")
```

Bu kontrolu mevcut diger kontrollerden (rakam kontrolu) sonra ekle.
  </action>
  <verify>
    <automated>cd C:\Nextcloud2\TonbilAiFirevallv5 && python -c "
from backend.app.schemas.auth import _validate_password_strength
# Ozel karakter olmadan reddedilmeli
try:
    _validate_password_strength('TestPass1')
    print('FAIL: ozel karakter kontrolu calismiyor')
except ValueError as e:
    print(f'PASS: {e}')
# Gecerli sifre
try:
    _validate_password_strength('TestPass1!')
    print('PASS: gecerli sifre kabul edildi')
except ValueError as e:
    print(f'FAIL: gecerli sifre reddedildi: {e}')
"</automated>
  </verify>
  <done>
    - Reboot/shutdown confirm=true olmadan 400 donuyor
    - Username+IP bazli rate limiting aktif (hem Redis hem in-memory fallback)
    - Sifre degisiminde tum oturumlar Redis'ten siliniyor
    - Sifre validasyonu ozel karakter zorunlu kiliyor
  </done>
</task>

<task type="auto">
  <name>Task 2: WebSocket Per-IP Baglanti Limiti</name>
  <files>
    backend/app/api/v1/ws.py
  </files>
  <action>
ConnectionManager sinifina per-IP baglanti takibi ekle:

```python
MAX_CONNECTIONS_PER_IP = 5

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._ip_counts: dict[str, int] = {}  # IP -> aktif baglanti sayisi

    async def connect(self, websocket: WebSocket, client_ip: str = "") -> bool:
        # Global limit
        if len(self.active_connections) >= MAX_WS_CONNECTIONS:
            logger.warning(f"WebSocket global limit asildi ({MAX_WS_CONNECTIONS})")
            await websocket.close(code=1013, reason="Server at capacity")
            return False

        # Per-IP limit
        current_ip_count = self._ip_counts.get(client_ip, 0)
        if client_ip and current_ip_count >= MAX_CONNECTIONS_PER_IP:
            logger.warning(
                f"WebSocket per-IP limit asildi: {client_ip} ({current_ip_count}/{MAX_CONNECTIONS_PER_IP})"
            )
            await websocket.close(code=1013, reason="Too many connections from this IP")
            return False

        await websocket.accept()
        self.active_connections.append(websocket)
        if client_ip:
            self._ip_counts[client_ip] = current_ip_count + 1
        logger.info(
            f"WebSocket baglandi: {client_ip}. "
            f"Aktif: {len(self.active_connections)}, IP count: {self._ip_counts.get(client_ip, 0)}"
        )
        return True

    def disconnect(self, websocket: WebSocket, client_ip: str = ""):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if client_ip and client_ip in self._ip_counts:
            self._ip_counts[client_ip] = max(0, self._ip_counts[client_ip] - 1)
            if self._ip_counts[client_ip] == 0:
                del self._ip_counts[client_ip]
        logger.info(
            f"WebSocket koptu: {client_ip}. "
            f"Aktif: {len(self.active_connections)}"
        )
```

`websocket_endpoint` fonksiyonunda `client_ip` degiskenini `connect()` ve `disconnect()` cagrilarina gecir:

```python
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(default=None)):
    ...
    client_ip = _get_ws_client_ip(websocket)
    ...
    connected = await manager.connect(websocket, client_ip=client_ip)
    if not connected:
        return
    try:
        while True:
            ...
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_ip=client_ip)
    except Exception as e:
        logger.error(f"WebSocket hatasi: {e}")
        manager.disconnect(websocket, client_ip=client_ip)
```
  </action>
  <verify>
    <automated>cd C:\Nextcloud2\TonbilAiFirevallv5 && python -c "
import ast, sys
with open('backend/app/api/v1/ws.py') as f:
    source = f.read()
checks = [
    ('MAX_CONNECTIONS_PER_IP', 'MAX_CONNECTIONS_PER_IP' in source),
    ('_ip_counts', '_ip_counts' in source),
    ('client_ip param in connect', 'def connect(self, websocket' in source and 'client_ip' in source),
    ('client_ip param in disconnect', 'def disconnect(self, websocket' in source and 'client_ip' in source),
    ('per-IP limit check', 'Too many connections' in source or 'per-IP limit' in source.lower()),
]
all_pass = True
for name, ok in checks:
    status = 'PASS' if ok else 'FAIL'
    if not ok: all_pass = False
    print(f'{status}: {name}')
sys.exit(0 if all_pass else 1)
"</automated>
  </verify>
  <done>
    - Per-IP WebSocket limiti MAX_CONNECTIONS_PER_IP=5 aktif
    - Ayni IP'den 6. baglanti reddediliyor (code=1013)
    - Disconnect'te IP sayaci dogru azaltiliyor
    - Global 100 limiti korunuyor
  </done>
</task>

<task type="auto">
  <name>Task 3: Pi'ye Deploy + Dogrulama</name>
  <files>
    deploy_quick12.py
  </files>
  <action>
Mevcut deploy scriptlerinden birini (ornegin deploy_quick10.py) temel alarak deploy scripti olustur. Script su dosyalari Pi'ye yukleyecek:

1. `backend/app/api/v1/system_management.py` -> `/opt/tonbilaios/backend/app/api/v1/system_management.py`
2. `backend/app/api/v1/auth.py` -> `/opt/tonbilaios/backend/app/api/v1/auth.py`
3. `backend/app/schemas/auth.py` -> `/opt/tonbilaios/backend/app/schemas/auth.py`
4. `backend/app/api/v1/ws.py` -> `/opt/tonbilaios/backend/app/api/v1/ws.py`

Deploy sonrasi:
- `sudo systemctl restart tonbilaios-backend`
- 5 saniye bekle
- `systemctl is-active tonbilaios-backend` ile servisin ayakta oldugunu dogrula

Paramiko SFTP kullan (ProxyJump tunnel ile, mevcut deploy scriptlerindeki pattern):
- Jump host: pi.tonbil.com:2323 (admin/benbuyum9087)
- Target: 192.168.1.2:22 (admin/benbuyum9087)
- SFTP /tmp/ uzerinden sudo cp (root ownership)

Deploy sonrasi SSH uzerinden dogrulama komutlari calistir:
```bash
# Backend ayakta mi
systemctl is-active tonbilaios-backend

# Confirmation kontrolu (confirm olmadan reboot reddedilmeli)
curl -s -X POST http://localhost:8000/api/v1/system-management/reboot \
  -H "Content-Type: application/json" -d '{}' | grep -o "confirm"

# WebSocket per-IP limit kontrolu (kaynak kodda MAX_CONNECTIONS_PER_IP)
grep "MAX_CONNECTIONS_PER_IP" /opt/tonbilaios/backend/app/api/v1/ws.py
```
  </action>
  <verify>
    <automated>python deploy_quick12.py</automated>
  </verify>
  <done>
    - 4 dosya Pi'ye yuklendi
    - Backend basariyla yeniden basladi (is-active: active)
    - Reboot endpoint confirm olmadan 400/422 donuyor
    - ws.py dosyasinda MAX_CONNECTIONS_PER_IP tanimli
  </done>
</task>

</tasks>

<verification>
1. Backend Pi'de calistigi dogrulandi (systemctl is-active)
2. Reboot/shutdown confirm parametresi olmadan reddediliyor
3. Sifre ozel karakter icermeyen degerleri reddediyor
4. WebSocket per-IP limiti aktif (MAX_CONNECTIONS_PER_IP=5)
5. Username+IP rate limiting key'leri Redis'te olusturuluyor
</verification>

<success_criteria>
- Tum 4 backend dosyasi Pi'ye deploy edildi
- Backend hatasiz calisiyor
- 5 guvenlik iyilestirmesi aktif: confirmation, username rate limit, session invalidation, ozel karakter, per-IP WS limit
</success_criteria>

<output>
After completion, create `.planning/quick/12-guvenlik-denetimi-bruteforce-koruma-auth/12-SUMMARY.md`
</output>
