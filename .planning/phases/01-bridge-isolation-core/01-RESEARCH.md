# Phase 1: Bridge Isolation Core - Research

**Researched:** 2026-02-25
**Domain:** Linux bridge networking / nftables bridge family / Python async HAL (linux_nftables.py)
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ISOL-01 | Pi bridge forward chain'inde eth0↔eth1 arasi L2 iletimi drop kurallari ile engelleyebilmeli | nftables bridge filter forward hook — iifname/oifname drop rules; atomic via `nft -f -` |
| ISOL-02 | Pi, inet nat postrouting'de LAN subnet icin MASQUERADE kurali uygulayabilmeli | `ensure_nat_postrouting_chain()` already exists; add LAN MASQUERADE rule with comment anchor |
| ISOL-03 | ip_forward=1 sysctl ayari aktif ve kalici olmali | `sysctl -w net.ipv4.ip_forward=1`; Phase 1 sets runtime only — persistence is Phase 4 |
| ISOL-04 | br_netfilter modulu yuklu ve bridge-nf-call-iptables=1 aktif olmali | `modprobe br_netfilter` + `sysctl -w net.bridge.bridge-nf-call-iptables=1`; already done in `ensure_bridge_masquerade()` |
| ISOL-05 | ICMP redirect (send_redirects) tum interface'lerde devre disi olmali | `sysctl -w net.ipv4.conf.all.send_redirects=0` + `net.ipv4.conf.br0.send_redirects=0` |
| ISOL-06 | Eski bridge masquerade_fix tablosu kaldirilmali (MAC rewrite artik gereksiz) | `nft delete table bridge masquerade_fix`; `BRIDGE_MASQ_TABLE` constant already exists in codebase |
| ISOL-07 | Izolasyon kurallari atomik olarak uygulanmali (nft -f ile tek transaction) | Both drop rules in one `nft -f -` stdin call; MASQUERADE also via stdin |
| ROLL-01 | remove_bridge_isolation() fonksiyonu ile seffaf kopru moduna donulebilmeli | Handle-based deletion via `nft -a list chain bridge filter forward`; regex parse handle numbers |
| ROLL-02 | Rollback sirasinda izolasyon kurallari handle ile silinmeli | `nft delete rule bridge filter forward handle N`; comment anchor "bridge_isolation" used to identify target rules |
| ROLL-03 | Rollback sirasinda ICMP redirect'ler geri acilmali | `sysctl -w net.ipv4.conf.all.send_redirects=1` + persist_nftables() |
</phase_requirements>

---

## Summary

