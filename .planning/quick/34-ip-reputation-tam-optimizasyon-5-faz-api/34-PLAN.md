---
phase: 34-ip-reputation-optimization
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/v1/ip_reputation.py
  - backend/app/workers/ip_reputation.py
  - backend/app/workers/ip_blocklist_sync.py
  - backend/app/services/http_pool.py
  - frontend/src/components/firewall/IpReputationTab.tsx
  - frontend/src/services/ipReputationApi.ts
autonomous: true
requirements: [API-WASTE-FIX, GEOIP-BATCH, HTTP-POOL, SMART-TTL, LOCAL-BLOCKLIST, HYBRID-SCORE, FRONTEND-OPT]

must_haves:
  truths:
    - "API-usage endpoint'leri artik gercek AbuseIPDB sorgusu yapmaz, sadece Redis cache'den okur"
    - "Summary endpoint cache yoksa null dondurur, canli sorgu yapmaz"
    - "GeoIP sorgulari batch olarak tek istekte yapilir (10 IP -> 1 istek)"
    - "Tum HTTP istekleri paylasilan AsyncClient uzerinden yapilir (connection pool)"
    - "Temiz IP'ler (skor=0) 7 gun, kritik IP'ler (skor>=80) 6 saat TTL ile cache'lenir"
    - "Lokal blocklist kaynaklari (Firehol, Spamhaus, DShield vb.) Redis SET'e indirilir"
    - "Worker, IP kontrolunde once lokal blocklist kontrol eder, AbuseIPDB sadece bilinmeyen IP'ler icin sorgulanir"
    - "Frontend tab gecislerinde gereksiz API cagrisi yapmaz, istemci tarafi cache kullanir"
  artifacts:
    - path: "backend/app/services/http_pool.py"
      provides: "Paylasilan httpx.AsyncClient singleton"
      exports: ["get_client", "close_all"]
    - path: "backend/app/workers/ip_blocklist_sync.py"
      provides: "Lokal IP blocklist indirme + Redis SET yazma"
      exports: ["sync_all_blocklists", "is_ip_in_local_blocklist", "start_blocklist_sync"]
    - path: "backend/app/api/v1/ip_reputation.py"
      provides: "Duzeltilmis API endpoint'ler (sifir israf)"
    - path: "backend/app/workers/ip_reputation.py"
      provides: "Batch GeoIP + lokal blocklist entegrasyonu + akilli TTL + hibrit skor"
  key_links:
    - from: "backend/app/workers/ip_reputation.py"
      to: "backend/app/services/http_pool.py"
      via: "get_client() import"
      pattern: "from app.services.http_pool import get_client"
    - from: "backend/app/workers/ip_reputation.py"
      to: "backend/app/workers/ip_blocklist_sync.py"
      via: "is_ip_in_local_blocklist() cagirisi"
      pattern: "from app.workers.ip_blocklist_sync import is_ip_in_local_blocklist"
    - from: "backend/app/api/v1/ip_reputation.py"
      to: "Redis cache"
      via: "API-usage endpoint'leri sadece cache okur"
      pattern: "redis.get.*abuseipdb_remaining"
---

<objective>
IP Reputation sisteminin API israfini ortadan kaldirmak, katmanli savunma mimarisi kurmak ve performansi optimize etmek.

Purpose: Mevcut sistem gunde ~900 AbuseIPDB sorgusu yapiyor ve 3 farkli "api-usage" endpoint'i her cagrildiginda gercek API hakki harciyor. Bu plan ile API tuketimini %85-95 azaltmayi, lokal blocklist entegrasyonu ile bagimsiz tehdit tespiti eklemeyi ve frontend'deki gereksiz API cagrilarini optimize etmeyi hedefliyoruz.

Output: Optimize edilmis backend (API + worker + yeni blocklist worker + HTTP pool) ve frontend dosyalari
</objective>

<execution_context>
@.planning/ip-reputation-optimization/ANALYSIS.md
@.planning/ip-reputation-optimization/PLAN.md
</execution_context>

