# Feature Research

**Domain:** Bridge isolation / transparent-bridge to router-mode transition on Linux (Raspberry Pi)
**Researched:** 2026-02-25
**Confidence:** HIGH (kernel/nftables mechanics are well-documented; project-specific hook changes verified from codebase)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features the system cannot work correctly without after the mode transition. Missing any of these = devices lose internet or isolation is not achieved.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Bridge L2 forward drop (LAN↔WAN) | Core isolation: modem must not see individual device MACs. Without this the "router mode" is just a bridge with NAT bolted on — devices are still exposed to modem | LOW | Two nftables rules on `bridge filter forward` chain: `iifname eth1 oifname eth0 drop` and reverse. Both must exist atomically. |
| ip_forward=1 (kernel sysctl) | NAT cannot route packets between interfaces without IP forwarding enabled at the kernel level | LOW | Already enabled in most scenarios but must be verified and persisted in `/etc/sysctl.d/`. Regression risk: systemd-sysctl can reset this on reboot. |
| NAT MASQUERADE on WAN egress | Without NAT, LAN device packets arrive at modem with private src IP. Modem drops or ignores them because it's never seen those IPs via DHCP | LOW | Rule: `ip saddr 192.168.1.0/24 ip daddr != 192.168.1.0/24 masquerade` in `inet nat postrouting`. Already partially in place for VPN — must confirm LAN subnet rule is separate. |
| DHCP gateway change (.1 → .2) | After isolation Pi IS the router. Clients that still route via .1 (modem) will try to send packets through the modem, which now has no route back to the LAN devices (it lost their MAC visibility). Traffic dies silently. | MEDIUM | Two-part: (a) dnsmasq config `dhcp-option=3,192.168.1.2`, (b) DB `dhcp_pools.gateway`. Existing clients hold old lease — they won't reconnect until lease expires or are rebooted. Forced DHCPNAK not implemented. |
| br_netfilter module load | NAT at the inet layer only fires for packets that reach the IP stack. br_netfilter is required so bridge-traversing packets are also subjected to ip(6)tables/nftables nat hooks. Without it, MASQUERADE silently does nothing for bridged frames. | LOW | `modprobe br_netfilter` + `net.bridge.bridge-nf-call-iptables=1`. Must be persistent via `/etc/modules-load.d/`. |
| ICMP redirect disable on all interfaces | After Pi becomes router, Pi's kernel may send ICMP Redirect to LAN clients saying "use .1 directly" — which bypasses Pi and breaks DNS filtering, bandwidth accounting, and firewall | LOW | `net.ipv4.conf.all.send_redirects=0` and `net.ipv4.conf.br0.send_redirects=0`. Must be persisted. |
| Remove old bridge masquerade_fix table | The old `bridge masquerade_fix` table rewrites MAC addresses so modem accepts frames. In router mode this is actively harmful — it fights with the new isolation rules and introduces unnecessary overhead | LOW | `nft delete table 'bridge masquerade_fix'`. One-shot cleanup. |
| Bridge accounting hook migration (forward → input/output) | After L2 forward is dropped, the `bridge accounting per_device` chain on the `forward` hook sees zero traffic — all LAN traffic now enters/exits via the IP stack boundary. Counters go dead. | MEDIUM | Replace single `per_device` chain (hook: forward, priority -2) with two chains: `upload` (hook: input, priority -2, iifname eth1) and `download` (hook: output, priority -2, oifname eth1). Counter comment format unchanged so read/parse logic needs minimal update. |
| TC mark chain migration (forward → input/output) | Same hook problem as accounting but for bandwidth limiting. TC marks set on the forward hook die when forward traffic is dropped. Bandwidth limits stop working silently. | MEDIUM | Replace `tc_mark` chain (hook: forward, priority -1) with `tc_mark_up` (hook: input, priority -1) and `tc_mark_down` (hook: output, priority -1). SKB marks survive IP stack routing, so HTB qdiscs on eth1/eth0 continue to function. |
| main.py lifespan swap (masquerade → isolation) | Startup must call `ensure_bridge_isolation()` not `ensure_bridge_masquerade()`. If not changed, every backend restart re-adds the old MAC rewrite table and re-enables bridge forwarding workarounds that conflict with isolation. | LOW | One-line change in `lifespan()`. Old function deprecated/removed. |
| sysctl persistence across reboots | `sysctl -w` changes are in-memory only. After Pi reboot, ICMP redirects re-enable, bridge isolation kernel params reset. Isolation appears to work until next reboot. | LOW | Write to `/etc/sysctl.d/99-bridge-isolation.conf`. Also verify ip_forward is in persistent config. |
| nftables persist after transition | After applying all nftables rules, if `/etc/nftables.conf` is not updated, a Pi reboot loses: isolation drop rules, new accounting chains, tc mark chains. System reverts to transparent bridge silently. | LOW | `nft list ruleset > /etc/nftables.conf` (with `flush ruleset` header). Or call `persist_nftables()` function already implemented. |

