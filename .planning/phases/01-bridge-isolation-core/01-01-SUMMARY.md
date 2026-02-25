---
phase: 01-bridge-isolation-core
plan: 01
subsystem: infra
tags: [nftables, bridge, isolation, hal, linux, networking, masquerade, rollback]

# Dependency graph
requires: []
provides:
  - ensure_bridge_isolation() in backend/app/hal/linux_nftables.py
  - remove_bridge_isolation() in backend/app/hal/linux_nftables.py
  - ensure_bridge_masquerade() marked deprecated (not removed)
affects:
  - 02-bridge-accounting (bridge accounting chains must work after isolation)
  - 03-tc-mark (TC mark chains build on isolated interface)
  - 04-persistence (Phase 4 swaps ensure_bridge_masquerade with ensure_bridge_isolation in main.py)
  - 05-dhcp-gateway (DHCP gateway change applies after isolation is active)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent rule application via comment anchors (check ruleset before adding)"
    - "Atomic two-rule application via nft -f stdin (both drop directions in one transaction)"
    - "Handle-based deletion with live re-query (never cache handles across reboots)"
    - "Ordered setup sequence for SSH lockout prevention (sysctl → br_netfilter → ICMP off → NAT → drop)"

key-files:
  created: []
  modified:
    - backend/app/hal/linux_nftables.py

key-decisions:
  - "MASQUERADE verified BEFORE drop rules — abort function (not exception) if MASQUERADE fails to prevent SSH lockout"
  - "Both L2 drop rules applied in single atomic nft -f - transaction to avoid asymmetric isolation window"
  - "remove_bridge_isolation() re-queries handles at call time — handles change after nftables.service reloads on boot"
  - "masquerade_fix table deleted in Step 6 ONLY after drop rules are active (Step 5) — prevents MAC-rewrite disruption"
  - "ensure_bridge_masquerade() marked DEPRECATED but not removed — Phase 4 handles the main.py lifespan swap"
  - "ICMP redirects (send_redirects) disabled in ensure_bridge_isolation() and restored in remove_bridge_isolation()"

patterns-established:
  - "Pattern 1: Comment anchors as idempotency gates — string search in full ruleset before applying rules"
  - "Pattern 2: Atomic batch via asyncio.create_subprocess_exec(sudo, NFT_BIN, -f, -) with stdin for multi-rule transactions"
  - "Pattern 3: Live handle lookup for deletion — re.search(handle\\s+(\\d+)) on nft -a list chain output at call time"
  - "Pattern 4: Abort-on-NAT-failure — return (not raise) when MASQUERADE step fails to preserve SSH access"

requirements-completed: [ISOL-01, ISOL-02, ISOL-03, ISOL-04, ISOL-05, ISOL-06, ISOL-07, ROLL-01, ROLL-02, ROLL-03]

# Metrics
duration: 15min
completed: 2026-02-25
---

# Phase 1 Plan 01: Bridge Isolation Core Summary

**Two async HAL functions added to linux_nftables.py: ensure_bridge_isolation() (7-step ordered L2 forward-drop isolation with MASQUERADE-first safety) and remove_bridge_isolation() (live handle-based rollback restoring transparent bridge mode)**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-25T10:00:00Z
- **Completed:** 2026-02-25T10:14:42Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Added ensure_bridge_isolation() with 7-step ordered sequence preventing SSH lockout: ip_forward=1 (Step 1) → br_netfilter + bridge-nf-call-iptables=1 (Step 2) → ICMP redirects off (Step 3) → MASQUERADE verified/added (Step 4) → atomic L2 drop rules (Step 5) → masquerade_fix table cleanup (Step 6) → persist (Step 7)
- Added remove_bridge_isolation() with live handle lookup (never cached), filtering by "bridge_isolation" comment anchor, restoring ICMP redirects, and persisting rollback state
- Marked ensure_bridge_masquerade() as DEPRECATED in docstring (not removed — Phase 4 handles main.py lifespan swap)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ensure_bridge_isolation() to linux_nftables.py** - `fc1e4ec` (feat)
2. **Task 2: Add remove_bridge_isolation() to linux_nftables.py** - `98bfd92` (feat)

**Plan metadata:** (to be added in final commit)

## Files Created/Modified

- `backend/app/hal/linux_nftables.py` - Added ensure_bridge_isolation() (lines 1141-1229), remove_bridge_isolation() (lines 1231-1267), deprecated ensure_bridge_masquerade() docstring (line 1058)

