# Architecture Research

**Domain:** Raspberry Pi Router — Bridge-to-Router Mode Transition
**Researched:** 2026-02-25
**Confidence:** HIGH (analysis based on actual codebase, BRIDGE_ISOLATION_PLAN.md, and nftables/Linux kernel documented behavior)

---

## Standard Architecture

### System Overview: Before vs After

#### BEFORE — Transparent Bridge Mode (Current)

```
Internet
    |
[ZTE Modem .1]
    |
  eth0
    |
  br0 (bridge)  <─── L2 forwarding active, modem sees all MACs
    |
  eth1
    |
[LAN Devices .10, .39, .57, ...]
```

nftables table layout (current):

```
table inet tonbilai      (filter: input, forward, output)
table inet nat           (prerouting DNS redirect, postrouting MASQUERADE)
table bridge accounting  (chain per_device: hook forward -2)  ← bandwidth counters
table bridge masquerade_fix  (chain mac_rewrite: hook postrouting 300)  ← MAC rewrite
table bridge accounting  (chain tc_mark: hook forward -1)    ← TC shaping marks
```

Packet path for a LAN device reaching the internet (bridge mode):

```
[Device frame] → eth1 ingress
    → bridge forward (L2, no IP stack) → eth0 egress
        ├─ bridge accounting.per_device (-2): count bytes by MAC
        ├─ bridge accounting.tc_mark (-1): set SKB mark for shaping
        └─ bridge masquerade_fix.mac_rewrite (+300): rewrite src MAC to br0 MAC
    → modem sees Pi's MAC, forwards packet
```

The `inet tonbilai forward` chain only fires when `br_netfilter` is loaded and
`net.bridge.bridge-nf-call-iptables=1`, which makes bridge-forwarded frames also
traverse the inet layer. This is the current mechanism for MAC-based blocking.

#### AFTER — Isolated Router Mode (Target)

```
Internet
    |
[ZTE Modem .1]  ← sees only Pi's MAC
    |
  eth0
    |
  br0 (Pi IP stack — routing enabled)
    |
  eth1
    |
[LAN Devices .10, .39, .57, ...]
```

nftables table layout (target):

```
table bridge filter      (chain forward: DROP eth1↔eth0 L2 forwarding)
table bridge accounting  (chain upload: hook input -2, chain download: hook output -2)
table bridge accounting  (chain tc_mark_up: hook input -1, chain tc_mark_down: hook output -1)
table inet tonbilai      (filter: input, forward, output — now handles routed packets)
table inet nat           (prerouting DNS redirect, postrouting MASQUERADE for LAN)
```

Packet path after isolation:

```
[Device frame] → eth1 ingress
    → bridge forward chain: DROP (L2 path killed)
    → packet passes up to Pi IP stack
        → bridge accounting.upload (-2): count bytes (iifname eth1, ether saddr MAC)
        → bridge accounting.tc_mark_up (-1): set SKB mark (iifname eth1, ether saddr MAC)
    → Pi routes packet: routing table decision
    → inet tonbilai forward: MAC block, IP block, VPN forward rules
    → inet nat postrouting: MASQUERADE (LAN subnet → modem)
    → eth0 egress (Pi's MAC on the wire — modem unaware of LAN devices)
```

Return path (download):

```
[Internet response] → eth0 ingress → Pi IP stack
    → inet tonbilai forward (if applicable)
    → routed to br0/eth1
    → bridge accounting.download (-2): count bytes (oifname eth1, ether daddr MAC)
    → bridge accounting.tc_mark_down (-1): set SKB mark (oifname eth1, ether daddr MAC)
    → [Device frame] delivered via eth1
```

---

## Component Boundaries

### Kernel-Level Components

| Component | Family | Hook | Priority | Responsibility | Changes |
|-----------|--------|------|----------|----------------|---------|
| `bridge filter forward` | bridge | forward | 0 | DROP eth1↔eth0 L2 forwarding | NEW (2 drop rules) |
| `bridge accounting upload` | bridge | input | -2 | Count bytes from LAN devices (saddr) | RENAMED from per_device |
| `bridge accounting download` | bridge | output | -2 | Count bytes to LAN devices (daddr) | NEW chain |
| `bridge accounting tc_mark_up` | bridge | input | -1 | Set SKB mark for upload shaping | RENAMED from tc_mark |
| `bridge accounting tc_mark_down` | bridge | output | -1 | Set SKB mark for download shaping | NEW chain |
| `inet tonbilai forward` | inet | forward | 0 | Device block, IP block, VPN permit | UNCHANGED |
| `inet nat postrouting` | inet | postrouting | 100 | MASQUERADE LAN traffic to modem | UNCHANGED (already present) |
| `bridge masquerade_fix mac_rewrite` | bridge | postrouting | 300 | MAC rewrite (old mode) | REMOVED |