---

### Differentiators (Competitive Advantage)

Features that make this a robust, production-quality router transition rather than a minimal hack.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Software rollback function (`remove_bridge_isolation()`) | Pi is the single internet path. If transition breaks something, no rollback = hard-down until physical access. A tested rollback via SSH is the difference between 2-minute recovery and driving home. | LOW | Already designed in BRIDGE_ISOLATION_PLAN.md. Removes nftables rules by handle, re-enables ICMP redirects, optionally re-loads old masquerade table. Should be an API endpoint or at minimum a CLI call. |
| Atomic nftables rule application | Applying isolation drop rules one-by-one creates a window where only one direction is blocked. During that window clients may establish new connections that later become orphaned. | MEDIUM | Use `nft -f -` with a heredoc that adds both drop rules in a single batch. nftables processes `-f` input atomically per-transaction. |
| Validation test suite post-transition | Operators cannot visually confirm modem isolation is working without testing. Without automated checks, silent failures (only one drop rule applied, wrong interface name) go undetected. | MEDIUM | Seven verification checks designed in BRIDGE_ISOLATION_PLAN.md: ARP table check, conntrack ESTABLISHED count, veth namespace test, bridge forward stats, Pi internet access, DNS resolution, bridge counter activity. |
| Conntrack flush after gateway change | After DHCP gateway changes from .1 to .2, existing client TCP connections have conntrack entries that still route return traffic via the old path. Until entries expire (minutes for TCP), some connections fail silently. | MEDIUM | `conntrack -F` (or selective flush) after gateway change. Clients reconnect with new gateway. Trade-off: brief connection drop vs. extended stale routing. Controlled disruption is better than random failures. |
| Per-interface ICMP redirect disable (not just `all`) | `net.ipv4.conf.all.send_redirects=0` sets the default but per-interface settings can override it. `br0` interface created dynamically may inherit wrong default if `all` is set after interface creation. | LOW | Also set `net.ipv4.conf.br0.send_redirects=0` and `net.ipv4.conf.eth0.send_redirects=0` explicitly. BRIDGE_ISOLATION_PLAN.md already includes br0; eth0 is an additional hardening. |
| Counter value preservation during hook migration | When deleting `per_device` chain and recreating as `upload`/`download`, existing byte counts are lost. This causes a visible counter reset spike in the dashboard bandwidth charts. | HIGH | Read all counter values via `read_device_counters()` before deleting old chain, store as a migration offset in Redis, add offset to subsequent reads. Complex but prevents confusing "bandwidth reset to zero" events in UI. |
| DHCP lease force-renewal after gateway change | Clients with long leases (24h default) will use the old .1 gateway until lease expires. During that window they bypass Pi's firewall and DNS filtering. | HIGH | Options: (a) set very short lease time briefly then restore, (b) send DHCPFORCERENEW (requires RFC 3203 support — most clients don't support), (c) rely on natural expiry (simplest, acceptable for home network). Option (a) is the practical choice. |
| Mode status API endpoint | Operators need to know programmatically whether the system is in bridge mode or router mode. Useful for the dashboard and for scripted health checks. | LOW | Read nftables ruleset, check for `bridge_isolation_lan_wan` comment presence. Return `{"mode": "router"}` or `{"mode": "bridge"}`. |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Remove bridge (br0) entirely, use eth0/eth1 directly | "Clean" architecture — no bridge at all, just two routed interfaces | Requires reconfiguring DHCP server, all MAC-based accounting (which uses bridge layer hooks), TC marking, and potentially WireGuard bindings. Massive scope expansion — accounting system was designed around bridge MAC visibility. At least 5 subsystems need changes. | Keep br0. Drop forwarding between its ports. br0 still provides MAC visibility for accounting via input/output hooks. |
| Move to VLAN-based segmentation simultaneously | "While we're at it, separate IoT/trusted VLANs" | Requires 802.1q VLAN support on switch, VLAN-aware bridge config, separate DHCP pools, separate nftables rules per VLAN. This is a separate milestone of its own. | Keep flat 192.168.1.0/24. VLAN segmentation is a future milestone. |
| Replace dnsmasq DHCP with ISC DHCP or Kea | Some prefer dedicated DHCP server | dnsmasq is already in production and working. Migration mid-transition is a compounding risk — two systems changing at once makes debugging impossible. | Keep dnsmasq. Update only the gateway option. |
| IPv6 NAT (NAT66) | IPv6 clients on LAN would also benefit from isolation | NAT66 is non-standard, poorly supported, and unnecessary for home use — ISPs don't give Raspberry Pi home devices IPv6 WAN addresses in this topology. Adds complexity to firewall rules. | Disable IPv6 on br0 (`net.ipv6.conf.br0.disable_ipv6=1`) or accept that IPv6 traffic bypasses the transition scope entirely. |
| Implement QoS traffic shaping changes simultaneously | "The TC qdiscs need updating too" | TC qdiscs on eth0/eth1 do NOT need changes — only the nftables mark chains that feed them need hook migration. Changing qdiscs simultaneously increases debugging surface. | Only migrate the nftables mark hooks (tc_mark_up / tc_mark_down). Keep HTB qdiscs unchanged. |
| UI toggle for bridge/router mode | Frontend switch to flip between modes | Adds API surface and state management that is not needed — this is a one-way migration for this deployment. A toggle creates the illusion that both modes are equally supported long-term. | Implement `remove_bridge_isolation()` as an emergency CLI/API call only, not a UI feature. |

