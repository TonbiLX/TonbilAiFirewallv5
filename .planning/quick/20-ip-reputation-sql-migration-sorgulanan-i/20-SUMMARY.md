---
phase: quick-20
plan: 01
subsystem: ip-reputation
tags: [sql-migration, redis, dual-write, retention, mariadb]
tech-stack:
  added: [SQLAlchemy text UPSERT, SQL bulk INSERT, async_session_factory]
  patterns: [SQL-primary + Redis fallback, dual-write, batch insert]
key-files:
  created:
    - backend/app/models/ip_reputation_check.py
    - backend/app/models/ip_blacklist_entry.py
    - migrations/20_ip_reputation_tables.sql
  modified:
    - backend/app/models/__init__.py
    - backend/app/workers/db_retention.py
    - backend/app/workers/ip_reputation.py
    - backend/app/api/v1/ip_reputation.py
decisions:
  - SQL UPSERT (INSERT ... ON DUPLICATE KEY UPDATE) ile idempotent yazma
  - Blacklist fetch sonrasi DELETE + batch INSERT (tablo temizleme stratejisi)
  - API SQL-primary, Redis fallback pattern (consistency + performance dengesi)
  - ip_reputation_checks 30g, ip_blacklist_entries 7g retention suresi
metrics:
  duration: 8 min
  completed: "2026-03-09"
  tasks: 2
  files_created: 3
  files_modified: 4
---

# Quick-20: IP Reputation SQL Migration Ozeti

**Tek cumle:** IP reputation Redis-only mimarisinden SQL master + Redis cache mimarisine gecisi — 2 yeni SQLAlchemy model, migration SQL, dual-write worker ve SQL-primary API ile tamamlandi.

## Tamamlanan Gorevler

| Task | Ad | Commit | Dosyalar |
|------|----|--------|---------|
| 1 | SQL modelleri + migration + retention | 2f8710e | ip_reputation_check.py, ip_blacklist_entry.py, __init__.py, db_retention.py, 20_ip_reputation_tables.sql |
| 2 | Worker SQL dual-write + API SQL-first okuma | 81ee466 | ip_reputation.py (worker + api) |

## Yapilan Degisiklikler

### Task 1: SQL Modelleri + Migration + Retention

**`backend/app/models/ip_reputation_check.py`** (yeni):
- `IpReputationCheck` modeli, `ip_reputation_checks` tablosu
- Sutunlar: id, ip_address (UNIQUE), abuse_score, total_reports, country, country_code, city, isp, org, checked_at, updated_at
- Index: `idx_irc_score` (abuse_score), `idx_irc_checked_at` (checked_at)

**`backend/app/models/ip_blacklist_entry.py`** (yeni):
- `IpBlacklistEntry` modeli, `ip_blacklist_entries` tablosu
- Sutunlar: id, ip_address (UNIQUE), abuse_score, country, last_reported_at (String, AbuseIPDB ISO format), fetched_at
- Index: `idx_ibe_score` (abuse_score), `idx_ibe_fetched` (fetched_at)

**`backend/app/models/__init__.py`** (guncellendi):
- `IpReputationCheck` ve `IpBlacklistEntry` export listesine eklendi

**`backend/app/workers/db_retention.py`** (guncellendi):
- `ip_reputation_checks`: 30 gun retention, `checked_at` timestamp sutunu
- `ip_blacklist_entries`: 7 gun retention, `fetched_at` timestamp sutunu

**`migrations/20_ip_reputation_tables.sql`** (yeni):
- Pi'de dogrudan calistirilacak CREATE TABLE IF NOT EXISTS ifadeleri
- `mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios < 20_ip_reputation_tables.sql`

### Task 2: Worker Dual-Write + API SQL-Primary

**`backend/app/workers/ip_reputation.py`** (guncellendi):
- Import: `from sqlalchemy import select, text`, iki yeni model import
- `_process_ip()`: Redis HSET'ten sonra SQL UPSERT (`INSERT ... ON DUPLICATE KEY UPDATE`)
- `fetch_abuseipdb_blacklist()`: Redis pipeline.execute() sonrasi SQL `DELETE FROM ip_blacklist_entries` + batch INSERT (1000'er)

**`backend/app/api/v1/ip_reputation.py`** (guncellendi):
- Import: `from sqlalchemy import text`, `from app.db.session import async_session_factory`
- `/ips` endpoint: SQL SELECT primary, Redis fallback
- `/blacklist` endpoint: SQL SELECT primary, Redis fallback
- `/summary` endpoint: SQL COUNT/SUM primary, Redis SCAN fallback
- `/cache` DELETE endpoint: Redis temizleme + SQL DELETE FROM iki tablodan, `sql_deleted` response field eklendi

## Mimari Karar

Redis cache yazma islemleri **korunuyor** (hiz icin). SQL, master veri deposu olarak eklendi:

```
IP kontrol edilir
    ↓
Redis HSET (cache, 24s TTL)  ←─ Hiz icin korundu
    ↓
SQL UPSERT (kalici)          ←─ Yeni eklendi
    ↓
API /ips → SQL SELECT        ←─ Artik SQL'den okuyor
         → Redis fallback    ←─ SQL basarisizsa
```

## Pi Deploy Talimati

Tablolari Pi'de olusturmak icin:
```bash
mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios < migrations/20_ip_reputation_tables.sql
```

Ardindan backend restart:
```bash
sudo systemctl restart tonbilaios-backend
```

## Deviations from Plan

None — plan tam olarak uygulanmistir.

## Self-Check: PASSED

- backend/app/models/ip_reputation_check.py: FOUND
- backend/app/models/ip_blacklist_entry.py: FOUND
- backend/app/models/__init__.py: IpReputationCheck + IpBlacklistEntry export ediliyor
- backend/app/workers/db_retention.py: ip_reputation_checks (30g) + ip_blacklist_entries (7g) tanimli
- migrations/20_ip_reputation_tables.sql: CREATE TABLE IF NOT EXISTS ifadeleri mevcut
- backend/app/workers/ip_reputation.py: ON DUPLICATE KEY UPDATE + SQL bulk insert mevcut
- backend/app/api/v1/ip_reputation.py: SQL SELECT + Redis fallback + sql_deleted mevcut
- Commit 2f8710e: Task 1 — FOUND
- Commit 81ee466: Task 2 — FOUND
- Tum Python dosyalari: Syntax OK (ast.parse gecti)