<context>
@backend/app/api/v1/ip_reputation.py
@backend/app/workers/ip_reputation.py
@frontend/src/components/firewall/IpReputationTab.tsx
@frontend/src/services/ipReputationApi.ts
@backend/app/workers/threat_analyzer.py
@backend/app/db/redis_client.py
@backend/app/main.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend API israf fix + HTTP pool + GeoIP batch + akilli TTL (Faz 1+2)</name>
  <files>
    backend/app/services/http_pool.py
    backend/app/api/v1/ip_reputation.py
    backend/app/workers/ip_reputation.py
  </files>
  <action>
**1. Yeni dosya: `backend/app/services/http_pool.py`**

Paylasilan httpx.AsyncClient singleton modulu olustur:

```python
import httpx

_clients: dict[str, httpx.AsyncClient] = {}

async def get_client(name: str = "default", **kwargs) -> httpx.AsyncClient:
    if name not in _clients or _clients[name].is_closed:
        _clients[name] = httpx.AsyncClient(
            timeout=kwargs.get("timeout", 10),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            headers=kwargs.get("headers", {}),
        )
    return _clients[name]

async def close_all():
    for client in _clients.values():
        if not client.is_closed:
            await client.aclose()
    _clients.clear()
```

**2. `api/v1/ip_reputation.py` duzeltmeleri:**

a) **Summary endpoint (satir 228-249):** `if abuseipdb_remaining is None or abuseipdb_limit is None:` blogundan canli `httpx.AsyncClient` sorgusu blogunun TAMAMINI kaldir. Cache yoksa `abuseipdb_remaining=None, abuseipdb_limit=None` olarak don. ASLA canli API sorgusu yapma.

b) **`/api-usage` endpoint (satir 475-580):** Tamamen yeniden yaz. Gercek API sorgusu YAPMA. Sadece Redis'ten oku:
```python
@router.get("/api-usage")
async def check_api_usage(current_user: User = Depends(get_current_user)):
    redis = await get_redis()
    remaining_raw = await redis.get("reputation:abuseipdb_remaining")
    limit_raw = await redis.get("reputation:abuseipdb_limit")
    if remaining_raw is None or limit_raw is None:
        return {"status": "ok", "message": "API kullanim bilgisi henuz mevcut degil (worker dongusunu bekleyin).", "data": {"limit": None, "used": None, "remaining": None, "usage_percent": None}}
    remaining = int(remaining_raw)
    limit = int(limit_raw)
    used = limit - remaining
    pct = round((used / limit) * 100, 1) if limit > 0 else 0
    return {"status": "ok", "message": "Redis cache'den okundu.", "data": {"limit": limit, "used": used, "remaining": remaining, "usage_percent": pct}}
```

c) **`/check-block/api-usage` endpoint (satir 658-710):** Ayni sekilde canli sorgu blogu kaldirilacak. Cache yoksa `null` don.

d) **`/blacklist/api-usage` endpoint (satir 739-821):** Canli `httpx.AsyncClient` blacklist sorgusu blogu kaldirilacak. Cache yoksa `null` don.

e) **`/test` endpoint (satir 396-472):** `async with httpx.AsyncClient(...)` yerine `from app.services.http_pool import get_client; client = await get_client("abuseipdb")` kullan. Bu endpoint gercek test sorgusu yapmasi gerektigi icin API cagrisi kalir ama connection pool uzerinden yapilir.

**3. `workers/ip_reputation.py` duzeltmeleri:**

a) **HTTP pool entegrasyonu:** `check_abuseipdb()` ve `check_geoip()` fonksiyonlarindaki `async with httpx.AsyncClient(...) as client:` satirlarini `client = await get_client("abuseipdb")` ve `client = await get_client("geoip")` ile degistir. Her cagri icin yeni client OLUSTURMA.

