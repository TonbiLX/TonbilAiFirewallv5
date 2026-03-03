---
phase: 05-dhcp-gateway-and-validation
plan: 02
subsystem: infra
tags: [bash, shell, validation, nftables, dhcp, veth, netns, conntrack, tcpdump, dnsmasq]

requires:
  - phase: 01-bridge-isolation-core
    provides: "bridge_isolation_lan_wan / bridge_isolation_wan_lan drop rules in bridge filter forward"
  - phase: 02-accounting-chain-migration
    provides: "bridge accounting upload/download chains"
  - phase: 03-tc-mark-chain-migration
    provides: "TC mark chains for per-device bandwidth limiting"
  - phase: 04-startup-and-persistence
    provides: "nftables.service persistence, sysctl.d, modules-load.d"
  - phase: 05-plan-01
    provides: "DHCP gateway change to 192.168.1.2 in dnsmasq + DB"
provides:
  - "validate.sh: 449-line bash script covering all 9 checks (DHCP-01, DHCP-02, VALD-01 through VALD-07)"
  - "Root check, colored PASS/FAIL/WARN/SKIP output, summary footer with exit code"
  - "VALD-07 veth namespace test with trap-based cleanup"
affects: []

tech-stack:
  added: []
  patterns:
    - "Trap-based cleanup for veth/netns test resources (trap _veth_cleanup EXIT)"
    - "Graceful SKIP instead of FAIL when optional tools (dig, conntrack, tcpdump) not installed"
    - "WARN distinction for checks that pass infrastructure but lack live traffic data"

key-files:
  created:
    - ".planning/phases/05-dhcp-gateway-and-validation/validate.sh"
  modified: []

key-decisions:
  - "VALD-07 uses trap EXIT for cleanup so namespace/veth are always removed even on script error"
  - "VALD-01 skips (not fails) when no ARP packets captured — requires live LAN traffic"
  - "VALD-02 and VALD-05 use WARN instead of FAIL when infrastructure exists but no active traffic yet"
  - "DHCP-02 uses SKIP if mysql client not installed — validation is optional when DB is not directly accessible"
  - "VALD-07 sub-checks (internet + DNS) counted as one VALD-07 total for the 9-check summary"
  - "Test IP 192.168.1.250 chosen outside DHCP pool range (100-200); auto-falls back to .240/.245 if in use"

requirements-completed: [VALD-01, VALD-02, VALD-03, VALD-04, VALD-05, VALD-06, VALD-07]

duration: 3min
completed: 2026-03-03
---

# Phase 5 Plan 2: Validation Script Summary

**9-check bash validation script (validate.sh) covering DHCP gateway verification and all 7 VALD post-deployment checks including a veth namespace simulated LAN client test**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-03T15:59:27Z
- **Completed:** 2026-03-03T16:02:47Z
- **Tasks:** 2 of 2
- **Files modified:** 1

## Accomplishments

- Complete 449-line validate.sh covering DHCP-01, DHCP-02, and VALD-01 through VALD-07
- VALD-07 veth namespace test with ip netns / veth pair setup, routing through Pi as gateway, and trap-based cleanup
- Colored PASS/FAIL/WARN/SKIP output per check with summary footer and exit code (0=all pass, 1=any fail)
- DHCP-01 checks /etc/dnsmasq.d/pool-1.conf for dhcp-option=3,192.168.1.2; DHCP-02 queries MariaDB directly
- Graceful degradation: optional tools (dig, conntrack, tcpdump) cause SKIP not FAIL; zero-traffic counters cause WARN not FAIL

## Task Commits

Each task was committed atomically:

1. **Task 1: Write validate.sh with all 7 VALD checks** - `a7b76a6` (feat)
2. **Task 2: Add DHCP config verification commands to validate.sh** - `606974e` (feat)

**Plan metadata:** (to be added in final commit)

## Files Created/Modified

- `.planning/phases/05-dhcp-gateway-and-validation/validate.sh` - Complete 9-check post-deployment validation script for Pi

## Decisions Made

- VALD-07 uses `trap _veth_cleanup EXIT` so namespace and veth are cleaned up even if curl/dig fail mid-test
- VALD-01 (ARP tcpdump) uses SKIP not FAIL when no packets captured — live LAN traffic required, not always available
- VALD-05 (accounting counters) uses WARN for zero counters — chains may exist but no traffic yet at validation time
- Script deliberately has no SSH or API calls — runs entirely from Pi local system commands
- Test IP 192.168.1.250 probed before use; falls back to .240 then .245 if the address is already in use
- DHCP-01 and DHCP-02 placed before VALD-06 — DHCP gateway is the prerequisite change this phase delivers

## Deviations from Plan

None - plan executed exactly as written. DHCP-01 and DHCP-02 were included in the initial Task 1 implementation (pre-emptively satisfying Task 2 requirements), and Task 2 added remediation hints for DHCP-specific failures.

## Issues Encountered

None.

## User Setup Required

**The validate.sh script is intended to be run manually on Pi after deploying all phases.**

To run:
```bash
# Copy to Pi (already at .planning/phases/05-dhcp-gateway-and-validation/validate.sh locally)
# Then on Pi:
sudo bash validate.sh
```

Expected output: All 9 checks PASS after full deployment. WARNs are acceptable if run immediately after deployment before active traffic is present.

## Next Phase Readiness

Phase 5 is complete. All 5 phases of the bridge isolation transition are now implemented and documented:
- Phase 1: Bridge isolation core (L2 drop rules + MASQUERADE)
- Phase 2: Accounting chain migration (upload/download counters)
- Phase 3: TC mark chain migration (per-device bandwidth limiting)
- Phase 4: Boot persistence (nftables.service + sysctl.d + modules-load.d)
- Phase 5: DHCP gateway change + validation script

The validate.sh script provides the definitive post-deployment verification for the complete transition.

---
*Phase: 05-dhcp-gateway-and-validation*
*Completed: 2026-03-03*
