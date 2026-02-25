# Phase 3: TC Mark Chain Migration - Research

**Researched:** 2026-02-25
**Domain:** nftables bridge chain migration — TC mark chains from forward hook to input/output hooks in linux_tc.py
**Confidence:** HIGH

---

## Summary

Phase 3 migrates TC mark chain from the old `bridge accounting tc_mark` (forward hook, priority -1) to two split chains: `tc_mark_up` (input hook, priority -1, iifname eth1, ether saddr) and `tc_mark_down` (output hook, priority -1, oifname eth1, ether daddr). This is the exact same hook migration pattern that Phase 2 applied to the accounting counters — the `forward` hook receives no traffic after bridge isolation drops all L2 forwarding, so mark rules sitting on the forward hook would never fire.

The scope of this phase is entirely within `backend/app/hal/linux_tc.py`. Four functions need rewriting: `_ensure_tc_mark_chain()`, `add_device_limit()`, `remove_device_limit()`, and `_remove_nft_mark_rule()`. The HTB qdisc setup on slave interfaces (`setup_htb_root()`, `get_device_stats()`) is explicitly out of scope — those are unchanged. The `tc fw filter` machinery on eth0/eth1 stays identical; only the nftables chains that set the SKB marks need to be migrated.

The key insight confirmed by architecture research: SKB marks set in bridge nftables rules persist as packets travel through the routing stack. `tc fw filter` on eth0 and eth1 matches these marks to route packets into the correct HTB class. This mechanism works equally in bridge mode and router mode — marks are on the SKB, not the frame header. No changes are needed to TC setup once the mark chains are firing on the correct hooks.

**Primary recommendation:** Rewrite `_ensure_tc_mark_chain()` to create `tc_mark_up` (hook input, priority -1) and `tc_mark_down` (hook output, priority -1) chains, then update `add_device_limit()` and `_remove_nft_mark_rule()` to target both chains using the same comment-anchored handle-based pattern established in Phase 2.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TCMK-01 | TC mark chain (forward hook) migrated to tc_mark_up/tc_mark_down (input/output hooks) | Architecture research confirms forward hook dead after isolation; input/output hooks are correct targets. `_ensure_tc_mark_chain()` rewrite creates both chains atomically. |
| TCMK-02 | tc_mark_up chain: iifname eth1, ether saddr MAC, meta mark set rules | Upload path analysis: eth1 is LAN interface; bridge input hook fires when LAN frame arrives; saddr identifies the device. Same pattern as ACCT-02 (iifname eth1, ether saddr). |
| TCMK-03 | tc_mark_down chain: oifname eth1, ether daddr MAC, meta mark set rules | Download path analysis: bridge output hook fires when Pi delivers frame to eth1; daddr identifies the destination device. Same pattern as ACCT-03 (oifname eth1, ether daddr). |
| TCMK-04 | add_device_limit(mac, rate, ceil) adds mark rules to both tc_mark_up and tc_mark_down chains | Requires `_ensure_tc_mark_chain()` to be called first, then two nft add rule calls (one per chain), each with a unique comment anchor. Identical add-then-verify pattern as add_device_counter(). |
| TCMK-05 | remove_device_limit(mac) removes mark rules from both chains without affecting other devices | Comment-anchored handle lookup pattern (same as remove_device_counter()). List chain with -a, find lines matching tc_mark_{mac}_up and tc_mark_{mac}_down, delete by handle. check=False on delete. |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nftables | system (Pi OS Bookworm) | nft CLI for chain/rule management | Native kernel firewall subsystem; already used for all accounting chains |
| asyncio.create_subprocess_exec | Python stdlib | Async subprocess execution for nft/tc commands | Already established pattern in linux_tc.py and linux_nftables.py; avoids shell injection |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (Python stdlib) | stdlib | Parse nft output for handle numbers | Already used in _remove_nft_mark_rule(); handle extraction pattern is `re.search(r"# handle (\d+)", line)` |
| logging | Python stdlib | Structured log output | All functions already use `logger = logging.getLogger("tonbilai.tc")` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| comment-anchored handle deletion | rule-by-content deletion | Handle is stable; content-based deletion is fragile to whitespace changes in nft output |
| nft -f - stdin for chain creation | individual nft add chain calls | nft -f - is atomic (all-or-nothing); individual calls can leave partial state on failure |

---

## Architecture Patterns

