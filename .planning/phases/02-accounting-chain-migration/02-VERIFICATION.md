---
phase: 02-accounting-chain-migration
verified: 2026-02-25T13:50:00Z
status: passed
score: 7/7 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Deploy to Pi and confirm bridge counter accumulates on upload/download chains after L2 isolation"
    expected: "nft list ruleset shows counter packets/bytes incrementing in bridge accounting upload and download chains for known LAN devices"
    why_human: "Requires live nftables on bridge-isolated Pi with actual LAN traffic; cannot simulate kernel bridge hook behavior programmatically"
---

# Phase 2: Accounting Chain Migration Verification Report

**Phase Goal:** Bridge bandwidth counters correctly accumulate on the input/output hooks so device traffic accounting works after L2 forwarding is disabled
**Verified:** 2026-02-25T13:50:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `ensure_bridge_accounting_chain()` creates upload chain (input hook, iifname eth1) and download chain (output hook, oifname eth1) in bridge accounting table | VERIFIED | Lines 615-634: nft commands use `hook input priority -2` and `hook output priority -2`; `iifname` and `oifname` confirmed via python AST + grep |
| 2 | `ensure_bridge_accounting_chain()` auto-deletes old per_device chain if present | VERIFIED | Lines 606-610: checks `chain {BRIDGE_CHAIN}` in ruleset, flushes then deletes it; log message "Eski per_device chain temizlendi" |
| 3 | `add_device_counter(mac)` adds counter rules to both upload and download chains | VERIFIED | Lines 668-694: adds `iifname "eth1" ether saddr {mac}` to upload, `oifname "eth1" ether daddr {mac}` to download; raises RuntimeError on partial failure |
| 4 | `remove_device_counter(mac)` removes counter rules from both chains by handle | VERIFIED | Lines 710-741: lists each chain with `-a`, finds rules by `bw_{mac}_up/down` comment, deletes by handle; logs warning if MAC not found (no exception) |
| 5 | `read_device_counters()` returns merged upload+download byte/packet totals per MAC using nft reset | VERIFIED | Lines 793-825: `nft -a reset chain bridge accounting upload/download` called; both outputs parsed and merged into `{mac: {upload_bytes, upload_packets, download_bytes, download_packets}}`; returns `{}` on error |
| 6 | `sync_device_counters(macs)` synchronizes MAC rules across both upload and download chains | VERIFIED | Lines 828-858: calls `ensure_bridge_accounting_chain()` first, lists BRIDGE_CHAIN_UPLOAD for existing MACs, adds/removes via `add_device_counter`/`remove_device_counter` |
| 7 | `bandwidth_monitor.py` works with nft-reset semantics (each read returns delta, not cumulative) | VERIFIED | Lines 113-116: `delta_up_bytes = current["upload_bytes"]` (direct assignment, no subtraction); `_cumulative_totals` accumulates across cycles; `_previous_counters` entirely absent; `_write_hourly_snapshot` uses `_cumulative_totals` |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/hal/linux_nftables.py` | Rewritten accounting chain functions (upload/download on input/output hooks) | VERIFIED | All 5 functions present; `chain upload`, `chain download`, `hook input`, `hook output`, `iifname`, `oifname`, `reset` all confirmed; AST parse succeeds; 1354+ lines |
| `backend/app/workers/bandwidth_monitor.py` | Updated bandwidth monitor compatible with nft reset counter semantics | VERIFIED | `_calculate_and_store_bandwidth` present; direct delta assignment; `_cumulative_totals` present; no `_previous_counters`; all three nft calls present; AST parse succeeds |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/workers/bandwidth_monitor.py` | `backend/app/hal/linux_nftables.py` | `nft.ensure_bridge_accounting_chain()`, `nft.sync_device_counters()`, `nft.read_device_counters()` | WIRED | Line 276: `ensure_bridge_accounting_chain()` called at startup; Lines 285, 307: `sync_device_counters()` called at startup and in MAC refresh loop; Lines 290, 310: `read_device_counters()` called for baseline and in main loop |
| `backend/app/hal/linux_nftables.py:read_device_counters` | `nft reset counter` | `nft -a reset chain bridge accounting upload/download` | WIRED | Lines 793-804: both chains read with `["-a", "reset", "chain", "bridge", "accounting", BRIDGE_CHAIN_UPLOAD]` and `BRIDGE_CHAIN_DOWNLOAD` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ACCT-01 | 02-01-PLAN.md | Bridge accounting per_device chain (forward hook) tasinmali to upload/download chains (input/output hook) | SATISFIED | `ensure_bridge_accounting_chain()` creates upload (hook input) and download (hook output) chains; per_device auto-cleaned |
| ACCT-02 | 02-01-PLAN.md | Upload chain: iifname eth1, ether saddr MAC counter rules | SATISFIED | `add_device_counter()` line 674-679: `"iifname", "eth1", "ether", "saddr", mac_lower, "counter"` |
| ACCT-03 | 02-01-PLAN.md | Download chain: oifname eth1, ether daddr MAC counter rules | SATISFIED | `add_device_counter()` line 684-689: `"oifname", "eth1", "ether", "daddr", mac_lower, "counter"` |
| ACCT-04 | 02-01-PLAN.md | `add_device_counter(mac)` adds rules to new chains | SATISFIED | Function present, adds to BRIDGE_CHAIN_UPLOAD and BRIDGE_CHAIN_DOWNLOAD; idempotent; raises on partial failure |
| ACCT-05 | 02-01-PLAN.md | `remove_device_counter(mac)` removes from both chains | SATISFIED | Function present, removes from both chains by handle; warning (no exception) if MAC not found |
| ACCT-06 | 02-01-PLAN.md | `read_device_counters()` reads both chains and merges | SATISFIED | Uses `nft -a reset` on both chains; parses `up` and `down` direction outputs; merges per MAC |
| ACCT-07 | 02-01-PLAN.md | `sync_device_counters(macs)` uses new chain names | SATISFIED | Lists BRIDGE_CHAIN_UPLOAD for existing MACs; calls add/remove functions which use BRIDGE_CHAIN_UPLOAD and BRIDGE_CHAIN_DOWNLOAD |

