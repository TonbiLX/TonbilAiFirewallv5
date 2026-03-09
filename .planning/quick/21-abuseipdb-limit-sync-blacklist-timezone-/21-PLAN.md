---
phase: quick-21
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/workers/ip_reputation.py
  - backend/app/api/v1/ip_reputation.py
autonomous: true
requirements: [BUG-LIMIT-FALLBACK, BUG-BLACKLIST-TIMEZONE]
must_haves:
  truths:
    - "Summary endpoint AbuseIPDB remaining/limit degerlerini her zaman dogru dondurur (Redis key'leri expire olsa bile)"
    - "Blacklist otomatik fetch 24 saatte tam 1 kez calisir (timezone farki nedeniyle fazladan tetiklenmez)"
    - "Frontend gunluk kullanim gostergesi gercek API limitini yansitir, 900 fallback'i gosterilmez"
  artifacts:
    - path: "backend/app/workers/ip_reputation.py"
      provides: "Blacklist last_fetch UTC ISO format kaydedilmesi + UTC karsilastirmasi"
    - path: "backend/app/api/v1/ip_reputation.py"
      provides: "Summary endpoint'te Redis key yoksa AbuseIPDB header kontrolu"
  key_links:
    - from: "backend/app/api/v1/ip_reputation.py"
      to: "backend/app/workers/ip_reputation.py"
      via: "check_abuseipdb fonksiyonu veya direkt httpx header sorgusu"
      pattern: "X-RateLimit-Remaining"
    - from: "backend/app/workers/ip_reputation.py"
      to: "Redis reputation:blacklist_last_fetch"
      via: "UTC ISO timestamp kaydetme"
      pattern: "datetime\\.utcnow.*isoformat"
---

<objective>
AbuseIPDB API istatistik gosterimindeki iki bug'i duzelt:
1. Redis key'leri expire oldugunda summary endpoint'in 900 fallback donmesi
2. Blacklist last_fetch timestamp'inin local timezone ile kaydedilip UTC ile karsilastirilmasi

Purpose: Frontend'te dogru API limit bilgisi gostermek ve blacklist fetch'in 24 saatte 1 dogru calismasini saglamak
Output: Duzeltilmis ip_reputation.py (worker) ve ip_reputation.py (API)
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/workers/ip_reputation.py
@backend/app/api/v1/ip_reputation.py
@backend/app/services/timezone_service.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Blacklist timestamp'ini UTC ISO formatina gecir</name>
  <files>backend/app/workers/ip_reputation.py</files>
  <action>
iki degisiklik yapilacak:

A) Satir ~550 (`fetch_abuseipdb_blacklist` fonksiyonu icerisinde, "Meta veri guncelle" bolumu):
   - ONCE: `await redis.set(REDIS_KEY_BLACKLIST_LAST_FETCH, format_local_time())`
   - SONRA: `await redis.set(REDIS_KEY_BLACKLIST_LAST_FETCH, datetime.utcnow().isoformat() + "Z")`
   - Bu sayede Redis'e UTC ISO formatinda kaydedilir (ornek: "2026-03-09T14:30:00.123456Z")

B) Satir ~623-632 (`_run_reputation_cycle` fonksiyonu icerisinde, blacklist otomatik fetch kontrolu):
   - ONCE:
     ```python
     last_dt = datetime.fromisoformat(last_fetch_raw.replace("+03:00", "").replace("Z", ""))
     if (datetime.utcnow() - last_dt).total_seconds() < BLACKLIST_FETCH_INTERVAL:
     ```
   - SONRA:
     ```python
     # UTC ISO formatini parse et ("Z" suffix'i kaldir, naive UTC datetime olustur)
     clean = last_fetch_raw.replace("Z", "").replace("+00:00", "")
     # Eski format uyumlulugu: "HH:MM:SS DD/MM/YYYY" → skip (parse edemez, yeniden fetch tetiklenir)
     last_dt = datetime.fromisoformat(clean)
     if (datetime.utcnow() - last_dt).total_seconds() < BLACKLIST_FETCH_INTERVAL:
     ```
   - Boylece hem yeni UTC format hem de eski local format parse hatasi durumunda guvenli sekilde yeniden fetch tetiklenir
   - `format_local_time` import'u dosyada baska yerde kullaniliyorsa (satir 327, `_process_ip` checked_at icin) kalsin; sadece blacklist meta verisi icin UTC'ye gecilir

