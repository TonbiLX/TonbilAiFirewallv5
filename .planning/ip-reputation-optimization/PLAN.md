# IP Reputation Optimizasyon Planı — Uygulama Detayları

**Tarih:** 2026-03-12
**Hedef:** API çağrılarını %85-95 azaltmak, katmanlı savunma mimarisi kurmak

---

## FAZ 1: Acil API İsrafı Düzeltmeleri

### Görev 1.1: API-Usage Endpoint'lerini Düzelt

**Dosya:** `backend/app/api/v1/ip_reputation.py`

3 endpoint değişecek:
- `GET /ip-reputation/api-usage` (satır 475-580)
- `GET /ip-reputation/check-block/api-usage` (satır 658-710)
- `GET /ip-reputation/blacklist/api-usage` (satır 739-821)

**Değişiklik:** Cache yoksa `null` döndür, **asla** gerçek API sorgusu yapma.

```python
# ÖNCEKİ (1 API hakkı harcıyor):
if abuseipdb_remaining is None or abuseipdb_limit is None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(ABUSEIPDB_URL, ...)  # GERÇEK SORGU!

# YENİ (sıfır API harcıyor):
if abuseipdb_remaining is None or abuseipdb_limit is None:
    return {"status": "ok", "data": {"limit": None, "remaining": None, ...}}
```

### Görev 1.2: Summary Endpoint'inden Canlı Sorguyu Kaldır

**Dosya:** `backend/app/api/v1/ip_reputation.py` satır 228-249

**Değişiklik:** Cache'de veri yoksa None döndür.

### Görev 1.3: Frontend Cache + Throttle

**Dosya:** `frontend/src/components/firewall/IpReputationTab.tsx`

- API usage bar'ı açılışta otomatik çekme, kullanıcı isteğiyle çek
- Summary verisini 60s istemci tarafı cache'le
- Tab geçişlerinde veriyi yeniden çekme (stale-while-revalidate)

---

## FAZ 2: GeoIP Batch + HTTP Client Optimizasyonu

### Görev 2.1: Paylaşılan httpx.AsyncClient

**Yeni dosya:** `backend/app/services/http_pool.py`

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

**Değişecek dosyalar:**
- `workers/ip_reputation.py` — tüm `httpx.AsyncClient()` kullanımları
- `api/v1/ip_reputation.py` — test endpoint

### Görev 2.2: GeoIP Batch Endpoint

**Dosya:** `workers/ip_reputation.py`

```python
GEOIP_BATCH_URL = "http://ip-api.com/batch"

async def check_geoip_batch(ips: list[str]) -> dict[str, dict]:
    """ip-api.com batch API — 100 IP tek istekte."""
    client = await get_client("geoip")
    payload = [{"query": ip, "fields": "status,country,countryCode,city,isp,org,as"} for ip in ips[:100]]
    response = await client.post(GEOIP_BATCH_URL, json=payload)
    results = {}
    if response.status_code == 200:
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
```

### Görev 2.3: Akıllı Cache TTL

**Dosya:** `workers/ip_reputation.py`

```python
def _get_cache_ttl(abuse_score: int) -> int:
    """Skor bazlı dinamik cache süresi."""
    if abuse_score >= 80:
        return 6 * 3600      # 6 saat — kritik, sık güncelle
    elif abuse_score >= 50:
        return 12 * 3600     # 12 saat
    elif abuse_score > 0:
        return 24 * 3600     # 24 saat
    else:
        return 7 * 86400     # 7 gün — temiz IP
```

---

## FAZ 3: Lokal Blocklist Entegrasyonu

### Görev 3.1: Blocklist İndirme Worker'ı

**Yeni dosya:** `backend/app/workers/ip_blocklist_sync.py`

```python
# Ücretsiz IP blocklist kaynakları
BLOCKLIST_SOURCES = [
    {
        "name": "firehol_level1",
        "url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset",
        "interval": 3600,       # Saatlik güncelleme
        "redis_key": "blocklist:firehol_l1",
        "type": "netset",       # IP + CIDR karışık
    },
    {
        "name": "spamhaus_drop",
        "url": "https://www.spamhaus.org/drop/drop.txt",
        "interval": 86400,      # Günlük
        "redis_key": "blocklist:spamhaus_drop",
        "type": "cidr",
    },
    {
        "name": "spamhaus_edrop",
        "url": "https://www.spamhaus.org/drop/edrop.txt",
        "interval": 86400,
        "redis_key": "blocklist:spamhaus_edrop",
        "type": "cidr",
    },
    {
        "name": "dshield_top20",
        "url": "https://feeds.dshield.org/block.txt",
        "interval": 86400,
        "redis_key": "blocklist:dshield",
        "type": "dshield",      # Özel format
    },
    {
        "name": "emerging_threats",
        "url": "https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt",
        "interval": 86400,
        "redis_key": "blocklist:et_block",
        "type": "iplist",
    },
    {
        "name": "tor_exit_nodes",
        "url": "https://check.torproject.org/torbulkexitlist",
        "interval": 3600,
        "redis_key": "blocklist:tor_exit",
        "type": "iplist",
    },
]
```

**Redis yapısı:**
```
blocklist:combined          → SET (tüm bilinen kötü IP'ler, birleşik)
blocklist:combined_nets     → SORTED SET (CIDR ağları, prefix_len score)
blocklist:{source}_meta     → HASH (last_fetch, count, etag)
```

### Görev 3.2: Hızlı Lokal Lookup

