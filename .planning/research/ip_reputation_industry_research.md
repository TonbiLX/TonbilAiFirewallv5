# IP Reputation Endustri Arastirmasi

**Proje:** TonbilAiOS v5
**Tarih:** 2026-03-12
**Kapsam:** Endustri standardi firewall ve guvenlik sistemlerinin IP reputation yaklasimlarini arastirma
**Genel Guven:** MEDIUM-HIGH (cogu bulgu resmi dokumantasyon ve birden fazla kaynak ile dogrulanmis)

---

## 1. Yonetici Ozeti

TonbilAiOS'un mevcut IP reputation sistemi **yalnizca AbuseIPDB'ye bagimli** bir yapida calisiyor. Bu, endustri standardinin oldukca gerisinde. pfSense, OPNsense, Suricata ve CrowdSec gibi sistemler **katmanli (tiered) sorgulama**, **lokal blocklist veritabanlari**, **topluluk tabanlı istihbarat** ve **coklu kaynak birlestirme** kullaniyor. Mevcut sistemin en buyuk zayifligi: tek bir API'ye bagimlilik, gunluk 1000 sorgu limiti ve lokal tehdit veritabaninin olmamasi.

Arastirma sonucunda onerilen strateji: **3 katmanli IP reputation mimarisi** -- (1) lokal blocklist dosyalari (FireHOL, ET, Spamhaus DROP), (2) topluluk istihbarati (CrowdSec CTI), (3) detayli API sorgulari (AbuseIPDB, VirusTotal). Bu yaklasim API tuketimini %90+ azaltirken koruma seviyesini onemli olcude arttirir.

---

## 2. Endustri Sistemlerinin IP Reputation Mekanizmalari

### 2.1 Suricata IP Reputation Sistemi

**Guven:** HIGH (resmi dokumantasyon)

Suricata, yerlesik bir IP reputation modulu sunuyor:

- **Dosya Formati:** CSV tabanlı iki dosya:
  - Kategoriler: `<id>,<kisa_ad>,<aciklama>` (max 60 kategori)
  - Skorlar: `<ip>,<kategori_id>,<skor>` (1-127 arasi, 0 = veri yok)
  - CIDR notasyonu destekli (orn: `1.1.1.0/24,6,88`)
- **Hub-Spoke Mimarisi:** Merkezi hub tum feed'leri alir, agirlikli ortalama hesaplar, sonucu spoke sensörlere dagitir
- **Feed Agirliklari:** Her feed'e genel veya kategori bazli agirlik atanabilir. Guvenilir feed'e yuksek agirlik, supheliye dusuk
- **Kural Entegrasyonu:** `iprep` anahtar kelimesiyle Suricata kurallari yazilabilir (orn: `alert ip $HOME_NET any -> any any (iprep:src,BadHosts,>,30;)`)
- **Lokal Oncelik:** Tum veriler lokal dosyalarda tutulur, calisma zamaninda harici API gerekmiyor