---

## Feature Dependencies

```
[br_netfilter module load]
    └──required by──> [NAT MASQUERADE on WAN egress]
                          └──required by──> [Bridge L2 forward drop (LAN↔WAN)]
                                                (drop alone without NAT = no internet for LAN devices)

[Bridge L2 forward drop]
    └──required by──> [Bridge accounting hook migration]
                      (forward hook sees zero traffic after L2 drop)
    └──required by──> [TC mark chain migration]
                      (mark chain on forward hook stops firing)

[DHCP gateway change (.1 → .2)]
    └──enhances──> [Bridge L2 forward drop]
                   (clients that still use .1 as gateway bypass isolation partially)
    └──triggers need for──> [Conntrack flush after gateway change]

[ip_forward=1]
    └──required by──> [NAT MASQUERADE]
                      (without it, packets are not forwarded between interfaces at all)

[Remove old bridge masquerade_fix table]
    └──required by──> [Bridge L2 forward drop]
                      (masquerade_fix MAC rewrite conflicts with isolation semantics)

[sysctl persistence]
    └──required by──> [ICMP redirect disable]
    └──required by──> [ip_forward=1]
                      (both are runtime-only without persistence)

[nftables persist]
    └──required by──> ALL nftables changes
                      (reboots revert all rules without persistence)

[main.py lifespan swap]
    └──conflicts with──> [Remove old bridge masquerade_fix table]
                         (if lifespan still calls ensure_bridge_masquerade(), it re-creates the table on each restart)

[Software rollback]
    └──depends on──> [Bridge L2 forward drop]
                     (rollback only meaningful after isolation is applied)
    └──independent of──> ALL other features
                         (can be tested before transition is applied)
```

### Dependency Notes