### Software-Level Components

| Component | File | Responsibility | Changes in Transition |
|-----------|------|----------------|----------------------|
| `ensure_bridge_isolation()` | `hal/linux_nftables.py` | Set ip_forward, load br_netfilter, add bridge forward DROP rules, ensure MASQUERADE, remove masquerade_fix table | NEW FUNCTION (replaces ensure_bridge_masquerade) |
| `remove_bridge_isolation()` | `hal/linux_nftables.py` | Remove bridge forward DROP rules, restore send_redirects | NEW FUNCTION (rollback path) |
| `ensure_bridge_accounting_chain()` | `hal/linux_nftables.py` | Create upload+download chains with input/output hooks | REWRITE (was single forward-hook per_device chain) |
| `add_device_counter(mac)` | `hal/linux_nftables.py` | Add counter rules to upload and download chains separately | REWRITE (chain name + iifname/oifname filter) |
| `remove_device_counter(mac)` | `hal/linux_nftables.py` | Remove counter rules from both chains | REWRITE (two chains) |
| `read_device_counters()` | `hal/linux_nftables.py` | Read and merge upload+download chain output | REWRITE (two chain reads, merge) |
| `sync_device_counters(macs)` | `hal/linux_nftables.py` | Sync counter rules across both chains | REWRITE (reference both chains) |
| `_ensure_tc_mark_chain()` | `hal/linux_tc.py` | Create tc_mark_up and tc_mark_down chains | REWRITE (was single forward-hook tc_mark) |
| `add_device_limit(mac, rate, ceil)` | `hal/linux_tc.py` | Add mark rules to tc_mark_up and tc_mark_down | REWRITE (chain names + iifname/oifname) |
| `remove_device_limit(mac)` | `hal/linux_tc.py` | Remove mark rules from both tc_mark chains | REWRITE |
| `_remove_nft_mark_rule(mac)` | `hal/linux_tc.py` | Handle cleanup for both up/down chains | REWRITE |
| `lifespan()` startup | `main.py` | Replace ensure_bridge_masquerade call with ensure_bridge_isolation | ONE-LINE SWAP |
| DHCP pool config | `hal/linux_dhcp_driver.py` + dnsmasq conf | Gateway option changes from 192.168.1.1 to 192.168.1.2 | DHCP config file on Pi + DB update |

---

## Architectural Patterns

### Pattern 1: Hook Family Boundary — Bridge vs Inet

**What:** nftables has two separate processing pipelines: `bridge` family and `inet` (IP) family. When `br_netfilter` is active, bridge-forwarded frames can also traverse inet hooks — but the converse is not true. After isolation, L2 forwarding is killed at the bridge forward hook, so all traffic reaches the inet layer exclusively through the Pi's routing stack.

**When to use:** Any packet classification that must happen before the IP stack routes the packet (MAC-layer counters, MAC-layer TC marking) must stay in the bridge family. Any IP-level filtering (DDoS protection, VPN forwarding, IP blocklists) stays in the inet family. After isolation, both families remain active — bridge hooks process the physical ingress/egress on eth1, inet hooks process the routed forwarding between LAN and WAN.

**Critical implication for accounting:** In bridge mode, the `forward` hook fires once for L2-forwarded packets traversing the bridge. After isolation, bridge L2 forwarding is killed, so the `forward` hook no longer sees LAN-to-WAN traffic. Instead:
- `input` hook fires when a packet arrives on an interface and is destined for the local IP stack (LAN devices sending through Pi).
- `output` hook fires when the IP stack sends a packet out through an interface (Pi delivering to LAN devices).

This is why all accounting and TC marking chains must migrate from `hook forward` to `hook input` (upload) and `hook output` (download).

### Pattern 2: Comment-Anchored Rule Identification

**What:** Every nftables rule added by the software carries a unique `comment` field (e.g., `"bw_aa:bb:cc:dd:ee:ff_up"`, `"tc_mark_{mac}_down"`, `"bridge_isolation_lan_wan"`). Deletion is done by listing chains with `-a` flag to get handle numbers, searching for the comment string, then deleting by handle.