### Recommended Project Structure

No new files. All changes are within:

```
backend/app/hal/
├── linux_tc.py        # All Phase 3 changes
└── linux_nftables.py  # Read-only reference; ensure_bridge_accounting_chain() must create the table before tc.py adds chains
```

### Pattern 1: Split Bridge Chains for Upload/Download

**What:** The same pattern already implemented in Phase 2 for accounting. One chain per traffic direction: `tc_mark_up` on bridge input hook (iifname eth1 filter) for upload marking; `tc_mark_down` on bridge output hook (oifname eth1 filter) for download marking.

**When to use:** Every time per-device MAC classification must happen on the bridge layer after isolation. Both accounting and TC marking use this pattern.

**Target nft structure:**

```
table bridge accounting {
    # Phase 2 — already exists
    chain upload {
        type filter hook input priority -2; policy accept;
        iifname "eth1" ether saddr aa:bb:cc:dd:ee:ff counter comment "bw_aa:bb:cc:dd:ee:ff_up"
    }
    chain download {
        type filter hook output priority -2; policy accept;
        oifname "eth1" ether daddr aa:bb:cc:dd:ee:ff counter comment "bw_aa:bb:cc:dd:ee:ff_down"
    }
    # Phase 3 — new chains
    chain tc_mark_up {
        type filter hook input priority -1; policy accept;
        iifname "eth1" ether saddr aa:bb:cc:dd:ee:ff meta mark set 101 comment "tc_mark_aa:bb:cc:dd:ee:ff_up"
    }
    chain tc_mark_down {
        type filter hook output priority -1; policy accept;
        oifname "eth1" ether daddr aa:bb:cc:dd:ee:ff meta mark set 101 comment "tc_mark_aa:bb:cc:dd:ee:ff_down"
    }
}
```

Priority ordering matters: accounting chains at -2 fire before tc_mark chains at -1 (lower number = higher priority in nftables). This is correct — count first, then mark.

**Source:** `backend/app/hal/linux_nftables.py` upload/download chain creation (Phase 2 pattern). Architecture research ARCHITECTURE.md "target nftables table layout".

### Pattern 2: Comment-Anchored Rule Identification

**What:** Every dynamically added rule carries a unique `comment` field. The comment encodes the MAC and direction: `tc_mark_{mac}_up` and `tc_mark_{mac}_down`. Deletion finds the rule by comment, extracts the handle from the same output line, then deletes by handle.

**Example for add_device_limit():**

```python
mac_lower = mac.lower()
mark = mac_to_mark(mac)

# Upload chain (TCMK-02)
await run_nft([
    "add", "rule", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN_UP,
    "iifname", "eth1",
    "ether", "saddr", mac_lower,
    "meta", "mark", "set", str(mark),
    "comment", f'"tc_mark_{mac_lower}_up"',
])

# Download chain (TCMK-03)
await run_nft([
    "add", "rule", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN_DOWN,
    "oifname", "eth1",
    "ether", "daddr", mac_lower,
    "meta", "mark", "set", str(mark),
    "comment", f'"tc_mark_{mac_lower}_down"',
])
```

**Example for _remove_nft_mark_rule():**

```python
for chain, pattern in [
    (TC_MARK_CHAIN_UP, f"tc_mark_{mac_lower}_up"),
    (TC_MARK_CHAIN_DOWN, f"tc_mark_{mac_lower}_down"),
]:
    out = await run_nft(["-a", "list", "chain", "bridge", BRIDGE_TABLE, chain], check=False)
    for line in (out or "").splitlines():
        if pattern in line:
            match = re.search(r"# handle (\d+)", line)
            if match:
                await run_nft([
                    "delete", "rule", "bridge", BRIDGE_TABLE, chain,
                    "handle", match.group(1),
                ])
```

**Source:** Phase 2 `remove_device_counter()` implementation in linux_nftables.py (lines 699-743 of current file). Direct code inspection — HIGH confidence.

### Pattern 3: Idempotent _ensure_tc_mark_chain()

**What:** Check if both `tc_mark_up` and `tc_mark_down` chains already exist before creating them. If both present, return early (no-op). If neither or only one present, create both atomically via `nft -f -` stdin. Also clean up the old forward-hook `tc_mark` chain if present.

**Implementation structure:**

