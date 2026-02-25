# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Modem sadece Pi'yi gorsun, tum LAN cihazlari modemden gizlensin — trafik Pi'nin IP stack'i uzerinden route edilsin.
**Current focus:** Phase 1 — Bridge Isolation Core

## Current Position

Phase: 1 of 5 (Bridge Isolation Core)
Plan: 0 of 1 in current phase
Status: Ready to plan
Last activity: 2026-02-25 - Phase 1 context gathered, ready to replan

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: none yet
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Bridge L2 drop (forward chain): Modem must not see LAN device MACs
- Accounting input/output hook: Forward hook receives no traffic after isolation drop
- DHCP gateway .2: Pi is now the router, must be the gateway
- Eski masquerade_fix kaldirilir: Router modunda MAC rewrite gereksiz
- Rollback dahil: Pre-staged before any live step is applied
- [Phase quick-1]: Used Python shutil.copytree instead of robocopy due to bash/Windows path-with-spaces incompatibility

### Research Flags (from SUMMARY.md)

- Phase 1: Validate handle-based deletion stability after Pi reboots
- Phase 3: Validate TC mark preservation across bridge to inet boundary with live bandwidth test
- Both: Confirm `inet tonbilai forward` MAC-block rules still fire after isolation (br_netfilter still loaded)
- All phases: Confirm eth0/eth1/br0 interface naming stability on Pi OS Bookworm

### Critical Pitfalls to Avoid

- SSH lockout: Apply ip_forward + MASQUERADE + verify curl BEFORE drop rules
- Silent zero counters: Verify br_netfilter and ip_forward before applying isolation
- sysctl boot-order: br_netfilter in modules-load.d must load before systemd-sysctl
- DHCP gap: Shorten lease to 5 min before gateway change, wait for full renewal cycle

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Yapiyi tamamen yeni bir klasore yaz. ismi: TonbilAiFirevallv5 olsun. | 2026-02-25 | 5151374 | [1-yapiyi-tamamen-yeni-bir-klasore-yaz-ismi](./quick/1-yapiyi-tamamen-yeni-bir-klasore-yaz-ismi/) |
| 2 | TonbilAiFirevallv5 klasorunde CLAUDE.md guncelle. | 2026-02-25 | 71853f7 | [2-tonbilaifirevallv5-klasorunde-claude-md-](./quick/2-tonbilaifirevallv5-klasorunde-claude-md-/) |

## Session Continuity

Last session: 2026-02-25
Stopped at: Phase 1 context gathered
Resume file: .planning/phases/01-bridge-isolation-core/01-CONTEXT.md
