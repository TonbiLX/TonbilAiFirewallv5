# IP Reputation Sistemi — Kapsamlı Analiz Raporu

**Tarih:** 2026-03-12
**Analiz Ekibi:** 5 paralel ajan + manuel kod incelemesi

---

## 1. MEVCUT DURUM ÖZETİ

### 1.1 Dosya Haritası

| Dosya | Satır | Rol |
|-------|-------|-----|
| `backend/app/api/v1/ip_reputation.py` | 958 | API endpoint'ler (15 endpoint) |
| `backend/app/workers/ip_reputation.py` | 958 | Worker: AbuseIPDB + GeoIP döngüsü |
| `backend/app/services/domain_reputation.py` | 250 | Domain risk skoru (Shannon entropi, TLD) |
| `backend/app/workers/threat_analyzer.py` | ~1500 | DNS tehdit analizi + otomatik engelleme |
| `backend/app/models/ip_reputation_check.py` | 30 | SQL model |
| `frontend/src/components/firewall/IpReputationTab.tsx` | ~1800 | UI bileşeni |
| `frontend/src/services/ipReputationApi.ts` | 28 | API istemci |

### 1.2 Harici API Kullanımı

| API | Endpoint | Kullanım | Ücretsiz Limit | Maliyet Sorunu |
|-----|----------|----------|-----------------|----------------|
| AbuseIPDB `/check` | Tekil IP sorgu | Her 300s döngüde max 10 IP | 1000/gün | **YÜKSEK** |
| AbuseIPDB `/check-block` | Subnet analizi | Manuel + kritik IP tetikli | Ayrı havuz | ORTA |
| AbuseIPDB `/blacklist` | Kara liste | 24 saatte 1 otomatik | 5/gün | DÜŞÜK |
| ip-api.com `/json` | GeoIP bilgisi | Her IP kontrolünde | 45/dakika | ORTA |

---

## 2. KRİTİK SORUNLAR (API İsrafı)

### 2.1 🔴 Summary endpoint'te gereksiz API çağrısı (Satır 228-249)
**Dosya:** `api/v1/ip_reputation.py:228-249`

`/ip-reputation/summary` endpoint'i çağrıldığında, Redis'te rate limit cache'i yoksa **8.8.8.8'e canlı sorgu atıyor** ve 1 API hakkı harcıyor. Bu, kullanıcı her sayfa yenilemesinde gerçekleşebilir.

**İsraf:** Sayfa her yenilendiğinde 1 API hakkı

### 2.2 🔴 API-usage endpoint'i 1 hak harcıyor (Satır 475-580)
**Dosya:** `api/v1/ip_reputation.py:475-580`

`/ip-reputation/api-usage` endpoint'i her çağrıldığında AbuseIPDB'ye **gerçek bir IP sorgusu** atarak header'dan rate limit bilgisi okuyor. Yorum bile yazıyor: "Bu çağrı 1 check hakkı harcar."

**İsraf:** Kullanıcı "API Kullanımı" butonuna her bastığında 1 API hakkı

### 2.3 🔴 Check-block API usage endpoint'i de 1 hak harcıyor (Satır 658-710)
**Dosya:** `api/v1/ip_reputation.py:672-691`

`/ip-reputation/check-block/api-usage` endpoint'i aynı şekilde gerçek subnet sorgusu yaparak 1 check-block hakkı harcıyor.

### 2.4 🔴 Blacklist API usage endpoint'i 1 blacklist hakkı harcıyor (Satır 739-821)
**Dosya:** `api/v1/ip_reputation.py:762-793`

Sadece API kullanım bilgisi almak için blacklist endpoint'ine gerçek sorgu atılıyor. Günlük 5 haktan 1'i boşa gidiyor.

### 2.5 🟠 GeoIP her IP için ayrı sorgu (ip-api.com)
**Dosya:** `workers/ip_reputation.py:150-171`

Her IP için ayrı HTTP isteği yapılıyor ve 1.5s bekleniyor. ip-api.com **batch endpoint** destekliyor (100 IP/istek) ama kullanılmıyor.

### 2.6 🟠 Her IP kontrolünde yeni httpx.AsyncClient oluşturuluyor
**Dosya:** `workers/ip_reputation.py:112, 153`

Her `check_abuseipdb()` ve `check_geoip()` çağrısında yeni HTTP client oluşturuluyor. Connection pool paylaşılmıyor.