Phase 1 implements two new HAL functions in `backend/app/hal/linux_nftables.py`: `ensure_bridge_isolation()` and `remove_bridge_isolation()`. These functions transform the Pi from transparent bridge mode (modem sees all LAN device MACs) to router mode (modem sees only Pi's MAC) and reverse that transformation cleanly. This phase writes only to `linux_nftables.py` — no other files change in Phase 1.

The implementation pattern is directly established by the existing codebase. `ensure_bridge_masquerade()` (line ~1055) is the immediate predecessor — it already calls `_get_wan_bridge_port()`, `_detect_lan_subnet()`, `modprobe br_netfilter`, `sysctl`, and `run_nft`. `ensure_bridge_isolation()` extends this same pattern with forward-drop rules, MASQUERADE verification, and masquerade_fix removal. `remove_bridge_isolation()` follows the existing handle-based deletion pattern already used in `_delete_rule_by_handle()` (line ~236).

The critical ordering constraint within `ensure_bridge_isolation()` is: (1) ip_forward=1, (2) br_netfilter + bridge-nf-call-iptables=1, (3) ICMP redirects off, (4) MASQUERADE rule verified present, (5) forward drop rules applied atomically, (6) masquerade_fix table deleted. Drop rules must come AFTER MASQUERADE is confirmed — applying drop before NAT causes SSH lockout with no remote recovery path.

**Primary recommendation:** Implement `ensure_bridge_isolation()` with the six-step ordered sequence and `remove_bridge_isolation()` with handle-based deletion. Both functions follow patterns already established in `linux_nftables.py` — no new patterns are needed.

---

## Standard Stack

### Core
| Component | Version/Detail | Purpose | Why Standard |
|-----------|---------------|---------|--------------|
| nftables bridge family | kernel 6.1+ (Pi OS Bookworm) | L2 forward drop rules in bridge filter/forward hook | Only mechanism for bridge-layer packet filtering; ebtables deprecated on Debian 12 |
| nftables inet nat | already present in codebase | MASQUERADE for LAN subnet → internet | Bridge family cannot do NAT; inet nat required |
| br_netfilter kernel module | standard on Debian | Forces bridged packets through inet Netfilter hooks | Without it, existing `inet tonbilai forward` MAC-block rules stop seeing LAN traffic |
| sysctl (runtime only) | standard Linux | ip_forward=1, send_redirects=0, bridge-nf-call-iptables=1 | Kernel parameters; Phase 1 sets runtime; Phase 4 handles persistence |
| Python asyncio subprocess | already used in codebase | Async nft/sysctl execution | All HAL functions are async; pattern established |

### Supporting (already in codebase)
| Component | Purpose | Location |
|-----------|---------|----------|
| `run_nft(args, check)` | Async nft command wrapper | linux_nftables.py line 24 |
| `_run_system_cmd(cmd, check)` | Async generic subprocess | linux_nftables.py |
| `_get_wan_bridge_port()` | Returns "eth0" dynamically | linux_nftables.py line 990 |
| `_detect_lan_subnet()` | Returns "192.168.1.0/24" | linux_nftables.py |
| `ensure_nat_postrouting_chain()` | Creates inet nat postrouting if absent | linux_nftables.py line 109 |
| `persist_nftables()` | Writes ruleset to /etc/nftables.conf | linux_nftables.py line 538 |
| `BRIDGE_MASQ_TABLE` | Constant = "bridge masquerade_fix" | linux_nftables.py line 20 |

**No new packages required.** All kernel features available on Pi OS Bookworm (kernel 6.1+).

---

## Architecture Patterns

### Recommended File Change

Only one file changes in Phase 1:

```
backend/app/hal/
└── linux_nftables.py    # Add ensure_bridge_isolation(), remove_bridge_isolation()
                         # Mark ensure_bridge_masquerade() as deprecated (do not remove yet — Phase 4 swaps it)
```

### Pattern 1: Idempotent Rule Application with Comment Anchors

**What:** Check for comment string in ruleset before adding a rule. If comment already present, skip. This makes functions safe to call multiple times.

**When to use:** All isolation rules — both drop rules and MASQUERADE rule.

```python
# Source: existing ensure_bridge_masquerade() pattern in linux_nftables.py
ruleset = await run_nft(["list", "ruleset"], check=False)
if "bridge_isolation_lan_wan" not in ruleset:
    # apply rule with comment "bridge_isolation_lan_wan"
```

**Comment anchors to use:**
- `"bridge_isolation_lan_wan"` — eth1→eth0 drop rule
- `"bridge_isolation_wan_lan"` — eth0→eth1 drop rule
- `"bridge_lan_masq"` — MASQUERADE rule

### Pattern 2: Atomic Two-Rule Application via nft -f stdin

**What:** Both drop rules (eth1→eth0 and eth0→eth1) must be applied in a single `nft -f -` transaction to avoid an asymmetric isolation window.

**When to use:** ISOL-07 — both forward drop rules together.

```python
# Source: existing stdin pattern in linux_nftables.py lines ~90, ~131, ~206
ruleset_text = f"""
add rule bridge filter forward iifname "eth1" oifname "{wan_iface}" drop comment "bridge_isolation_lan_wan"
add rule bridge filter forward iifname "{wan_iface}" oifname "eth1" drop comment "bridge_isolation_wan_lan"
"""
proc = await asyncio.create_subprocess_exec(
    "sudo", NFT_BIN, "-f", "-",
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
_, stderr = await proc.communicate(input=ruleset_text.encode())
if proc.returncode != 0:
    raise RuntimeError(f"Bridge isolation rules failed: {stderr.decode().strip()}")
```

### Pattern 3: Handle-Based Deletion with Comment Filter

**What:** List chain with `-a` flag to get handle numbers, regex-extract handle for lines containing the target comment, delete by handle.

**When to use:** `remove_bridge_isolation()` — ROLL-01, ROLL-02.

```python
# Source: existing _delete_rule_by_handle() pattern in linux_nftables.py line ~236
out = await run_nft(["-a", "list", "chain", "bridge", "filter", "forward"], check=False)
if out:
    for line in out.splitlines():
        if "bridge_isolation" in line and "handle" in line:
            handle_match = re.search(r"handle\s+(\d+)", line)
            if handle_match:
                handle = handle_match.group(1)
                await run_nft(
                    ["delete", "rule", "bridge", "filter", "forward", "handle", handle],
                    check=False,
                )
```

### Pattern 4: Ordered Setup Sequence (SSH Lockout Prevention)

**What:** The six steps inside `ensure_bridge_isolation()` must execute in strict order. Steps 1-4 establish routing before isolation is applied.

```
Step 1: ip_forward=1                          (enables Pi IP stack routing)
Step 2: modprobe br_netfilter                  (enables bridge→inet hook bridging)
        bridge-nf-call-iptables=1
Step 3: send_redirects=0 (all + br0)          (prevents Pi redirecting clients past itself)
Step 4: MASQUERADE rule verified/added         (NAT working BEFORE isolation)
Step 5: Forward drop rules — ATOMIC           (isolation applied)
Step 6: Delete masquerade_fix table            (cleanup; safe only after drop is active)
Step 7: persist_nftables()
```

### Anti-Patterns to Avoid

- **Drop rules before MASQUERADE:** Applying eth1↔eth0 drop before NAT is confirmed breaks SSH path. Always verify MASQUERADE in ruleset before adding drop rules.
- **Two separate `nft add rule` calls for the two drop directions:** Creates a window where only one direction is blocked. Use stdin batch for both.
- **Deleting masquerade_fix before isolation is active:** Removes MAC rewrite while bridge forwarding still flows, dropping active TCP sessions. Only delete AFTER drop rules are applied.
- **Non-idempotent isolation function:** Not checking for existing rules causes duplicate drop rules on repeated calls. Always check comment anchors first.
- **check=True on sysctl calls:** sysctl commands can fail non-fatally (e.g., br0 not yet up); use `check=False` consistent with existing codebase pattern.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MASQUERADE creation | Custom nat table setup | `ensure_nat_postrouting_chain()` (already exists) | Already handles idempotency and table/chain creation |
| WAN interface detection | Hardcode "eth0" | `_get_wan_bridge_port()` (already exists) | Pi udev naming could change; dynamic detection is safer |
| LAN subnet detection | Hardcode "192.168.1.0/24" | `_detect_lan_subnet()` (already exists) | Keeps subnet detection DRY |
| nftables persistence | Manual file write | `persist_nftables()` (already exists) | Already writes to /etc/nftables.conf correctly |
| Handle regex parsing | Custom parser | `re.search(r"handle\s+(\d+)", line)` | Minimal regex; same pattern already in codebase |

**Key insight:** Phase 1 is almost entirely pattern reuse. The predecessor function `ensure_bridge_masquerade()` provides the exact call sequence; `ensure_bridge_isolation()` replaces its MAC-rewrite body with forward-drop logic.

---

## Common Pitfalls

### Pitfall 1: SSH Lockout (Critical — No Remote Recovery)
**What goes wrong:** If forward drop rules are applied before `ip_forward=1` and MASQUERADE are confirmed working, Pi cannot route packets. SSH path (pi.tonbil.com:2323 → 192.168.1.2:22) drops. No remote recovery without physical access.
**Why it happens:** Forward drop kills bridge path immediately. If IP routing is not ready, packets have nowhere to go.
**How to avoid:** Strict step order — Steps 1-4 before Step 5. After Step 4, verify MASQUERADE is in ruleset before proceeding. The comment check (`"bridge_lan_masq" not in ruleset`) is the gate.
**Warning signs:** If `ensure_nat_postrouting_chain()` raises an exception, abort — do not proceed to drop rules.

### Pitfall 2: Duplicate Drop Rules on Repeated Calls
**What goes wrong:** Calling `ensure_bridge_isolation()` twice adds duplicate drop rules. Both drop rules fire, rule count grows, and `remove_bridge_isolation()` must delete more handles than expected.
**Why it happens:** Not checking idempotency before adding rules.
**How to avoid:** Read full ruleset once at function start; check for both comment anchors before applying the atomic batch.
**Warning signs:** `nft list chain bridge filter forward` shows more than 2 rules after calling the function.

### Pitfall 3: masquerade_fix Deletion Timing
**What goes wrong:** Deleting `bridge masquerade_fix` before drop rules are active drops active TCP connections for currently-connected LAN devices.
**Why it happens:** masquerade_fix rewrites MACs for bridge-forwarded packets. If deleted while forwarding still flows, MACs are wrong and connections fail.
**How to avoid:** Delete masquerade_fix ONLY as Step 6 — after drop rules (Step 5) are already in the ruleset. At that point, no traffic flows via bridge forwarding, so masquerade_fix is already inactive.

### Pitfall 4: Handle Stability Concern
**What goes wrong:** Handle numbers assigned to rules by nftables are not guaranteed to be the same after a Pi reboot if rules are re-added.
**Why it happens:** Handles are runtime-assigned; they can change when rules are flushed and re-applied (e.g., by nftables.service on boot).
**How to avoid:** `remove_bridge_isolation()` must always re-read handles at call time via `nft -a list chain` — never cache handle numbers. The comment-anchor filter approach is correct for this reason.
**Research flag from STATE.md:** "Validate handle-based deletion stability after Pi reboots" — this is handled by always reading live handles, not storing them.

### Pitfall 5: br_netfilter sysctl Silently Lost
**What goes wrong:** `net.bridge.bridge-nf-call-iptables=1` set at runtime via sysctl is lost on reboot if br_netfilter module is not loaded first at boot.
**Why it happens:** The sysctl key is created by the br_netfilter module. If module is not loaded, sysctl.d silently skips the key.
**How to avoid:** Phase 1 sets it at runtime (modprobe + sysctl). Phase 4 handles persistence (modules-load.d + sysctl.d). Phase 1 does NOT write persistence files — that is Phase 4's responsibility.

---

## Code Examples

### ensure_bridge_isolation() Structure

```python
# Source: BRIDGE_ISOLATION_PLAN.md + existing ensure_bridge_masquerade() pattern
async def ensure_bridge_isolation():
    """Apply bridge isolation: drop L2 forwarding, enable router mode.

    Safe to call multiple times (idempotent via comment anchors).
    Steps are ordered to prevent SSH lockout — do not reorder.
    """
    # Step 1: ip_forward
    await _run_system_cmd(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=False)

    # Step 2: br_netfilter
    await _run_system_cmd(["sudo", "modprobe", "br_netfilter"], check=False)
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.bridge.bridge-nf-call-iptables=1"], check=False
    )

    # Step 3: ICMP redirects off
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.ipv4.conf.all.send_redirects=0"], check=False
    )
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.ipv4.conf.br0.send_redirects=0"], check=False
    )

    # Step 4: MASQUERADE — verified present before drop rules
    wan_iface = await _get_wan_bridge_port()
    lan_subnet = await _detect_lan_subnet()
    ruleset = await run_nft(["list", "ruleset"], check=False) or ""

    if "bridge_lan_masq" not in ruleset:
        await ensure_nat_postrouting_chain()
        masq_rule = (
            f'add rule inet nat postrouting '
            f'ip saddr {lan_subnet} ip daddr != {lan_subnet} '
            f'masquerade comment "bridge_lan_masq"'
        )
        proc = await asyncio.create_subprocess_exec(
            "sudo", NFT_BIN, "-f", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate(input=masq_rule.encode())
        if proc.returncode != 0:
            logger.error(f"MASQUERADE rule failed: {stderr.decode().strip()}")
            return  # ABORT — do not apply drop rules without NAT

    # Step 5: Forward drop rules — ATOMIC (both directions in one transaction)
    if "bridge_isolation_lan_wan" not in ruleset or "bridge_isolation_wan_lan" not in ruleset:
        drop_rules = (
            f'add rule bridge filter forward '
            f'iifname "eth1" oifname "{wan_iface}" drop comment "bridge_isolation_lan_wan"\n'
            f'add rule bridge filter forward '
            f'iifname "{wan_iface}" oifname "eth1" drop comment "bridge_isolation_wan_lan"\n'
        )
        proc = await asyncio.create_subprocess_exec(
            "sudo", NFT_BIN, "-f", "-",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate(input=drop_rules.encode())
        if proc.returncode != 0:
            raise RuntimeError(f"Bridge isolation drop rules failed: {stderr.decode().strip()}")
        logger.info("Bridge isolation: L2 forwarding blocked (eth1<->eth0)")

    # Step 6: Remove masquerade_fix (safe only after drop rules are active)
    if BRIDGE_MASQ_TABLE in ruleset:
        await run_nft(["delete", "table", BRIDGE_MASQ_TABLE], check=False)
        logger.info("Removed bridge masquerade_fix table (no longer needed in router mode)")

    # Step 7: Persist
    await persist_nftables()
    logger.info("Bridge isolation active — router mode")
```

### remove_bridge_isolation() Structure

```python
# Source: handle deletion pattern from linux_nftables.py ~line 236
async def remove_bridge_isolation():
    """Remove bridge isolation rules — return to transparent bridge mode.

    Uses live handle lookup — never caches handles (they change on reboot).
    """
    out = await run_nft(["-a", "list", "chain", "bridge", "filter", "forward"], check=False)
    if out:
        for line in out.splitlines():
            if "bridge_isolation" in line and "handle" in line:
                handle_match = re.search(r"handle\s+(\d+)", line)
                if handle_match:
                    handle = handle_match.group(1)
                    await run_nft(
                        ["delete", "rule", "bridge", "filter", "forward", "handle", handle],
                        check=False,
                    )
                    logger.info(f"Removed bridge isolation rule handle {handle}")

    # Restore ICMP redirects
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.ipv4.conf.all.send_redirects=1"], check=False
    )
    await _run_system_cmd(
        ["sudo", "sysctl", "-w", "net.ipv4.conf.br0.send_redirects=1"], check=False
    )

    await persist_nftables()
    logger.info("Bridge isolation removed — transparent bridge mode restored")
```

### Verifying the Result (shell commands for manual validation)

```bash
# Confirm drop rules are present
sudo nft list chain bridge filter forward
# Expected: two rules with bridge_isolation_lan_wan and bridge_isolation_wan_lan comments

# Confirm MASQUERADE is present
sudo nft list chain inet nat postrouting
# Expected: rule with bridge_lan_masq comment

# Confirm masquerade_fix is gone
sudo nft list tables
# Expected: "bridge masquerade_fix" NOT in output

# Confirm Pi internet access (NAT working)
curl -s --connect-timeout 5 -o /dev/null -w '%{http_code}' https://www.google.com
# Expected: 200

# Confirm ip_forward
sysctl net.ipv4.ip_forward
# Expected: net.ipv4.ip_forward = 1
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|-----------------|-------|
| ebtables (bridge layer filtering) | nftables bridge family | ebtables deprecated on Debian 12; nftables bridge family is the standard |
| bridge masquerade_fix (MAC rewrite) | inet nat MASQUERADE | Router mode makes MAC rewrite unnecessary; Pi's own MAC used for all outbound |
| Transparent bridge (modem sees all MACs) | L2 forward drop + ip routing | Target state for this entire project |

**Deprecated/outdated:**
- `ensure_bridge_masquerade()`: Will be deprecated after Phase 4 swaps it in main.py lifespan. Do NOT remove in Phase 1 — Phase 4 handles the swap.
- `bridge masquerade_fix` nftables table: Removed by `ensure_bridge_isolation()` Step 6.

---

## Open Questions

1. **handle stability after Pi reboot with nftables.service persistence**
   - What we know: Handles are runtime-assigned. The comment-anchor approach for identification is correct. `remove_bridge_isolation()` reads live handles at call time.
   - What's unclear: If nftables.service reloads the persisted ruleset on boot, handles may differ from those assigned at initial application.
   - Recommendation: `remove_bridge_isolation()` must always re-query handles via `nft -a list chain` — the implementation above does this correctly. No issue in practice.

2. **`inet tonbilai forward` MAC-block rules after isolation**
   - What we know: br_netfilter is loaded and bridge-nf-call-iptables=1 is set, so bridged packets reach inet hooks. After isolation (L2 forward dropped), LAN traffic enters Pi's IP stack via routing, still passing inet hooks.
   - What's unclear: Whether MAC-based rules in `inet tonbilai forward` continue to fire for routed (not bridged) packets.
   - Recommendation: From STATE.md research flags: "Confirm `inet tonbilai forward` MAC-block rules still fire after isolation (br_netfilter still loaded)." This is a validation item for after implementation — not a blocker for Phase 1 coding. MAC blocking is a Phase 5 validation concern.

3. **br0 / eth0 / eth1 interface naming stability**
   - What we know: Current code hardcodes `eth0`, `eth1`, `br0`. `_get_wan_bridge_port()` adds dynamic detection for eth0.
   - What's unclear: Whether Pi OS Bookworm udev renames to `enp*` style.
   - Recommendation: Per STATE.md accumulated context — interface naming has been stable. `_get_wan_bridge_port()` provides the safety net. Low risk for Phase 1.

---

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/app/hal/linux_nftables.py` (direct inspection) — `ensure_bridge_masquerade()`, `run_nft()`, `persist_nftables()`, `BRIDGE_MASQ_TABLE`, `_get_wan_bridge_port()`, `ensure_nat_postrouting_chain()`, handle deletion pattern
- `.planning/research/SUMMARY.md` — Full domain research completed 2026-02-25; HIGH confidence across all areas
- `BRIDGE_ISOLATION_PLAN.md` — Detailed implementation plan with exact code patterns
- `.planning/REQUIREMENTS.md` — Phase 1 requirement IDs ISOL-01 through ISOL-07, ROLL-01 through ROLL-03
- nftables wiki — Bridge filtering: https://wiki.nftables.org/wiki-nftables/index.php/Bridge_filtering
- nftables wiki — Netfilter hooks: https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` — Accumulated context, research flags, critical pitfalls
- `.planning/ROADMAP.md` — Phase 1 success criteria (5 items)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all components are existing codebase patterns; no new dependencies
- Architecture: HIGH — single file change (`linux_nftables.py`); patterns directly verified from codebase inspection
- Pitfalls: HIGH — SSH lockout and ordering pitfalls confirmed via SUMMARY.md domain research + codebase analysis; handle stability is documented

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (stable domain — nftables bridge semantics do not change rapidly)

---

## Implementation Scope Summary for Planner

Phase 1 is **one plan, one file**: `backend/app/hal/linux_nftables.py`.

**Add:**
- `ensure_bridge_isolation()` — 7-step ordered function (Steps 1-4 establish routing, Step 5 atomic drop, Step 6 cleanup, Step 7 persist)
- `remove_bridge_isolation()` — handle-based deletion + ICMP restore + persist

**Mark deprecated (do not remove):**
- `ensure_bridge_masquerade()` — Phase 4 will swap it; removing now breaks startup

**Do not touch in Phase 1:**
- `main.py` — Phase 4
- Bridge accounting chains — Phase 2
- TC mark chains — Phase 3
- sysctl.d / modules-load.d persistence files — Phase 4
- dnsmasq / DHCP gateway — Phase 5