C) Satir ~526 (`fetch_abuseipdb_blacklist` auto-block bolumu):
   - ONCE: `now_iso = datetime.utcnow().isoformat()`
   - Bu zaten UTC, dokunulmayacak (dogru)

NOT: `_process_ip` fonksiyonundaki `checked_at = format_local_time()` (satir ~327) bu scope disindadir — o kullanici goruntuleme icin local time kaydeder ve dogrudur.
  </action>
  <verify>
    <automated>cd C:\Nextcloud2\TonbilAiFirevallv5 && python -c "
import ast, sys
with open('backend/app/workers/ip_reputation.py') as f:
    content = f.read()
# Verify: blacklist_last_fetch artik UTC ISO kullaniyor
assert 'datetime.utcnow().isoformat()' in content and 'REDIS_KEY_BLACKLIST_LAST_FETCH' in content, 'UTC isoformat kullanilmiyor'
# Verify: eski format_local_time blacklist_last_fetch'te yok
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'BLACKLIST_LAST_FETCH' in line and 'format_local_time' in line:
        print(f'HATA: Satir {i+1} hala format_local_time kullaniyor: {line.strip()}')
        sys.exit(1)
# Verify: parse kismi +03:00 hardcode yerine temiz UTC parse
assert '+03:00' not in content or content.count('+03:00') == 0, 'Hardcoded +03:00 hala mevcut'
print('OK: Blacklist timestamp UTC ISO formatina gecti')
"</automated>
  </verify>
  <done>
    - `reputation:blacklist_last_fetch` Redis key'i UTC ISO formatinda kaydediliyor (ornek: "2026-03-09T14:30:00Z")
    - Otomatik fetch karsilastirmasi UTC-UTC arasinda yapiliyor (timezone farki yok)
    - Eski local format parse edilemezse except yakalanir ve yeniden fetch tetiklenir (geriye uyumlu)
  </done>
</task>

<task type="auto">
  <name>Task 2: Summary endpoint'te Redis key expire durumunda AbuseIPDB limit guncelle</name>
  <files>backend/app/api/v1/ip_reputation.py</files>
  <action>
`get_ip_reputation_summary` endpoint'inde (satir ~155-239) su degisiklikleri yap:

A) AbuseIPDB remaining/limit Redis key'leri None donerse (expire olmus veya hic yazilmamis), API anahtari varsa AbuseIPDB'ye hafif bir sorgu yap ve header'lardan limit bilgilerini al:

Satir ~213-223 arasindaki blogu guncelle. `abuseipdb_remaining` ve `abuseipdb_limit` None olarak kaldiysa:

```python
# AbuseIPDB gercek rate limit degerleri (worker tarafindan kaydedilir)
abuseipdb_remaining: int | None = None
abuseipdb_limit: int | None = None
try:
    remaining_raw = await redis.get("reputation:abuseipdb_remaining")
    limit_raw     = await redis.get("reputation:abuseipdb_limit")
    if remaining_raw is not None:
        abuseipdb_remaining = int(remaining_raw)
    if limit_raw is not None:
        abuseipdb_limit = int(limit_raw)
except Exception as exc:
    logger.debug(f"AbuseIPDB rate limit okunamadi: {exc}")

# Redis'te rate limit bilgisi yoksa (TTL dolmus), API anahtari varsa canli sorgu yap
if abuseipdb_remaining is None or abuseipdb_limit is None:
    try:
        api_key_raw = await redis.get(REDIS_KEY_API_KEY)
        if api_key_raw and api_key_raw.strip():
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                resp = await client.get(
                    ABUSEIPDB_URL,
                    headers={"Key": api_key_raw.strip(), "Accept": "application/json"},
                    params={"ipAddress": "8.8.8.8", "maxAgeInDays": 1},
                )
                if resp.status_code == 200:
                    h_remaining = resp.headers.get("X-RateLimit-Remaining")
                    h_limit = resp.headers.get("X-RateLimit-Limit")
                    if h_remaining is not None:
                        abuseipdb_remaining = int(h_remaining)
                        await redis.set("reputation:abuseipdb_remaining", str(abuseipdb_remaining), ex=86400)
                    if h_limit is not None:
                        abuseipdb_limit = int(h_limit)
                        await redis.set("reputation:abuseipdb_limit", str(abuseipdb_limit), ex=86400)
                    logger.info(f"AbuseIPDB limit canli guncellendi: {abuseipdb_remaining}/{abuseipdb_limit}")
    except Exception as exc:
        logger.debug(f"AbuseIPDB canli limit sorgusu basarisiz: {exc}")
```

