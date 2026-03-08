---
phase: quick
plan: 7
subsystem: backend-performance
tags: [redis, bandwidth, flow-tracker, iptv, eth1, ring-buffer]
dependency_graph:
  requires: []
  provides: [redis-pool-fix, poll-optimization, eth1-tuning]
  affects: [bandwidth_monitor, flow_tracker, redis_client]
tech_stack:
  added: []
  patterns: [singleton-redis-client, connection-pool-timeout]
key_files:
  created: [deploy_quick7.py]
  modified: [backend/app/db/redis_client.py, backend/app/workers/bandwidth_monitor.py, backend/app/workers/flow_tracker.py]
decisions:
  - Singleton Redis client pattern adopted to prevent connection leaks
  - POLL_INTERVAL 3s to 10s reduces sudo overhead by ~75%
  - eth1 ring buffer 4096 persistent via rc.local
metrics:
  duration: "3 min"
  completed: "2026-03-08"
  tasks_completed: 3
  tasks_total: 3
---

# Quick Plan 7: IPTV Streaming Performans Duzeltmeleri Summary

Redis baglanti havuzu singleton + timeout parametreleri, bandwidth poll interval 3s->10s, eth1 ring buffer 100->4096

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Redis baglanti havuzu duzeltmesi | 91a095d | backend/app/db/redis_client.py |
| 2 | Bandwidth monitor + flow tracker poll interval optimizasyonu | 8d6017f | backend/app/workers/bandwidth_monitor.py, backend/app/workers/flow_tracker.py |
| 3 | Pi'de eth1 ring buffer + IRQ fix deploy | a6d66d3 | deploy_quick7.py |

## Changes Made

### Task 1: Redis Connection Pool Fix
- `socket_timeout=5` ve `socket_connect_timeout=5` eklendi (asilmis baglantilari keser)
- `retry_on_timeout=True` eklendi (timeout sonrasi otomatik yeniden deneme)
- `health_check_interval=30` eklendi (baglanti saglik kontrolu)
- Singleton pattern: `get_redis()` artik her cagrisinda ayni Redis client instance'ini dondurur
- **Sonuc:** Redis baglanti sayisi 1000+ -> 4

### Task 2: Poll Interval Optimizasyonu
- `bandwidth_monitor.py` POLL_INTERVAL: 3s -> 10s (sudo cagrisi dakikada ~83 -> ~20)
- IP refresh counter: 20 -> 6 dongu (~60s aralik korundu)
- HISTORY_MAX_LEN: 600 -> 300 (10s aralikla ~50 dakika gecmis)
- `flow_tracker.py` conntrack subprocess timeout: 30s -> 10s (hizli hata tespiti)

### Task 3: Pi Deploy + eth1 Ring Buffer
- 3 degistirilmis dosya SFTP ile Pi'ye aktarildi
- eth1 rx ring buffer: 100 -> 4096 (LAN tarafinda paket kaybi azaltildi)
- RPS dogrulandi: eth0=f, eth1=f (4 CPU core'a dagitim)
- rc.local'a eth1 ring buffer komutu eklendi (kalici)
- Backend restart basarili, status=active
- Redis baglanti sayisi dogrulandi: 4

## Deviations from Plan

None - plan executed exactly as written.

**Not:** wg show cagrisi bandwidth_monitor.py'de bulunmadi (bandwidth izleme nft counter kullaniyor), bu nedenle wg interval ayari atlandi.

## Decisions Made

1. **Singleton Redis client:** Her `get_redis()` cagrisi yeni Redis() objesi olusturmak yerine tek bir instance paylasiyor. Bu, connection pool icinde bile gereksiz obje olusturmayı onler.
2. **health_check_interval=30:** Redis pool baglantilari 30 saniyede bir saglik kontrolundan geciyor — olmus baglantilari otomatik temizler.
3. **HISTORY_MAX_LEN 300:** 10s aralikla ~50 dakika gecmis yeterli. Frontend zaten son 3 dakikayi gosteriyor.

## Verification Results

| Check | Result |
|-------|--------|
| Redis max_connections=50 | PASS |
| Redis socket_timeout=5 | PASS |
| Redis retry_on_timeout=True | PASS |
| POLL_INTERVAL=10 | PASS |
| conntrack timeout=10 | PASS |
| eth1 ring buffer=4096 | PASS |
| RPS eth0=f, eth1=f | PASS |
| Backend status=active | PASS |
| Redis connections=4 | PASS |
| rc.local persistent | PASS |

## Self-Check: PASSED

All 5 files found, all 3 commits verified.