**When to use:** Mandatory for all dynamically added rules. This is the existing pattern throughout linux_nftables.py and must be preserved for isolation rules. The two new drop rules must use comments `"bridge_isolation_lan_wan"` and `"bridge_isolation_wan_lan"` so `remove_bridge_isolation()` can find and delete them precisely.

**Example:**
```python
# Add with comment
await run_nft([
    "add", "rule", "bridge", "filter", "forward",
    "iifname", "eth1", "oifname", "eth0", "drop",
    "comment", '"bridge_isolation_lan_wan"',
])

# Remove by handle lookup
out = await run_nft(["-a", "list", "chain", "bridge", "filter", "forward"], check=False)
for line in out.splitlines():
    if "bridge_isolation_lan_wan" in line:
        handle_match = re.search(r"handle\s+(\d+)", line)
        if handle_match:
            await run_nft(["delete", "rule", "bridge", "filter", "forward",
                           "handle", handle_match.group(1)], check=False)
```

### Pattern 3: Idempotent Setup Functions

**What:** All `ensure_*()` functions check whether the target state already exists before applying it. They check chain presence or comment presence before adding rules. This allows safe repeated calls (startup restarts, hot-reload).

**When to use:** `ensure_bridge_isolation()` must follow this pattern: check whether bridge forward DROP rules exist by searching for `"bridge_isolation_lan_wan"` in the ruleset before adding them. Likewise for the MASQUERADE rule (`"bridge_lan_masq"`).

### Pattern 4: TC Marks Survive the Bridge-to-Inet Transition

**What:** SKB (socket buffer) marks set in bridge nftables rules persist as packets travel through the routing stack. The `tc fw filter` on eth0 and eth1 matches these marks to route packets into the correct HTB class. This mechanism works in both bridge mode and router mode — marks are on the SKB, not the frame header.

**When to use:** No change needed to the HTB qdisc setup on eth0 and eth1. The `setup_htb_root()` and `fw filter` application in `linux_tc.py` remain unchanged. Only the nftables chains that set the marks need to be migrated from the forward hook to input/output hooks.

---

## Data Flow

### Upload Path (LAN Device → Internet) After Isolation

```
Device (e.g. 192.168.1.57)
    ↓  sends IP packet
eth1 ingress
    ↓
bridge filter forward chain
    → iifname eth1 oifname eth0 DROP  ← L2 path killed
    ↓  (packet not forwarded at L2, passes to IP stack)
bridge accounting.upload (hook input, prio -2)
    → iifname "eth1" ether saddr {MAC} counter "bw_{mac}_up"
    ↓
bridge accounting.tc_mark_up (hook input, prio -1)
    → iifname "eth1" ether saddr {MAC} meta mark set {N}
    ↓
Pi IP stack — routing decision
    ↓
inet tonbilai forward (hook forward, prio 0)
    → blocked MAC/IP check → drop if blocked
    → VPN accept rules
    ↓
inet nat postrouting (hook postrouting, prio 100)
    → MASQUERADE (src 192.168.1.x → Pi's external IP on eth0)
    ↓
eth0 egress
    → TC HTB on eth0 (fw filter matches mark → class → rate limit)
    ↓
Modem (sees only Pi's MAC/IP)
    ↓ Internet
```

### Download Path (Internet → LAN Device) After Isolation

```
Internet response
    ↓
eth0 ingress
    → TC HTB on eth0 (fw filter — classifies returning traffic if marked)
    ↓
Pi IP stack — conntrack reversal (MASQUERADE inverse)
    ↓
inet tonbilai forward
    ↓
Routing decision → br0/eth1
    ↓
bridge accounting.download (hook output, prio -2)
    → oifname "eth1" ether daddr {MAC} counter "bw_{mac}_down"
    ↓
bridge accounting.tc_mark_down (hook output, prio -1)
    → oifname "eth1" ether daddr {MAC} meta mark set {N}
    ↓
eth1 egress
    → TC HTB on eth1 (fw filter matches mark → class → rate limit)
    ↓
Device receives packet
```

### DNS Query Path (Unchanged)

```
Device DNS query → eth1 → Pi → inet nat prerouting
    → redirect to port 5353 (dns_proxy.py)
    → profile/blocklist lookup (Redis)
    → ALLOW: forward to upstream DNS
    → BLOCK: return NXDOMAIN or block page IP
```