B) `httpx` import'unun dosyanin basinda mevcut oldugunu dogrula (satir 4'te zaten var).

C) Bu sorgu 8.8.8.8 (Google DNS) ile yapilir — guvenli test IP'si, zaten `/test` endpoint'inde de kullaniliyor. `maxAgeInDays=1` ile minimal veri cekilir.

D) Redis'e kaydederken TTL=86400 (24 saat) ayarla — `ex=86400`. Bu worker'in kullandigi CACHE_TTL ile ayni.

DIKKAT: Bu canli sorgu AbuseIPDB'nin 1 check hakkini harcar. Ancak sadece Redis key'leri expire olmus ve summary endpoint cagrilmissa tetiklenir (nadir durum). IP check yapilirsa zaten header'lar yeniden yazilir.
  </action>
  <verify>
    <automated>cd C:\Nextcloud2\TonbilAiFirevallv5 && python -c "
import sys
with open('backend/app/api/v1/ip_reputation.py') as f:
    content = f.read()
# Verify: canli AbuseIPDB sorgusu eklenmis
assert 'X-RateLimit-Remaining' in content, 'X-RateLimit-Remaining header kontrolu yok'
assert 'X-RateLimit-Limit' in content, 'X-RateLimit-Limit header kontrolu yok'
# Verify: 8.8.8.8 ile sorgu (test IP)
assert '8.8.8.8' in content, '8.8.8.8 test IP kullanilmiyor'
# Verify: Redis'e geri yazma (cache guncelleme)
assert 'reputation:abuseipdb_remaining' in content, 'remaining Redis key yazilmiyor'
assert 'reputation:abuseipdb_limit' in content, 'limit Redis key yazilmiyor'
# Verify: TTL 86400
assert '86400' in content, 'TTL 86400 ayarlanmamis'
print('OK: Summary endpoint canli limit sorgusu eklendi')
"</automated>
  </verify>
  <done>
    - Summary endpoint Redis'te abuseipdb_remaining/limit yoksa API anahtari ile canli sorgu yapar
    - Header'lardan X-RateLimit-Remaining ve X-RateLimit-Limit okunup Redis'e 24s TTL ile kaydedilir
    - Frontend her zaman gercek API limitini gorur, 900 fallback'i gosterilmez
    - Hata durumunda sessizce basarisiz olur (mevcut davranis korunur)
  </done>
</task>

</tasks>

<verification>
1. `python -c "..."` ile her iki dosyadaki degisikliklerin varligini dogrula
2. Frontend build basarili olmali (frontend degisiklik yok, sadece backend)
3. Backend syntax hatasi olmamali: `python -c "import ast; ast.parse(open('backend/app/workers/ip_reputation.py').read()); ast.parse(open('backend/app/api/v1/ip_reputation.py').read()); print('Syntax OK')"`
</verification>

<success_criteria>
- Summary endpoint her zaman dogru AbuseIPDB limit/remaining degeri dondurur
- Blacklist otomatik fetch tam 24 saatte 1 tetiklenir (timezone kaymasiz)
- Eski format_local_time() ile kaydedilmis last_fetch degerleri graceful handle edilir
- Frontend gunluk kullanim gostergesi gercek API limitini yansitir
</success_criteria>

<output>
After completion, create `.planning/quick/21-abuseipdb-limit-sync-blacklist-timezone-/21-SUMMARY.md`
</output>