b) **GeoIP batch fonksiyonu ekle:**
```python
GEOIP_BATCH_URL = "http://ip-api.com/batch"

async def check_geoip_batch(ips: list[str]) -> dict[str, dict]:
    """ip-api.com batch API — 100 IP tek istekte."""
    client = await get_client("geoip")
    payload = [{"query": ip, "fields": "status,country,countryCode,city,isp,org,as"} for ip in ips[:100]]
    try:
        response = await client.post(GEOIP_BATCH_URL, json=payload)
        if response.status_code == 200:
            results = {}
            for item in response.json():
                if item.get("status") == "success":
                    results[item["query"]] = {
                        "country": item.get("country", ""),
                        "country_code": item.get("countryCode", "??"),
                        "city": item.get("city", ""),
                        "isp": item.get("isp", ""),
                        "org": item.get("org", ""),
                        "asn": item.get("as", ""),
                    }
            return results
    except Exception as exc:
        logger.warning(f"GeoIP batch hatasi: {exc}")
    return {}
```

c) **Akilli TTL fonksiyonu ekle:**
```python
def _get_cache_ttl(abuse_score: int) -> int:
    if abuse_score >= 80:
        return 6 * 3600      # 6 saat
    elif abuse_score >= 50:
        return 12 * 3600     # 12 saat
    elif abuse_score > 0:
        return 24 * 3600     # 24 saat
    else:
        return 7 * 86400     # 7 gun — temiz IP
```

Sabit `CACHE_TTL = 86400` yerine `_get_cache_ttl(abuse_score)` kullan. `_process_ip()` fonksiyonunda Redis cache yazildiktan sonra: `await redis.expire(cache_key, _get_cache_ttl(abuse_score))` seklinde degistir.

d) **`_run_reputation_cycle()` fonksiyonunu batch GeoIP ile degistir:** `_process_ip()` icinde tek tek GeoIP sorgusu yapmak yerine, once tum IP'leri topla, batch GeoIP sorgusu yap, sonra her IP'yi isle. `GEOIP_SLEEP = 1.5` global bekleme KALDIRILACAK (batch endpoint rate limit farkli).

Yeni akis:
```python
# _run_reputation_cycle icinde:
to_check = unchecked_ips[:MAX_CHECKS_PER_CYCLE]
# Batch GeoIP: tum IP'ler icin tek sorgu
geo_batch = await check_geoip_batch(to_check)
# Sonra her IP'yi isle (geo_data parametresi ile)
for ip in to_check:
    geo_data = geo_batch.get(ip)
    await _process_ip(ip, api_key, redis, geo_data=geo_data)
```

`_process_ip()` fonksiyonuna `geo_data: dict | None = None` parametresi ekle. Eger geo_data verilmisse `check_geoip()` cagrisi YAPMA, dogrudan kullan.

e) **`fetch_abuseipdb_blacklist()` ve `check_abuseipdb_block()` fonksiyonlarindaki** `async with httpx.AsyncClient(timeout=30) as client:` satirlarini `client = await get_client("abuseipdb", timeout=30)` ile degistir.

f) **`main.py` lifespan close'a** `from app.services.http_pool import close_all; await close_all()` ekle (uygulama kapatilirken pool temizligi).
  </action>
  <verify>
    <automated>cd /opt/tonbilaios/backend && python3 -c "
from app.services.http_pool import get_client, close_all
from app.workers.ip_reputation import check_geoip_batch, _get_cache_ttl
import asyncio

async def test():
    # HTTP pool singleton testi
    c1 = await get_client('test')
    c2 = await get_client('test')
    assert c1 is c2, 'Pool singleton calismali'

    # TTL testi
    assert _get_cache_ttl(90) == 21600, '6 saat olmali'
    assert _get_cache_ttl(60) == 43200, '12 saat olmali'
    assert _get_cache_ttl(10) == 86400, '24 saat olmali'
    assert _get_cache_ttl(0) == 604800, '7 gun olmali'

    await close_all()
    print('PASS: Tum testler gecti')

asyncio.run(test())
" && echo "Backend OK"</automated>
  </verify>
  <done>
    - 3 api-usage endpoint'i gercek API sorgusu yapmaz, sadece Redis cache okur
    - Summary endpoint canli sorgu yapmaz, cache yoksa null dondurur
    - GeoIP batch fonksiyonu calisiyor (tek POST ile 10 IP)
    - Tum HTTP istekleri paylasilan pool uzerinden yapiliyor
    - Akilli TTL: skor=0 icin 7 gun, skor>=80 icin 6 saat
    - Backend restart sonrasi log'da "yeni client olusturuluyor" mesaji sadece 1 kere gorulur
  </done>
