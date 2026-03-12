# Katmanli Savunma Algoritmalari ve API-Verimli IP Itibar Yonetimi

**Domain:** Network Security / IP Reputation Management / Defense in Depth
**Researched:** 2026-03-12
**Overall Confidence:** HIGH
**Context:** TonbilAiOS v5 mevcut IP reputation sistemi (AbuseIPDB tabanli) uzerinde katmanli savunma mimarisi onerisi

---

## 1. MEVCUT DURUM ANALIZI

### 1.1 Mevcut Sistem Yapisi

Mevcut `ip_reputation.py` worker'i tek katmanli bir yaklasim kullaniyor:

```
Her 300s:
  Redis'ten aktif flow IP'leri topla
  → Cache'de yoksa: AbuseIPDB + ip-api.com sorgula (max 10/dongu)
  → Skor >= 50: warning, >= 80: critical + auto_block
```

**Mevcut sorunlar:**
- Tum IP'ler icin dogrudan AbuseIPDB API sorgusu (1000/gun ucretsiz limit)
- Dongude max 10 IP: yuksek trafik aninda 100+ yeni IP geldiginde kuyruk birikmesi
- ip-api.com icin 1.5s bekleme (40/dk limit): serisel islem, yavas
- Lokal IP listeleri (firehol, spamhaus) kullanilmiyor
- GeoIP lookup dis sunucuya bagimli (ip-api.com)
- threat_analyzer.py sinyalleri (DGA, flood, scan) IP reputation kararina girdi olmuyor

### 1.2 Mevcut Guclu Yanlar

- Redis cache (24s TTL) calisiyor
- SQL kalici depo (UPSERT) mevcut
- Auto-block mekanizmasi aktif (threat_analyzer.auto_block_ip)
- Blacklist endpoint entegrasyonu var (AbuseIPDB blacklist)
- Subnet analizi var (check-block)
- Rate limit header senkronizasyonu var
- Ulke bazli engelleme var

---

## 2. KATMANLI SAVUNMA MIMARISI (DEFENSE IN DEPTH)

### 2.1 Onerilen 4-Katmanli Pipeline

```
Gelen IP
    |
    v
[Layer 1] Lokal Blocklist/Allowlist (0ms, sifir API maliyeti)
    |  HIT → BLOCK/ALLOW (pipeline durur)
    |  MISS → devam
    v
[Layer 2] Lokal Itibar Veritabani (1-5ms, sifir API maliyeti)
    |  KNOWN BAD → BLOCK
    |  KNOWN GOOD → ALLOW
    |  UNKNOWN → devam
    v
[Layer 3] Davranis Analizi + Topluluk (10-50ms, sinirli API)
    |  RISK SKORU hesapla
    |  DUSUK RISK → ALLOW (API sorgusu YAPMA)
    |  ORTA RISK → izle, API sorgulama
    |  YUKSEK RISK → devam (API dogrulama gerekli)
    v
[Layer 4] Harici API Sorgusu (100-500ms, kisitli kota)
    |  Sadece Layer 3'te YUKSEK RISK alan IP'ler
    |  AbuseIPDB check
    |  Sonucu cache'le ve Layer 2'ye ekle
```

**Tasarruf tahmini:** Mevcut sistemde her IP icin API cagrisi yapilirken, katmanli yaklasimda tahminen IP'lerin %85-95'i Layer 1-2'de filtrelenir. Bu, gunluk 1000 API kotasinin ~50-150 gercekten supheyli IP'ye harcanmasini saglar.

### 2.2 Layer 1: Lokal Blocklist/Allowlist

**Amac:** Bilinen kotu/iyi IP'leri sifir maliyetle aninda filtrele.

#### Ucretsiz IP Listesi Kaynaklari

| Kaynak | Icerik | Boyut | Guncelleme | Format | URL |
|--------|--------|-------|------------|--------|-----|
| **Firehol Level 1** | dshield + spamhaus DROP/EDROP + fullbogons + feodo | ~15K IP/subnet | 6 saat | netset | https://iplists.firehol.org/ |
| **Firehol Level 2** | Level 1 + blocklist.de + openbl + autoshun | ~50K IP | 6 saat | netset | https://iplists.firehol.org/ |
| **Spamhaus DROP** | Hijacked netblock'lar (tum trafigi dusur) | ~1K subnet | 12 saat | netset | https://www.spamhaus.org/drop/drop.txt |
| **Spamhaus EDROP** | Extended DROP | ~500 subnet | 12 saat | netset | https://www.spamhaus.org/drop/edrop.txt |
| **DShield Top 20** | En aktif saldiri /24 subnet'leri | 20 subnet | 1 saat | text | https://feeds.dshield.org/block.txt |
| **Emerging Threats** | Varsayilan blocklist | ~10K IP | 6 saat | text | https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt |
| **Tor Exit Nodes** | Tor cikis dugumleri | ~1-2K IP | 1 saat | text | https://check.torproject.org/torbulklist/ |
| **Abuse.ch Feodo** | Botnet C&C sunuculari | ~500 IP | 5 dk | text | https://feodotracker.abuse.ch/downloads/ipblocklist.txt |
| **Abuse.ch SSLBL** | SSL blacklist IP'leri | ~1K IP | 15 dk | csv | https://sslbl.abuse.ch/blacklist/sslipblacklist.txt |

