---
phase: 03-tc-mark-chain-migration
verified: 2026-02-25T18:15:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 3: TC Mark Chain Migration Verification Report

**Phase Goal:** Per-device bandwidth limits remain enforced after isolation because TC mark chains operate on the input/output hooks where LAN traffic now flows
**Verified:** 2026-02-25T18:15:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | tc_mark_up chain exists on bridge input hook (priority -1) and tc_mark_down chain exists on bridge output hook (priority -1) after _ensure_tc_mark_chain() runs | VERIFIED | Lines 139/152: `hook input priority -1` and `hook output priority -1` in nft_commands; both branch cases (fresh install + table-exists) use these hooks |
| 2 | add_device_limit(mac, rate, ceil) adds iifname eth1 + ether saddr mark rule to tc_mark_up AND oifname eth1 + ether daddr mark rule to tc_mark_down | VERIFIED | Lines 293-310: two distinct run_nft add-rule calls; first uses TC_MARK_CHAIN_UP + iifname/saddr, second uses TC_MARK_CHAIN_DOWN + oifname/daddr |
| 3 | remove_device_limit(mac) removes mark rules from BOTH tc_mark_up and tc_mark_down without affecting rules for other MACs | VERIFIED | Lines 351-368: _remove_nft_mark_rule iterates [(TC_MARK_CHAIN_UP, f"tc_mark_{mac_lower}_up"), (TC_MARK_CHAIN_DOWN, f"tc_mark_{mac_lower}_down")]; handle-based deletion with comment_key anchor ensures MAC isolation |
| 4 | Old forward-hook tc_mark chain is cleaned up on startup when _ensure_tc_mark_chain() detects it | VERIFIED | Lines 127-131: checks `chain {TC_MARK_CHAIN}` in ruleset, flushes then deletes with check=False |
| 5 | Existing inet tonbilai forward cleanup in _remove_nft_mark_rule() is preserved unchanged | VERIFIED | Lines 370-386: old_pattern lookup in inet/tonbilai/forward chain fully preserved; additional suffix-exclusion logic (_up/_down) prevents false matches |
| 6 | A device with a bandwidth limit has its nft mark set on input/output hooks enabling HTB qdiscs on slave interfaces to enforce the rate cap | VERIFIED (structural) | TC class/filter setup (lines 235-280) is unchanged; marks set in bridge input/output hooks persist as SKB marks, matching fw filters on eth0/eth1; HTB functions (setup_htb_root, get_device_stats) are untouched |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/hal/linux_tc.py` | TC mark chain migration — split upload/download mark chains on input/output hooks | VERIFIED | 418 lines, 15330 chars; contains TC_MARK_CHAIN_UP, TC_MARK_CHAIN_DOWN constants, rewritten _ensure_tc_mark_chain(), add_device_limit(), _remove_nft_mark_rule(); syntax valid (ast.parse OK) |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `linux_tc.py::_ensure_tc_mark_chain` | bridge accounting table (tc_mark_up + tc_mark_down chains) | `nft -f - stdin` adds `add chain bridge accounting tc_mark_up` and `add chain bridge accounting tc_mark_down` | WIRED | Lines 149-153: nft_commands string contains both add chain commands; asyncio.create_subprocess_exec with stdin=PIPE at lines 155-165; RuntimeError raised on failure |
| `linux_tc.py::add_device_limit` | tc_mark_up and tc_mark_down chains | run_nft add rule with comment anchors `tc_mark_{mac}_up` and `tc_mark_{mac}_down` | WIRED | Lines 293-310: two run_nft add-rule calls, each with unique comment; TC_MARK_CHAIN_UP used in first, TC_MARK_CHAIN_DOWN in second; both present in add_section (verified programmatically) |
| `linux_tc.py::_remove_nft_mark_rule` | tc_mark_up and tc_mark_down chains | handle-based deletion iterating both chains | WIRED | Lines 351-368: for loop over [(TC_MARK_CHAIN_UP, ...), (TC_MARK_CHAIN_DOWN, ...)]; run_nft with -a list chain; re.search(r"# handle (\d+)", line); delete rule by handle with check=False |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| TCMK-01 | 03-01-PLAN.md | TC mark chain (forward hook) migrated to tc_mark_up/tc_mark_down (input/output hooks) | SATISFIED | TC_MARK_CHAIN_UP = "tc_mark_up" (line 25), TC_MARK_CHAIN_DOWN = "tc_mark_down" (line 26); _ensure_tc_mark_chain creates both with hook input/output priority -1 |
| TCMK-02 | 03-01-PLAN.md | tc_mark_up chain: iifname eth1, ether saddr MAC, meta mark set rules | SATISFIED | Lines 293-299: run_nft add rule with TC_MARK_CHAIN_UP, "iifname", "eth1", "ether", "saddr", mac_lower, "meta", "mark", "set", str(mark) |
| TCMK-03 | 03-01-PLAN.md | tc_mark_down chain: oifname eth1, ether daddr MAC, meta mark set rules | SATISFIED | Lines 303-310: run_nft add rule with TC_MARK_CHAIN_DOWN, "oifname", "eth1", "ether", "daddr", mac_lower, "meta", "mark", "set", str(mark) |
| TCMK-04 | 03-01-PLAN.md | add_device_limit(mac, rate, ceil) adds mark rules to both tc_mark_up and tc_mark_down chains | SATISFIED | Lines 283-310: _ensure_tc_mark_chain() called first (line 283), _remove_nft_mark_rule(mac) cleanup (line 286), then two add-rule calls; verified 2 distinct run_nft("add","rule") calls in add_section |
| TCMK-05 | 03-01-PLAN.md | remove_device_limit(mac) removes mark rules from both chains without affecting other devices | SATISFIED | Lines 318-343: remove_device_limit delegates to _remove_nft_mark_rule(mac) (line 341); _remove_nft_mark_rule uses MAC-specific comment_key anchors for each chain; only matching handle deleted per MAC |

**Note on REQUIREMENTS.md traceability table:** REQUIREMENTS.md still shows TCMK-01 through TCMK-05 as "Pending" (the table at lines 110-114). This is a documentation artifact — the traceability table was not updated after plan execution. All five requirements are fully implemented in the codebase. The checklist at lines 38-42 correctly marks all five as `[x]`.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/hal/linux_tc.py` | 82-92 | `run_nft` defaults to `check=False` — nft add rule failures in `add_device_limit` are silently discarded (no exception raised when rule add fails) | Warning | If mark rule add fails silently, device traffic bypasses rate limiting without error. Not a structural stub — this was the pre-existing behavior before this phase and the plan explicitly calls for check=False on delete operations only. The add-rule calls at lines 293-310 do not pass check=True, meaning a missing chain would be silently swallowed. |

