---
phase: quick-20
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/models/ip_reputation_check.py
  - backend/app/models/ip_blacklist_entry.py
  - backend/app/models/__init__.py
  - backend/app/workers/ip_reputation.py
  - backend/app/api/v1/ip_reputation.py
  - backend/app/workers/db_retention.py
  - migrations/20_ip_reputation_tables.sql
autonomous: true
requirements: [QUICK-20]

must_haves:
  truths:
    - "Sorgulanan IP'ler Redis TTL sonrasi kaybolmuyor, SQL'de kalici"
    - "Blacklist IP'leri Redis TTL sonrasi kaybolmuyor, SQL'de kalici"
    - "API endpoint'leri SQL'den okuyarak tam liste donduruyor"
    - "Redis cache hala calisiyor (hiz icin), SQL master veri deposu"
    - "Eski IP kayitlari retention worker ile otomatik temizleniyor"
  artifacts:
    - path: "backend/app/models/ip_reputation_check.py"
      provides: "Sorgulanan IP'lerin SQL modeli"
      contains: "class IpReputationCheck"
    - path: "backend/app/models/ip_blacklist_entry.py"
      provides: "Blacklist IP'lerin SQL modeli"
      contains: "class IpBlacklistEntry"
    - path: "migrations/20_ip_reputation_tables.sql"
      provides: "Pi'de calistirilacak CREATE TABLE ifadeleri"
      contains: "CREATE TABLE"
  key_links:
    - from: "backend/app/workers/ip_reputation.py"
      to: "ip_reputation_checks table"
      via: "async_session_factory UPSERT"
      pattern: "INSERT INTO.*ON DUPLICATE KEY UPDATE"
    - from: "backend/app/api/v1/ip_reputation.py"
      to: "ip_reputation_checks table"
      via: "SQLAlchemy SELECT"
      pattern: "select.*IpReputationCheck"
---

<objective>
IP Reputation sisteminin tum verilerini Redis-only mimarisinden SQL+Redis cache mimarisine tasi.

Purpose: Sorgulanan IP'ler ve blacklist IP'leri su anda sadece Redis'te 24-48 saat TTL ile tutuluyor ve kaybolabiliyor. SQL master veri deposu olacak, Redis sadece cache olarak kalacak. Boylece gecmis IP kontrolleri kalici sekilde saklanacak.

Output: 2 yeni SQL model, migration SQL dosyasi, worker ve API guncellemeleri, retention kurallari.
</objective>

<execution_context>
@C:/Users/Administrator/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Administrator/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/models/blocked_ip.py (ornek model yapisi — Column, String, DateTime, func.now)
@backend/app/models/connection_flow.py (ornek model — Index, BigInteger, __table_args__)
@backend/app/models/__init__.py (model export listesi — yeni modeller eklenecek)
@backend/app/db/session.py (async_session_factory kullanimi)
@backend/app/db/base.py (Base sinifi)
@backend/app/workers/ip_reputation.py (mevcut worker — Redis HSET + blacklist)
@backend/app/api/v1/ip_reputation.py (mevcut API — Redis SCAN + SMEMBERS)
@backend/app/workers/db_retention.py (retention pattern — RETENTION_DAYS, TIMESTAMP_COLUMNS)

<interfaces>
<!-- Mevcut veritabani session fabrikasi -->
From backend/app/db/session.py:
```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

<!-- Mevcut model base sinifi -->
From backend/app/db/base.py:
```python
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass
```

<!-- Worker'daki Redis cache payload yapisi (SQL'e de yazilacak) -->
From backend/app/workers/ip_reputation.py (_process_ip icinde):
```python
cache_payload = {
    "abuse_score":   str(abuse_score),
    "total_reports": str(total_reports),
    "country":       country,
    "country_code":  country_code,
    "city":          city,
    "isp":           isp,
    "org":           org,
    "checked_at":    checked_at,
}
```

<!-- Blacklist veri yapisi (fetch_abuseipdb_blacklist icinde) -->
From backend/app/workers/ip_reputation.py:
```python
# Her blacklist item:
{
    "ipAddress": "1.2.3.4",
    "abuseConfidenceScore": 100,
    "countryCode": "CN",
    "lastReportedAt": "2026-03-09T12:00:00+00:00"
}
```

<!-- Retention worker pattern -->
From backend/app/workers/db_retention.py:
```python
RETENTION_DAYS = {"connection_flows": 7, "dns_query_logs": 14, "traffic_logs": 30}
TIMESTAMP_COLUMNS = {"connection_flows": "first_seen", ...}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: SQL modelleri + migration dosyasi + retention ekleme</name>
  <files>
    backend/app/models/ip_reputation_check.py,
    backend/app/models/ip_blacklist_entry.py,
    backend/app/models/__init__.py,
    backend/app/workers/db_retention.py,
    migrations/20_ip_reputation_tables.sql
  </files>
  <action>