- **NAT MASQUERADE requires br_netfilter:** Packets traversing a Linux bridge do not automatically pass through the inet (IP layer) netfilter hooks. `br_netfilter` is the module that forces bridged packets through IP-layer hooks so MASQUERADE fires. Without it, MASQUERADE rules exist but silently do nothing for LAN-originating traffic. (Confidence: HIGH — verified via nftables wiki and kernel docs)

- **L2 forward drop makes accounting forward hook useless:** Once `iifname eth1 oifname eth0 drop` is in place, LAN packets are no longer bridged — they enter the IP stack at the bridge input hook and exit at the bridge output hook. The `per_device` chain on `forward` hook never fires. Counter values stop incrementing. This is the core reason the accounting hook migration is mandatory, not optional. (Confidence: HIGH — verified via nftables bridge filtering docs)

- **DHCP gateway change conflicts with client lease caching:** Existing clients hold leases with gateway=.1. Even after dnsmasq is updated, clients only pick up the new gateway on lease renewal or reboot. During this window, clients route return traffic through the modem, which now cannot reach LAN devices directly (their MACs are hidden). This creates an asymmetric routing window. (Confidence: MEDIUM — standard DHCP behavior, verified via multiple sources)

- **main.py lifespan swap conflicts with masquerade_fix table removal:** If `ensure_bridge_masquerade()` is still called in `lifespan()`, every backend restart re-creates the `bridge masquerade_fix` table. The manual cleanup step must be paired with the lifespan code change — they cannot be applied independently. (Confidence: HIGH — direct codebase inspection)

---

## MVP Definition

### Launch With (v1 — Minimum for functional bridge isolation)

These features together achieve the stated goal: modem sees only Pi, LAN devices have internet, existing features work.

- [x] **Bridge L2 forward drop (both directions)** — Core isolation. Without this, nothing else matters.
- [x] **br_netfilter load + bridge-nf-call-iptables=1** — Without this, MASQUERADE is a no-op for LAN traffic.
- [x] **ip_forward=1 (verified + persisted)** — Prerequisite for any routing.
- [x] **NAT MASQUERADE rule for LAN subnet** — LAN devices need this to reach internet after isolation.
- [x] **Remove bridge masquerade_fix table** — Old MAC rewrite conflicts with router mode.
- [x] **ICMP redirect disable (all + br0)** — Without this, Pi tells clients to bypass it, breaking DNS filtering.
- [x] **Bridge accounting hook migration (forward → input/output)** — Bandwidth counters go dead otherwise.
- [x] **TC mark chain migration (forward → input/output)** — Bandwidth limiting goes dead otherwise.
- [x] **main.py lifespan swap** — Every backend restart would undo the transition otherwise.
- [x] **DHCP gateway change (.1 → .2)** — Clients that renew leases must get Pi as gateway, not modem.
- [x] **sysctl persistence + nftables persistence** — Reboot resilience.

### Add After Validation (v1.x)

Once the transition is confirmed working and devices are communicating:

- [ ] **Software rollback (`remove_bridge_isolation()`)** — Needed before transition is applied; validates rollback path works. Should be implemented first but only invoked if problems arise.
- [ ] **Validation test suite** — Run post-transition to confirm each subsystem is working. The 7-step test in BRIDGE_ISOLATION_PLAN.md is the checklist.
- [ ] **Mode status API endpoint** — Dashboard health widget can surface current mode. Low priority; rollback and validation are higher value.

### Future Consideration (v2+)