**Oneri:** Firehol Level 1 + Tor Exit Nodes + Abuse.ch Feodo ile basla. Bu kombinasyon bilinen zarali IP'lerin >95%'ini kapsar.

#### Guncelleme Stratejisi

```python
# Onerilen guncelleme altyapisi
FEED_CONFIG = {
    "firehol_level1": {
        "url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset",
        "interval_hours": 6,
        "format": "netset",  # IP ve CIDR karisik
        "priority": 1,       # En yuksek oncelik
    },
    "firehol_level2": {
        "url": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level2.netset",
        "interval_hours": 12,
        "format": "netset",
        "priority": 2,
    },
    "tor_exit": {
        "url": "https://check.torproject.org/torbulklist/",
        "interval_hours": 1,
        "format": "ip_list",
        "priority": 3,
    },
    "feodo": {
        "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
        "interval_hours": 1,
        "format": "ip_list",
        "priority": 1,
    },
}
```

#### nftables Set Yukleme (Pi Performans Notlari)

```
KRITIK: nftables'a buyuk IP seti yukleme Pi'de sorunlu olabilir.
- 10K IP: ~50MB RAM, sorunsuz
- 50K IP: ~250MB RAM, kabul edilebilir
- 100K+ IP: 1GB+ RAM, Pi 4 icin riskli (toplam 4GB RAM)

ONERI:
- Firehol Level 1 (~15K): guvenli
- Firehol Level 2 (~50K): dikkatli (RAM izle)
- Level 3-4: kullanma (cok buyuk, false positive riski)

STRATEJI: nftables set yerine Redis SET kullan + lookup pipeline'da kontrol et.
nftables set'i sadece "kesin engelle" listesi icin kullan (Spamhaus DROP, Feodo).
```

**Confidence:** HIGH - Firehol, Spamhaus, DShield endustri standardi kaynaklar. nftables performans verileri Red Hat benchmark'larindan.

### 2.3 Layer 2: Lokal Itibar Veritabani

**Amac:** Daha once sorgulanmis IP'lerin sonuclarini lokal olarak sakla + GeoIP/ASN bilgisiyle zenginlestir.

#### MaxMind GeoLite2 Entegrasyonu

Mevcut sistem ip-api.com'a bagimli (40/dk rate limit). MaxMind GeoLite2 ile lokal cozum:

```python
# pip install geoip2
import geoip2.database

# Haftalik guncellenen .mmdb dosyalari (~70MB toplam)
city_reader = geoip2.database.Reader('/opt/tonbilaios/data/GeoLite2-City.mmdb')
asn_reader  = geoip2.database.Reader('/opt/tonbilaios/data/GeoLite2-ASN.mmdb')

def lookup_local(ip: str) -> dict:
    """Lokal GeoIP + ASN lookup — 0 API cagrisi, <1ms."""
    result = {}
    try:
        city = city_reader.city(ip)
        result["country"] = city.country.iso_code
        result["city"] = city.city.name or ""
    except Exception:
        pass
    try:
        asn = asn_reader.asn(ip)
        result["asn"] = f"AS{asn.autonomous_system_number}"
        result["org"] = asn.autonomous_system_organization or ""
    except Exception:
        pass
    return result
```

**MaxMind hesap gereksinimleri:**
- Ucretsiz GeoLite2 hesabi: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/
- Haftalik otomatik guncelleme: `geoipupdate` araci ile
- Dosya boyutu: City ~70MB, ASN ~8MB, Country ~5MB
- Lisans: CC BY-SA 4.0 (ucretsiz kullanim, atif gerekli)

**ASN Bazli Toplu Degerlendirme:**
Bazi ASN'ler bilinen zarali hosting saglayicilarina aittir. Lokal ASN veritabani ile:
- Bilinen hosting ASN'leri (Hetzner, OVH, DigitalOcean): otomatik yuksek risk degil ama izleme onceliklendirme
- Bilinen zarali ASN'ler (bullet-proof hosting): otomatik yuksek risk skoru

