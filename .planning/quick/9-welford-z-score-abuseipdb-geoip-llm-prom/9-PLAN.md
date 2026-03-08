---
phase: quick
plan: 9
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/workers/traffic_baseline.py
  - backend/app/workers/daily_summary.py
  - backend/app/workers/llm_log_analyzer.py
  - backend/app/main.py
autonomous: true
requirements: [QUICK-9-BASELINE, QUICK-9-SUMMARY, QUICK-9-LLM-PROMPT]
must_haves:
  truths:
    - "Bandwidth ve DNS metrikleri icin Welford online ortalama/stddev hesaplaniyor"
    - "Z-score anomalileri AiInsight + Telegram ile bildiriliyor"
    - "Her gun 08:00'da Telegram'a gunluk ozet raporu gonderiliyor"
    - "LLM log analizi ham log yerine istatistiksel ozet gonderiyor"
  artifacts:
    - path: "backend/app/workers/traffic_baseline.py"
      provides: "Welford Z-score anomali tespiti — bandwidth + DNS metrikleri"
      min_lines: 120
    - path: "backend/app/workers/daily_summary.py"
      provides: "Gunluk Telegram ozet raporu worker"
      min_lines: 80
  key_links:
    - from: "backend/app/workers/traffic_baseline.py"
      to: "Redis bw:total + dns:stats"
      via: "10s polling ile Welford online guncelleme"
      pattern: "welford|z_score|baseline"
    - from: "backend/app/workers/daily_summary.py"
      to: "telegram_service.notify_hourly_summary"
      via: "DB aggregate + send_message"
      pattern: "daily_summary|notify_hourly_summary"
    - from: "backend/app/workers/llm_log_analyzer.py"
      to: "LLM API"
      via: "Istatistiksel ozet prompt"
      pattern: "aggregate|summary|istatistik"
---

<objective>
Welford Z-score adaptif anomali tespiti, gunluk Telegram ozet raporu ve LLM prompt iyilestirmesi

Purpose: Quick 8 arastirmasinda belirlenen "Faz 1 — Sifir Bagimlilik, Yuksek Deger" kalemlerinden 3 tanesini hayata gecirmek. Mevcut bandwidth_monitor ve dns_proxy verilerini kullanarak sifir ek bagimlilik ile adaptif anomali tespiti yapmak, mevcut ama cagrilmayan gunluk Telegram ozet fonksiyonunu aktive etmek ve LLM log analizinin kalitesini artirmak.
Output: traffic_baseline.py (Welford worker), daily_summary.py (gunluk ozet worker), iyilestirilmis llm_log_analyzer.py
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/workers/bandwidth_monitor.py
@backend/app/workers/llm_log_analyzer.py
@backend/app/workers/threat_analyzer.py
@backend/app/services/telegram_service.py
@backend/app/services/llm_prompts.py
@backend/app/main.py
@backend/app/db/redis_client.py

<interfaces>
<!-- Mevcut Redis key'leri ve fonksiyonlar — executor bunlari direkt kullanacak -->

From backend/app/workers/bandwidth_monitor.py:
```python
REDIS_PREFIX_TOTAL = "bw:total"          # HASH: upload_bps, download_bps, ts
REDIS_PREFIX_DEVICE = "bw:device:"       # HASH: upload_bps, download_bps, ...
REDIS_HISTORY_TOTAL = "bw:history:total" # LIST: JSON {ts, up, down}
POLL_INTERVAL = 10  # saniye
```

From backend/app/services/telegram_service.py:
```python
async def send_message(text: str, bot_token=None, chat_ids=None, use_html=True) -> bool
async def notify_ai_insight(severity: str, message: str, category: str = "security")
async def notify_hourly_summary(stats: dict)  # Mevcut ama hic cagrilmiyor!
```

From backend/app/workers/threat_analyzer.py:
```python
# Redis key'leri:
# "dns:query_count:{ip}" — IP bazli DNS sorgu sayisi
# "dns:blocked_count" — engellenen sorgu sayaci (threat_analyzer icinde)
# DGA_ENTROPY_THRESHOLD = 3.5
# EXTERNAL_RATE_THRESHOLD = 20
```

