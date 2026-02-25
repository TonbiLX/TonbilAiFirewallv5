---
phase: 03-tc-mark-chain-migration
plan: 01
subsystem: infra
tags: [nftables, tc, htb, bridge, bandwidth, mark-chain, linux_tc]

# Dependency graph
requires:
  - phase: 02-accounting-chain-migration
    provides: bridge accounting table (bridge accounting) with upload/download chains on input/output hooks
  - phase: 01-bridge-isolation-core
    provides: bridge isolation (L2 forward drop) that makes the forward hook dead for TC marks

provides:
  - TC_MARK_CHAIN_UP constant ("tc_mark_up") for input hook marking
  - TC_MARK_CHAIN_DOWN constant ("tc_mark_down") for output hook marking
  - _ensure_tc_mark_chain() creates split chains on input/output hooks with idempotency and legacy cleanup
  - add_device_limit() sets marks on both tc_mark_up (iifname eth1 saddr) and tc_mark_down (oifname eth1 daddr)
  - _remove_nft_mark_rule() iterates both tc_mark_up and tc_mark_down chains for handle-based deletion

affects:
  - Phase 4 (main.py lifespan swap — calls add_device_limit on startup for bandwidth restore)
  - Phase 5 (live bandwidth validation — the mark chains must fire for HTB enforcement to work)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Split TC mark chains on bridge input/output hooks (same pattern as Phase 2 accounting chains)
    - Comment-anchored handle-based rule deletion iterating per-direction chains
    - Idempotency check using list ruleset before chain creation
    - Legacy chain cleanup (flush+delete old forward-hook tc_mark chain on detection)

key-files:
  created: []
  modified:
    - backend/app/hal/linux_tc.py

key-decisions:
  - "TC_MARK_CHAIN kept as legacy reference (not removed) — mirrors Phase 2 BRIDGE_CHAIN = 'per_device' precedent"
  - "_remove_nft_mark_rule() uses check=False on bridge delete calls (explicit, avoids exception when chain empty)"
  - "tc_mark_up/down priority -1, accounting upload/download priority -2 — accounting fires first (count then mark)"
  - "remove_device_limit() inherits new behavior via delegation — no body changes needed (TCMK-05 coverage by design)"

patterns-established:
  - "Pattern: Split bridge chains for upload/download — tc_mark_up (input, iifname eth1, ether saddr) and tc_mark_down (output, oifname eth1, ether daddr)"
  - "Pattern: Comment-anchored handle deletion — iterate chains with for loop, find by comment_key, delete by handle"
  - "Pattern: Idempotency via ruleset check — list ruleset, check both chain names before creating"

requirements-completed: [TCMK-01, TCMK-02, TCMK-03, TCMK-04, TCMK-05]

# Metrics
duration: 3min
completed: 2026-02-25
---

# Phase 3 Plan 01: TC Mark Chain Migration Summary

**TC mark chain migrated from dead forward hook to split tc_mark_up (input) + tc_mark_down (output) bridge chains in linux_tc.py — per-device bandwidth marks now fire on hooks that carry traffic after bridge isolation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-25T14:56:26Z
- **Completed:** 2026-02-25T14:59:10Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Added TC_MARK_CHAIN_UP = "tc_mark_up" and TC_MARK_CHAIN_DOWN = "tc_mark_down" constants alongside legacy TC_MARK_CHAIN for cleanup
- Rewrote _ensure_tc_mark_chain() to create split chains on bridge input (priority -1) and output (priority -1) hooks with full idempotency and legacy forward-chain cleanup
- Rewrote add_device_limit() nft section to add iifname eth1 + ether saddr rules to tc_mark_up and oifname eth1 + ether daddr rules to tc_mark_down
- Rewrote _remove_nft_mark_rule() bridge section to iterate over both tc_mark_up and tc_mark_down chains with check=False deletes; inet tonbilai forward cleanup preserved unchanged
- HTB qdisc setup (setup_htb_root, get_device_stats) left untouched as planned

## Task Commits

Each task was committed atomically:

1. **Task 1: Add constants and rewrite _ensure_tc_mark_chain()** - `6d44503` (feat)
2. **Task 2: Rewrite add_device_limit() and _remove_nft_mark_rule()** - `b2a4e77` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/app/hal/linux_tc.py` - TC mark chain migration: split input/output hooks, new constants, rewritten chain create/add/delete functions

## Decisions Made
- TC_MARK_CHAIN = "tc_mark" kept as legacy reference constant — not removed — mirrors Phase 2 precedent of keeping BRIDGE_CHAIN = "per_device" for cleanup detection only
- _remove_nft_mark_rule() bridge section uses explicit `check=False` on delete calls — matches plan spec and avoids RuntimeError when chain is empty or not yet created
- Accounting chains at priority -2, TC mark chains at priority -1: correct ordering (count first, then mark) as documented in RESEARCH.md
- remove_device_limit() body unchanged — it delegates entirely to _remove_nft_mark_rule() which already handles both new chains (TCMK-05 coverage by design)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Minor: The plan's automated verify script uses `ast.FunctionDef` only, missing `AsyncFunctionDef` for async functions — causing the `_ensure_tc_mark_chain in funcs` assertion to fail when run as-is. All actual content checks (constants, chain creation, hooks) passed. The script was verified manually with the correct `(ast.FunctionDef, ast.AsyncFunctionDef)` check — all assertions pass. No code changes required; this is a plan artifact issue only.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- linux_tc.py now produces bridge nftables mark rules on hooks that carry traffic after isolation
- tc_mark_up and tc_mark_down chains coexist with Phase 2 accounting chains in the same bridge accounting table at the correct priority ordering
- Phase 4 (main.py lifespan swap) can safely call add_device_limit() — marks will fire on the correct hooks
- Phase 5 live bandwidth test: validate tc -s class show dev eth1 shows non-zero bytes in device's HTB class when device is active

---
*Phase: 03-tc-mark-chain-migration*
*Completed: 2026-02-25*