#### Lokal IP Reputation Cache Yapisi

```
Redis HASH: reputation:local:{ip}
  - source: "firehol_l1" | "spamhaus" | "abuseipdb" | "local_behavior"
  - risk_score: 0-100
  - country: "TR"
  - asn: "AS12345"
  - org: "Example ISP"
  - first_seen: ISO timestamp
  - last_seen: ISO timestamp
  - ttl_class: "static" | "dynamic"

Static TTL (liste tabanli): Liste guncellenene kadar gecerli
Dynamic TTL (API/davranis tabanli): 24s (dusuk risk) / 6s (orta) / 1s (yuksek)
```

**Confidence:** HIGH - MaxMind GeoLite2 endustri standardi, Python kutuphanesi (geoip2) olgun ve iyi dokumante.

### 2.4 Layer 3: Topluluk + Davranis Analizi

#### CrowdSec CTI Entegrasyonu

CrowdSec, topluluk tabanli (crowdsourced) tehdit istihbarati saglayan bir platformdur.

```python
# CrowdSec CTI API - smoke endpoint (hizli kontrol)
CROWDSEC_CTI_URL = "https://cti.api.crowdsec.net/v2/smoke/{ip}"

# Ucretsiz plan:
# - 50 sorgu/gun (CTI API key ile)
# - Veya CrowdSec agent kurarak yerel LAPI + topluluk datalari

# pycrowdsec kutuphanesi:
# pip install pycrowdsec
from pycrowdsec.client import StreamClient
client = StreamClient(api_key="...", lapi_url="http://localhost:8080")
decisions = client.get_current_decisions()
```

**CrowdSec vs AbuseIPDB Karsilastirma:**

| Ozellik | CrowdSec CTI | AbuseIPDB |
|---------|--------------|-----------|
| Ucretsiz sorgu/gun | 50 (API) veya sinirsin (agent) | 1000 |
| Veri kaynagi | Topluluk sensorleri (canlı) | Kullanici raporlari |
| Lokal agent | Evet (CrowdSec bouncer) | Yok |
| Yanit suresi | <100ms | ~200-500ms |
| IP detay | Davranis profili, attack_details | Skor + rapor sayisi |