```python
async def is_ip_in_local_blocklist(ip: str) -> tuple[bool, str]:
    """
    IP'nin lokal blocklist'te olup olmadığını kontrol et.
    Returns: (is_blocked, source_name)
    O(1) SET lookup + O(log N) subnet kontrolü
    """
    redis = await get_redis()

    # 1. Tam IP eşleşmesi (O(1))
    if await redis.sismember("blocklist:combined", ip):
        return True, "local_blocklist"

    # 2. CIDR subnet eşleşmesi (ağ tabanlı listeler için)
    # Not: Bu kısım için bir Bloom filter veya IP-to-prefix tree daha verimli olabilir
    # Basit yaklaşım: /8, /16, /24 prefix'lerini kontrol et
    addr = ipaddress.ip_address(ip)
    for prefix_len in [24, 16, 8]:
        network = ipaddress.ip_network(f"{ip}/{prefix_len}", strict=False)
        if await redis.sismember("blocklist:combined_nets", str(network)):
            return True, "local_subnet_blocklist"

    return False, ""
```

### Görev 3.3: IP Reputation Worker'a Entegrasyon

**Değişecek akış:**
```
Eski:
  IP → AbuseIPDB (1 API hakkı) → GeoIP → Cache → Uyarı

Yeni:
  IP → Lokal Blocklist? (0 API)
     ├── EVET → Engelle + Cache (AbuseIPDB sormaya gerek yok!)
     └── HAYIR → Redis Cache?
           ├── EVET → Cache'den dön
           └── HAYIR → AbuseIPDB (1 API hakkı) → GeoIP → Cache → Uyarı
```

---

## FAZ 4: Hibrit Skor Sistemi

### Görev 4.1: Lokal Davranış Skoru

**Yeni fonksiyon:** `workers/ip_reputation.py`

```python
async def _calculate_local_score(ip: str, redis) -> tuple[int, list[str]]:
    """
    Lokal sinyallerden IP risk skoru hesapla.
    AbuseIPDB'ye gerek duymadan risk değerlendirmesi.
    Returns: (score 0-100, reason_list)
    """
    score = 0
    reasons = []

    # 1. Lokal blocklist eşleşmesi (50 puan)
    in_blocklist, source = await is_ip_in_local_blocklist(ip)
    if in_blocklist:
        score += 50
        reasons.append(f"Lokal blocklist: {source}")

    # 2. Bağlantı hızı analizi (threat_analyzer'dan)
    rate_key = f"dns:rate:{ip}"
    rate = await redis.get(rate_key)
    if rate and int(rate) > 20:
        score += 20
        reasons.append(f"Yüksek bağlantı hızı: {rate}/dk")

    # 3. Bilinen saldırı pattern'i (DDoS set'inden)
    if await redis.sismember("ddos:attacker_ips", ip):
        score += 30
        reasons.append("DDoS saldırgan seti")

    # 4. Daha önce engellenmiş mi?
    if await redis.sismember("dns:threat:blocked", ip):
        score += 20
        reasons.append("Daha önce engellenmiş")

    # 5. Engellenen ülke (GeoIP varsa)
    geo_cache = await redis.hgetall(f"reputation:ip:{ip}")
    if geo_cache:
        cc = geo_cache.get("country_code", "")
        blocked_countries = await _get_blocked_countries(redis)
        if cc and cc.upper() in [c.upper() for c in blocked_countries]:
            score += 40
            reasons.append(f"Engellenen ülke: {cc}")

    return min(100, score), reasons
```

### Görev 4.2: Karar Motoru

```python
async def _should_query_abuseipdb(ip: str, local_score: int) -> bool:
    """
    AbuseIPDB'ye sormaya değer mi?
    Lokal skor yeterince yüksekse API harcamaya gerek yok.
    """
    # Lokal skor >= 70 → zaten yeterince tehlikeli, API'ye sormaya gerek yok
    if local_score >= 70:
        return False

    # Lokal skor 30-70 arası → belirsiz, API'ye sor (doğrulama)
    if local_score >= 30:
        return True

    # Lokal skor < 30 → muhtemelen temiz, yine de sor ama düşük öncelikle
    return True
```

---

## FAZ 5: Frontend İyileştirmeleri

### Görev 5.1: İstemci Tarafı Cache

```typescript
// Basit in-memory cache (TTL bazlı)
const cache = new Map<string, { data: any; ts: number }>();

function getCached<T>(key: string, ttlMs: number): T | null {
  const entry = cache.get(key);
  if (entry && Date.now() - entry.ts < ttlMs) return entry.data as T;
  return null;
}

// Kullanım:
const summary = getCached<ReputationSummary>("rep-summary", 60_000)
  ?? await fetchReputationSummary();
```

### Görev 5.2: API Kullanım Bar'ını Pasif Yap

- "API Kullanımını Kontrol Et" butonu kaldırılacak
- API kullanım bilgisi sadece worker'ın normal döngüsünde güncellenen Redis cache'den okunacak
- Frontend 120s'de bir arka planda çekecek (gerçek API çağrısı yapmayan endpoint'ten)

---

## SONUÇ

| Metrik | Şimdi | Hedef | İyileşme |
|--------|-------|-------|----------|
| AbuseIPDB sorgu/gün | ~900 | ~50-100 | %89-94 |
| GeoIP istek/döngü | 10 ayrı | 1 batch | %90 |
| HTTP client oluşturma | Her istekte | Paylaşılan | ∞ |
| Yanıt süresi (10 IP) | ~17s | ~3s | %82 |
| Lokal savunma katmanı | Yok | 6 kaynak | Yeni |
| Cache verimliliği | Sabit 24h | Dinamik 6h-7d | ~%50 daha az sorgu |