```python
async def _ensure_tc_mark_chain():
    ruleset = await run_nft(["list", "ruleset"], check=False)

    # Idempotency: both new chains present?
    if f"chain {TC_MARK_CHAIN_UP}" in ruleset and f"chain {TC_MARK_CHAIN_DOWN}" in ruleset:
        logger.debug("tc_mark_up/tc_mark_down chains already present")
        return

    # Cleanup: old forward-hook tc_mark chain
    if "table bridge accounting" in ruleset and f"chain {TC_MARK_CHAIN}" in ruleset:
        logger.info("Eski tc_mark forward chain temizleniyor...")
        await run_nft(["flush", "chain", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN], check=False)
        await run_nft(["delete", "chain", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN], check=False)

    # Create both chains atomically (table already exists from Phase 2 accounting)
    if "table bridge accounting" not in ruleset:
        nft_commands = (
            f"table bridge {BRIDGE_TABLE} {{\n"
            f"    chain {TC_MARK_CHAIN_UP} {{\n"
            f"        type filter hook input priority -1; policy accept;\n"
            f"    }}\n"
            f"    chain {TC_MARK_CHAIN_DOWN} {{\n"
            f"        type filter hook output priority -1; policy accept;\n"
            f"    }}\n"
            f"}}\n"
        )
    else:
        # Table exists (accounting chains already there from Phase 2) — add chains only
        nft_commands = (
            f"add chain bridge {BRIDGE_TABLE} {TC_MARK_CHAIN_UP} "
            f"{{ type filter hook input priority -1; policy accept; }}\n"
            f"add chain bridge {BRIDGE_TABLE} {TC_MARK_CHAIN_DOWN} "
            f"{{ type filter hook output priority -1; policy accept; }}\n"
        )
    # ... nft -f - stdin atomic execution
```

**Source:** Phase 2 `ensure_bridge_accounting_chain()` pattern (linux_nftables.py lines 574-648). Direct code inspection.

### Pattern 4: Constants for New Chain Names

**What:** Current code has `TC_MARK_CHAIN = "tc_mark"` as a single constant. After migration, two new constants are needed:

```python
TC_MARK_CHAIN = "tc_mark"           # Legacy reference for cleanup
TC_MARK_CHAIN_UP = "tc_mark_up"     # Input hook, iifname eth1, ether saddr
TC_MARK_CHAIN_DOWN = "tc_mark_down" # Output hook, oifname eth1, ether daddr
```

Keep `TC_MARK_CHAIN` as a legacy reference in `_ensure_tc_mark_chain()` cleanup logic only (same approach as `BRIDGE_CHAIN = "per_device"` in linux_nftables.py).

### Pattern 5: HTB qdisc and fw Filter — Unchanged

**What:** `setup_htb_root()`, `get_device_stats()`, the entire TC class/filter management on eth0 and eth1 slave interfaces — untouched.

The fw filter on eth0/eth1 already matches on the mark value (`handle {mark} fw`) and routes to the correct HTB class. SKB marks set in bridge input/output hooks persist through the IP routing stack and are still present when the packet reaches eth0/eth1 egress. This is a documented kernel property.

**When this matters:** The planner does NOT need to add any tasks for modifying the TC qdisc/filter setup. The REQUIREMENTS.md explicitly notes "TC qdisc degisiklikleri — Sadece nftables mark chain'leri gocuyor, HTB qdisc'ler degismiyor" in Out of Scope.

### Anti-Patterns to Avoid

- **Do not add tc_mark_up/tc_mark_down to a new separate table.** They must live in `bridge accounting` (same table as upload/download). Architecture ARCHITECTURE.md notes that flushing the accounting table would destroy TC chains — they must coexist in one table so ownership is clear.
- **Do not call `_ensure_tc_mark_chain()` without first ensuring the accounting table exists.** Phase 2's `ensure_bridge_accounting_chain()` creates the `bridge accounting` table. In Phase 3, `_ensure_tc_mark_chain()` can assume the table exists when called after `setup_htb_root()` → which is called by `add_device_limit()`. However, the function should still handle the case where the table doesn't exist yet (guard with table-creation block as shown in Pattern 3).
- **Do not use `check=True` (default) on the old chain cleanup.** The old `tc_mark` chain may not exist if this is a fresh install. Use `check=False` on flush and delete of legacy chains.
- **Do not remove the old `tc_mark` chain constant entirely.** Keep it for cleanup detection. This matches the Phase 2 precedent of keeping `BRIDGE_CHAIN = "per_device"` as a legacy reference.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Generating unique mark values per MAC | Custom hash function | `mac_to_mark(mac)` already exists in linux_tc.py | Existing function: `mac_to_classid(mac) + 100`. Produces stable, collision-resistant values in 101-10098 range. Changing this would invalidate existing fw filters. |
| Finding rule handles | Custom nft JSON parser | `run_nft(["-a", "list", "chain", ...])` + regex | nft -j JSON output is heavier; `-a` text output + `re.search(r"# handle (\d+)", line)` is the established pattern throughout the codebase |
| Detecting existing rules | Full ruleset diff | Comment string in chain output | Comment anchors provide stable, intent-explicit identification regardless of rule position in chain |

