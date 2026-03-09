---
phase: quick-22
plan: 01
subsystem: iptv-device-support
tags: [iptv, dns-bypass, nftables, multicast, igmp, frontend-toggle]
dependency_graph:
  requires: []
  provides: [iptv-device-support, dns-iptv-bypass, nftables-multicast-rules]
  affects: [dns-proxy, nftables, device-api, frontend-devices]
tech_stack:
  added: []
  patterns: [redis-set-ip-bypass, nftables-raw-notrack, toggle-switch-cyberpunk]
key_files:
  created: []
  modified:
    - backend/app/models/device.py
    - backend/app/schemas/device.py
    - backend/app/api/v1/devices.py
    - backend/app/workers/dns_proxy.py
    - backend/app/hal/linux_nftables.py
    - backend/app/main.py
    - frontend/src/types/index.ts
    - frontend/src/pages/DeviceDetailPage.tsx
    - frontend/src/pages/DevicesPage.tsx
decisions:
  - "Redis key olarak iptv:device_ids SET secildi (device ID degil IP adresi — DNS proxy performansi icin)"
  - "DNS bypass IPTV kontrolu device_blocked kontrolunden ONCE yapiliyor (en yuksek oncelik)"
  - "nftables raw_iptv ayri tablo olarak olusturuldu (tonbilai tablosuyla cakisma olmamasi icin)"
  - "handle_dot'ta continue kullanildi (while dongu icinde), handle_query'de return (async fonksiyon)"
metrics:
  duration: "~12 dakika"
  completed_date: "2026-03-09"
  tasks_completed: 2
  files_modified: 9
---

# Quick Task 22: IPTV Cihaz Destegi Summary

## One-liner

IPTV cihaz destegi: `is_iptv` flag ile DNS filtreleme bypass (Redis SET IP kontrolu), nftables raw tablosu ile multicast/IGMP notrack, ve cyberpunk-temali frontend toggle/badge.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backend — Device modeli + API + DNS proxy bypass + nftables IPTV kurallari | 257f7d0 | models/device.py, schemas/device.py, api/v1/devices.py, dns_proxy.py, linux_nftables.py, main.py |
| 2 | Frontend — IPTV toggle (DeviceDetailPage) + IPTV badge (DevicesPage) | 1eebe2a | types/index.ts, DeviceDetailPage.tsx, DevicesPage.tsx |

## What Was Built

### Backend (Task 1)

**Device Modeli:**
- `backend/app/models/device.py`: `is_iptv = Column(Boolean, default=False)` eklendi

**Device Semalari:**
- `backend/app/schemas/device.py`: `DeviceUpdate`'e `is_iptv: Optional[bool] = None`, `DeviceResponse`'a `is_iptv: bool = False` eklendi. Ayrica eksik `device_type`, `risk_score`, `risk_level` alanlari da eklendi.

**Device API:**
- `backend/app/api/v1/devices.py`: PATCH endpoint `is_iptv` degisikliginde Redis `iptv:device_ids` SET'ini gunceller (sadd/srem)

**DNS Proxy:**
- `backend/app/workers/dns_proxy.py`: `handle_query()` ve `handle_dot()` fonksiyonlarinda `total_queries` sayiminden hemen sonra `sismember("iptv:device_ids", client_ip)` kontrolu eklendi. IPTV cihazlar tum engelleme kontrolunu atlayarak direkt upstream'e yonlendirilir.

**nftables IPTV Kurallari:**
- `backend/app/hal/linux_nftables.py`: `ensure_iptv_rules()` fonksiyonu eklendi:
  - `table inet raw_iptv`: multicast 224.0.0.0/4 ve IGMP icin prerouting+output chain'de `notrack` (conntrack bypass)
  - `inet tonbilai forward`: multicast ve IGMP icin `accept` kurallari (basina insert)

