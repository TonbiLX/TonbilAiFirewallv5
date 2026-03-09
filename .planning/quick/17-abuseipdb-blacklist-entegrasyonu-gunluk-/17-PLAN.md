---
plan: 17
title: "AbuseIPDB blacklist entegrasyonu + gunluk limit gercek API verisi ile senkronizasyon"
type: quick
tasks: 3
---

# Quick Task 17: AbuseIPDB Blacklist + Limit Senkronizasyonu

## Task 1: Gunluk Limit Senkronizasyonu (Backend + Frontend)

**Sorun:** Lokal counter 900/900 gosteriyor ama AbuseIPDB gercekte 611/1000 kullanmis. Lokal counter API'nin gercek verisiyle senkronize degil. Lokal counter dolunca API cagrilmiyor → header yakalanmiyor → dongusal tikaniklik.

**Dosyalar:**
- `backend/app/workers/ip_reputation.py` — _process_ip() limit kontrolu
- `backend/app/api/v1/ip_reputation.py` — /summary endpoint
- `frontend/src/components/firewall/IpReputationTab.tsx` — limit gosterimi

**Yapilacaklar:**
1. `_process_ip()`: Lokal counter (900) dolmus olsa bile, `reputation:abuseipdb_remaining` > 0 ise API cagrisina izin ver. Boylece lokal counter API ile senkronize kalir.
2. `_process_ip()`: Basarili API cagrisindan sonra, `X-RateLimit-Remaining` degerine gore lokal counter'i senkronize et: `redis.set(REDIS_KEY_DAILY_CHECKS, str(api_limit - api_remaining))`
3. `/summary` endpoint: `daily_checks_used` alani icin: eger `abuseipdb_remaining` varsa, bunu kullan (`api_limit - remaining`). Yoksa lokal counter.
4. Frontend: Limit gosteriminde AbuseIPDB verisi birincil kaynak olsun. "Gunluk Kullanim" progress bar'i AbuseIPDB verisini kullansin (varsa), yoksa lokal counter.

---

## Task 2: AbuseIPDB Blacklist Worker (Backend)

**Ozellik:** AbuseIPDB blacklist endpoint'i (5 sorgu/gun, 10000 IP/sorgu) ile en kotucul IP'lerin otomatik indirilmesi ve DNS engelleme ile entegrasyonu.

**Dosyalar:**
- `backend/app/workers/ip_reputation.py` — Yeni fonksiyonlar ekle
- `backend/app/api/v1/ip_reputation.py` — Yeni endpoint'ler ekle

**Yeni Redis Key'leri:**
- `reputation:blacklist_ips` → SET (blacklist IP adresleri)
- `reputation:blacklist_data:{ip}` → HASH (ip, score, country, lastReportedAt)
- `reputation:blacklist_last_fetch` → STRING (son fetch zamani ISO)
- `reputation:blacklist_count` → STRING (toplam IP sayisi)
- `reputation:blacklist_daily_fetches` → INTEGER (gunluk fetch sayaci, 86400s TTL)
- `reputation:blacklist_auto_block` → STRING ("1"/"0", varsayilan "1")
- `reputation:blacklist_min_score` → STRING (minimum skor filtresi, varsayilan "100")
- `reputation:blacklist_limit` → STRING (max IP sayisi, varsayilan "10000")

**Backend yapilacaklar:**

### Worker (ip_reputation.py):
1. `ABUSEIPDB_BLACKLIST_URL = "https://api.abuseipdb.com/api/v2/blacklist"`
2. `BLACKLIST_MAX_DAILY = 5` sabiti
3. `fetch_abuseipdb_blacklist()` async fonksiyonu:
   - API key kontrolu
   - Gunluk fetch sayaci kontrolu (max 5)
   - GET /api/v2/blacklist?confidenceMinimum={min_score}&limit={limit}
   - Her IP icin: `reputation:blacklist_ips` SET'e ekle + `reputation:blacklist_data:{ip}` HASH'e kaydet
   - Auto-block etkin ise: Her IP icin `auto_block_ip()` cagir
   - `reputation:blacklist_last_fetch` ve `reputation:blacklist_count` guncelle
   - X-RateLimit header'larini kaydet
4. `_run_reputation_cycle()` icinde: Her 24 saatte 1 kez blacklist fetch tetikle (son fetch > 24 saat ise)

### API (ip_reputation.py):
5. `GET /blacklist` — Blacklist IP'lerini listele (Redis'ten)
6. `POST /blacklist/fetch` — Manuel blacklist fetch tetikle
7. `GET /blacklist/config` — Blacklist ayarlari (auto_block, min_score, limit, daily_fetches)
8. `PUT /blacklist/config` — Blacklist ayarlarini guncelle

---

## Task 3: AbuseIPDB Blacklist UI (Frontend)

**Dosyalar:**
- `frontend/src/components/firewall/IpReputationTab.tsx` — Blacklist bolumu ekle
- `frontend/src/services/ipReputationApi.ts` — Blacklist API fonksiyonlari ekle

**Frontend yapilacaklar:**

### API fonksiyonlari (ipReputationApi.ts):
1. `fetchBlacklist()` — GET /ip-reputation/blacklist
2. `triggerBlacklistFetch()` — POST /ip-reputation/blacklist/fetch
3. `fetchBlacklistConfig()` — GET /ip-reputation/blacklist/config
4. `updateBlacklistConfig(data)` — PUT /ip-reputation/blacklist/config

### UI (IpReputationTab.tsx):
Mevcut tablonun UZERINE "AbuseIPDB Kara Liste" bolumu ekle:

1. **Kara Liste Ozet Karti:**
   - Toplam blacklist IP sayisi
   - Son fetch zamani
   - Gunluk fetch: X/5
   - "Simdi Cek" butonu (POST /blacklist/fetch)

2. **Ayarlar:**
   - Auto-block toggle (varsayilan: acik)
   - Minimum skor filtresi (input, varsayilan 100)
   - Max IP limiti (input, varsayilan 10000)

3. **Kara Liste Tablosu:**
   - IP adresi, skor, ulke (flag+code), son raporlanma tarihi
   - Siralama: skor (desc), IP, ulke
   - Arama filtresi

4. **Stil:** Cyberpunk tema, neon-magenta (#FF00E5) vurgulu (kara liste = tehlike)