- [ ] **Counter value preservation during hook migration** — Prevents cosmetic counter-reset spikes. High implementation effort, low user impact (data is still collected post-migration).
- [ ] **DHCP lease force-renewal** — Clients pick up new gateway faster. Involves brief intentional disruption; most home users tolerate natural expiry.
- [ ] **Conntrack flush after gateway change** — Eliminates stale routing window. Causes brief TCP RST storm; must be user-triggered, not automatic.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Bridge L2 forward drop | HIGH | LOW | P1 |
| br_netfilter + bridge-nf-call-iptables | HIGH | LOW | P1 |
| ip_forward=1 persisted | HIGH | LOW | P1 |
| NAT MASQUERADE (LAN subnet) | HIGH | LOW | P1 |
| Remove masquerade_fix table | HIGH | LOW | P1 |
| ICMP redirect disable | HIGH | LOW | P1 |
| Bridge accounting hook migration | HIGH | MEDIUM | P1 |
| TC mark chain migration | HIGH | MEDIUM | P1 |
| main.py lifespan swap | HIGH | LOW | P1 |
| DHCP gateway change | HIGH | LOW | P1 |
| sysctl + nftables persistence | HIGH | LOW | P1 |
| Software rollback function | HIGH | LOW | P2 |
| Validation test suite | MEDIUM | MEDIUM | P2 |
| Atomic nftables rule application | MEDIUM | LOW | P2 |
| Per-interface ICMP disable (eth0) | LOW | LOW | P2 |
| Mode status API endpoint | LOW | LOW | P3 |
| Counter value preservation | LOW | HIGH | P3 |
| DHCP lease force-renewal | LOW | MEDIUM | P3 |
| Conntrack flush after gateway change | MEDIUM | LOW | P3 |

**Priority key:**
- P1: Must have for the transition to function correctly
- P2: Should have for robustness and recovery
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

"Competitors" in this context are established home router firmware implementations that have solved the same bridge→router transition problem.

| Feature | OpenWrt | pfSense | Our Approach |
|---------|---------|---------|--------------|
| Bridge isolation via nftables | Yes (uses iptables/nf_tables under the hood via firewall4) | Yes (pf-based, different mechanism) | Direct nftables rules — same semantics as OpenWrt firewall4 bridge isolation |
| Accounting on input/output hooks | Yes — OpenWrt's traffic accounting uses FORWARD/INPUT on inet, not bridge hooks, because it typically runs as a pure router (no br_netfilter needed in clean mode) | N/A | Our approach must handle the bridge-specific case because br0 persists; direct inet hook accounting would miss MAC-to-device mapping |
| DHCP gateway management | Integrated — UCI sets gateway atomically with interface config | Integrated via GUI | Separate dnsmasq config file + DB update — must coordinate both manually |
| Rollback | Full config snapshot/restore via UCI | Config backup/restore via GUI | `remove_bridge_isolation()` function — minimal but sufficient for this topology |
| Sysctl persistence | Via `/etc/sysctl.conf` managed by UCI | Via tunable system | `/etc/sysctl.d/99-bridge-isolation.conf` — standard Linux approach |

---

## Sources

- nftables wiki — Simple ruleset for a home router: https://wiki.nftables.org/wiki-nftables/index.php/Simple_ruleset_for_a_home_router (HIGH confidence)
- nftables wiki — Bridge filtering hooks: https://wiki.nftables.org/wiki-nftables/index.php/Bridge_filtering (HIGH confidence — canonical hook descriptions)
- nftables wiki — Performing NAT: https://wiki.nftables.org/wiki-nftables/index.php/Performing_Network_Address_Translation_(NAT) (HIGH confidence)
- ebtables bridge-nf documentation — br_netfilter requirement: https://ebtables.netfilter.org/documentation/bridge-nf.html (HIGH confidence)
- Vincent Bernat — Proper isolation of a Linux bridge: https://vincent.bernat.ch/en/blog/2017-linux-bridge-isolation (MEDIUM confidence — 2017, mechanics unchanged)
- Linux Kernel docs — IP Sysctl: https://docs.kernel.org/networking/ip-sysctl.html (HIGH confidence)
- Thermalcircle — nftables packet flow and Netfilter hooks: https://thermalcircle.de/doku.php?id=blog:linux:nftables_packet_flow_netfilter_hooks_detail (MEDIUM confidence)
- BRIDGE_ISOLATION_PLAN.md — project-specific implementation details (HIGH confidence — ground truth for this system)
- Codebase inspection — `linux_nftables.py`, `linux_tc.py`, `main.py` (HIGH confidence — direct source review)

---

*Feature research for: Bridge isolation / transparent-bridge to router-mode transition, TonbilAiOS*
*Researched: 2026-02-25*