## Decisions Made

- MASQUERADE verified BEFORE drop rules — if ensure_nat_postrouting_chain() or the stdin nft call fails, function returns immediately (not raises) so the caller does not get an exception while SSH is still accessible
- Both drop rules (bridge_isolation_lan_wan + bridge_isolation_wan_lan) applied in a single atomic nft -f - stdin transaction to prevent asymmetric isolation window
- remove_bridge_isolation() re-queries handles at call time via `nft -a list chain bridge filter forward` — handles assigned by nftables are runtime values that change after Pi reboots when nftables.service reloads the persisted ruleset
- masquerade_fix table deletion deferred to Step 6 (after drop rules confirmed active in Step 5) — deleting it before drop rules would disrupt MAC rewrite for actively-connected LAN devices
- send_redirects set to 0 during isolation and restored to 1 on rollback — prevents Pi from redirecting clients past itself in router mode
- ensure_bridge_masquerade() DEPRECATED marker placed in docstring, function body untouched — Phase 4 is responsible for the main.py lifespan swap

## Deviations from Plan

None — plan executed exactly as written. All 7 steps implemented in specified order. All comment anchors used as specified. All code patterns from RESEARCH.md applied as documented.

## Issues Encountered

None — implementation was straightforward pattern reuse from existing codebase functions (ensure_bridge_masquerade(), _delete_rule_by_handle()). All helper functions (_get_wan_bridge_port(), _detect_lan_subnet(), ensure_nat_postrouting_chain(), persist_nftables(), BRIDGE_MASQ_TABLE) existed and worked as expected.

## Verification Results

All automated checks passed:

1. Python syntax valid: `ast.parse` returns OK
2. Both functions present:
   - `1141:async def ensure_bridge_isolation`
   - `1231:async def remove_bridge_isolation`
3. Comment anchors present (9 occurrences across both functions and ensure_bridge_masquerade):
   - bridge_isolation_lan_wan (2 occurrences in ensure_bridge_isolation)
   - bridge_isolation_wan_lan (2 occurrences in ensure_bridge_isolation)
   - bridge_lan_masq (3 occurrences: ensure_bridge_masquerade, ensure_bridge_isolation, remove_bridge_masquerade)
4. DEPRECATED marker: `1058: DEPRECATED: Use ensure_bridge_isolation() instead. Removed in Phase 4 (main.py lifespan swap).`
5. Ordering assertion: bridge_lan_masq position 1668 < bridge_isolation_lan_wan position 2821 — MASQUERADE anchor precedes drop rule anchor within ensure_bridge_isolation() body
6. Function ordering in file: ensure_bridge_masquerade (1055) → ensure_bridge_isolation (1141) → remove_bridge_isolation (1231) → remove_bridge_masquerade (1268)
7. No hardcoded "eth0" or "192.168.1.0/24" in new functions — wan_iface from _get_wan_bridge_port(), lan_subnet from _detect_lan_subnet()
8. Atomic batch pattern: NFT_BIN -f - used for both MASQUERADE rule and drop rules (2 separate calls within ensure_bridge_isolation)
9. send_redirects=1 appears 2 times in file (both in remove_bridge_isolation)

## User Setup Required

None — no external service configuration required. Pi deployment and activation is handled in Phase 4 (main.py lifespan swap).

## Next Phase Readiness

- Phase 2 (bridge accounting chains) can proceed: ensure_bridge_isolation() provides the isolated interface topology that accounting chains require (per_device → upload/download split on input/output hooks)
- Phase 4 (persistence) will swap ensure_bridge_masquerade() → ensure_bridge_isolation() in main.py lifespan startup; ensure_bridge_masquerade() is marked deprecated and ready for removal
- Research flag remains open: "Validate handle-based deletion stability after Pi reboots" — addressed architecturally by live re-query in remove_bridge_isolation(), but physical Pi validation occurs when Phase 4 deploys

## Self-Check: PASSED

- FOUND: backend/app/hal/linux_nftables.py
- FOUND: .planning/phases/01-bridge-isolation-core/01-01-SUMMARY.md
- FOUND: commit fc1e4ec (feat(01-01): add ensure_bridge_isolation())
- FOUND: commit 98bfd92 (feat(01-01): add remove_bridge_isolation())

---
*Phase: 01-bridge-isolation-core*
*Completed: 2026-02-25*