</task>

<task type="auto">
  <name>Task 2: Lokal blocklist worker + hibrit skor entegrasyonu (Faz 3+4)</name>
  <files>
    backend/app/workers/ip_blocklist_sync.py
    backend/app/workers/ip_reputation.py
    backend/app/main.py
  </files>
  <action>
**1. Yeni dosya: `backend/app/workers/ip_blocklist_sync.py`**

Lokal IP blocklist indirme worker'i olustur:

```python
BLOCKLIST_SOURCES = [
    {
        "name": "firehol_level1",
        "url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset",
        "interval": 3600,
        "type": "netset",  # Yorum satirlari # ile baslar, IP ve CIDR karisik
    },
    {
        "name": "spamhaus_drop",
        "url": "https://www.spamhaus.org/drop/drop.txt",
        "interval": 86400,
        "type": "cidr",  # Her satir: CIDR ; yorum
    },
    {
        "name": "spamhaus_edrop",
        "url": "https://www.spamhaus.org/drop/edrop.txt",
        "interval": 86400,
        "type": "cidr",
    },
    {
        "name": "dshield_top20",
        "url": "https://feeds.dshield.org/block.txt",
        "interval": 86400,
        "type": "dshield",  # Tab-separated: start_ip	end_ip	...
    },
    {
        "name": "emerging_threats",
        "url": "https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt",
        "interval": 86400,
        "type": "iplist",  # Her satir: IP adresi veya yorum #
    },
]
```

Her kaynak icin:
- `_parse_netset(text)` -> IP'ler ve CIDR'lar ayri ayri
- `_parse_cidr(text)` -> sadece CIDR (`;` sonrasi yorum atla)
- `_parse_dshield(text)` -> start IP'den /24 CIDR olustur
- `_parse_iplist(text)` -> satir basina 1 IP

`sync_single_blocklist(source)` fonksiyonu:
1. HTTP GET ile listeyi indir (`get_client("blocklist")` kullan)
2. Parse et -> IP seti + CIDR seti
3. Redis pipeline ile:
   - `blocklist:{name}_ips` SET -> tum IP'ler
   - `blocklist:{name}_nets` SET -> tum CIDR'lar
   - `blocklist:{name}_meta` HASH -> {last_fetch, count, url}
4. `blocklist:combined` SET'e SUNIONSTORE ile tum kaynaklarin IP'lerini birlesir
5. `blocklist:combined_nets` SET'e tum CIDR'lari birlesir

`is_ip_in_local_blocklist(ip: str) -> tuple[bool, str]` fonksiyonu:
1. `redis.sismember("blocklist:combined", ip)` -> O(1) tam eslesme
2. CIDR kontrolu: IP'nin /24, /16, /8 network adreslerini hesapla, `blocklist:combined_nets` SET'te ara
3. Return `(True, "firehol_level1")` veya `(False, "")`

`sync_all_blocklists()` fonksiyonu: Tum kaynaklari donguyle senkronize et, her kaynak icin meta bilgisini kontrol et (interval gecmediyse atla).

`start_blocklist_sync()` fonksiyonu: Asenkron worker — her 3600s'de bir `sync_all_blocklists()` calistir. Ilk calistirmada 60s bekle (diger worker'lar hazir olsun).

**2. `workers/ip_reputation.py` hibrit skor entegrasyonu:**