DNS is entirely within Pi's IP stack and is unaffected by bridge isolation. The dns_proxy worker binds to port 53/5353 on Pi's address.

### DHCP Gateway Change Impact

```
Before: dnsmasq sends dhcp-option=3,192.168.1.1 (modem as gateway)
After:  dnsmasq sends dhcp-option=3,192.168.1.2 (Pi as gateway)

Client ARP for .2 → Pi responds → Pi routes packet
Existing leases: clients keep .1 as gateway until DHCP renew
    → short-term: some clients route via modem directly → modem blocks (no Pi NAT)
    → fix: send DHCP FORCERENEW or wait lease expiry (24h default)
    → immediate fix: restart dnsmasq (clients re-request) or reduce lease time temporarily
```

---

## Build Order (Required Sequence)

The transition has hard dependencies. Building out of order causes connectivity loss or broken accounting.

### Phase 1: nftables HAL — Bridge Isolation Function (FIRST)

**Must happen before anything else.** Without `ensure_bridge_isolation()`, there is no router mode to validate against.

Files to change:
- `backend/app/hal/linux_nftables.py`: Add `ensure_bridge_isolation()` and `remove_bridge_isolation()`
- Keep `ensure_bridge_masquerade()` in place during development (remove after Phase 3)

Rationale: This function is the single source of truth for the new network topology. All other components depend on the IP stack receiving packets that previously bypassed it.

### Phase 2: Bridge Accounting Chain Migration (SECOND)

**Depends on Phase 1** because the accounting chains must match the hook that now receives traffic. After Phase 1 drops L2 forwarding, the old `per_device forward` chain sees zero traffic. The new `upload (input)` and `download (output)` chains must exist before bandwidth data becomes meaningful.

Files to change:
- `backend/app/hal/linux_nftables.py`:
  - Rewrite `ensure_bridge_accounting_chain()` (two chains, input/output hooks)
  - Rewrite `add_device_counter(mac)` (upload chain with iifname filter, download chain with oifname filter)
  - Rewrite `remove_device_counter(mac)` (delete from both chains)
  - Rewrite `read_device_counters()` (read both chains, merge results)
  - Rewrite `sync_device_counters(macs)` (reference both chain names)
  - Update `BRIDGE_CHAIN` constant or remove it (replace with `"upload"` and `"download"`)

### Phase 3: TC Marking Chain Migration (THIRD)

**Depends on Phase 2** conceptually (same hook migration pattern) but technically independent of Phase 2. Must happen after Phase 1 for the same reason — the old `tc_mark forward` chain is dead after isolation.

Files to change:
- `backend/app/hal/linux_tc.py`:
  - Rewrite `_ensure_tc_mark_chain()` (two chains: tc_mark_up input, tc_mark_down output)
  - Rewrite `add_device_limit(mac, rate, ceil)` mark rules (tc_mark_up with iifname, tc_mark_down with oifname)
  - Rewrite `remove_device_limit(mac)` (both chains)
  - Rewrite `_remove_nft_mark_rule(mac)` (both chains)
  - `setup_htb_root()`, `get_device_stats()`: UNCHANGED (HTB on slave interfaces stays identical)

### Phase 4: main.py Startup Swap (FOURTH)

**Depends on Phases 1-3** being implemented. The one-line swap from `ensure_bridge_masquerade` to `ensure_bridge_isolation` is the deployment trigger. All HAL functions must be correct before this is activated.

File to change:
- `backend/app/main.py` lifespan(): replace `ensure_bridge_masquerade` import and call with `ensure_bridge_isolation`
- Retain `_restore_bandwidth_limits()` call — it calls `tc.add_device_limit()` which will now use the migrated marking chains

### Phase 5: DHCP Gateway Update (FIFTH — LAST, separate from code)

**Independent of Phases 1-4** in terms of code changes, but must happen after the router mode is live on the Pi. Changing the gateway before bridge isolation is active would route LAN traffic to Pi without NAT, breaking connectivity.

Actions (on Pi via SSH, not code files):
1. Update `/etc/dnsmasq.d/pool-1.conf`: `dhcp-option=3,192.168.1.2`
2. Update `tonbilaios.dhcp_pools` table: `UPDATE dhcp_pools SET gateway='192.168.1.2'`
3. Reload dnsmasq: `sudo systemctl reload dnsmasq`
4. Persist sysctl: add `net.ipv4.conf.all.send_redirects=0` to `/etc/sysctl.d/99-bridge-isolation.conf`