1. `backend/app/models/ip_reputation_check.py` olustur:
   - `class IpReputationCheck(Base)` — `__tablename__ = "ip_reputation_checks"`
   - Sutunlar: `id` (Integer PK auto), `ip_address` (String(45) NOT NULL, UNIQUE index), `abuse_score` (Integer default=0), `total_reports` (Integer default=0), `country` (String(100)), `country_code` (String(10)), `city` (String(100)), `isp` (String(200)), `org` (String(200)), `checked_at` (DateTime server_default=func.now()), `updated_at` (DateTime server_default=func.now(), onupdate=func.now())
   - `__table_args__` icinde: `Index("idx_irc_score", "abuse_score")`, `Index("idx_irc_checked_at", "checked_at")`

2. `backend/app/models/ip_blacklist_entry.py` olustur:
   - `class IpBlacklistEntry(Base)` — `__tablename__ = "ip_blacklist_entries"`
   - Sutunlar: `id` (Integer PK auto), `ip_address` (String(45) NOT NULL, UNIQUE index), `abuse_score` (Integer default=0), `country` (String(10)), `last_reported_at` (String(50) — AbuseIPDB ISO format string olarak gelir), `fetched_at` (DateTime server_default=func.now())
   - `__table_args__` icinde: `Index("idx_ibe_score", "abuse_score")`, `Index("idx_ibe_fetched", "fetched_at")`

3. `backend/app/models/__init__.py` guncelle:
   - Dosyanin sonuna ekle: `from app.models.ip_reputation_check import IpReputationCheck`
   - Dosyanin sonuna ekle: `from app.models.ip_blacklist_entry import IpBlacklistEntry`
   - `__all__` listesine ekle: `"IpReputationCheck"`, `"IpBlacklistEntry"`

4. `backend/app/workers/db_retention.py` guncelle:
   - `RETENTION_DAYS` dict'ine ekle: `"ip_reputation_checks": 30`, `"ip_blacklist_entries": 7`
   - `TIMESTAMP_COLUMNS` dict'ine ekle: `"ip_reputation_checks": "checked_at"`, `"ip_blacklist_entries": "fetched_at"`