`_calculate_local_score(ip, redis)` fonksiyonu ekle:
```python
async def _calculate_local_score(ip: str, redis) -> tuple[int, list[str]]:
    score = 0
    reasons = []

    # 1. Lokal blocklist eslesmesi (50 puan)
    from app.workers.ip_blocklist_sync import is_ip_in_local_blocklist
    in_blocklist, source = await is_ip_in_local_blocklist(ip)
    if in_blocklist:
        score += 50
        reasons.append(f"Lokal blocklist: {source}")

    # 2. DDoS saldirgan seti (30 puan)
    if await redis.sismember("ddos:attacker_ips", ip):
        score += 30
        reasons.append("DDoS saldirgan seti")

    # 3. Daha once engellenmis (20 puan)
    if await redis.sismember("dns:threat:blocked", ip):
        score += 20
        reasons.append("Daha once engellenmis")

    # 4. Engellenen ulke (40 puan — GeoIP cache varsa)
    geo_cache = await redis.hgetall(f"reputation:ip:{ip}")
    if geo_cache:
        cc = geo_cache.get("country_code", "")
        blocked_countries = await _get_blocked_countries(redis)
        if cc and cc.upper() in [c.upper() for c in blocked_countries]:
            score += 40
            reasons.append(f"Engellenen ulke: {cc}")

    return min(100, score), reasons
```

`_process_ip()` fonksiyonunu guncelle — karar motoru ekle:
```python
# _process_ip icinde, AbuseIPDB sorgusu ONCESINDE:
local_score, local_reasons = await _calculate_local_score(ip, redis)

# Lokal skor >= 70 ise AbuseIPDB'ye sormaya GEREK YOK
if local_score >= 70:
    abuse_score = local_score
    # AbuseIPDB sorgusu ATLA, API hakki harcanmaz
    used_abuseipdb = False
    logger.info(f"[LOKAL] {ip} skor={local_score} (AbuseIPDB atlatildi): {', '.join(local_reasons)}")
else:
    # Normal AbuseIPDB + lokal skor birlestirmesi
    if api_key:
        abuse_data = await check_abuseipdb(ip, api_key)
        used_abuseipdb = True
    # final_score = max(local_score, abuseipdb_score)
    abuseipdb_score = int((abuse_data or {}).get("abuse_score", 0))
    abuse_score = max(local_score, abuseipdb_score)
```

Cache'e `local_score` ve `local_reasons` alanlarini da ekle (UI'da gosterilecek):
```python
cache_payload["local_score"] = str(local_score)
cache_payload["local_reasons"] = json.dumps(local_reasons)
```

**3. `main.py` lifespan'a blocklist worker baslat:**
```python
from app.workers.ip_blocklist_sync import start_blocklist_sync
asyncio.create_task(start_blocklist_sync())
```

Bu gorevi `start_ip_reputation()` task'indan ONCE baslat — boylece IP reputation worker basladiginda lokal blocklist zaten hazir olur.
  </action>
  <verify>
    <automated>cd /opt/tonbilaios/backend && python3 -c "
from app.workers.ip_blocklist_sync import _parse_netset, _parse_iplist, _parse_cidr, _parse_dshield
import asyncio

# Parser testleri
ips, nets = _parse_netset('# comment\n1.2.3.4\n5.6.0.0/16\n')
assert '1.2.3.4' in ips, 'IP parse basarisiz'
assert '5.6.0.0/16' in nets, 'CIDR parse basarisiz'

ips2, nets2 = _parse_cidr('10.0.0.0/8 ; test\n192.168.0.0/16 ; internal\n')
assert '10.0.0.0/8' in nets2

ips3, _ = _parse_iplist('# comment\n8.8.8.8\n1.1.1.1\n')
assert '8.8.8.8' in ips3
assert '1.1.1.1' in ips3

print('PASS: Parser testleri gecti')
" && echo "Blocklist OK"</automated>
  </verify>
  <done>
    - ip_blocklist_sync.py olusturuldu, 5 kaynak tanimi mevcut
    - Parser fonksiyonlari (netset, cidr, dshield, iplist) dogru calisiyor
    - is_ip_in_local_blocklist() O(1) SET lookup + CIDR subnet kontrolu yapiyor
    - Worker 3600s aralikla tum listeleri senkronize ediyor
    - _calculate_local_score() 5 sinyal kaynagindan hibrit skor hesapliyor
    - Lokal skor >= 70 olan IP'ler icin AbuseIPDB sorgusu ATLANIR
    - main.py lifespan'da blocklist worker baslatiliyor (ip_reputation worker'dan once)
    - Cache'e local_score ve local_reasons alanlari yaziliyor
  </done>
