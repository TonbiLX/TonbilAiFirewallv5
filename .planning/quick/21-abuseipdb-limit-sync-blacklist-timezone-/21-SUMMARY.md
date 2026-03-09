---
phase: quick-21
plan: 01
subsystem: ip-reputation
tags: [bug-fix, abuseipdb, timezone, redis, rate-limit]
dependency_graph:
  requires: []
  provides: [abuseipdb-limit-accurate-display, blacklist-24h-exact-interval]
  affects: [backend/app/workers/ip_reputation.py, backend/app/api/v1/ip_reputation.py]
tech_stack:
  added: []
  patterns: [UTC-consistent-timestamps, live-api-fallback-for-cache-miss]
key_files:
  modified:
    - backend/app/workers/ip_reputation.py
    - backend/app/api/v1/ip_reputation.py
decisions:
  - "Blacklist last_fetch artik UTC ISO ('2026-03-09T14:30:00Z') formatinda kaydediliyor — local +03:00 yerine"
  - "Summary endpoint Redis key'leri expire olunca AbuseIPDB'ye canli sorgu yapar (8.8.8.8, 1 check harcar)"
  - "Eski local format parse edilemezse except blogu devreye girer ve yeniden fetch tetiklenir (geriye uyumlu)"
metrics:
  duration: "8 min"
  completed: "2026-03-09"
  tasks_completed: 2
  files_modified: 2
---

# Quick 21: AbuseIPDB Limit Sync ve Blacklist Timezone Bug Fix Ozeti

**Tek cumle:** Blacklist fetch araligi UTC-UTC karsilastirmasina gectirilerek 3 saatlik erken tetiklenme sorunu cozuldu; summary endpoint Redis key'leri expire olunca canli API sorgusuyla 900 fallback'i engellendi.

## Gerceklestirilen Degisiklikler

### Task 1: Blacklist Timestamp UTC ISO Formatina Gecis

**Dosya:** `backend/app/workers/ip_reputation.py`

**Bug:** `fetch_abuseipdb_blacklist()` fonksiyonu `format_local_time()` ile local +03:00 timestamp kaydediyordu. `_run_reputation_cycle()` bunu `datetime.utcnow()` ile karsilastiriyordu — 3 saatlik fark nedeniyle blacklist 24 saat yerine ~21 saatte bir yeniden fetch ediliyordu.

**Duzeltme:**
- `format_local_time()` -> `datetime.utcnow().isoformat() + "Z"` (UTC ISO)
- `+03:00` hardcode parse -> temiz UTC parse (Z ve +00:00 suffix kaldirilir)
- Eski format parse edilemezse `except` blogu `should_fetch=True` birakmak icin devreye girer

**Commit:** `68d9c24`

### Task 2: Summary Endpoint Canli AbuseIPDB Limit Sorgusu

**Dosya:** `backend/app/api/v1/ip_reputation.py`

**Bug:** `reputation:abuseipdb_remaining` ve `reputation:abuseipdb_limit` Redis key'leri 24 saatlik TTL sonrasi expire oluyor, summary endpoint None donuyordu. Frontend bunu 900 sabit degerine fallback yapiyordu — gercek API limitini yansitmiyordu.

**Duzeltme:**
- Redis key'leri None ise ve API anahtari varsa AbuseIPDB'ye canli sorgu (8.8.8.8, maxAgeInDays=1)
- `X-RateLimit-Remaining` ve `X-RateLimit-Limit` header'larindan deger okunur
- Redis'e 86400s (24h) TTL ile geri yazilir
- Hata durumunda sessizce basarisiz olur (mevcut davranis korunur)

**Not:** Bu sorgu 1 AbuseIPDB check hakkini harcar. Sadece Redis key'leri expire olmus ve summary endpoint cagirilmissa tetiklenir (nadir, gunluk 1 kez).

**Commit:** `ca05942`

## Deviations from Plan

None - plan tam olarak uygulandi.

## Deploy

- Pi'ye SFTP ile yuklendi, `sudo cp` ile yerlestirildi
- `sudo systemctl restart tonbilaios-backend` — status: `active`
- Dogrulama: Backend aktif, dosyalar Pi'de guncel

## Self-Check: PASSED

- `backend/app/workers/ip_reputation.py` — FOUND
- `backend/app/api/v1/ip_reputation.py` — FOUND
- Commit `68d9c24` — FOUND
- Commit `ca05942` — FOUND