**Oneri:** CrowdSec agent kurmayi dusun (Pi'de calisir) — bu sayede topluluk verisi lokal olarak kullanilabilir, API limiti olmadan. Ancak bu ek bir daemon ve kaynak tuketimi demek. Alternatif olarak sadece CTI API kullanimi (50/gun) ile baslayip, yuksek riskli IP'ler icin AbuseIPDB oncesi ek filtreleme sagla.

#### Lokal Davranis Analizi Sinyalleri

Mevcut `threat_analyzer.py` zaten su sinyalleri uretiyor:

| Sinyal | Mevcut Tespit | IP Reputation'a Etkisi |
|--------|--------------|----------------------|
| DNS flood (>20 sorgu/dk) | Evet, `report_external_query()` | risk_score += 30 |
| DGA algilama (entropy > 3.5) | Evet, `_check_dga()` | risk_score += 25 |
| Subnet flood (5+ IP/5dk) | Evet, subnet izleme | risk_score += 20 (tum subnet) |
| Koordineli tarama | Evet, scan pattern | risk_score += 15 |
| Supheli DNS query type | Evet, AXFR/ANY/NULL | risk_score += 10 |
| Port scan (conntrack) | Kismen (flow_tracker) | risk_score += 25 |
| Brute force (SSH/FTP) | Kismen (nftables meter) | risk_score += 35 |
| SYN flood | Evet (DDoS servisi) | risk_score += 40 |

**Risk Skoru Hesaplama Algoritmasi:**

```python
def calculate_composite_risk(ip: str, signals: dict) -> int:
    """
    Birikimli risk skoru hesapla.
    Lokal sinyaller + liste uyeligi + gecmis itibar birlestirilir.

    Returns: 0-100 arasi risk skoru
    """
    score = 0

    # Layer 1: Liste uyeligi (kesin bilgi)
    if signals.get("in_blocklist"):
        return 100  # Aninda engelle
    if signals.get("in_allowlist"):
        return 0    # Aninda izin ver

    # Layer 2: GeoIP/ASN bazli
    if signals.get("country_blocked"):
        score += 50
    if signals.get("suspicious_asn"):
        score += 15

    # Layer 3: Davranis bazli (birikimli)
    score += signals.get("dns_flood_score", 0)      # 0-30
    score += signals.get("dga_score", 0)             # 0-25
    score += signals.get("scan_score", 0)            # 0-25
    score += signals.get("brute_force_score", 0)     # 0-35
    score += signals.get("syn_flood_score", 0)       # 0-40

    # Layer 4: Gecmis API sonucu (cache'den)
    cached_abuse = signals.get("cached_abuse_score", 0)
    if cached_abuse > 0:
        score = max(score, cached_abuse)  # API skoru varsa en az o kadar

    return min(score, 100)
```

**API Sorgulama Esikleri:**

| Risk Skoru | Aksiyon | API Kullanimi |
|-----------|---------|--------------|
| 0-20 | Izin ver, loglama | YOK |
| 21-40 | Izle, metadata kaydet | YOK |
| 41-60 | CrowdSec CTI kontrol | CrowdSec (50/gun) |
| 61-80 | AbuseIPDB kontrol | AbuseIPDB (1000/gun) |
| 81-100 | Aninda engelle + API dogrula | AbuseIPDB + log |

**Confidence:** MEDIUM - CrowdSec CTI API limitleri dogrulanmali. Davranis sinyalleri mevcut kodda var ancak birikimli skor entegrasyonu yeni gelistirme gerektirir.

### 2.5 Layer 4: Harici API Sorgusu (AbuseIPDB)

Mevcut AbuseIPDB entegrasyonu korunur ancak sadece yuksek risk skoru olan IP'ler icin tetiklenir.

**Mevcut vs Onerilen Karsilastirma:**

| Metrik | Mevcut | Onerilen |
|--------|--------|----------|
| API cagrisi/dongu | 10 (tum yeni IP'ler) | 1-3 (sadece risk > 60) |
| Gunluk tuketim | ~300-900 sorgu | ~50-150 sorgu |
| Cache TTL | 24 saat (sabit) | Dinamik: 1s-24s (riske gore) |
| ip-api.com cagrisi | Her IP icin | 0 (MaxMind lokal) |
| Karar suresi | ~2s/IP (API bekleme) | <5ms (lokal katmanlar) |

---

## 3. API MALIYET OPTIMIZASYONU

### 3.1 Lazy Evaluation Pipeline

```
IP geldi → Layer 1 kontrol (O(1) SET lookup)
  |
  HIT? → Son. (API cagrisi: 0)
  |
  MISS → Layer 2 kontrol (O(1) HASH lookup)
  |
  KNOWN? → Son. (API cagrisi: 0)
  |
  UNKNOWN → Layer 3 risk skoru hesapla
  |
  risk < 60? → Sadece logla. (API cagrisi: 0)
  |
  risk >= 60? → Layer 4: AbuseIPDB sorgu (API cagrisi: 1)
```

### 3.2 TTL-Based Caching Stratejisi

| Kategori | TTL | Mantik |
|----------|-----|--------|
| **Temiz IP (skor 0-20)** | 24 saat | Dusuk risk, uzun cache |
| **Suphelimsı (skor 21-50)** | 12 saat | Orta risk, makul cache |
| **Supheli (skor 51-80)** | 6 saat | Yuksek risk, sik yenileme |
| **Tehlikeli (skor 81-100)** | 1 saat | Cok yuksek risk, hizli guncelleme |
| **Blocklist IP** | Liste guncellenene kadar | Statik, TTL yok |
| **Allowlist IP** | Sinirsiz | Kullanici yonetimli |

### 3.3 Bloom Filter ile Hizli On-Filtreleme

Buyuk IP listelerinde (50K+) uyelik testi icin Bloom Filter kullanimi:

**Secenek A: Redis Bloom Filter (redis-stack modulu)**

```python
# Redis BF.* komutlari — redis-stack veya RedisBloom modulu gerekli
# Pi'de redis-stack yuklu degilse, standart Redis'te KULLANILAMAZ

await redis.execute_command("BF.RESERVE", "ip:blocklist_bloom", 0.001, 100000)
await redis.execute_command("BF.ADD", "ip:blocklist_bloom", "1.2.3.4")
exists = await redis.execute_command("BF.EXISTS", "ip:blocklist_bloom", "5.6.7.8")
```

**Secenek B: Python rbloom (Rust tabanli, hizli)**

```python
# pip install rbloom
from rbloom import Bloom

# 100K IP icin ~120KB bellek, %0.1 false positive
bloom = Bloom(100000, 0.001)
bloom.add("1.2.3.4")
if "5.6.7.8" in bloom:
    # Muhtemelen blocklist'te — Redis SET ile kesin dogrulama yap
    pass
```

**Oneri:** Pi'de Redis Bloom Filter modulu kurulumuna gerek yok. Python `rbloom` kutuphanesi yeterli — Rust tabanli, hizli, bellege yuklenir. Bloom Filter'i sadece "quick reject" icin kullan: "Bu IP kesinlikle listede degil" diyebilmek icin. Pozitif sonuc geldiginde Redis SET ile kesin dogrulama yap.

**Confidence:** HIGH - Bloom Filter performansi akademik olarak kanitlanmis. rbloom kutuphanesi PyPI'da mevcut.

### 3.4 Batch vs Single Query Analizi

| Yontem | AbuseIPDB Destegi | Avantaj | Dezavantaj |
|--------|-------------------|---------|------------|
| **Tekli `/check`** | Evet | Anlik sonuc | 1 sorgu/IP |
| **Batch `/check-block`** | Evet (CIDR) | Tek sorguda 256 IP (/24) | Sadece subnet bazli |
| **Blacklist `/blacklist`** | Evet | 10K+ IP tek sorguda | Gunluk 5 sorgu limiti |

**Oneri:** Mevcut `check-block` entegrasyonu iyi kullaniliyor (kritik IP'nin /24'u analiz ediliyor). Ek olarak, blacklist endpoint'ini gunluk 1 kez otomatik cagirarak "en tehlikeli" IP'leri lokal cache'e al.

### 3.5 API Quota Tracking ve Akilli Butceleme

```python
class APIBudgetManager:
    """
    Gunluk API butcesini akilli dagitir.

    Ornek: 1000 sorgu/gun
    - Otomatik worker: max 600 (saatte ~25)
    - Manuel kontrol: max 200 (UI'dan tetiklenen)
    - Rezerv: 200 (acil durumlar icin)
    """

    TOTAL_DAILY = 1000
    AUTO_BUDGET = 600
    MANUAL_BUDGET = 200
    RESERVE_BUDGET = 200

    async def can_auto_query(self) -> bool:
        """Worker otomatik sorgu yapabilir mi?"""
        used = await self._get_auto_used()
        hour = datetime.now().hour
        # Saate gore butce dagitimi (gece daha az, gunduz daha cok)
        hourly_budget = self.AUTO_BUDGET / 24
        used_this_hour = await self._get_hourly_used()
        return used_this_hour < hourly_budget * 1.5  # %50 esneklik
```

---

## 4. AKILLI SORGULAMA ALGORITMALARI

### 4.1 Risk Bazli Onceliklendirme

```python
async def prioritize_ips(unchecked_ips: list[str]) -> list[str]:
    """
    Kontrol edilmemis IP'leri risk onceligi ile sirala.
    En riskli IP'ler once kontrol edilir (API kotasi verimli kullanimi).
    """
    scored = []
    for ip in unchecked_ips:
        pre_score = 0

        # 1. Davranis sinyali varsa (threat_analyzer'dan)
        threat_score = await redis.get(f"dns:threat:score:{ip}")
        if threat_score:
            pre_score += int(threat_score)

        # 2. Cografi on-filtreleme
        geo = lookup_local_geo(ip)  # MaxMind lokal
        if geo.get("country") in BLOCKED_COUNTRIES:
            pre_score += 50
        if geo.get("country") in HIGH_RISK_COUNTRIES:
            pre_score += 20

        # 3. ASN bazli
        if is_suspicious_asn(geo.get("asn")):
            pre_score += 15

        # 4. Baglanti davranisi (flow_tracker'dan)
        flow_count = await redis.scard(f"flow:device_flows:{ip}")
        if flow_count and int(flow_count) > 50:  # Cok sayida baglanti
            pre_score += 10

        scored.append((ip, pre_score))

    # En yuksek risk once
    scored.sort(key=lambda x: x[1], reverse=True)
    return [ip for ip, _ in scored]
```

### 4.2 Cografi On-Filtreleme

Mevcut sistemde ulke engelleme zaten var (`reputation:blocked_countries`). Buna ek olarak:

```python
# Yuksek riskli ulkeler (istatistiksel olarak daha fazla saldiri kaynagi)
# NOT: Bu liste prejuisiz degil, istatistiksel veri bazli
HIGH_RISK_COUNTRIES = {"CN", "RU", "KP", "IR", "VN", "IN", "BR", "ID"}

# Dusuk riskli ulkeler (baglanti beklenen, normal)
LOW_RISK_COUNTRIES = {"TR", "US", "DE", "NL", "GB", "FR", "JP"}
```

### 4.3 ASN Bazli Toplu Degerlendirme

```python
# Bilinen hosting/VPS saglayicilari — saldiri potansiyeli yuksek
SUSPICIOUS_ASNS = {
    "AS14061": "DigitalOcean",
    "AS63949": "Linode",
    "AS24940": "Hetzner",
    "AS16509": "Amazon AWS",
    "AS15169": "Google Cloud",
    "AS8075":  "Microsoft Azure",
}

# Bilinen bullet-proof hosting — cok yuksek risk
BULLETPROOF_ASNS = {
    "AS202425": "IP Volume",
    "AS49505":  "Selectel",
    # ... dinamik olarak guncellenebilir
}
```

### 4.4 Baglanti Davranisi Bazli Skor

Mevcut `flow_tracker.py` ve `threat_analyzer.py`'den alinan sinyaller:

| Davranis | Tespit Yontemi | Risk Puani |
|----------|---------------|------------|
| Port scan (20+ farkli port/dk) | conntrack unique dst_port sayisi | +25 |
| SSH brute force (5+ basarisiz/dk) | nftables meter (ddos_syn_meter) | +35 |
| DNS amplification (ANY/TXT flood) | threat_analyzer query type | +30 |
| DGA domain sorgusu | Shannon entropy > 3.5 | +25 |
| Yatay tarama (5+ farkli hedef IP) | flow_tracker benzersiz dst_ip | +20 |
| Tek port yoğunlasma (80/443 disinda) | conntrack dst_port dagilimi | +15 |
| SYN flood (100+ SYN/dk) | DDoS anomaly monitor | +40 |

---

## 5. UCRETSIZ IP LISTESI KAYNAKLARI — DETAYLI ANALIZ

### 5.1 Firehol IP Lists

**Confidence:** HIGH

Firehol, 200+ ucretsiz IP listesini birlestirip 4 seviye halinde sunar:

| Seviye | Icerik | False Positive | IP Sayisi | Tavsiye |
|--------|--------|---------------|-----------|---------|
| **Level 1** | spamhaus DROP/EDROP + dshield + fullbogons + feodo | Cok dusuk | ~15K | KULLAN (tum sunucularda) |
| **Level 2** | Level 1 + blocklist.de + openbl + autoshun + bruteforcelogin | Dusuk | ~50K | KULLAN (router/firewall icin) |
| **Level 3** | Level 2 + emerging threats + zeus + palevo + malware | Orta | ~200K | DIKKATLI (false positive artar) |
| **Level 4** | Level 3 + daha agresif listeler | Yuksek | ~500K+ | KULLANMA (cok agresif) |

**Pi icin oneri:** Level 1 kesinlikle, Level 2 dikkatli (RAM izle). Level 3-4 kullanma.

### 5.2 Spamhaus DROP/EDROP

**Confidence:** HIGH

- DROP: ~800 hijacked netblock (/8 - /24 arasi). Sifir false positive.
- EDROP: ~300 extended hijacked netblock. Sifir false positive.
- Firehol Level 1'in icinde zaten var ama ayrica da indirebilirsin.
- Format: CIDR notation, yorum satirlari `;` ile baslar.

### 5.3 DShield

**Confidence:** HIGH

- SANS Internet Storm Center tarafindan yurutulur.
- Top 20 en aktif saldiri /24 subnet'i.
- Saatlik guncelleme.
- Kucuk ama cok etkili liste.
- URL: https://feeds.dshield.org/block.txt

### 5.4 Tor Exit Nodes

**Confidence:** HIGH

- Resmi Tor Project listesi.
- Son 72 saatteki cikis dugumleri.
- ~1000-2000 IP.
- Engelleme politikasi tartismali: Tor kullanicilarini engellemek istenebilir veya istenmeyebilir.
- **Oneri:** Engelleme degil, "yuksek risk" isaretleme. Kullaniciya secim birak.

### 5.5 Abuse.ch

**Confidence:** HIGH

- **Feodo Tracker:** Botnet C&C sunuculari (~500 IP). Kesinlikle engelle.
- **SSL Blacklist:** Zararli SSL sertifika kullanan sunucular.
- **URLhaus:** Zararli URL'ler (IP degil, DNS tabanli).
- Tumu ucretsiz, sik guncellenir.

### 5.6 Otomatik Guncelleme Stratejisi

```python
# Onerilen cron-benzeri worker zamanlama
FEED_SCHEDULE = {
    # Yuksek oncelik — sik guncelle
    "feodo":           {"interval_h": 1,  "retry_h": 0.25},
    "dshield":         {"interval_h": 1,  "retry_h": 0.5},
    "tor_exit":        {"interval_h": 2,  "retry_h": 0.5},

    # Orta oncelik — 6 saatte bir
    "firehol_level1":  {"interval_h": 6,  "retry_h": 1},
    "firehol_level2":  {"interval_h": 12, "retry_h": 2},

    # Dusuk oncelik — gunluk
    "spamhaus_drop":   {"interval_h": 24, "retry_h": 4},
    "spamhaus_edrop":  {"interval_h": 24, "retry_h": 4},
    "et_block":        {"interval_h": 12, "retry_h": 2},
}

# Guncelleme akisi:
# 1. HTTP GET ile liste indir (checksum/etag kontrol)
# 2. Degismemisse atla
# 3. Degismisse: parse et, Redis SET'e yaz, nftables set guncelle
# 4. Istatistik logla (eklenen/cikarilan IP sayisi)
```

---

## 6. LOKAL DAVRANIS ANALIZI DETAYLARI

### 6.1 Connection Rate Monitoring

Mevcut `flow_tracker.py` zaten conntrack verisi isliyor. Ek gereksinim:

```python
# Per-IP baglanti hizi izleme (sliding window)
# Redis ZSET ile zaman bazli sayac

async def record_connection(ip: str):
    """Her yeni baglanti icin cagirilir."""
    now = time.time()
    key = f"rate:conn:{ip}"
    pipe = redis.pipeline()
    pipe.zadd(key, {str(now): now})
    pipe.zremrangebyscore(key, 0, now - 60)  # Son 60 saniye
    pipe.zcard(key)
    pipe.expire(key, 120)
    _, _, count, _ = await pipe.execute()
    return count  # Son 60 saniyedeki baglanti sayisi
```

### 6.2 Port Scan Detection

```python
# conntrack'ten alinan flow verileri ile
# Tek IP'nin son 60 saniyede eristigi benzersiz port sayisi

async def check_port_scan(ip: str, dst_port: int):
    key = f"scan:ports:{ip}"
    now = time.time()
    pipe = redis.pipeline()
    pipe.zadd(key, {str(dst_port): now})
    pipe.zremrangebyscore(key, 0, now - 60)
    pipe.zcard(key)
    pipe.expire(key, 120)
    _, _, unique_ports, _ = await pipe.execute()

    if unique_ports >= 20:
        # Port scan tespit edildi
        await increment_risk_score(ip, 25, "port_scan")
```

### 6.3 Brute Force Pattern Detection

```python
# SSH (22), FTP (21), SMTP (25), RDP (3389) icin
# Ayni porta kisa surede cok sayida baglanti

BRUTE_FORCE_PORTS = {22, 21, 25, 3389, 5900, 8080}
BRUTE_FORCE_THRESHOLD = 5  # 60 saniyede 5+ baglanti

async def check_brute_force(ip: str, dst_port: int):
    if dst_port not in BRUTE_FORCE_PORTS:
        return

    key = f"brute:{ip}:{dst_port}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)

    if count >= BRUTE_FORCE_THRESHOLD:
        await increment_risk_score(ip, 35, f"brute_force_port_{dst_port}")
```

### 6.4 DNS Query Anomaly Detection

Mevcut `threat_analyzer.py`'de zaten var:
- DGA algilama (Shannon entropy)
- Supheli query type (AXFR, ANY, NULL)
- Flood tespiti (>20 sorgu/dk)
- Subnet bazli koordineli tarama

Ek gereksinim: Bu sinyallerin IP reputation pipeline'ina entegrasyonu.

---

## 7. MIMARI ONERI

### 7.1 Yeni Worker: `ip_defense_pipeline.py`

```
ip_reputation.py (mevcut) → ip_defense_pipeline.py (yeni, katmanli)

Sorumluluklar:
1. Feed indirme ve guncelleme (cron-benzeri)
2. Layer 1-4 pipeline isletme
3. Risk skoru hesaplama
4. API butce yonetimi
5. nftables set senkronizasyonu
```

### 7.2 Dosya Yapisi Onerisi

```
backend/app/workers/
  ip_defense_pipeline.py    # Ana pipeline worker (yeni)
  ip_reputation.py          # AbuseIPDB entegrasyonu (mevcut, sadeleştirilir)
  threat_analyzer.py        # Davranis analizi (mevcut, sinyal cikisi eklenir)
  feed_manager.py           # Tehdit listesi indirme/guncelleme (yeni)

backend/app/services/
  risk_scorer.py            # Birikimli risk skoru hesaplama (yeni)
  geo_service.py            # MaxMind lokal GeoIP/ASN (yeni)
  api_budget.py             # API kota yonetimi (yeni)

backend/data/
  feeds/                    # Indirilen IP listeleri cache
  GeoLite2-City.mmdb        # MaxMind City DB
  GeoLite2-ASN.mmdb         # MaxMind ASN DB
  trusted_ips.txt           # Guvenilir IP listesi (mevcut)
```

### 7.3 Redis Key Yapisi (Ek)

```
# Feed management
feed:last_update:{feed_name}    → ISO timestamp
feed:checksum:{feed_name}       → MD5/SHA256
feed:ip_count:{feed_name}       → integer

# Blocklist SET'leri
blocklist:firehol_l1            → SET (IP'ler)
blocklist:firehol_l2            → SET (IP'ler)
blocklist:spamhaus_drop         → SET (CIDR'lar)
blocklist:tor_exit              → SET (IP'ler)
blocklist:feodo                 → SET (IP'ler)
blocklist:combined              → SET (tum listelerin birlesimi)

# Risk skorlari
risk:score:{ip}                 → STRING (0-100)
risk:signals:{ip}               → HASH (sinyal detaylari)
risk:history:{ip}               → ZSET (skor gecmisi, timestamp score)

# API butce
api:budget:auto_used            → STRING (gunluk otomatik sorgu sayisi)
api:budget:manual_used          → STRING (gunluk manuel sorgu sayisi)
api:budget:hourly:{hour}        → STRING (saatlik sorgu sayisi)
```

### 7.4 Frontend UI Onerisi

Mevcut IP Reputation sayfasina ek:
- **Katman gorunumu:** Her katmanin kac IP filtreledigi (gunluk istatistik)
- **Feed durumu:** Listelerin son guncelleme zamani, IP sayisi
- **API butce gostergesi:** Gunluk kota kullanimi, saatlik dagilim
- **Risk skoru dagilimi:** Histogram veya pie chart

---

## 8. UYGULAMA ONCELIKLERI VE FAZLAMA

### Faz 1: Lokal Listeler (En yuksek ROI)
- Firehol Level 1 + Feodo + DShield indirme worker'i
- Redis SET'e yukleme
- Pipeline'da Layer 1 kontrol ekleme
- Tahmini etki: API cagrisi %70 azalma

### Faz 2: Lokal GeoIP
- MaxMind GeoLite2 City + ASN kurulumu
- ip-api.com bagimliligi kaldirilmasi
- ASN bazli risk katkisi
- Tahmini etki: ip-api.com rate limit sorunu tamamen cozulur

### Faz 3: Akilli Sorgulama
- Risk skoru hesaplama motoru
- API butce yonetimi
- TTL-based dinamik cache
- Bloom filter on-filtreleme
- Tahmini etki: API cagrisi %90+ azalma (toplam)

### Faz 4: Topluluk Katmani (Opsiyonel)
- CrowdSec CTI API entegrasyonu
- Veya CrowdSec agent kurulumu
- Tahmini etki: Ek veri katmani, zero-day tespiti iyilestirmesi

### Faz 5: Davranis Entegrasyonu
- threat_analyzer sinyal cikislarinin risk skoruna entegrasyonu
- flow_tracker'dan port scan/brute force sinyalleri
- Birikimli skor gecmisi ve trend analizi
- Tahmini etki: Proaktif tespit, liste tabanli degil davranis tabanli

---

## 9. KAYNAKLAR VE GUVEN DEGERLENDIRMESI

| Kaynak | Guven | URL |
|--------|-------|-----|
| FireHOL IP Lists | HIGH | https://iplists.firehol.org/ |
| Spamhaus DROP | HIGH | https://www.spamhaus.org/drop/ |
| AbuseIPDB API Docs | HIGH | https://www.abuseipdb.com/api.html |
| MaxMind GeoLite2 | HIGH | https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/ |
| CrowdSec CTI API | MEDIUM | https://docs.crowdsec.net/ |
| rbloom (Bloom Filter) | HIGH | https://github.com/KenanHanke/rbloom |
| Redis Bloom Filter Docs | HIGH | https://redis.io/docs/latest/develop/data-types/probabilistic/bloom-filter/ |
| DShield Feeds | HIGH | https://www.dshield.org/xml.html |
| nftables Set Performance | MEDIUM | https://developers.redhat.com/blog/2017/04/11/benchmarking-nftables |
| geoip2 Python Library | HIGH | https://geoip2.readthedocs.io/ |
| Abuse.ch Feodo Tracker | HIGH | https://feodotracker.abuse.ch/ |
| CrowdSec pycrowdsec | MEDIUM | https://github.com/crowdsecurity/pycrowdsec |

---

*Research completed: 2026-03-12*
*Mode: Ecosystem + Feasibility*
*Ready for roadmap: yes*
