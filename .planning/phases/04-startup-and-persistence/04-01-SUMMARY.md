---
phase: 04-startup-and-persistence
plan: 01
subsystem: infra
tags: [nftables, sysctl, systemd, boot-persistence, bridge-isolation]

# Dependency graph
requires:
  - phase: 01-bridge-isolation-core
    provides: "ensure_bridge_isolation() function that applies router mode rules at runtime"
provides:
  - "ensure_bridge_isolation_persistence() writes /etc/sysctl.d/99-bridge-isolation.conf, /etc/modules-load.d/99-bridge-isolation.conf, enables nftables.service"
  - "main.py lifespan calls ensure_bridge_isolation() + ensure_bridge_isolation_persistence() on backend start"
affects:
  - 05-testing-and-validation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sudo tee file write pattern (asyncio.create_subprocess_exec with stdin=PIPE) extended to sysctl.d and modules-load.d"
    - "Boot persistence trio: sysctl.d + modules-load.d + systemctl enable nftables.service"

key-files:
  created: []
  modified:
    - backend/app/hal/linux_nftables.py
    - backend/app/main.py

key-decisions:
  - "[04-01]: ensure_bridge_isolation_persistence() calls three private helpers in order: sysctl.d -> modules-load.d -> systemctl enable"
  - "[04-01]: ensure_bridge_masquerade() fully removed from main.py lifespan (deprecated since Phase 1, finally swapped)"
  - "[04-01]: Persistence called AFTER isolation — nftables.conf contains isolation rules before nftables.service is enabled"

patterns-established:
  - "Boot persistence pattern: write sysctl.d + modules-load.d + enable service — three-step idempotent boot setup"
  - "Private helper pattern: _write_sysctl_persistence, _write_modules_persistence, _enable_nftables_service — each focused on one file/service"

requirements-completed: [STRT-01, STRT-02, STRT-03, STRT-04]

# Metrics
duration: 5min
completed: 2026-03-03
---

# Phase 4 Plan 1: Startup and Persistence Summary

**Boot persistence for bridge isolation via sysctl.d, modules-load.d, and nftables.service enable — main.py lifespan swapped from deprecated ensure_bridge_masquerade to ensure_bridge_isolation + persistence**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-03T14:49:16Z
- **Completed:** 2026-03-03T14:54:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `ensure_bridge_isolation_persistence()` to linux_nftables.py with three private helpers that write /etc/sysctl.d/99-bridge-isolation.conf, /etc/modules-load.d/99-bridge-isolation.conf, and enable nftables.service
- Swapped main.py lifespan from `ensure_bridge_masquerade()` (deprecated since Phase 1) to `ensure_bridge_isolation()` + `ensure_bridge_isolation_persistence()`
- Bridge isolation (router mode) now fully survives Pi reboots — br_netfilter loads on boot, ip_forward stays enabled, nftables rules reload from nftables.conf

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ensure_bridge_isolation_persistence() to linux_nftables.py** - `85991bf` (feat)
2. **Task 2: Swap main.py lifespan from ensure_bridge_masquerade to ensure_bridge_isolation + persistence** - `049ab92` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `backend/app/hal/linux_nftables.py` - Added four new async functions: `_write_sysctl_persistence()`, `_write_modules_persistence()`, `_enable_nftables_service()`, `ensure_bridge_isolation_persistence()`; placed between `ensure_bridge_isolation()` and `remove_bridge_isolation()`
- `backend/app/main.py` - Replaced bridge masquerade try/except block with bridge isolation try/except block calling both `ensure_bridge_isolation()` and `ensure_bridge_isolation_persistence()`

## Decisions Made

- `ensure_bridge_isolation_persistence()` calls helpers in order: sysctl.d first (depends on br_netfilter being loaded), modules-load.d second (ensures br_netfilter loads at next boot), nftables.service enable last (ensures nftables.conf is loaded at boot after rules were persisted by ensure_bridge_isolation)
- Three private helper functions keep each responsibility isolated and testable independently
- `ensure_bridge_masquerade()` fully removed from main.py — it was deprecated in Phase 1 comment but never cleaned up until now

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Boot persistence is complete: bridge isolation + sysctl + br_netfilter + nftables.service all survive Pi reboots
- Phase 5 (testing and validation) can now validate reboot survival with live Pi testing
- Research flag from Phase 1 ("Validate handle-based deletion stability after Pi reboots") is now addressable — nftables.service enabled means rules load from nftables.conf, handles are re-queried at call time in remove_bridge_isolation()

---
*Phase: 04-startup-and-persistence*
*Completed: 2026-03-03*
