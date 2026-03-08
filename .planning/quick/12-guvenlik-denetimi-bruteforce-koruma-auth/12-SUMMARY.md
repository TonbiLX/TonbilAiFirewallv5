---
phase: quick-12
plan: 01
subsystem: backend-security
tags: [security, auth, rate-limiting, websocket, brute-force]
dependency_graph:
  requires: []
  provides: [SEC-01, SEC-02, SEC-03]
  affects: [auth.py, ws.py, system_management.py, schemas/auth.py]
tech_stack:
  added: []
  patterns:
    - Username+IP dual-key Redis rate limiting
    - Session invalidation via scan_iter on password change
    - Per-IP WebSocket connection tracking with dict counter
    - Pydantic ConfirmAction body for destructive endpoints
key_files:
  created:
    - deploy_quick12.py
  modified:
    - backend/app/api/v1/system_management.py
    - backend/app/api/v1/auth.py
    - backend/app/schemas/auth.py
    - backend/app/api/v1/ws.py
decisions:
  - confirm=true body parametresi (GET query yerine POST body) — Pydantic validation ile
  - Username rate limit ek katman (IP'ye ek, silmez) — iki bagimsiz Redis key
  - scan_iter ile oturum temizleme (SCAN 0 yerine) — bellek dostu iterasyon
  - MAX_CONNECTIONS_PER_IP=5 (sabit deger, konfigurasyon tabloya tasinmadi)
metrics:
  duration: "~12 dakika"
  completed_date: "2026-03-09"
  tasks_completed: 3
  files_modified: 5
---

# Quick 12: Guvenlik Denetimi — Brute Force Koruma + Auth Guclendir

**Ozet:** 5 guvenlik acigi kapatildi: reboot/shutdown confirmation zorunlulugu, username+IP dual-key rate limiting, sifre degisiminde tum oturum invalidasyonu, ozel karakter sifre zorunlulugu, per-IP WebSocket baglanti limiti (maks 5).

## Gerceklestirilen Degisiklikler

### Task 1: Reboot/Shutdown Confirmation + Auth Guclendir

**system_management.py — ConfirmAction body:**
- `ConfirmAction(BaseModel)` modeli eklendi: `confirm: bool = False`
- `/reboot` ve `/shutdown` endpoint'leri body parametresi kabul ediyor
- `confirm=False` durumunda `HTTP 400` + "Onay gerekli: confirm=true gonderilmelidir"

**auth.py — Username+IP Rate Limiting:**
- `check_rate_limit(redis, client_ip, username=None)` — username parametresi eklendi
- `auth:failed:user:{username}` Redis key'i ile ek katman
- `record_failed_attempt` — pipeline'a username key INCR/EXPIRE eklendi
- `clear_failed_attempts` — basarili giriste her iki key siliniyor
- In-memory fallback (`_check_memory_rate_limit`, `_record_memory_attempt`) da username destekliyor
- Login endpoint: `username=data.username` ile cagri guncellendi

**auth.py — Session Invalidation:**
- `change-password` endpoint'ine `redis: aioredis.Redis = Depends(get_redis_dep)` eklendi
- Basarili sifre degisikliginde `auth:session:{user_id}:*` pattern SCAN ile taranip siliniyor
- Log: "Sifre degistirildi, N oturum kapatildi"

**schemas/auth.py — Ozel Karakter Zorunlulugu:**
- `_validate_password_strength` fonksiyonuna regex eklendi: `[!@#$%^&*()\-_=+...]`
- Dogrulanmis: `TestPass1` reddediliyor, `TestPass1!` kabul ediliyor

### Task 2: WebSocket Per-IP Baglanti Limiti

**ws.py:**
- `MAX_CONNECTIONS_PER_IP = 5` sabiti eklendi
- `ConnectionManager._ip_counts: dict[str, int]` tracker dict eklendi
- `connect(websocket, client_ip="")` — per-IP limit kontrolu (code=1013, reason="Too many connections from this IP")
- `disconnect(websocket, client_ip="")` — IP sayaci azaltiliyor, 0'a dustugunde key siliniyor
- `websocket_endpoint` — `client_ip` artik `connect()` ve `disconnect()`'e geciyor

### Task 3: Pi Deploy + Dogrulama

- 4 dosya Pi'ye SFTP ile yuklendi (`/tmp/` staging, `sudo cp`, `chown root:root`)
- `sudo systemctl restart tonbilaios-backend` → `is-active: active`
- Dogrulama sonuclari (Pi'de):
  - Reboot endpoint token olmadan: HTTP 401 (OK — auth katmani calisıyor)
  - `MAX_CONNECTIONS_PER_IP=5` ws.py'de mevcut
  - `auth:failed:user:` key auth.py'de mevcut
  - `ozel karakter` validasyonu schemas/auth.py'de mevcut

## Deviations from Plan

None - plan tam olarak uygulandı.

## Commit Ozeti

| Commit | Aciklama | Dosyalar |
|--------|----------|----------|
| `7642f2a` | feat(quick-12): 5 guvenlik iyilestirmesi | system_management.py, auth.py, schemas/auth.py, ws.py |
| `ecad49a` | feat(quick-12): deploy scripti + Pi dogrulama | deploy_quick12.py |

## Self-Check: PASSED

- backend/app/api/v1/system_management.py — mevcut (ConfirmAction body)
- backend/app/api/v1/auth.py — mevcut (username rate limit + session invalidation)
- backend/app/schemas/auth.py — mevcut (ozel karakter zorunlu)
- backend/app/api/v1/ws.py — mevcut (MAX_CONNECTIONS_PER_IP + _ip_counts)
- deploy_quick12.py — mevcut (Pi'ye deploy + dogrulama)
- Commit 7642f2a — mevcut
- Commit ecad49a — mevcut
- Backend Pi'de: active (systemctl is-active)