---

## Integration Points

### Components Unaffected by Isolation

| Component | Reason Unaffected |
|-----------|-------------------|
| `inet tonbilai` (DDoS, device block, VPN forward) | Already on IP stack, isolation brings more traffic here, not less |
| `inet nat` prerouting (DNS redirect) | Operates on Pi's local traffic, unchanged |
| `wg0` VPN server | Independent interface, routing through Pi's stack already |
| `dns_proxy.py` | Binds to Pi's IP port 53/5353, no L2 dependency |
| `flow_tracker.py` (conntrack) | conntrack tracks IP flows; in bridge mode with br_netfilter these were visible; in router mode they are natively visible without br_netfilter dependency |
| `traffic_monitor.py` | Same as flow_tracker |
| `device_discovery.py` | ARP-based, works on br0 interface regardless of mode |
| TC HTB qdiscs on eth0/eth1 | Slave interface qdiscs are unchanged; marks on SKBs survive routing |
| Fail2ban | SSH protection on Pi's inet input chain |
| Telegram, AI workers | Application-level, no network topology dependency |

### Critical Internal Boundary: Bridge Family vs Inet Family

```
bridge family (L2):
    ├─ bridge filter forward    → DROP rules (isolation boundary)
    ├─ bridge accounting upload → MAC counter, hook input
    ├─ bridge accounting download → MAC counter, hook output
    ├─ bridge accounting tc_mark_up → SKB mark, hook input
    └─ bridge accounting tc_mark_down → SKB mark, hook output

inet family (L3):
    ├─ inet tonbilai input      → rate limiting, SSH protection
    ├─ inet tonbilai forward    → device block, VPN accept, IP block
    ├─ inet nat prerouting      → DNS redirect (port 53 → 5353)
    └─ inet nat postrouting     → MASQUERADE (LAN → WAN)
```

After isolation, bridge family sees traffic only on eth1 physical ingress/egress. The inet family sees all routed traffic. These two domains do not overlap for LAN↔WAN flows — bridge hooks classify and mark, inet hooks filter and NAT.

### HAL Layer Coupling

```
linux_tc.py
    └─ calls linux_nftables.run_nft() for bridge mark chains
    └─ has its own run_nft() wrapper (local, not shared)
    └─ uses BRIDGE_TABLE = "accounting" (matches linux_nftables.py BRIDGE_TABLE)

linux_nftables.py
    └─ creates and owns "bridge accounting" table
    └─ linux_tc.py adds chains and rules to this shared table
    → RISK: both files must agree on table name and chain names
    → RECOMMENDATION: define chain name constants in ONE place and import
```

The current codebase duplicates the `BRIDGE_TABLE = "accounting"` constant and `run_nft()` function between files. After the migration adds `tc_mark_up` and `tc_mark_down` chains to this shared table, the naming must remain consistent.

---

## Anti-Patterns

### Anti-Pattern 1: Migrating Accounting/TC Before Isolation Drop Rules

**What people do:** Change the accounting chains from `forward` to `input`/`output` hooks first, then add the isolation drop rules later.

**Why it's wrong:** Before the bridge forward DROP rules are in place, `hook input` and `hook output` in the bridge family only see traffic explicitly addressed to/from the bridge device itself (Pi's own traffic). LAN-to-WAN bridge-forwarded frames do NOT traverse bridge input/output hooks — they only use the forward hook. Adding input/output accounting chains before isolation would count zero bytes for LAN device traffic.

**Do this instead:** Add bridge forward DROP rules first (Phase 1 `ensure_bridge_isolation()`). This forces all LAN traffic up to the IP stack, which then means all delivery back to eth1 goes through bridge output. Only after this is the input/output hook approach correct.

### Anti-Pattern 2: Removing the masquerade_fix Table Without MASQUERADE in Inet

**What people do:** Delete `bridge masquerade_fix` table (MAC rewrite) as part of cleanup without verifying the `inet nat postrouting` MASQUERADE rule is in place.

**Why it's wrong:** Without either MAC rewrite (old mode) or MASQUERADE (new mode), the Pi sends packets with LAN device source IPs to the modem. The modem discards or does not route return traffic, breaking internet access for all devices.