**Key insight:** The entire pattern library for this phase already exists in the codebase. Phase 2 is the direct template. The only new content is the chain names and the iifname/oifname filter direction.

---

## Common Pitfalls

### Pitfall 1: mark set on wrong hook — mark not seen by tc fw filter

**What goes wrong:** If `tc_mark_up` uses `hook output` (instead of `hook input`), upload traffic from a LAN device never gets its mark set, because the output hook fires when Pi sends data out, not when it receives from eth1. The TC fw filter on eth1 never matches, device gets default class, no rate limiting.

**Why it happens:** Confusing upload/download direction in hook selection.

**How to avoid:**
- Upload (device → Pi): bridge **input** hook (eth1 ingress to Pi's stack), `iifname "eth1"`, `ether saddr {mac}`
- Download (Pi → device): bridge **output** hook (Pi's stack to eth1 egress), `oifname "eth1"`, `ether daddr {mac}`

This exactly mirrors Phase 2's upload (input) and download (output) chain directions.

**Warning signs:** `tc -s class show dev eth1` shows zero bytes in the device's HTB class while the device is actively downloading.

---

### Pitfall 2: Duplicate mark rules when _ensure_tc_mark_chain() is called with old tc_mark chain still present

**What goes wrong:** If `_ensure_tc_mark_chain()` does not clean up the old `tc_mark` (forward hook) chain, and if add_device_limit() previously added rules to the old chain, those rules now sit on a dead hook (forward hook sees no traffic after isolation). The old chain coexists with the new chains but does nothing. This is a silent bug — no error, no rate limiting.

**Why it happens:** Migration leaves stale chains in place if cleanup logic is not added.

**How to avoid:** `_ensure_tc_mark_chain()` must detect and clean up the old `tc_mark` forward chain before creating the new chains. The idempotency check at the top of the function must check for BOTH new chain names — if either is missing, re-create both cleanly.

**Warning signs:** `nft list table bridge accounting` shows three or four chains (upload, download, tc_mark, tc_mark_up, tc_mark_down).

---

### Pitfall 3: Partial mark state (upload chain updated, download not) causes asymmetric rate limiting

**What goes wrong:** If `add_device_limit()` adds a rule to `tc_mark_up` but fails before adding to `tc_mark_down`, only upload traffic gets marked. Download traffic flows at full speed, bypassing the HTB class. The device appears rate-limited on upload but uncapped on download.

**Why it happens:** Error handling that does not clean up on partial failure.

**How to avoid:** Follow the Phase 2 decision: if upload nft rule succeeds but download nft rule fails, raise an exception. The tc class/filter setup on the slave interfaces should also be validated (but tc operations are separate from nft — handle tc and nft failures independently, log both).

**Warning signs:** Device upload appears limited but download runs at full wire speed.

---

### Pitfall 4: _remove_nft_mark_rule() also cleans up old inet forward chain rules — must NOT break after migration

**What goes wrong:** Current `_remove_nft_mark_rule()` has two sections: (1) delete from `bridge accounting tc_mark`, (2) delete old-format rules from `inet tonbilai forward`. After Phase 3, the bridge chain lookup changes from `tc_mark` to `tc_mark_up` + `tc_mark_down`. The inet cleanup section should remain as-is (Phase 1 notes this as a migration-period cleanup pattern). If the bridge section is updated but the inet section is accidentally removed, devices that had old-format rules in the inet chain will have stale rules stuck there.

**How to avoid:** When rewriting `_remove_nft_mark_rule()`, preserve the inet forward chain cleanup block. Only update the bridge accounting chain lookup to target `tc_mark_up` and `tc_mark_down` instead of `tc_mark`.

---

### Pitfall 5: Mark value collision with accounting chain (different priority, same hook)

**What goes wrong:** The accounting chains (priority -2) and TC mark chains (priority -1) both fire on the same hooks (input/output). If they interfere with each other — for example, if an accounting chain rule somehow drops the packet — the TC mark chain never fires.

**Why this is NOT a problem:** Both chains use `policy accept` and contain only `counter` (accounting) and `meta mark set` (TC) statements. Neither drops packets. nftables evaluates all chains at a given hook in priority order, and each statement in both chains is non-terminating. The packet traverses accounting chain (prio -2) then TC mark chain (prio -1) on the same hook without interruption.

**How to confirm:** `nft list table bridge accounting` — all chains show `policy accept`, no `drop` verdicts.

---

## Code Examples

Verified patterns from existing codebase:

### Chain creation (from linux_nftables.py ensure_bridge_accounting_chain, Phase 2)

```python
# Table exists, add two chains atomically
nft_commands = (
    f"add chain bridge {BRIDGE_TABLE} {TC_MARK_CHAIN_UP} "
    f"{{ type filter hook input priority -1; policy accept; }}\n"
    f"add chain bridge {BRIDGE_TABLE} {TC_MARK_CHAIN_DOWN} "
    f"{{ type filter hook output priority -1; policy accept; }}\n"
)
proc = await asyncio.create_subprocess_exec(
    "sudo", NFT_BIN, "-f", "-",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
stdout, stderr = await proc.communicate(input=nft_commands.encode())
if proc.returncode != 0:
    err = stderr.decode().strip()
    raise RuntimeError(f"tc_mark chain create error: {err}")
```

Source: linux_nftables.py lines 627-648 (direct code inspection).

### Mark rule add (from current linux_tc.py add_device_limit)

```python
# Upload: cihazdan gelen trafik — tc_mark_up chain (TCMK-02)
await run_nft([
    "add", "rule", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN_UP,
    "iifname", "eth1",
    "ether", "saddr", mac_lower,
    "meta", "mark", "set", str(mark),
    "comment", f'"tc_mark_{mac_lower}_up"',
])

# Download: cihaza giden trafik — tc_mark_down chain (TCMK-03)
await run_nft([
    "add", "rule", "bridge", BRIDGE_TABLE, TC_MARK_CHAIN_DOWN,
    "oifname", "eth1",
    "ether", "daddr", mac_lower,
    "meta", "mark", "set", str(mark),
    "comment", f'"tc_mark_{mac_lower}_down"',
])
```

Source: Derived from current linux_tc.py lines 258-273 (forward hook rules) + Phase 2 iifname/oifname pattern.

### Handle-based deletion (from linux_nftables.py remove_device_counter)

```python
for chain, comment_key in [
    (TC_MARK_CHAIN_UP,   f"tc_mark_{mac_lower}_up"),
    (TC_MARK_CHAIN_DOWN, f"tc_mark_{mac_lower}_down"),
]:
    out = await run_nft(["-a", "list", "chain", "bridge", BRIDGE_TABLE, chain], check=False)
    for line in (out or "").splitlines():
        if comment_key in line:
            match = re.search(r"# handle (\d+)", line)
            if match:
                handle = match.group(1)
                await run_nft([
                    "delete", "rule", "bridge", BRIDGE_TABLE, chain,
                    "handle", handle,
                ], check=False)
```

Source: linux_nftables.py lines 710-741 (remove_device_counter — direct code inspection).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `tc_mark` chain on `bridge forward` hook | Split `tc_mark_up` (input) + `tc_mark_down` (output) chains | Phase 3 (this phase) | Marks now fire correctly after bridge isolation drops L2 forwarding |
| Upload and download marks in same chain | Separate chains per direction | Phase 3 (this phase) | Cleaner per-direction control, mirrors Phase 2 accounting split |
| `_ensure_tc_mark_chain()` creates only forward chain | Creates two input/output chains + cleans up old forward chain | Phase 3 (this phase) | Idempotent startup with forward-compatible cleanup |

**Deprecated/outdated:**
- `TC_MARK_CHAIN = "tc_mark"` (forward hook, priority -1): Dead after bridge isolation. Kept only as cleanup reference constant. All new code uses `TC_MARK_CHAIN_UP` and `TC_MARK_CHAIN_DOWN`.

---

## Open Questions

1. **Should tc_mark cleanup call ensure_bridge_accounting_chain() from linux_nftables.py?**
   - What we know: Architecture research ARCHITECTURE.md identifies cross-file table ownership as a risk — "both files must agree on table name and chain names". The ARCHITECTURE.md recommends `ensure_bridge_accounting_chain()` create ALL chains including tc_mark chains.
   - What's unclear: This would create a cross-module dependency (linux_tc.py importing linux_nftables.py). The current codebase avoids this (linux_tc.py has its own run_nft wrapper).
   - Recommendation: For Phase 3, keep the current pattern — `_ensure_tc_mark_chain()` handles its own table/chain creation with the `bridge accounting` table fallback block. This avoids introducing a cross-import. The anti-pattern risk (table flush destroying TC chains) is a Phase 4+ concern, not a blocker here.

2. **What happens to devices that already have mark rules in the old tc_mark forward chain when _ensure_tc_mark_chain() cleans up?**
   - What we know: `_ensure_tc_mark_chain()` flush+delete of the old `tc_mark` chain will delete ALL rules in that chain, including per-device mark rules.
   - What's unclear: Is there a re-sync mechanism that re-adds all device limits to the new chains?
   - Recommendation: This is handled by the normal startup sequence. `main.py` lifespan calls `_restore_bandwidth_limits()` which calls `add_device_limit()` for all devices with bandwidth limits. This re-populates the new chains after cleanup. The startup sequence for Phase 4 will handle this correctly. No special handling needed in Phase 3.

3. **Priority -1 for tc_mark chains vs accounting at -2: confirmed safe on Pi OS Bookworm?**
   - What we know: nftables priority ordering is numeric (lower = higher priority). Priority -2 chains (accounting) fire before -1 chains (TC mark) on the same hook. Both policy accept, no drop statements.
   - Confidence: HIGH — this is standard nftables documented behavior. The existing codebase already uses priority -2 for accounting and priority -1 for tc_mark in the old forward-hook setup.

---

## Validation Architecture

> nyquist_validation is not set in .planning/config.json (key absent from workflow object) — treating as disabled. Skipping Validation Architecture section.

---

## Sources

### Primary (HIGH confidence)

- `backend/app/hal/linux_tc.py` (direct code inspection) — Current `_ensure_tc_mark_chain()`, `add_device_limit()`, `remove_device_limit()`, `_remove_nft_mark_rule()` implementations; `mac_to_mark()`, `BRIDGE_TABLE`, `TC_MARK_CHAIN` constants
- `backend/app/hal/linux_nftables.py` (direct code inspection) — Phase 2 accounting chain functions as implementation template; `ensure_bridge_accounting_chain()`, `add_device_counter()`, `remove_device_counter()` patterns
- `.planning/research/ARCHITECTURE.md` (direct read) — Upload/download packet paths after isolation, tc_mark_up/tc_mark_down target structure, hook priority ordering, "SKB marks survive routing" confirmation
- `.planning/REQUIREMENTS.md` (direct read) — TCMK-01 through TCMK-05 definitions; "TC qdisc degisiklikleri" in Out of Scope
- `.planning/research/PITFALLS.md` (direct read) — "TC marking in new chains" checklist item; silent zero counter patterns

### Secondary (MEDIUM confidence)

- `.planning/phases/02-accounting-chain-migration/02-01-PLAN.md` — Phase 2 task structure as planning template
- `.planning/phases/02-accounting-chain-migration/02-01-SUMMARY.md` — Phase 2 decisions (atomic failure, comment anchors, idempotency) confirmed applicable to Phase 3
- `.planning/phases/02-accounting-chain-migration/02-CONTEXT.md` — Decision rationale for split chain approach

### Tertiary (LOW confidence)

None — all claims verified against codebase or architecture research.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; existing nftables + asyncio subprocess pattern
- Architecture: HIGH — packet path analysis from ARCHITECTURE.md verified against actual code; hook direction confirmed by Phase 2 implementation
- Pitfalls: HIGH — most pitfalls derived from direct code inspection and Phase 2 patterns; partial state pitfall confirmed by Phase 2 decision (add_device_counter raises on partial)

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable kernel/nftables semantics; valid until Pi OS kernel upgrade or nftables major version change)