5. `migrations/20_ip_reputation_tables.sql` olustur (Pi'de dogrudan calistirilacak):
```sql
-- IP Reputation SQL Migration
-- Kullanim: mysql -u tonbilai -p tonbilaios < 20_ip_reputation_tables.sql

CREATE TABLE IF NOT EXISTS ip_reputation_checks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    abuse_score INT DEFAULT 0,
    total_reports INT DEFAULT 0,
    country VARCHAR(100) DEFAULT NULL,
    country_code VARCHAR(10) DEFAULT NULL,
    city VARCHAR(100) DEFAULT NULL,
    isp VARCHAR(200) DEFAULT NULL,
    org VARCHAR(200) DEFAULT NULL,
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_irc_ip (ip_address),
    INDEX idx_irc_score (abuse_score),
    INDEX idx_irc_checked_at (checked_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ip_blacklist_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    abuse_score INT DEFAULT 0,
    country VARCHAR(10) DEFAULT NULL,
    last_reported_at VARCHAR(50) DEFAULT NULL,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX idx_ibe_ip (ip_address),
    INDEX idx_ibe_score (abuse_score),
    INDEX idx_ibe_fetched (fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5 && python -c "from app.models.ip_reputation_check import IpReputationCheck; from app.models.ip_blacklist_entry import IpBlacklistEntry; print('Models OK')" 2>&1 || echo "Import check (local env may not have deps, check file syntax instead)" && python -c "import ast; ast.parse(open('backend/app/models/ip_reputation_check.py').read()); ast.parse(open('backend/app/models/ip_blacklist_entry.py').read()); print('Syntax OK')"</automated>
  </verify>
  <done>
    - ip_reputation_check.py ve ip_blacklist_entry.py modelleri olusturuldu
    - __init__.py'de export edildiler
    - db_retention.py'de retention kurallari eklendi (30g ve 7g)
    - migrations/20_ip_reputation_tables.sql dosyasi hazir
  </done>
</task>

<task type="auto">
  <name>Task 2: Worker SQL yazma + API SQL okuma entegrasyonu</name>
  <files>
    backend/app/workers/ip_reputation.py,
    backend/app/api/v1/ip_reputation.py
  </files>
  <action>
1. **Worker guncelleme** (`backend/app/workers/ip_reputation.py`):

   a) Dosyanin basindaki import'lara ekle:
      ```python
      from sqlalchemy import text
      from app.models.ip_reputation_check import IpReputationCheck
      from app.models.ip_blacklist_entry import IpBlacklistEntry
      ```

   b) `_process_ip()` fonksiyonunda, Redis cache yazma bloguna (`await redis.hset(cache_key, mapping=cache_payload)`) hemen SONRA, SQL UPSERT ekle:
      ```python
      # ── SQL kalici kayit (UPSERT) ──
      try:
          async with async_session_factory() as session:
              await session.execute(
                  text(
                      "INSERT INTO ip_reputation_checks "
                      "(ip_address, abuse_score, total_reports, country, country_code, city, isp, org, checked_at) "
                      "VALUES (:ip, :score, :reports, :country, :cc, :city, :isp, :org, NOW()) "
                      "ON DUPLICATE KEY UPDATE "
                      "abuse_score=:score, total_reports=:reports, country=:country, country_code=:cc, "
                      "city=:city, isp=:isp, org=:org, checked_at=NOW()"
                  ),
                  {"ip": ip, "score": abuse_score, "reports": total_reports,
                   "country": country, "cc": country_code, "city": city, "isp": isp, "org": org},
              )
              await session.commit()
      except Exception as sql_exc:
          logger.warning(f"SQL UPSERT hatasi {ip}: {sql_exc}")
      ```

   c) `fetch_abuseipdb_blacklist()` fonksiyonunda, Redis'e yeni verileri yazdiktan sonra (pipe.execute() satiri sonrasi), SQL bulk islem ekle:
      ```python
      # ── SQL kalici kayit (blacklist) ──
      try:
          async with async_session_factory() as session:
              # Eski kayitlari temizle
              await session.execute(text("DELETE FROM ip_blacklist_entries"))
              # Yeni kayitlari batch ekle (1000'er)
              batch = []
              for item in ip_list:
                  ip_addr = item.get("ipAddress", "")
                  if not ip_addr:
                      continue
                  batch.append({
                      "ip": ip_addr,
                      "score": item.get("abuseConfidenceScore", 0),
                      "country": item.get("countryCode", ""),
                      "reported": item.get("lastReportedAt", ""),
                  })
                  if len(batch) >= 1000:
                      await session.execute(
                          text(
                              "INSERT INTO ip_blacklist_entries (ip_address, abuse_score, country, last_reported_at, fetched_at) "
                              "VALUES (:ip, :score, :country, :reported, NOW())"
                          ),
                          batch,
                      )
                      batch = []
              if batch:
                  await session.execute(
                      text(
                          "INSERT INTO ip_blacklist_entries (ip_address, abuse_score, country, last_reported_at, fetched_at) "
                          "VALUES (:ip, :score, :country, :reported, NOW())"
                      ),
                      batch,
                  )
              await session.commit()
              logger.info(f"Blacklist SQL: {len(ip_list)} IP yazildi")
      except Exception as sql_exc:
          logger.warning(f"Blacklist SQL yazma hatasi: {sql_exc}")
      ```

2. **API guncelleme** (`backend/app/api/v1/ip_reputation.py`):

   a) Dosyanin basindaki import'lara ekle:
      ```python
      from sqlalchemy import text
      from app.db.session import async_session_factory
      ```

   b) `get_checked_ips()` endpoint'ini guncelle — Redis SCAN'i KALDIR, SQL SELECT ile degistir:
      ```python
      @router.get("/ips")
      async def get_checked_ips(
          min_score: int = Query(default=0, ge=0, le=100),
          current_user: User = Depends(get_current_user),
      ):
          ips: list[dict] = []
          try:
              async with async_session_factory() as session:
                  result = await session.execute(
                      text(
                          "SELECT ip_address, abuse_score, total_reports, country, country_code, "
                          "city, isp, org, checked_at FROM ip_reputation_checks "
                          "WHERE abuse_score >= :min_score ORDER BY abuse_score DESC"
                      ),
                      {"min_score": min_score},
                  )
                  for row in result.mappings():
                      checked_str = ""
                      if row["checked_at"]:
                          checked_str = row["checked_at"].strftime("%Y-%m-%d %H:%M:%S")
                      ips.append({
                          "ip": row["ip_address"],
                          "abuse_score": row["abuse_score"] or 0,
                          "total_reports": row["total_reports"] or 0,
                          "country": row["country"] or "",
                          "city": row["city"] or "",
                          "isp": row["isp"] or "",
                          "org": row["org"] or "",
                          "checked_at": checked_str,
                      })
          except Exception as exc:
              logger.error(f"IP listesi SQL hatasi: {exc}")
              # SQL basarisizsa Redis'e fallback
              redis = await get_redis()
              cursor = 0
              while True:
                  cursor, keys = await redis.scan(cursor, match=f"{REDIS_KEY_IP_PREFIX}*", count=200)
                  for key in keys:
                      data = await redis.hgetall(key)
                      if not data:
                          continue
                      score = int(data.get("abuse_score", 0))
                      if score < min_score:
                          continue
                      ip_addr = key.removeprefix(REDIS_KEY_IP_PREFIX) if isinstance(key, str) else key
                      ips.append({
                          "ip": ip_addr, "abuse_score": score,
                          "total_reports": int(data.get("total_reports", 0)),
                          "country": data.get("country", ""), "city": data.get("city", ""),
                          "isp": data.get("isp", ""), "org": data.get("org", ""),
                          "checked_at": data.get("checked_at", ""),
                      })
                  if cursor == 0:
                      break
              ips.sort(key=lambda x: x["abuse_score"], reverse=True)
          return {"ips": ips, "total": len(ips)}
      ```

   c) `get_blacklist_ips()` endpoint'ini guncelle — Redis SMEMBERS'i KALDIR, SQL SELECT ile degistir:
      ```python
      @router.get("/blacklist")
      async def get_blacklist_ips(
          current_user: User = Depends(get_current_user),
      ):
          redis = await get_redis()
          ips = []
          try:
              async with async_session_factory() as session:
                  result = await session.execute(
                      text(
                          "SELECT ip_address, abuse_score, country, last_reported_at, fetched_at "
                          "FROM ip_blacklist_entries ORDER BY abuse_score DESC"
                      )
                  )
                  for row in result.mappings():
                      ips.append({
                          "ip": row["ip_address"],
                          "abuse_score": row["abuse_score"] or 0,
                          "country": row["country"] or "",
                          "last_reported_at": row["last_reported_at"] or "",
                      })
          except Exception as exc:
              logger.error(f"Blacklist SQL hatasi: {exc}")
              # SQL basarisizsa Redis'e fallback
              try:
                  ip_set = await redis.smembers("reputation:blacklist_ips")
                  for ip in ip_set:
                      data = await redis.hgetall(f"reputation:blacklist_data:{ip}")
                      if data:
                          ips.append({
                              "ip": ip,
                              "abuse_score": int(data.get("abuse_score", 0)),
                              "country": data.get("country", ""),
                              "last_reported_at": data.get("last_reported_at", ""),
                          })
                  ips.sort(key=lambda x: x["abuse_score"], reverse=True)
              except Exception as fallback_exc:
                  logger.error(f"Blacklist Redis fallback hatasi: {fallback_exc}")

          last_fetch = await redis.get("reputation:blacklist_last_fetch") or ""
          total_count = await redis.get("reputation:blacklist_count") or "0"
          return {"ips": ips, "total": len(ips), "last_fetch": last_fetch, "total_count": int(total_count)}
      ```

   d) `clear_reputation_cache()` endpoint'ini guncelle — SQL'i de temizle:
      Mevcut Redis temizleme kodundan sonra (return oncesi), SQL DELETE ekle:
      ```python
      # SQL temizleme
      sql_deleted = 0
      try:
          async with async_session_factory() as session:
              r1 = await session.execute(text("DELETE FROM ip_reputation_checks"))
              r2 = await session.execute(text("DELETE FROM ip_blacklist_entries"))
              await session.commit()
              sql_deleted = (r1.rowcount or 0) + (r2.rowcount or 0)
              logger.info(f"SQL reputation verileri temizlendi: {sql_deleted} kayit")
      except Exception as sql_exc:
          logger.warning(f"SQL temizleme hatasi: {sql_exc}")
      ```
      Return degerini guncelle: `"deleted": deleted_count` yerine `"deleted": deleted_count, "sql_deleted": sql_deleted`

   e) `get_ip_reputation_summary()` endpoint'ini guncelle — summary sayilarini SQL'den al:
      Mevcut Redis SCAN blogunun YERINE SQL SELECT kullan:
      ```python
      try:
          async with async_session_factory() as session:
              result = await session.execute(
                  text(
                      "SELECT COUNT(*) as total, "
                      "SUM(CASE WHEN abuse_score >= 80 THEN 1 ELSE 0 END) as critical, "
                      "SUM(CASE WHEN abuse_score >= 50 AND abuse_score < 80 THEN 1 ELSE 0 END) as warning "
                      "FROM ip_reputation_checks"
                  )
              )
              row = result.mappings().first()
              if row:
                  total_checked = int(row["total"] or 0)
                  flagged_critical = int(row["critical"] or 0)
                  flagged_warning = int(row["warning"] or 0)
      except Exception as exc:
          logger.error(f"IP reputation summary SQL hatasi: {exc}")
          # SQL basarisizsa mevcut Redis SCAN kodu fallback olarak calissin
          # (mevcut Redis SCAN kodunu except blogu icine tasi)
      ```

ONEMLI: Redis cache yazma islemi worker'da KALACAK (hiz icin). API, oncelikli olarak SQL'den okuyacak, SQL basarisiz olursa Redis'e fallback yapacak.
  </action>
  <verify>
    <automated>cd C:/Nextcloud2/TonbilAiFirevallv5 && python -c "import ast; ast.parse(open('backend/app/workers/ip_reputation.py').read()); ast.parse(open('backend/app/api/v1/ip_reputation.py').read()); print('Syntax OK')"</automated>
  </verify>
  <done>
    - Worker: _process_ip() icinde Redis HSET'ten sonra SQL UPSERT calisiyor
    - Worker: fetch_abuseipdb_blacklist() icinde Redis'ten sonra SQL bulk insert calisiyor
    - API /ips: SQL SELECT ile okuyor, hata durumunda Redis fallback
    - API /blacklist: SQL SELECT ile okuyor, hata durumunda Redis fallback
    - API /summary: SQL COUNT/SUM ile okuyor, hata durumunda Redis fallback
    - API /cache DELETE: Redis + SQL'den temizliyor
    - Redis cache yazma korunuyor (hiz icin)
  </done>
</task>

</tasks>

<verification>
1. Model dosyalari dogru syntax ile olusturuldu: `python -c "import ast; ast.parse(...)"`
2. Migration SQL dosyasi var ve CREATE TABLE IF NOT EXISTS iceriyor
3. Worker'da SQL UPSERT kodu mevcut (INSERT ... ON DUPLICATE KEY UPDATE)
4. API'de SQL SELECT kodu mevcut + Redis fallback
5. Retention worker'da ip_reputation_checks (30g) ve ip_blacklist_entries (7g) tanimli
6. __init__.py'de her iki model export ediliyor
</verification>

<success_criteria>
- 2 yeni SQLAlchemy model dosyasi olusturuldu (ip_reputation_check.py, ip_blacklist_entry.py)
- Migration SQL dosyasi Pi'ye deploy edilmeye hazir
- Worker hem Redis'e hem SQL'e yaziyor (dual-write)
- API SQL'den okuyor, Redis fallback mevcut
- Retention kurallari eklendi (30g + 7g)
- Tum Python dosyalari syntax hatasi icermiyor
</success_criteria>

<output>
After completion, create `.planning/quick/20-ip-reputation-sql-migration-sorgulanan-i/20-SUMMARY.md`
</output>