**Severity assessment:** Warning only, not a blocker. The `_ensure_tc_mark_chain()` call immediately before the add-rule calls guarantees chain existence (raises RuntimeError on failure). The add-rule calls silently fail only if nft rejects the rule syntax — which would require a regression in nftables or BRIDGE_TABLE mismatch. The existing codebase-wide pattern accepts this behavior.

---

### Human Verification Required

#### 1. Live Mark Firing on Pi

**Test:** On the Pi, set a bandwidth limit for a test device with `add_device_limit("aa:bb:cc:dd:ee:ff", 10, 10)`, then run `nft list table bridge accounting` and verify both `tc_mark_up` and `tc_mark_down` chains appear with `meta mark set` rules for that MAC.

**Expected:** Two chains visible with hook input/output priority -1; each chain contains one rule with the MAC's mark value and the correct comment anchor.

**Why human:** Requires live nftables on the Pi; cannot verify actual kernel chain creation from static code inspection alone.

#### 2. HTB Enforcement After Isolation

**Test:** With a device actively downloading, check `tc -s class show dev eth1` for the device's HTB class. Bytes should be non-zero if the mark chain is firing correctly.

**Expected:** The HTB class for the device shows incrementing byte counts during active traffic.

**Why human:** Requires live traffic on the bridge-isolated Pi; static code analysis confirms structural correctness but cannot validate SKB mark persistence through the IP stack at runtime (deferred to Phase 5 as documented in PLAN truth #6).

---

## Commits Verified

| Commit | Description | Files |
|--------|-------------|-------|
| `6d44503` | Add TC_MARK_CHAIN_UP/DOWN constants and rewrite _ensure_tc_mark_chain() | linux_tc.py only |
| `b2a4e77` | Rewrite add_device_limit() and _remove_nft_mark_rule() for split chains | linux_tc.py only |

Both commits touch only `backend/app/hal/linux_tc.py` — no unintended file modifications.

---

## Summary

Phase 3 goal is achieved. The single forward-hook `tc_mark` chain has been replaced by two split chains — `tc_mark_up` (bridge input, priority -1) for upload marking and `tc_mark_down` (bridge output, priority -1) for download marking. All five TCMK requirements are satisfied in `backend/app/hal/linux_tc.py`:

- Constants defined (lines 24-26)
- `_ensure_tc_mark_chain()` creates both chains atomically via `nft -f -` stdin with idempotency and legacy cleanup (lines 106-167)
- `add_device_limit()` adds iifname/saddr rules to tc_mark_up and oifname/daddr rules to tc_mark_down with comment anchors (lines 282-315)
- `_remove_nft_mark_rule()` iterates both chains via for loop with handle-based MAC-specific deletion (lines 346-386)
- `remove_device_limit()` inherits new behavior by delegation (line 341)
- HTB qdisc functions (setup_htb_root, get_device_stats) are untouched
- inet tonbilai forward legacy cleanup is preserved with improved suffix-exclusion logic

The one warning-level anti-pattern (silent `run_nft` failures on add-rule) is pre-existing behavior and is mitigated by the guaranteed chain creation immediately before add-rule calls.

---

_Verified: 2026-02-25T18:15:00Z_
_Verifier: Claude (gsd-verifier)_
