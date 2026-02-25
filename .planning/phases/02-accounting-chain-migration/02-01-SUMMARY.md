---
phase: 02-accounting-chain-migration
plan: 01
subsystem: infra
tags: [nftables, bridge, bandwidth, accounting, linux, nft-reset]

# Dependency graph
requires:
  - phase: 01-bridge-isolation-core
    provides: Bridge L2 drop (forward chain drops all LAN traffic, forward hook gets no packets)
provides:
  - Split upload/download accounting chains on input/output hooks (eth1 iifname/oifname)
  - nft-reset-based atomic counter read and clear per cycle
  - Cumulative bandwidth totals tracked in bandwidth_monitor for Redis persistence
affects:
  - 03-qos-tc-marking
  - 04-main-lifespan-swap
  - 05-dhcp-gateway-migration

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "nft reset chain: atomic read-and-zero — returned values are cycle delta, not cumulative"
    - "Split accounting chains: upload (input hook, iifname) + download (output hook, oifname)"
    - "_cumulative_totals dict: module-level accumulator when nft zeroes counters on each read"

key-files:
  created: []
  modified:
    - backend/app/hal/linux_nftables.py
    - backend/app/workers/bandwidth_monitor.py

key-decisions:
  - "nft reset semantics: each read_device_counters() call resets counters atomically; returned values ARE the delta"
  - "Upload chain: type filter hook input priority -2, iifname eth1, ether saddr {mac}"
  - "Download chain: type filter hook output priority -2, oifname eth1, ether daddr {mac}"
  - "ensure_bridge_accounting_chain(): auto-cleans old per_device chain on startup via flush+delete"
  - "add_device_counter(): raises RuntimeError if upload succeeds but download fails (no partial state)"
  - "remove_device_counter(): logs warning but does not raise if MAC not found (idempotent-close)"
  - "read_device_counters(): returns {} and logs error on nftables failure (bandwidth_monitor skips cycle)"
  - "_cumulative_totals: tracks running byte/packet totals so Redis upload_total/download_total remain meaningful"
  - "_write_hourly_snapshot: uses _cumulative_totals as snapshot source, not raw delta counters"

patterns-established:
  - "Pattern: nft reset chain for atomic per-cycle delta reads (no stale counter drift)"
  - "Pattern: Split bridge chains for upload/download — one chain per traffic direction"
  - "Pattern: Baseline read on startup discards result (clears stale counters from previous run)"

requirements-completed: [ACCT-01, ACCT-02, ACCT-03, ACCT-04, ACCT-05, ACCT-06, ACCT-07]

# Metrics
duration: 4min
completed: 2026-02-25
---

# Phase 2 Plan 01: Accounting Chain Migration Summary

**Bridge bandwidth accounting migrated from single forward-hook per_device chain to split upload (input hook) + download (output hook) chains on eth1, with nft-reset-based atomic per-cycle delta reads in bandwidth_monitor.py**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-25T13:19:48Z
- **Completed:** 2026-02-25T13:23:49Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote all five bridge accounting functions to use split upload/download chains on input/output hooks (not forward hook, which Phase 1 isolation dropped all traffic on)
- ensure_bridge_accounting_chain() now auto-detects and cleans old per_device chain, then creates upload + download chains atomically
- read_device_counters() switched from `nft list` (cumulative) to `nft reset` (atomic read-and-clear), each call returns the cycle delta
- bandwidth_monitor.py updated: removed _previous_counters and subtraction logic, added _cumulative_totals for Redis upload_total/download_total persistence, hourly snapshot uses cumulative data

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite accounting chain functions in linux_nftables.py** - `52a45b0` (feat)
2. **Task 2: Update bandwidth_monitor.py for nft-reset counter semantics** - `6182aa6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/app/hal/linux_nftables.py` - Five accounting functions rewritten: ensure_bridge_accounting_chain (split chains + per_device cleanup), add_device_counter (both chains, raises on partial), remove_device_counter (both chains by handle, warns if not found), read_device_counters (nft reset), sync_device_counters (upload chain detection). Added BRIDGE_CHAIN_UPLOAD and BRIDGE_CHAIN_DOWNLOAD constants.
- `backend/app/workers/bandwidth_monitor.py` - Removed _previous_counters global and delta subtraction; added _cumulative_totals accumulator; simplified baseline read; updated _write_hourly_snapshot to use cumulative totals.

## Decisions Made
- Used `nft reset` instead of `nft list` so each read atomically resets counters — no need to track previous values for delta calculation
- add_device_counter() raises RuntimeError on partial failure (upload added, download failed) — no silent half-state
- remove_device_counter() logs warnings but does not raise when MAC not found — idempotent-close behavior
- _cumulative_totals dict accumulates deltas per MAC so Redis upload_total/download_total remain meaningful across nft-reset cycles
- Hourly snapshot uses _cumulative_totals (not raw delta counters) for accurate per-hour byte counts

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] _write_hourly_snapshot updated to use _cumulative_totals**
- **Found during:** Task 2 (bandwidth_monitor.py update)
- **Issue:** Plan specified removing _previous_counters and using counter values as deltas, but _write_hourly_snapshot was still iterating over `counters` (10s delta). With nft reset, the snapshot would only record the last 10s worth of traffic instead of the full hour.
- **Fix:** Updated _write_hourly_snapshot to use `_cumulative_totals` as its data source when available, preserving hourly aggregate accuracy.
- **Files modified:** backend/app/workers/bandwidth_monitor.py
- **Verification:** Function references _cumulative_totals; counters parameter kept for fallback only
- **Committed in:** 6182aa6 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (missing critical)
**Impact on plan:** Fix necessary for correct hourly snapshot data. No scope creep.

## Issues Encountered
None — both files modified cleanly, all verifications passed.

## User Setup Required
None - no external service configuration required. Changes take effect on next `sudo systemctl restart tonbilaios-backend`.

## Next Phase Readiness
- Phase 3 (QoS TC Marking): bandwidth accounting infrastructure ready, split chains provide clean per-direction byte counts
- Phase 4 (Main lifespan swap): ensure_bridge_accounting_chain() startup sequence ready; ensure_bridge_masquerade() still present but deprecated per Phase 1 decision
- Research flag: Validate that nft reset on bridge chains works correctly when br_netfilter is loaded (accounting counter isolation from inet chain)

---
*Phase: 02-accounting-chain-migration*
*Completed: 2026-02-25*