</task>

<task type="auto">
  <name>Task 3: Frontend optimizasyon + UI iyilestirme (Faz 5)</name>
  <files>
    frontend/src/components/firewall/IpReputationTab.tsx
    frontend/src/services/ipReputationApi.ts
  </files>
  <action>
**1. `ipReputationApi.ts` istemci tarafi cache ekle:**

Dosyanin basina basit in-memory cache mekanizmasi ekle:

```typescript
// In-memory cache (TTL bazli)
const _cache = new Map<string, { data: any; ts: number }>();

function getCached<T>(key: string, ttlMs: number): T | null {
  const entry = _cache.get(key);
  if (entry && Date.now() - entry.ts < ttlMs) return entry.data as T;
  return null;
}

function setCache(key: string, data: any) {
  _cache.set(key, { data, ts: Date.now() });
}
```

Her API fonksiyonuna cache wrapper ekle (summary, config, ips, blacklist icin):

```typescript
export const fetchReputationSummary = async () => {
  const cached = getCached('rep-summary', 60_000); // 60s cache
  if (cached) return { data: cached };
  const resp = await api.get('/ip-reputation/summary');
  setCache('rep-summary', resp.data);
  return resp;
};

export const fetchReputationIps = async (minScore?: number) => {
  const key = `rep-ips-${minScore ?? 0}`;
  const cached = getCached(key, 30_000); // 30s cache
  if (cached) return { data: cached };
  const resp = await api.get('/ip-reputation/ips', { params: minScore ? { min_score: minScore } : {} });
  setCache(key, resp.data);
  return resp;
};

export const fetchBlacklist = async () => {
  const cached = getCached('rep-blacklist', 60_000);
  if (cached) return { data: cached };
  const resp = await api.get('/ip-reputation/blacklist');
  setCache('rep-blacklist', resp.data);
  return resp;
};
```

API-usage fonksiyonlari: Cache'siz birak (zaten backend artik Redis'ten okuyor, pahali degil).

Cache invalidation: `clearReputationCache` cagirildiginda `_cache.clear()` ekle. `triggerBlacklistFetch` cagirildiginda `_cache.delete('rep-blacklist')` ekle.

**2. `IpReputationTab.tsx` optimizasyonlari:**

a) **API Usage bar'i pasif yap:** "API Kullanimini Kontrol Et" butonlarina tiklama yerine, sayfa acilisinda 1 kere otomatik fetch yap + 120s aralikla arka planda yenile. Buton'u "Yenile" ikonu ile degistir (mevcut `RefreshCw` ikonu). API-usage response'unda `data: null` gelirse "Bilgi mevcut degil — worker dongusunu bekleyin" mesaji goster.

b) **Tab gecislerinde gereksiz fetch'i onle:** Mevcut kodda her tab gecisinde (`activeTab` degistiginde) ilgili verileri yeniden cekiyor. Bunu sartli hale getir:
- State'e `lastFetchTs` objesi ekle: `{ summary: number, ips: number, blacklist: number, checkBlock: number }`
- Tab aktiflestiginde `Date.now() - lastFetchTs[tab] < 30000` ise fetch YAPMA (30s stale-while-revalidate)
- 30s gecmisse arka planda fetch yap ama eski veriyi gostermeye devam et (loading spinner gosterme)

c) **Lokal skor gosterimi (yeni):** IP tablosunda eger `local_score` ve `local_reasons` verileri mevcutsa (Task 2'den gelecek), ek bir "Lokal Skor" sutunu goster. `local_reasons` tooltip olarak gosterilsin.

d) **Blocklist istatistikleri (yeni):** Config bolumune yeni bir bilgi karti ekle: "Lokal Blocklist Durumu" — `/ip-reputation/blocklist-stats` endpoint'i yoksa (bu task'ta eklenmeyecek), bu kismi ATLA. Sadece mevcut verileri optimize et.

