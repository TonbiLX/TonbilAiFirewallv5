# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-25)

**Core value:** Modem sadece Pi'yi gorsun, tum LAN cihazlari modemden gizlensin — trafik Pi'nin IP stack'i uzerinden route edilsin.
**Current focus:** Phase 3 — TC Mark Chain Migration

## Current Position

Phase: 3 of 5 (TC Mark Chain Migration)
Plan: 1 of 1 in current phase
Status: Phase complete
Last activity: 2026-02-25 - Completed plan 03-01: TC Mark Chain Migration (split tc_mark_up/tc_mark_down on input/output hooks)

Progress: [██████░░░░] 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 9.5 min
- Total execution time: 0.32 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-bridge-isolation-core | 1 | 15 min | 15 min |
| 02-accounting-chain-migration | 1 | 4 min | 4 min |
| 03-tc-mark-chain-migration | 1 | 3 min | 3 min |

**Recent Trend:**
- Last 5 plans: 15 min, 4 min, 3 min
- Trend: faster

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
- [01-01]: MASQUERADE verified BEFORE drop rules — abort (return) if MASQUERADE fails to prevent SSH lockout
- [01-01]: Both L2 drop rules applied atomically in single nft -f - stdin transaction (asymmetric isolation prevention)
- [01-01]: remove_bridge_isolation() re-queries handles at call time — handles change after nftables.service reloads on boot
- [01-01]: ensure_bridge_masquerade() DEPRECATED but not removed — Phase 4 handles main.py lifespan swap
- [02-01]: nft reset semantics — each read_device_counters() call resets counters atomically; returned values are delta
- [02-01]: Split accounting chains: upload (input hook, iifname eth1) + download (output hook, oifname eth1)
- [02-01]: _cumulative_totals dict tracks running totals in bandwidth_monitor (nft reset zeroes nft counters each cycle)
- [02-01]: ensure_bridge_accounting_chain() auto-cleans old per_device chain on startup
- [03-01]: TC_MARK_CHAIN kept as legacy reference constant for cleanup detection only (mirrors Phase 2 BRIDGE_CHAIN = 'per_device' precedent)
- [03-01]: tc_mark_up/tc_mark_down at priority -1, accounting chains at priority -2 — accounting fires first (count then mark)
- [03-01]: remove_device_limit() inherits new split-chain behavior via delegation to _remove_nft_mark_rule() — no body changes needed

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
| 3 | V41 .planning klasorunu V5 klasorune kopyala | 2026-02-25 | 93ba6c9 | [3-v41-planning-klasorunu-v5-klasorune-kopy](./quick/3-v41-planning-klasorunu-v5-klasorune-kopy/) |
| 4 | Turkce konusma tercihini CLAUDE.md'ye kaydet | 2026-03-03 | 22796f8 | [4-turkce-konusma-tercihini-kaydet-ve-planl](./quick/4-turkce-konusma-tercihini-kaydet-ve-planl/) |

## Session Continuity

Last session: 2026-03-03
Stopped at: Completed quick-4 (Turkce konusma tercihini CLAUDE.md'ye kaydet)
Resume file: None