**Startup Sync:**
- `backend/app/main.py`:
  - Migration: `ALTER TABLE devices ADD COLUMN is_iptv BOOLEAN DEFAULT FALSE`
  - `ensure_iptv_rules()` cagrisi
  - DB'deki is_iptv cihazlarinin IP'leri Redis `iptv:device_ids` SET'ine yukleniyor

### Frontend (Task 2)

**TypeScript Tipi:**
- `frontend/src/types/index.ts`: `Device` interface'ine `is_iptv: boolean` alani eklendi

**DeviceDetailPage:**
- "Bant Genisligi" bölümünün altina neon-cyan glow efektli IPTV toggle switch eklendi
- Toggle acikken: `bg-neon-cyan/30 border-neon-cyan/50 shadow-[0_0_10px_rgba(0,240,255,0.3)]`
- Toggle kapaliyken: `bg-white/10 border-white/20`
- Click handler: `updateDevice(device.id, { is_iptv: !device.is_iptv })` + `loadDevice()`
- Feedback mesaji: acma/kapama durumuna gore Turkce bildirim

**DevicesPage:**
- Cihaz kartinda hostname ile edit butonu arasina IPTV badge eklendi
- Badge: `bg-neon-cyan/10 text-neon-cyan border-neon-cyan/20` + `<Tv size={10}>` ikonu

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing fields] DeviceResponse semasi eksik alanlari**
- **Found during:** Task 1 - schemas/device.py incelemesinde
- **Issue:** `DeviceResponse`'da `device_type`, `risk_score`, `risk_level` alanlari yoktu ama model'de vardi; frontend'de kullaniliyordu
- **Fix:** Bu alanlari da `DeviceResponse`'a eklendi
- **Files modified:** backend/app/schemas/device.py
- **Commit:** 257f7d0 (Task 1 commit icinde)

**2. [Rule 3 - Blocking issue] async_session_factory inline import gerekliligi**
- **Found during:** Task 1 - main.py IPTV startup sync yazilirken
- **Issue:** `async_session_factory` dosyanin basinda global import edilmemis, diger startup bloklari da inline import kullaniyor
- **Fix:** `from app.db.session import async_session_factory as _iptv_session_factory` inline import eklendi
- **Files modified:** backend/app/main.py
- **Commit:** 257f7d0 (Task 1 commit icinde)

## Verification Results

### Backend Syntax
```
models/device.py OK
schemas/device.py OK
api/v1/devices.py OK
linux_nftables.py OK
main.py OK
dns_proxy.py OK
```

### Grep Checks
- `grep -c "is_iptv" backend/app/models/device.py` → 1
- `grep -c "ensure_iptv_rules" backend/app/hal/linux_nftables.py` → 1
- `grep -c "iptv:device_ids" backend/app/workers/dns_proxy.py` → 2
- `grep -c "iptv:device_ids" backend/app/api/v1/devices.py` → 3
- `grep -c "ensure_iptv_rules" backend/app/main.py` → 2

### Frontend TypeScript
- `npx tsc --noEmit` → 0 hata
- `grep -c "is_iptv" frontend/src/types/index.ts` → 1
- `grep -c "IPTV" frontend/src/pages/DeviceDetailPage.tsx` → 4
- `grep -c "IPTV" frontend/src/pages/DevicesPage.tsx` → 1

## Self-Check: PASSED

Dosyalar mevcut:
- backend/app/models/device.py: FOUND
- backend/app/schemas/device.py: FOUND
- backend/app/api/v1/devices.py: FOUND
- backend/app/workers/dns_proxy.py: FOUND
- backend/app/hal/linux_nftables.py: FOUND
- backend/app/main.py: FOUND
- frontend/src/types/index.ts: FOUND
- frontend/src/pages/DeviceDetailPage.tsx: FOUND
- frontend/src/pages/DevicesPage.tsx: FOUND

Commitler mevcut:
- 257f7d0: FOUND
- 1eebe2a: FOUND