e) **Null handling:** Backend artik `data: null` veya `data: {limit: null, ...}` dondurebilir. Frontend'de `null` kontrolu ekle:
```typescript
// API usage bar'inda:
if (!usageData || usageData.limit === null) {
  return <span className="text-gray-500">Bilgi mevcut degil</span>;
}
```

f) **Ilk yukleme optimizasyonu:** `useEffect` icindeki ilk fetch'leri `Promise.all` ile paralelize et (zaten paralel olabilir ama kontrol et). Sadece aktif tab'in verisini cek, diger tab'larin verisi tab'a gecildiginde lazy-load edilsin.
  </action>
  <verify>
    <automated>cd /opt/tonbilaios/frontend && npx tsc --noEmit 2>&1 | head -20 && echo "TypeScript OK" && npm run build 2>&1 | tail -5 && echo "Build OK"</automated>
  </verify>
  <done>
    - API client 30-60s istemci tarafi cache kullaniyor
    - Tab gecislerinde 30s icinde ayni veri tekrar cekilmiyor
    - API usage bar'i otomatik 120s arka plan yenilemesi yapiyor
    - Backend null response'lari "Bilgi mevcut degil" mesaji ile gosteriliyor
    - Cache invalidation dogru calisiyor (cache temizle butonu _cache.clear() tetikliyor)
    - Frontend TypeScript hata vermeden build oluyor
    - Sayfanin ilk yuklemesinde toplam API istegi sayisi azaldi (6+ -> 2-3)
  </done>
</task>

</tasks>

<verification>
## Genel Dogrulama (deploy sonrasi)

1. **API israf testi:** Pi'de backend restart sonrasi, browser'da IP Reputation sekmesini ac. Network tab'inda `/api-usage`, `/check-block/api-usage`, `/blacklist/api-usage` isteklerini kontrol et — hicbiri AbuseIPDB'ye gercek sorgu tetiklememeli.

2. **Blocklist worker testi:** Backend log'larinda `ip_blocklist_sync` mesajlarini kontrol et — kaynaklarin basariyla indirildigini ve Redis'e yazildigini dogrula:
```bash
sudo journalctl -u tonbilaios-backend --since "5 min ago" | grep blocklist
```

3. **GeoIP batch testi:** Worker dongusunde birden fazla IP kontrol edildiginde log'da "GeoIP batch: X IP sorgulanacak" mesaji gorunmeli.

4. **Akilli TTL testi:** Redis'te bir temiz IP'nin TTL'ini kontrol et:
```bash
redis-cli -a TonbilAiRedis2026 TTL "reputation:ip:8.8.8.8"
# 604800 (7 gun) civarinda olmali
```

5. **Hibrit skor testi:** Worker log'larinda `[LOKAL]` mesajlari gorunmeli — lokal blocklist'te olan IP'ler icin AbuseIPDB atlatildigini dogrular.

6. **Frontend build:** `npm run build` hatasiz tamamlanmali.
</verification>

<success_criteria>
- API-usage endpoint'leri 0 AbuseIPDB hakki harcar (once: her cagri 1 hak)
- Summary endpoint 0 AbuseIPDB hakki harcar (once: cache expire sonrasi 1 hak)
- GeoIP sorgulari: 10 IP icin 1 batch istek (once: 10 ayri istek + 15s bekleme)
- HTTP client: paylasilan pool (once: her istek icin yeni client)
- Cache TTL: skor=0 → 7 gun, skor>=80 → 6 saat (once: sabit 24 saat)
- Lokal blocklist: 5 kaynak Redis'te, is_ip_in_local_blocklist() O(1)
- Hibrit skor: lokal skor >= 70 → AbuseIPDB atlatilir
- Frontend: tab gecisinde 30s cache, API-usage 120s arka plan yenileme
- Hedef: gunde ~900 AbuseIPDB sorgu → ~50-100 sorgu (%85-95 azalma)
</success_criteria>

<output>
After completion, create `.planning/quick/34-ip-reputation-tam-optimizasyon-5-faz-api/34-SUMMARY.md`
</output>