### 2.7 🟠 Cache TTL stratejisi yetersiz
- IP reputation cache: 24 saat sabit TTL
- Düşük skorlu (güvenli) IP'ler de 24 saat sonra yeniden sorgulanıyor
- Yüksek riskli IP'lerin daha sık güncellenmesi gerekiyor

### 2.8 🟡 Frontend'de gereksiz API çağrıları
- Sayfa açıldığında aynı anda `summary`, `config`, `ips`, `blacklist` çağrıları
- Tab geçişlerinde tüm veriler yeniden çekiliyor
- Debounce/throttle eksik

---

## 3. MEVCUT MİMARİ AKIŞ

```
Her 300 saniyede:
  1. Redis'ten aktif flow IP'lerini topla
  2. Cache'de olmayanları filtrele (max 10)
  3. Her IP için:
     a. AbuseIPDB /check → 1 API hakkı (10s timeout)
     b. 1.5s bekle (GeoIP rate limit)
     c. ip-api.com /json → GeoIP bilgisi
     d. Redis HASH'e yaz (24h TTL)
     e. SQL UPSERT
     f. Skor >= 80 → auto_block + subnet check
     g. Skor >= 50 → AiInsight + Telegram
```

**Günlük maks AbuseIPDB tüketimi:**
- Worker: 10 IP × (86400/300) döngü = ~2880 sorgu/gün → LIMIT AŞIMI!
- Gerçekte DAILY_LIMIT=900 ile sınırlı ama yine de çok
- + Summary/API-usage UI çağrıları ekstra harcıyor

---

## 4. ÖNERİLEN İYİLEŞTİRMELER

### Faz 1: Acil API İsrafı Düzeltmeleri (0 ek API maliyeti)

#### 4.1 Rate limit bilgisini API çağrısı yapmadan öğren
**Sorun:** 3 ayrı "api-usage" endpoint'i gerçek sorgu yapıyor
**Çözüm:** Rate limit header'larını her normal API çağrısında zaten kaydediyoruz (`reputation:abuseipdb_remaining`). API-usage endpoint'leri sadece Redis'ten okumalı — cache yoksa "bilinmiyor" döndürmeli, gerçek sorgu YAPMAMALI.

**Tasarruf:** Günde ~10-50 gereksiz API çağrısı

#### 4.2 Summary endpoint'inden canlı sorguyu kaldır
**Çözüm:** Redis'te rate limit verisi yoksa `null` döndür, frontend "Bilinmiyor" göstersin.

**Tasarruf:** Sayfa yenileme başına 1 API hakkı

### Faz 2: Katmanlı Savunma Mimarisi (API kullanımını %80 azalt)

#### 4.3 Lokal IP Blocklist Entegrasyonu
**Fikir:** Ücretsiz, açık kaynak IP blocklist'leri indirip lokal olarak kontrol et. AbuseIPDB'yi sadece bu listelerde OLMAYAN IP'ler için kullan.

**Kaynaklar:**
1. **Firehol Level 1-4:** ~50K kötü IP, saatlik güncelleme
2. **Spamhaus DROP/EDROP:** ISP seviyesi kötü ağlar
3. **DShield Top 20:** Günlük en aktif saldırganlar
4. **Tor Exit Nodes:** Günlük güncelleme
5. **Emerging Threats:** Compromised IP listesi

**Uygulama:**
```
Yeni akış:
1. Lokal blocklist kontrolü (SET lookup, O(1)) → Zaten kötü bilinen? ENGELLE
2. Redis cache kontrolü → Daha önce sorgulandı mı? CACHE'den dön
3. Davranış analizi → Brute force/scan pattern? LOKAl SKOR VER
4. AbuseIPDB sorgusu → Sadece gerçekten bilinmeyen IP'ler için
```

**Tahmini tasarruf:** API çağrılarının %60-80'i gereksiz hale gelir

#### 4.4 GeoIP Batch Sorgu
**Sorun:** ip-api.com'a her IP için ayrı istek + 1.5s bekleme
**Çözüm:** `http://ip-api.com/batch` endpoint'i ile 100 IP'yi tek istekte sorgula

**Tasarruf:** 10 IP için 15s bekleme → 1 istek (<1s)

#### 4.5 Akıllı TTL Stratejisi
```python
# Skor bazlı dinamik cache TTL
if abuse_score >= 80:
    ttl = 6 * 3600     # 6 saat (kritik — sık güncelle)
elif abuse_score >= 50:
    ttl = 12 * 3600    # 12 saat
elif abuse_score > 0:
    ttl = 24 * 3600    # 24 saat
else:
    ttl = 7 * 86400    # 7 gün (temiz IP — nadiren sorgula)
```