**Do this instead:** `ensure_bridge_isolation()` must verify and add the `bridge_lan_masq` MASQUERADE rule to `inet nat postrouting` before or simultaneously with removing the masquerade_fix table. The function in BRIDGE_ISOLATION_PLAN.md does this correctly — steps 5 and 6 are: add MASQUERADE → remove masquerade_fix. Never reverse this order.

### Anti-Pattern 3: Hardcoding Chain Names in Both linux_nftables.py and linux_tc.py

**What people do:** Keep `BRIDGE_CHAIN = "per_device"` in linux_nftables.py and `TC_MARK_CHAIN = "tc_mark"` in linux_tc.py as separate constants with no cross-reference.

**Why it's wrong:** After migration, linux_tc.py adds `tc_mark_up` and `tc_mark_down` chains to the same `bridge accounting` table owned by linux_nftables.py. If linux_nftables.py's `ensure_bridge_accounting_chain()` creates the table but doesn't create the TC chains, and linux_tc.py's `_ensure_tc_mark_chain()` adds them, the shared table has mixed ownership. Any call to `nft flush table bridge accounting` (which could happen in error recovery) would destroy TC chains that linux_tc.py expects to exist.

**Do this instead:** Make `ensure_bridge_accounting_chain()` in linux_nftables.py responsible for creating ALL chains in the `bridge accounting` table, including `upload`, `download`, `tc_mark_up`, and `tc_mark_down`. linux_tc.py's `_ensure_tc_mark_chain()` should call `ensure_bridge_accounting_chain()` from linux_nftables.py, or at minimum call it first and only add rules into pre-existing chains.

### Anti-Pattern 4: DHCP Gateway Change Before Router Mode is Active

**What people do:** Update `/etc/dnsmasq.d/pool-1.conf` to `dhcp-option=3,192.168.1.2` and reload dnsmasq before the bridge isolation drop rules are in effect.

**Why it's wrong:** Clients that receive new DHCP leases will ARP for 192.168.1.2 as their gateway. Pi responds. Clients send traffic to Pi. But without NAT (the masquerade_fix table is gone, bridge_lan_masq may not be in place yet), Pi either routes packets without masquerading (modem rejects non-Pi source IPs) or drops them. Result: internet outage for all devices that renew leases.

**Do this instead:** Activate bridge isolation fully (Phases 1-4 deployed and backend restarted) before changing DHCP gateway. Phase 5 is explicitly last for this reason.

---

## Scalability Considerations

This is a single Raspberry Pi router. Traditional scale axes do not apply. Instead, the relevant scalability dimension is "number of tracked devices."

| Tracked Devices | nftables Chain Concern |
|-----------------|------------------------|
| 1-20 devices | No concern; each device has 2 counter rules + 2 TC mark rules |
| 20-100 devices | Each device adds 4 bridge chain rules (2 in accounting, 2 in tc_mark). At 100 devices = 400 bridge rules. nftables handles this without issue. |
| 100+ devices | Rule lookup is linear per chain. Consider nftables `set` + `map` approach for O(1) lookup. Not required for a home/SMB router scenario. |

The hook migration from one forward chain to two input/output chains does not change performance characteristics. Bridge hooks are identical in evaluation cost to forward hooks.

---

## Sources

- `backend/app/hal/linux_nftables.py` — actual implementation (read and analyzed)
- `backend/app/hal/linux_tc.py` — actual implementation (read and analyzed)
- `backend/app/main.py` lifespan() — startup sequence (read and analyzed)
- `BRIDGE_ISOLATION_PLAN.md` — migration design document (read in full)
- `.planning/PROJECT.md` — milestone context and constraints
- nftables bridge family hook documentation: hook input/output fire for bridge device's own traffic and bridge-local delivery; hook forward fires for L2-forwarded frames. This is the fundamental reason the chain migration is necessary. (HIGH confidence — standard Linux kernel/nftables documented behavior)
- br_netfilter module: when loaded with `bridge-nf-call-iptables=1`, bridge-forwarded frames additionally traverse inet hooks. After isolation, this is no longer needed for forwarding (packets reach inet via routing), but it must remain loaded for the `inet tonbilai forward` MAC-block rules to see bridge-originated connections. (MEDIUM confidence — validate on target Pi that `inet tonbilai forward` MAC block still fires for LAN devices after isolation)

---
*Architecture research for: TonbilAiOS Bridge-to-Router Isolation Transition*
*Researched: 2026-02-25*