No orphaned requirements: all 7 ACCT-0x IDs declared in plan frontmatter and all accounted for in REQUIREMENTS.md Phase 2 traceability table.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | - | - | - | No anti-patterns detected in either modified file |

- No TODO/FIXME/XXX/HACK/PLACEHOLDER comments in either file
- No `raise NotImplementedError` stubs in the five accounting functions
- No `return {}` or `return []` as stub returns (the `return {}` in `read_device_counters` is correct error-path behavior, not a stub)
- No `_previous_counters` remnants in `bandwidth_monitor.py`

### Human Verification Required

#### 1. Live Bridge Counter Accumulation Test

**Test:** On the Pi, after `sudo systemctl restart tonbilaios-backend`, generate LAN traffic (e.g., ping or HTTP download from a LAN device), then run `sudo nft list ruleset` and inspect the `bridge accounting` table.
**Expected:** The `chain upload` shows packets/bytes incrementing for `bw_{mac}_up` comment rules matching active device MACs; `chain download` shows matching `bw_{mac}_down` increments. Running `sudo nft reset chain bridge accounting upload` should return non-zero counter values and then reset them to zero.
**Why human:** Live kernel bridge hook behavior (br_netfilter + input/output hooks on bridge table) requires actual network traffic on a running Pi with bridge isolation active; cannot be verified by static code analysis.

### Gaps Summary

No gaps. All must-haves verified at all three levels (exists, substantive, wired). All 7 ACCT requirements satisfied. Both commits (52a45b0, 6182aa6) exist in git history and modified the correct files.

The one item flagged for human verification (live counter accumulation) is a runtime/hardware concern that cannot be checked programmatically — it does not block phase status from being passed, as the code correctness is fully verified.

---

_Verified: 2026-02-25T13:50:00Z_
_Verifier: Claude (gsd-verifier)_