**Tasarruf:** Temiz IP'ler 7 gün boyunca yeniden sorgulanmaz → %50+ azalma

### Faz 3: Paylaşılan HTTP Client + Connection Pool

#### 4.6 Singleton httpx.AsyncClient
```python
# Uygulamanın yaşam döngüsüyle aynı
_http_client: httpx.AsyncClient | None = None

async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=10,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
        )
    return _http_client
```

**Fayda:** TCP connection reuse, DNS resolution cache, daha hızlı istekler

### Faz 4: Lokal Davranış Bazlı IP Skorlama

#### 4.7 Hibrit Skor Sistemi
Mevcut `threat_analyzer.py` zaten bazı davranış tespiti yapıyor. Bunu IP reputation ile birleştir:

```python
# Lokal skor bileşenleri:
local_score = 0
local_score += connection_rate_score(ip)    # Bağlantı hızı anormalliği (0-25)
local_score += port_scan_score(ip)          # Port tarama tespiti (0-25)
local_score += brute_force_score(ip)        # Brute force pattern (0-25)
local_score += blocklist_score(ip)          # Lokal blocklist eşleşmesi (0-25)

# Sadece local_score < 50 VE bilinen listede değilse AbuseIPDB'ye sor
if local_score < 50 and not in_local_blocklist(ip):
    abuseipdb_score = await check_abuseipdb(ip)
    final_score = max(local_score, abuseipdb_score)
else:
    final_score = local_score  # API harcamaya gerek yok
```

### Faz 5: Frontend Optimizasyonu

#### 4.8 İstek Birleştirme ve Önbellekleme
- **Stale-While-Revalidate:** Eski veriyi göster, arka planda güncelle
- **API kullanım bar'ını Redis'ten oku:** Gerçek API çağrısı yapma
- **Tab geçişlerinde cache kullan:** 30 saniyelik istemci tarafı cache
- **Polling interval azalt:** Arka plan yenilemesi 60s → 120s

---

## 5. ENDÜSTRİ KARŞILAŞTIRMASI

| Özellik | TonbilAiOS (Şimdi) | pfSense | CrowdSec | OPNsense |
|---------|--------------------|---------|-----------| ---------|
| Lokal blocklist | ❌ | ✅ pfBlockerNG | ✅ Topluluk | ✅ ET |
| Batch GeoIP | ❌ | ✅ MaxMind lokal | ✅ Lokal DB | ✅ GeoIP2 |
| API çağrı optimizasyonu | ❌ | N/A | ✅ Akıllı | N/A |
| Davranış bazlı skor | Kısmi | ✅ Snort | ✅ Scenarios | ✅ Suricata |
| Katmanlı savunma | ❌ | ✅ | ✅ | ✅ |
| Dinamik cache TTL | ❌ | N/A | ✅ | N/A |

---

## 6. UYGULAMA ÖNCELİK SIRASI

### Öncelik 1 — Acil (1-2 saat)
- [ ] API-usage endpoint'lerinden canlı sorguları kaldır (4.1, 4.2)
- [ ] Frontend'de gereksiz çağrıları azalt (4.8)

### Öncelik 2 — Yüksek (4-6 saat)
- [ ] GeoIP batch sorgu (4.4)
- [ ] Akıllı TTL stratejisi (4.5)
- [ ] Paylaşılan HTTP client (4.6)

### Öncelik 3 — Orta (8-12 saat)
- [ ] Lokal blocklist entegrasyonu (4.3)
- [ ] Blocklist worker: Firehol, Spamhaus, DShield indirme

### Öncelik 4 — Uzun vadeli (1-2 gün)
- [ ] Hibrit skor sistemi (4.7)
- [ ] CrowdSec benzeri topluluk entegrasyonu

---

## 7. TAHMİNİ TASARRUF

| Değişiklik | API Tasarruf | Performans |
|-----------|-------------|-----------|
| API-usage fix | ~10-50 sorgu/gün | Anlık |
| Akıllı TTL | ~%50 azalma | 7 gün cache temiz IP |
| Lokal blocklist | ~%60-80 azalma | O(1) SET lookup |
| GeoIP batch | %90 istek azalma | 15s → <1s |
| Hibrit skor | ~%90 azalma | Lokal hesaplama |
| **TOPLAM** | **%85-95 API tasarrufu** | **Çok daha hızlı** |

Mevcut: ~900 AbuseIPDB sorgu/gün → Hedef: ~50-100 sorgu/gün