From backend/app/db/redis_client.py:
```python
async def get_redis() -> redis.Redis  # Singleton Redis client
```

From backend/app/models/ai_insight.py:
```python
class AiInsight(Base):
    __tablename__ = "ai_insights"
    id, timestamp, severity, message, suggested_action, category
class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
```

From backend/app/services/timezone_service.py:
```python
def format_local_time() -> str  # Yerel saat damgasi
def now_local() -> datetime     # Yerel datetime
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Welford Z-score Baseline Worker + Gunluk Telegram Ozet Worker</name>
  <files>backend/app/workers/traffic_baseline.py, backend/app/workers/daily_summary.py, backend/app/main.py</files>
  <action>
1. YENi DOSYA: `backend/app/workers/traffic_baseline.py` — Welford online algoritma ile adaptif anomali tespiti.

   Welford algoritmasi saf Python (sifir ek bagimlilik):
   ```python
   class WelfordAccumulator:
       """Welford online ortalama/varyans — tek geciste, O(1) bellek."""
       def __init__(self):
           self.n = 0
           self.mean = 0.0
           self.M2 = 0.0

       def update(self, x: float):
           self.n += 1
           delta = x - self.mean
           self.mean += delta / self.n
           delta2 = x - self.mean
           self.M2 += delta * delta2

       def variance(self) -> float:
           return self.M2 / self.n if self.n > 1 else 0.0

       def stddev(self) -> float:
           return self.variance() ** 0.5

       def z_score(self, x: float) -> float:
           sd = self.stddev()
           if sd < 1e-9 or self.n < 30:  # Minimum 30 ornek (5 dk @ 10s)
               return 0.0
           return (x - self.mean) / sd
   ```

   Izlenecek metrikler (her biri icin ayri WelfordAccumulator):
   - `bw_upload_bps` — toplam upload bps (Redis bw:total upload_bps)
   - `bw_download_bps` — toplam download bps (Redis bw:total download_bps)
   - `dns_queries_per_min` — DNS sorgu hizi (Redis dns:stats:total_queries delta)
   - `dns_blocked_per_min` — DNS engelleme hizi (Redis dns:stats:blocked_queries delta)
   - `active_flows` — aktif flow sayisi (Redis flow:active_ids SCARD)

   Worker dongusu (`start_traffic_baseline`):
   - 120s baslangic beklemesi (bandwidth_monitor verisi hazir olsun)
   - Her 10 saniyede Redis'ten mevcut metrikleri oku
   - Her metrik icin Welford accumulator'u guncelle
   - Z-score hesapla, esik: |z| > 3.0 (3 sigma kurali)
   - Anomali tespit edilirse:
     a) AiInsight tablosuna yaz (category="anomaly", severity= z>5 ? "critical" : "warning")
     b) Telegram notify_ai_insight() cagir
     c) 30 dakika cooldown (ayni metrik icin tekrar alarm gonderme — Redis key ile)
   - Welford state'i Redis'e persist et (restart'ta kaybolmasin):
     Redis HASH `baseline:welford:{metric}` → n, mean, M2 (her 60 ornekte bir kaydet)
   - Startup'ta Redis'ten mevcut Welford state'i yukle (cold start onleme)

   DNS metrik kaynagi: threat_analyzer.py zaten `dns:query_count:{ip}` tutuyor ama toplam sorgu/engelleme hizi icin farkli bir yaklasim gerekiyor. Basit cozum: Redis HASH `baseline:dns_counters` icinde `total_queries` ve `blocked_queries` sayaclarini tutmak. dns_proxy.py bu sayaclari zaten artiriyor olabilir — yoksa traffic_baseline worker DnsQueryLog son 1 dakika count'u ile hesaplayabilir. ANCAK en hafif yol: Redis'teki mevcut `flow:active_ids` SCARD ve `bw:total` degerlerini kullanmak. DNS metrikleri icin `dns_query_logs` tablosundan son 60s count almak yerine, her 60 saniyede bir DB sorgusu yapilabilir (agir degil).

   Cooldown mekanizmasi:
   - Redis key: `baseline:cooldown:{metric_name}` TTL=1800 (30 dk)
   - Alarm gondermeden once bu key'i kontrol et

2. YENi DOSYA: `backend/app/workers/daily_summary.py` — Gunluk Telegram ozet raporu.

   telegram_service.py'de `notify_hourly_summary(stats)` fonksiyonu MEVCUT ama hic cagrilmiyor. Bu worker her gun saat 08:00'da calisarak gunluk ozet gonderecek.

   Worker dongusu (`start_daily_summary`):
   - Baslangicta bir sonraki 08:00'a kadar bekle
   - Her gun 08:00'da:
     a) Son 24 saatlik DNS istatistiklerini DB'den topla:
        - Toplam sorgu sayisi (DnsQueryLog WHERE timestamp > now - 24h)
        - Engellenen sorgu sayisi (blocked=True)
        - Engelleme orani (%)
        - Aktif cihaz sayisi (DISTINCT device_id)
        - En aktif 5 cihaz (GROUP BY device_id ORDER BY COUNT DESC LIMIT 5)
        - En cok engellenen 5 domain (WHERE blocked=True GROUP BY domain LIMIT 5)
     b) Son 24 saatlik trafik istatistikleri:
        - Toplam upload/download bytes (DeviceTrafficSnapshot SUM)
        - DDoS drop counter'lar (ddos_service.get_ddos_drop_summary)
     c) Welford baseline durumu:
        - Her metrik icin mevcut ortalama ve stddev
        - Son 24 saatte kac anomali tespit edildi (AiInsight WHERE category='anomaly' AND timestamp > now-24h)
     d) `notify_hourly_summary(stats)` cagir (fonksiyon adi "hourly" ama gunluk olarak kullanacagiz, stats dict'i ayni formatta)
     e) AYRICA daha detayli bir Telegram mesaji hazirla (send_message ile):
        - Baslik: "GUNLUK GUVENLIK OZETI"
        - DNS istatistikleri
        - Trafik istatistikleri
        - Anomali ozeti (Welford)
        - DDoS ozeti
        - Genel saglık durumu (yesil/sari/kirmizi)
     f) 24 saat bekle, tekrarla

   Saat hesabi: `from app.services.timezone_service import now_local` kullanarak yerel 08:00'i hesapla.

3. `backend/app/main.py` GUNCELLE:
   - `from app.workers.traffic_baseline import start_traffic_baseline` ekle
   - `from app.workers.daily_summary import start_daily_summary` ekle
   - lifespan icinde iki yeni task ekle:
     ```python
     # Welford Z-score adaptif anomali tespiti
     baseline_task = asyncio.create_task(start_traffic_baseline())
     # Gunluk Telegram guvenlik ozeti (her gun 08:00)
     daily_summary_task = asyncio.create_task(start_daily_summary())
     ```
   - Kapanma bolumune `baseline_task.cancel()` ve `daily_summary_task.cancel()` ekle
   - Log mesajina ekleme yap

ONEMLI: Welford state Redis'te saklanacak, DB'ye ek tablo gerekmiyor. Sifir ek Python paketi. dns metrik verisi icin en basit yol: DnsQueryLog tablosundan son 60 saniyenin count'unu almak (SELECT COUNT(*) WHERE timestamp > NOW() - 60s). Bu her 10 saniyede calisir ama tek bir count sorgusu cok hafif.
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5 && python -c "from backend.app.workers.traffic_baseline import WelfordAccumulator; w = WelfordAccumulator(); [w.update(x) for x in [10,12,11,9,13,10,11,10,12,11]]; assert abs(w.mean - 10.9) < 0.01; assert w.z_score(20) > 3.0; print('Welford OK')" && python -c "import ast; ast.parse(open('backend/app/workers/daily_summary.py').read()); print('daily_summary syntax OK')" && python -c "import ast; t=ast.parse(open('backend/app/main.py').read()); s=ast.dump(t); assert 'start_traffic_baseline' in s; assert 'start_daily_summary' in s; print('main.py imports OK')"</automated>
  </verify>
  <done>
    - WelfordAccumulator sinifi dogru ortalama/stddev/z_score hesapliyor
    - traffic_baseline.py 5 metrik icin Welford izleme + anomali tespiti + Redis persist + cooldown iceriyor
    - daily_summary.py her gun 08:00'da DNS + trafik + anomali ozeti gonderecek worker iceriyor
    - main.py her iki worker'i lifespan icinde baslatip kapanista cancel ediyor
  </done>
</task>

<task type="auto">
  <name>Task 2: LLM Log Analizi Prompt Iyilestirmesi — Ham Log Yerine Istatistiksel Ozet</name>
  <files>backend/app/workers/llm_log_analyzer.py</files>
  <action>
`llm_log_analyzer.py` mevcut haliyle LLM'e ham DNS log satirlarini gonderiyor (her sorgu tek tek). Bu:
- Token israf ediyor (100 log = ~5000 token)
- LLM'in oruntu gormesini zorlastiriyor
- Maliyet artiriyor

IYILESTIRME: Ham log yerine istatistiksel ozet gondermek.

1. `_fetch_recent_logs` fonksiyonunu KORUYARAK yeni bir `_build_statistical_summary` fonksiyonu ekle:

   ```python
   async def _build_statistical_summary(max_logs: int) -> str:
       """Son N DNS logunu istatistiksel ozete donustur (LLM token tasarrufu)."""
       async with async_session_factory() as session:
           now = datetime.utcnow()
           since = now - timedelta(minutes=config_interval or 60)

           # 1. Toplam sorgu / engellenen
           total = await session.execute(
               select(func.count()).where(DnsQueryLog.timestamp >= since)
           )
           blocked = await session.execute(
               select(func.count()).where(
                   DnsQueryLog.timestamp >= since,
                   DnsQueryLog.blocked == True
               )
           )

           # 2. En cok sorgulanan 10 domain
           top_domains = await session.execute(
               select(DnsQueryLog.domain, func.count().label('cnt'))
               .where(DnsQueryLog.timestamp >= since)
               .group_by(DnsQueryLog.domain)
               .order_by(desc('cnt'))
               .limit(10)
           )

           # 3. En cok engellenen 10 domain
           top_blocked = await session.execute(
               select(DnsQueryLog.domain, func.count().label('cnt'))
               .where(DnsQueryLog.timestamp >= since, DnsQueryLog.blocked == True)
               .group_by(DnsQueryLog.domain)
               .order_by(desc('cnt'))
               .limit(10)
           )

           # 4. Cihaz bazli sorgu dagilimi (top 10)
           device_stats = await session.execute(
               select(DnsQueryLog.device_id, func.count().label('cnt'),
                      func.sum(case((DnsQueryLog.blocked == True, 1), else_=0)).label('blocked_cnt'))
               .where(DnsQueryLog.timestamp >= since)
               .group_by(DnsQueryLog.device_id)
               .order_by(desc('cnt'))
               .limit(10)
           )

           # 5. Sorgu tipi dagilimi
           qtype_stats = await session.execute(
               select(DnsQueryLog.query_type, func.count().label('cnt'))
               .where(DnsQueryLog.timestamp >= since)
               .group_by(DnsQueryLog.query_type)
               .order_by(desc('cnt'))
               .limit(10)
           )

           # 6. Engelleme sebepleri
           block_reasons = await session.execute(
               select(DnsQueryLog.block_reason, func.count().label('cnt'))
               .where(DnsQueryLog.timestamp >= since, DnsQueryLog.blocked == True,
                      DnsQueryLog.block_reason.isnot(None))
               .group_by(DnsQueryLog.block_reason)
               .order_by(desc('cnt'))
               .limit(5)
           )

           # 7. Yuksek entropili domainler (DGA adaylari) — son loglarin domain entropy'si
           # Burada ham loglari cekerek entropy hesapla (kucuk subset)
           recent_domains = await session.execute(
               select(DnsQueryLog.domain, DnsQueryLog.device_id)
               .where(DnsQueryLog.timestamp >= since, DnsQueryLog.blocked == False)
               .order_by(desc(DnsQueryLog.timestamp))
               .limit(200)
           )
           high_entropy = []
           for row in recent_domains:
               domain = row[0]
               if domain:
                   ent = _shannon_entropy(domain.split('.')[0])
                   if ent >= 3.5:
                       high_entropy.append((domain, row[1], round(ent, 2)))

       # Ozet metin olustur
       return format_summary(...)  # Yukaridaki tum verileri ozet metin olarak formatla
   ```

2. `LOG_ANALYSIS_PROMPT` sablonunu guncelle — ham log satirlari yerine istatistiksel ozet bekleyen format:

   ```
   DNS ISTATISTIKSEL OZET ({interval} dakika):
   - Toplam sorgu: {total}, Engellenen: {blocked} (%{rate})
   - En cok sorgulanan: domain1 (N), domain2 (N), ...
   - En cok engellenen: domain1 (N), domain2 (N), ...
   - Cihaz bazli: IP1 (N sorgu, M engel), IP2 (N sorgu, M engel), ...
   - Sorgu tipleri: A (N), AAAA (N), HTTPS (N), ...
   - Yuksek entropili domainler (DGA adayi): domain1 (entropy=3.8), ...
   - Engelleme sebepleri: sebep1 (N), sebep2 (N), ...
   ```

3. `_analyze_logs` fonksiyonunu guncelle:
   - Onceki davranisi koruyan fallback: eger istatistiksel ozet olusamazsa eski ham log formatina dusur
   - Yeni ozet ile prompt'u birlestir
   - DDoS verisi de ayni prompt'a eklenir (mevcut `_fetch_ddos_counters` korunur)

4. Shannon entropy hesabi icin basit yardimci fonksiyon ekle (threat_analyzer.py'den pattern alinabilir):
   ```python
   def _shannon_entropy(s: str) -> float:
       if not s: return 0.0
       freq = Counter(s)
       length = len(s)
       return -sum((c/length) * math.log2(c/length) for c in freq.values())
   ```

5. `from collections import Counter` ve `import math` import'larini ekle (zaten var olan import'lar ile cakisma kontrolu yap).

6. `from sqlalchemy import case` import'unu ekle (device_stats sorgusunda kullaniliyor).

SONUC: LLM'e gonderilen token sayisi ~5000'den ~500'e dusecek. Daha yapisal veri = daha iyi analiz sonuclari. Maliyet %80-90 azalir.
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5 && python -c "import ast; t=ast.parse(open('backend/app/workers/llm_log_analyzer.py').read()); funcs=[n.name for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]; assert '_build_statistical_summary' in funcs, f'Missing _build_statistical_summary, found: {funcs}'; assert '_shannon_entropy' in funcs, f'Missing _shannon_entropy'; print('LLM analyzer upgrade OK: ' + ', '.join(funcs))"</automated>
  </verify>
  <done>
    - _build_statistical_summary fonksiyonu DB'den istatistiksel ozet uretiyor (toplam/engellenen, top domainler, cihaz dagilimi, sorgu tipleri, yuksek entropili domainler)
    - LOG_ANALYSIS_PROMPT istatistiksel ozet formatina guncellenmis
    - _shannon_entropy yardimci fonksiyonu eklenmis
    - Eski ham log formati fallback olarak korunmus
    - Token kullanimi ~%80-90 azalmis
  </done>
</task>

</tasks>

<verification>
1. `traffic_baseline.py` dosyasi mevcut, WelfordAccumulator sinifi dogru hesaplama yapiyor
2. `daily_summary.py` dosyasi mevcut, 08:00 zamanlama mantigi dogru
3. `llm_log_analyzer.py` istatistiksel ozet fonksiyonu mevcut, prompt guncellenmis
4. `main.py` her iki yeni worker'i baslatip kapaniyor
5. Sifir ek Python paketi — tum islemler standard library + mevcut bagimliliklar ile
</verification>

<success_criteria>
- WelfordAccumulator unit test gecti (ortalama, stddev, z_score dogrulugu)
- traffic_baseline.py 5 metrik izliyor, anomalide Telegram + AiInsight gonderiyor
- daily_summary.py her gun 08:00'da gunluk ozet gonderiyor
- llm_log_analyzer.py ham log yerine istatistiksel ozet gonderiyor
- main.py her iki worker'i lifespan icinde baslatiyor
- Deploy sonrasi backend hatasiz calisiyor (systemctl status kontrol)
</success_criteria>

<output>
After completion, create `.planning/quick/9-welford-z-score-abuseipdb-geoip-llm-prom/9-SUMMARY.md`
</output>