**Kaynak:** [Suricata IP Reputation Docs](https://docs.suricata.io/en/latest/reputation/ipreputation/ip-reputation.html), [Format](https://docs.suricata.io/en/latest/reputation/ipreputation/ip-reputation-format.html)

### 2.2 pfSense / OPNsense -- pfBlockerNG

**Guven:** HIGH (topluluk belgeleri ve resmi dokumanlar)

- **pfBlockerNG** eklentisi ile harici IP blocklist'leri dogrudan firewall kurallarina entegre edilir
- Alias (takma ad) mekanizmasi: URL Table (IPs) tipinde alias olusturulur, periyodik guncellenir
- Desteklenen kaynaklar: FireHOL Level 1/2/3, ET Compromised IPs, Spamhaus DROP, Talos
- **Guncelleme frekansi:** Kullanici tarafindan yapilandirilabilir (tipik: 1-24 saat)
- **Performans:** ipset/pf table kullanimi ile yuz binlerce IP verimli sekilde engellenir
- **API bagimliligi:** YOK -- tamamen dosya tabanlı indirme + lokal filtreleme

**Kaynak:** [pfBlockerNG Guide](https://linuxincluded.com/using-pfblockerng-on-pfsense/), [OPNsense Blocklists](https://windgate.net/opnsense-ip-blocklists-and-geo-ip-block-to-enhance-security-against-malicious-attacks/)

### 2.3 CrowdSec -- Topluluk Tabanli IP Reputation

**Guven:** HIGH (resmi dokumantasyon)

CrowdSec fundamentally farkli bir yaklasim kullaniyor:

- **Topluluk Aglari:** 70.000+ aktif kullanici, 190+ ulke, gunluk ortalama 10 milyon sinyal
- **Veri Toplama:** Her CrowdSec instance saldiri sinyallerini (zaman damgasi + senaryo + IP) merkeze raporlar
- **Kurasyon:** Toplanan veriler false positive ve zehirleme saldirilarina karsi filtrelenir
- **Dagitim:** Temizlenmis tehdit verileri tum katilimcilara blocklist olarak dagitilir (%5 gunluk IP rotasyonu)

**CTI API:**
- **Smoke Dataset (Ucretsiz):** Topluluk tarafindan raporlanan IP'lerin cogunlugu, 50 sorgu/gun
- **Fire Dataset (Premium):** Daha detayli, kuratoryel blocklist + ek baglamsal veri
- API yaniti: `ip`, `reputation`, `classifications`, `attack_details`, `scores.overall/last_day/last_week/last_month`

**Bouncer (Onleyici) Mekanizmasi:**
- nftables, iptables, nginx, HAProxy, Cloudflare bouncer'lari mevcut
- Blocklist'ler lokal olarak indirilir ve firewall kurallarina yazilir
- API sorgularina **gerek yok** -- lokal blocklist periyodik guncellenir

**Kaynak:** [CrowdSec GitHub](https://github.com/crowdsecurity/crowdsec), [CTI API Docs](https://docs.crowdsec.net/u/cti_api/intro/), [Community CTI Key](https://www.crowdsec.net/blog/community-cti-api-key)

### 2.4 Fail2ban

**Guven:** MEDIUM (topluluk kaynaklari)

- **Temel Yaklasim:** Log analizi + IP ban (reputation sistemi degil, reaktif koruma)
- **Recidive Jail:** Tekrar tekrar banlanan IP'ler icin kademeli ceza (orn: 5 ban/gun → 1 hafta ban)
- **Kalici Banlama:** Ozel jail + text dosyasi ile reboot sonrasi ban devami
- **AbuseIPDB Entegrasyonu:** Banlanan IP'ler otomatik AbuseIPDB'ye raporlanabilir
- **Sinirlilik:** Tek makine bazli, blocklist paylasimi manuel, native reputation skoru yok

**Kaynak:** [Fail2ban Blacklist Jail](https://github.com/mitchellkrogza/Fail2Ban-Blacklist-JAIL-for-Repeat-Offenders-with-Perma-Extended-Banning), [AbuseIPDB + Fail2ban](https://blog.hackeriet.no/adventures-with-fail2ban/)

---

## 3. Ucretsiz IP Tehdit Istihbarat Kaynaklari

### 3.1 Dosya Tabanli Blocklist'ler (API Gerektirmeyen)

| Kaynak | Icerik | Format | Guncelleme | Kullanim |
|--------|--------|--------|------------|----------|
| **FireHOL Level 1** | Min false positive, max koruma | .netset (CIDR) | Her gun | Tum sunucularda KULLANIM |
| **FireHOL Level 2** | Saldiri, spyware, virus (30 gun) | .netset | Her gun | Web sunucularda |
| **FireHOL Level 3** | Agresif, false positive olabilir | .netset | Her gun | Dikkatli kullan |
| **Spamhaus DROP** | Toplevel hijacked netblock'lar | Netset | Her gun | Kesinlikle engelle |
| **Spamhaus EDROP** | Extended DROP | Netset | Her gun | Kesinlikle engelle |
| **ET Compromised IPs** | Taviz verilmis IP'ler (Proofpoint) | IP listesi | Her gun | Yuksek guvenilirlik |
| **CINS Army** | Nomic sensörlerinden saldiri verisi | IP listesi | Canli | Tavsiye edilir |
| **Blocklist.de** | 12 saatte 70K+ saldiri raporu | IP listesi | 12 saat | Detayli, guvenilir |
| **DShield Top 20** | SANS ISC en aktif /24 subnet'ler | Subnet listesi | Her gun | Klasik referans |
| **Talos IP Blacklist** | Cisco tehdit istihbarati | IP listesi | Her gun | Yuksek guvenilirlik |

**ONERI:** FireHOL Level 1 + Spamhaus DROP + ET Compromised IPs = API kullanmadan temel koruma katmani. Toplam ~50-100K IP/subnet, nftables set'e yazildiginda minimal performans etkisi.

**Guven:** HIGH -- FireHOL ve Spamhaus on yildir endustri standardi
**Kaynak:** [FireHOL IP Lists](https://iplists.firehol.org/), [FireHOL GitHub](https://github.com/firehol/blocklist-ipsets), [Open-Source Threat Intel Feeds](https://github.com/Bert-JanP/Open-Source-Threat-Intel-Feeds)

### 3.2 API Tabanli Ucretsiz Kaynaklar

| API | Ucretsiz Limit | Batch Destegi | Ek Ozellikler |
|-----|-----------------|---------------|---------------|
| **AbuseIPDB** | 1000/gun (domain dogrulamayla 3000) | Web UI bulk-check (CSV), API tekil | Abuse skoru, raporlar, ulke |
| **AlienVault OTX** | 10.000/saat (key ile), 1000/saat (keysiz) | Pulse tabanlı toplu veri | IOC'ler, raporlar, iliskiler |
| **VirusTotal** | 500/gun, 4/dk | Hayir (tekil) | Multi-AV, URL/dosya/IP/domain |
| **CrowdSec CTI** | 50/gun (smoke dataset) | Hayir | Saldiri detaylari, skorlar |
| **IPQualityScore** | 1000/ay | Hayir | Proxy/VPN/TOR tespiti, fraud skor |
| **ip-api.com** | 45/dk (HTTP), premium unlimited | 100 IP batch (POST /batch) | GeoIP, ISP, ASN |

**ONERI:** AbuseIPDB (mevcut) + AlienVault OTX (10K/saat!) ana API kaynaklari olmali. VirusTotal sadece yuksek riskli IP'ler icin ikincil dogrulama.

**Guven:** HIGH -- resmi fiyatlandirma sayfalari
**Kaynak:** [AbuseIPDB Pricing](https://www.abuseipdb.com/pricing), [OTX API](https://otx.alienvault.com/api), [Threat Intelligence API Comparison 2026](https://ismalicious.com/posts/best-threat-intelligence-api-comparison-2026)

---

## 4. Katmanli (Tiered) Sorgulama Mimarisi

### Mevcut Durum (TonbilAiOS)

```
Yeni IP → AbuseIPDB API → Cache (24s) → Karar
```

**Sorunlar:**
- Her yeni IP icin 1 API hakki harcanir
- Gunluk 1000 limit ile ~200 benzersiz IP/dongu (MAX_CHECKS_PER_CYCLE=10, 5dk aralik)
- Bilinen kotu IP'ler bile API sorgulanana kadar gecebilir
- Lokal koruma katmani yok

### Onerilen 3 Katmanli Mimari

```
Yeni IP tespiti
    |
    v
[KATMAN 1: Lokal Blocklist]  ← FireHOL L1 + Spamhaus DROP + ET (0ms, API yok)
    |
    | Bulunamadi
    v
[KATMAN 2: Topluluk]          ← CrowdSec smoke DB (lokal kopya) veya OTX (10K/saat)
    |
    | Hala belirsiz
    v
[KATMAN 3: Detayli API]       ← AbuseIPDB + VirusTotal (son care, sinirli kota)
```

**Avantajlar:**
1. Katman 1 tamamen lokal: **sifir API maliyeti**, milisaniye tepki suresi
2. Katman 2 yuksek limitli: OTX 10K/saat ucretsiz
3. Katman 3 sadece %5-10 IP'ye uygulanir: AbuseIPDB kotasi verimli kullanilir
4. Bilinen kotu IP'ler **aninda** engellenir (API beklemeden)

### Uygulama Detaylari

**Lokal Blocklist Guncelleme:**
```python
# Oner: blocklist_updater worker (6 saatte bir)
BLOCKLIST_SOURCES = {
    "firehol_level1": "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset",
    "spamhaus_drop": "https://www.spamhaus.org/drop/drop.txt",
    "spamhaus_edrop": "https://www.spamhaus.org/drop/edrop.txt",
    "et_compromised": "https://rules.emergingthreats.net/blockrules/compromised-ips.txt",
    "cins_army": "https://cinsscore.com/list/ci-badguys.txt",
}
# → Parse → Redis SET'e yaz → nftables set'e yaz
# Redis key: "reputation:blocklist:{source_name}" → SET
# Birlesmis: "reputation:local_blocklist" → SET (tum kaynaklarin union'i)
```

**Sorgulama Akisi:**
```python
async def check_ip_reputation(ip: str) -> ReputationResult:
    # Katman 1: Lokal
    if await redis.sismember("reputation:local_blocklist", ip):
        return ReputationResult(score=100, source="local_blocklist", blocked=True)

    # Subnet kontrolu (CIDR match)
    if await check_local_subnet_match(ip):
        return ReputationResult(score=90, source="local_blocklist_subnet", blocked=True)

    # Katman 2: OTX (yuksek limit)
    otx_data = await check_otx(ip)
    if otx_data and otx_data.pulse_count > 3:
        return ReputationResult(score=otx_to_score(otx_data), source="otx")

    # Katman 3: AbuseIPDB (sinirli kota)
    if daily_quota_remaining > 100:
        abuse_data = await check_abuseipdb(ip, api_key)
        return ReputationResult(score=abuse_data.score, source="abuseipdb")

    # Kota bitti — sadece GeoIP
    return ReputationResult(score=0, source="none")
```

---

## 5. IP Reputation Skorlama Algoritmalari

### 5.1 Endustrideki Yaklasimlar

**Suricata:** Agirlikli ortalama. Her feed'e admin tarafindan agirlik atanir, hub tum feed'lerin agirlikli ortalamasini hesaplar. Skor 1-127 arasi.

**CrowdSec:** Topluluk konsensusü. Milyonlarca sinyal toplanir, false positive filtrelenir. Sonuc: overall/last_day/last_week/last_month ayri skorlar.

**Akademik Yaklasim (IP SafeGuard):** Dynamic Threat Score (DTS). Birden fazla kaynak (AbuseIPDB, VirusTotal, vb.) toplanir, her kaynaga guvenilirlik katsayisi atanir, agirlikli birlestirme yapilir.

### 5.2 TonbilAiOS Icin Onerilen Skorlama

```
composite_score = (
    local_blocklist_hit * 40 +        # Lokal blocklist'te varsa: +40
    abuseipdb_score * 0.30 +           # AbuseIPDB skor (0-100): * 0.30 → max 30
    otx_pulse_factor * 15 +            # OTX pulse sayisi (0-10 normalize): * 15
    crowdsec_reputation * 10 +         # CrowdSec skor (0-1): * 10
    country_risk * 5                   # Ulke risk katsayisi (0-1): * 5
)
# Sonuc: 0-100 arasi normalize edilmis skor
# >= 80: KRITIK (otomatik engelle)
# >= 50: UYARI (izle)
# < 50: TEMIZ
```

**Avantaj:** Tek kaynaga bagimlilik yok. AbuseIPDB kotasi bittiginde bile lokal blocklist + OTX ile 70/100'luk bir skor mevcut.

---

## 6. Batch Sorgulama vs Tekil Sorgulama

| API | Batch Destegi | Batch Detay | Maliyet/Performans |
|-----|---------------|-------------|-------------------|
| **AbuseIPDB** | Web UI bulk-check (CSV upload) | API'de native batch endpoint YOK | Her IP = 1 sorgu hakki |
| **AbuseIPDB check-block** | Subnet bazli (/20-/24) | Tek istekle subnet analizi | 1 sorgu = 1 subnet |
| **ip-api.com** | POST /batch (100 IP) | JSON body ile toplu GeoIP | 1 istek = 100 IP |
| **AlienVault OTX** | Pulse bazli toplu veri | Pulse'lar binlerce IOC icerir | Cok verimli |
| **VirusTotal** | Hayir | Tekil istek zorunlu | 4/dk limit zorlayici |
| **CrowdSec CTI** | Hayir | Smoke dataset tekil | 50/gun cok sinirli |

**ONERI:**
- GeoIP icin **ip-api.com batch** kullan (100 IP/istek, mevcut 1'er 1'er sorgulama yerine)
- AbuseIPDB `check-block` endpoint'ini etkin kullan (zaten mevcut -- iyi)
- OTX pulse'lari bir kere indir, lokal cache'le (saatlik guncelleme yeterli)

---

## 7. Mevcut Sistemin Analizi ve Iyilestirme Onerileri

### 7.1 Mevcut Guclu Yanlar

1. Redis + SQL cift katmanli cache (iyi tasarim)
2. AbuseIPDB rate limit header senkronizasyonu (dogru yaklasim)
3. check-block subnet analizi (endustri standardi)
4. Otomatik engelleme + AiInsight + Telegram bildirimi (kapsamli)
5. Ulke bazli engelleme (geoblock)

### 7.2 Eksiklikler ve Iyilestirmeler

| Eksiklik | Oncelik | Onerilen Cozum |
|----------|---------|---------------|
| Lokal blocklist yok | KRITIK | FireHOL L1 + Spamhaus DROP worker'i ekle |
| Tek API kaynagi (AbuseIPDB) | YUKSEK | OTX + CrowdSec CTI ekle |
| ip-api.com 1'er 1'er sorgu | ORTA | Batch endpoint kullan (100 IP/istek) |
| Composite skorlama yok | ORTA | Coklu kaynak agirlikli birlestirme |
| CrowdSec bouncer entegrasyonu yok | DUSUK | nftables bouncer entegrasyonu |
| Fail2ban entegrasyonu yok | DUSUK | SSH/web saldiri loglari icin recidive jail |

### 7.3 Hizli Kazanimlar (Minimum Efor, Maksimum Etki)

1. **FireHOL Level 1 indirme worker'i** (4 saat is)
   - 6 saatte bir `firehol_level1.netset` indir
   - Parse et, Redis SET'e yaz (`reputation:local_blocklist`)
   - `_process_ip()` basina lokal kontrol ekle
   - **Etki:** Bilinen kotu IP'ler API sorgulamadan aninda tespit edilir

2. **ip-api.com batch sorgulama** (2 saat is)
   - 10 IP'yi tek tek sorgulamak yerine batch POST kullan
   - `GEOIP_SLEEP = 1.5s` yerine tek istek = 100 IP
   - **Etki:** GeoIP suresi 15s'den 0.5s'ye duser

3. **AlienVault OTX entegrasyonu** (6 saat is)
   - OTX API ile IP sorgulama (10.000/saat ucretsiz)
   - AbuseIPDB kotasi bittiginde fallback olarak kullan
   - **Etki:** API bagimliligi azalir, kapsam artar

---

## 8. CrowdSec Derinlemesine Analiz

### Neden CrowdSec Entegrasyonu Dusunulmeli?

1. **Sifir API maliyeti ile blocklist:** CrowdSec bouncer'lari lokal blocklist indirir
2. **Topluluk istihbarati:** 10M+ gunluk sinyal, %5 gunluk rotasyon
3. **nftables native destek:** `cs-bouncer-nftables` paketi mevcut
4. **Raporlama:** TonbilAiOS'un tespit ettigi saldirilar topluluga raporlanabilir

### CrowdSec vs AbuseIPDB Karsilastirmasi

| Ozellik | CrowdSec | AbuseIPDB |
|---------|----------|-----------|
| Lokal Blocklist | EVET (bouncer indirir) | HAYIR (API zorunlu) |
| Ucretsiz API | 50/gun (CTI) | 1000-3000/gun |
| Topluluk Buyuklugu | 70K+ aktif instance | ~200K kullanici |
| Otomatik Koruma | Bouncer ile anlık | Manuel/worker bazli |
| Raporlama | Otomatik (cift yonlu) | Manuel veya script |
| Self-hosted | EVET (tam kontrol) | HAYIR (SaaS) |

### Entegrasyon Yaklasimi

```
TonbilAiOS + CrowdSec Agent (Pi uzerinde)
    ↓ log okuma
CrowdSec Senaryo Motoru → saldiri tespiti
    ↓ sinyal
CrowdSec API (LAPI) → lokal karar veritabanı
    ↓ dagitim
nftables Bouncer → otomatik IP engelleme
    ↓ raporlama
CrowdSec Console → topluluk istihbarati
```

**Guven:** HIGH -- CrowdSec acik kaynak, 28K+ GitHub yildizi, aktif gelistirme
**Kaynak:** [CrowdSec GitHub](https://github.com/crowdsecurity/crowdsec), [CrowdSec Blocklists](https://docs.crowdsec.net/u/service_api/quickstart/blocklists/)

---

## 9. Ucretsiz Alternatiflerin Ozet Degerlendirmesi

### API Gerektirmeyen (En Degerli)

| Kaynak | Boyut | Kalite | Entegrasyon Kolayligi | Oneri |
|--------|-------|--------|----------------------|-------|
| FireHOL L1 | ~50K IP | Cok yuksek (min FP) | Basit (wget+parse) | **KESINLIKLE EKLE** |
| Spamhaus DROP | ~1K subnet | En yuksek | Basit | **KESINLIKLE EKLE** |
| ET Compromised | ~10K IP | Yuksek | Basit | **EKLE** |
| CINS Army | ~15K IP | Orta-Yuksek | Basit | Opsiyonel |
| Blocklist.de | ~70K IP | Orta | Basit | Opsiyonel |

### API Gerektiren (Ek Katman)

| Kaynak | Ucretsiz Kapasite | Entegrasyon Zorluğu | Oneri |
|--------|-------------------|---------------------|-------|
| AlienVault OTX | 10K/saat | Orta (REST API) | **EKLE** (AbuseIPDB yedegi) |
| CrowdSec CTI | 50/gun | Kolay (REST API) | **DUSUN** (bouncer tercih) |
| VirusTotal | 500/gun, 4/dk | Kolay | Sadece yuksek riskli IP icin |
| IPQualityScore | 1000/ay | Kolay | VPN/proxy tespiti icin opsiyonel |

---

## 10. Yol Haritasi Icin Oneriler

### Faz 1: Lokal Blocklist Katmani (Oncelik: KRITIK)
- FireHOL Level 1 + Spamhaus DROP + ET Compromised indir worker'i
- Redis SET'e yaz, `_process_ip()` basina lokal kontrol ekle
- nftables set'e toplu yazma (performans icin)
- **Sonuc:** API sorgulamadan once bilinen kotu IP'ler aninda engellenir

### Faz 2: Coklu API Kaynagi (Oncelik: YUKSEK)
- AlienVault OTX entegrasyonu (AbuseIPDB yedegi)
- ip-api.com batch sorgulama optimizasyonu
- Composite skorlama algoritmasi (agirlikli birlestirme)
- **Sonuc:** Tek noktali arizaya (AbuseIPDB) bagimlilik kalkar

### Faz 3: CrowdSec Entegrasyonu (Oncelik: ORTA)
- CrowdSec agent kurulumu (Pi uzerinde)
- Mevcut log kaynaklarini (SSH, DNS, web) CrowdSec'e bagla
- nftables bouncer ile otomatik koruma
- Topluluk raporlamasi
- **Sonuc:** Topluluk bazli istihbarat + otomatik koruma

### Faz 4: Gelismis Skorlama (Oncelik: DUSUK)
- ML tabanli anomali tespiti (mevcut trafik verileriyle)
- Zaman serisi analizi (IP davranis degisimi)
- ASN/subnet bazli toplu skorlama
- **Sonuc:** Proaktif tehdit tespiti

---

## 11. Teknik Uyari ve Tuzaklar

### Lokal Blocklist Tuzaklari
- **False Positive:** FireHOL L3 cok agresif, uretim ortaminda L1 ile basla
- **Boyut:** L1 ~50K IP, nftables set performansi izle (100K+ dikkat)
- **Guncelleme:** Stale (bayat) listeler tehlikeli, otomatik guncelleme ZORUNLU
- **CDN/Bulut IP'leri:** AWS/GCP/Azure IP'leri blocklist'te olabilir, whitelist mekanzimasi sart

### API Tuzaklari
- **AbuseIPDB Kota Yonetimi:** Mevcut sistem iyi yapiyor ama fallback kaynak yok
- **Rate Limit Cascading:** Bir API'nin kotasi bittiginde diger API'ye yuklenmeyi onle
- **Cache Invalidation:** 24 saat cok uzun olabilir, yuksek riskli IP'ler icin 6 saate dusur

### Performans Tuzaklari
- **Redis SET boyutu:** 100K+ uye ile SISMEMBER hala O(1), sorun yok
- **nftables set boyutu:** 100K IP'ye kadar performans iyi, uzerinde interval set kullan
- **Startup suresi:** Blocklist indirme startup'i yavaslabilir, asenkron yukle

---

## Kaynaklar

- [Suricata IP Reputation](https://docs.suricata.io/en/latest/reputation/ipreputation/ip-reputation.html)
- [Suricata IP Reputation Format](https://docs.suricata.io/en/latest/reputation/ipreputation/ip-reputation-format.html)
- [FireHOL IP Lists](https://iplists.firehol.org/)
- [FireHOL GitHub](https://github.com/firehol/blocklist-ipsets)
- [CrowdSec GitHub](https://github.com/crowdsecurity/crowdsec)
- [CrowdSec CTI API](https://docs.crowdsec.net/u/cti_api/intro/)
- [CrowdSec Community CTI Key](https://www.crowdsec.net/blog/community-cti-api-key)
- [CrowdSec Blocklists](https://docs.crowdsec.net/u/service_api/quickstart/blocklists/)
- [CrowdSec IP Range Reputation](https://www.crowdsec.net/blog/introducing-the-ip-range-reputation-system)
- [AbuseIPDB Pricing](https://www.abuseipdb.com/pricing)
- [AbuseIPDB API Docs](https://docs.abuseipdb.com/)
- [AbuseIPDB Bulk Check](https://www.abuseipdb.com/bulk-check)
- [AlienVault OTX API](https://otx.alienvault.com/api)
- [pfBlockerNG Guide](https://linuxincluded.com/using-pfblockerng-on-pfsense/)
- [OPNsense IP Blocklists](https://windgate.net/opnsense-ip-blocklists-and-geo-ip-block-to-enhance-security-against-malicious-attacks/)
- [Open-Source Threat Intel Feeds](https://github.com/Bert-JanP/Open-Source-Threat-Intel-Feeds)
- [Threat Intelligence API Comparison 2026](https://ismalicious.com/posts/best-threat-intelligence-api-comparison-2026)
- [Free Cybersecurity APIs](https://upskilld.com/article/free-cybersecurity-apis/)
- [IP SafeGuard Framework](https://www.mecs-press.org/ijwmt/ijwmt-v14-n2/IJWMT-V14-N2-1.pdf)
- [Fail2ban Persistent Banning](https://github.com/mitchellkrogza/Fail2Ban-Blacklist-JAIL-for-Repeat-Offenders-with-Perma-Extended-Banning)
- [Fail2ban + AbuseIPDB](https://blog.hackeriet.no/adventures-with-fail2ban/)
