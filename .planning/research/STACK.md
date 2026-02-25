# Stack Research

**Domain:** Linux bridge isolation — transparent bridge to router mode transition on Raspberry Pi
**Researched:** 2026-02-25
**Confidence:** MEDIUM-HIGH (core nftables bridge semantics verified via official wiki; mark preservation across families LOW confidence — not definitively documented)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| nftables bridge family | Kernel 5.3+ | L2 forwarding drop rules (forward hook) | Direct replacement for ebtables; supports `iifname`/`oifname` matching in forward hook; bridge family's `filter` chain type is the correct tool for L2 isolation drops |
| nftables bridge family | Kernel 5.3+ | Bandwidth accounting (input/output hooks) | After L2 forwarding is blocked, `input` hook sees frames arriving at br0's IP stack; `output` hook sees frames leaving to bridge ports — correct replacement for the lost `forward` hook |
| nftables inet family | Kernel 5.2+ | NAT / MASQUERADE | Bridge family does NOT support nat chain type. MASQUERADE must live in `inet nat` or `ip nat` table at postrouting hook. TonbilAiOS already uses `inet nat` — no change needed |
| nftables inet family | Kernel 5.2+ | TC mark assignment (alternative) | If bridge mark preservation is unreliable, move TC marking to `inet mangle` forward/postrouting hooks where mark behavior is well-documented |
| sysctl | any | ip_forward, send_redirects, bridge-nf-call | Three distinct sysctl namespaces control bridge→router behavior; each has specific load-order requirements |
| modprobe br_netfilter | Kernel ≥ 4.x | Legacy: passes bridged IPv4 packets to iptables/ip-family hooks | Load only if inet-family rules need to see bridged traffic. For this project — DO NOT load; it causes double-processing and unexpected nftables ip-family hits on bridge traffic |

### Supporting Libraries / Tools

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `conntrack -L` | iproute2 | Verify NAT sessions survive transition | After transition, confirm existing sessions are tracked through Pi IP stack |
| `nft -a list chain bridge filter forward` | nftables | List forward-chain rules with handles for rollback | Before any modification, snapshot handle numbers for safe deletion |
| `ip netns` + `veth` | iproute2 | Synthetic test device (namespace simulation) | Integration test without needing physical client device |
| `tcpdump -i eth0 arp` | libpcap | Verify modem ARP table no longer sees LAN MACs | Definitive isolation proof — only Pi MAC should appear on eth0 |
| `/etc/sysctl.d/99-bridge-isolation.conf` | sysctl.d | Persist isolation sysctls across reboots | Required; bare `sysctl -w` is lost on reboot |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `nft -f -` (stdin mode) | Apply multi-statement rulesets atomically | Use for complex rule sequences to avoid partial-apply state |
| `nft list ruleset` | Full ruleset dump before/after | Snapshot before changes; diff after for verification |
| `systemd-sysctl` | Apply sysctl.d files | Run `systemctl restart systemd-sysctl` after adding new conf files |

---

## nftables Bridge Family — Hook Points and Priority Values

This is the authoritative reference for the hook migration in this project.

### Bridge Family Hooks

| Hook | Named Priority | Numerical Value | NF Constant | What Fires Here |
|------|---------------|-----------------|-------------|-----------------|
| prerouting | dstnat | -300 | NF_BR_PRI_NAT_DST_BRIDGED | Before FDB decision; can redirect frames |
| all hooks | filter | -200 | NF_BR_PRI_FILTER_BRIDGED | Standard filtering priority |
| all hooks | (br_netfilter) | 0 | NF_BR_PRI_BRNF | Where br_netfilter intercepts (avoid using this priority) |
| output | out | 100 | NF_BR_PRI_NAT_DST_OTHER | Local bridge output |
| all hooks | (br_filter2) | 200 | NF_BR_PRI_FILTER_OTHER | Post-br_netfilter filtering |
| postrouting | srcnat | 300 | NF_BR_PRI_NAT_SRC | Bridge SNAT (filter type only — not real NAT) |

**Critical:** The same keyword `filter` maps to -200 in bridge family but 0 in inet/ip families. This is a known difference, not a bug. (Source: nftables wiki, Netfilter hooks page)

### Which Hook Fires for Which Traffic Path

```
BRIDGE TRANSPARENT MODE (current):
  External frame → eth0 → bridge FDB lookup → eth1 → client
                              ↓ fires: forward hook

ROUTER MODE (after isolation):
  External packet → eth0 → bridge input → Pi IP stack → routing → bridge output → eth1
                              ↓ fires: input hook           ↓ fires: output hook
```

**This is why accounting must move from forward to input/output.** After L2 forwarding is blocked, the forward hook never fires for LAN↔WAN traffic — packets instead traverse the IP stack and hit input (arriving at Pi) and output (leaving Pi toward eth1).

### Chain Types Supported by Bridge Family

| Chain Type | Bridge | inet | ip | Notes |
|------------|--------|------|----|-------|
| filter | YES | YES | YES | Only chain type available in bridge |
| nat | NO | YES (kernel 5.2+) | YES | Bridge cannot do NAT — use inet nat for MASQUERADE |
| route | NO | YES | YES | Not available in bridge |

**Implication:** All NAT/MASQUERADE rules stay in `inet nat` table. Bridge family rules are filter-only.

---

## sysctl Parameters for Bridge Isolation

### Required Parameters

| Parameter | Value | Why | Persistence |
|-----------|-------|-----|-------------|
| `net.ipv4.ip_forward` | 1 | Pi must route packets between eth0 and eth1 via IP stack | `/etc/sysctl.d/99-bridge-isolation.conf` |
| `net.ipv4.conf.all.send_redirects` | 0 | Prevent Pi from telling clients to go directly to modem (.1) — breaks isolation | Same file |
| `net.ipv4.conf.br0.send_redirects` | 0 | Interface-specific guard for the bridge interface | Same file |

### Parameters to NOT Set (Anti-recommendations)

| Parameter | Why to Avoid |
|-----------|-------------|
| `net.bridge.bridge-nf-call-iptables=1` | Causes br_netfilter to intercept bridged packets and feed them into ip-family nftables rules. Creates double-processing. Since TonbilAiOS uses nftables bridge family directly, this is not needed. |
| `net.bridge.bridge-nf-call-ip6tables=1` | Same reason for IPv6 |

### Boot-Order Problem with bridge-nf-call Sysctls

`net.bridge.bridge-nf-call-*` parameters only exist in sysctl namespace after `br_netfilter` module is loaded. If they appear in `/etc/sysctl.conf` without the module being loaded first, the kernel logs "unknown key" and ignores them. The solution is to not load `br_netfilter` at all — which is the correct choice here since TonbilAiOS already uses nftables bridge family.

If `br_netfilter` is currently loaded on the Pi, unload it:

```bash
sudo modprobe -r br_netfilter
# Verify absence:
lsmod | grep br_netfilter  # should be empty
```

---

## Bridge Isolation — nftables Rule Structure

### L2 Forwarding Drop (bridge filter forward chain)

```nft
# In bridge family — filter chain type — forward hook
table bridge filter {
    chain forward {
        type filter hook forward priority -200; policy accept;

        # Drop all direct L2 forwarding between LAN and WAN ports
        iifname "eth1" oifname "eth0" drop comment "bridge_isolation_lan_wan"
        iifname "eth0" oifname "eth1" drop comment "bridge_isolation_wan_lan"
    }
}
```

After these rules, no Ethernet frame can pass from eth1→eth0 or eth0→eth1 at L2. All traffic must traverse Pi's IP stack.

### Bandwidth Accounting (bridge filter input/output chains)

```nft
table bridge accounting {
    chain upload {
        type filter hook input priority -200; policy accept;
        # iifname "eth1" ether saddr <MAC> counter comment "bw_<MAC>_up"
    }
    chain download {
        type filter hook output priority -200; policy accept;
        # oifname "eth1" ether daddr <MAC> counter comment "bw_<MAC>_down"
    }
}
```

**Why input for upload:** When a client sends traffic, the frame arrives at br0 from eth1. The bridge `input` hook fires because the frame is destined for the bridge interface itself (which has an IP address and acts as gateway). `ether saddr` = client MAC = upload direction.

**Why output for download:** When Pi routes a packet to a client, it goes from IP stack → bridge `output` hook → eth1. `ether daddr` = client MAC = download direction.

### TC Marking (bridge filter input/output chains)

```nft
table bridge accounting {
    chain tc_mark_up {
        type filter hook input priority -200; policy accept;
        iifname "eth1" ether saddr <MAC> meta mark set <MARK> comment "tc_mark_<MAC>_up"
    }
    chain tc_mark_down {
        type filter hook output priority -200; policy accept;
        oifname "eth1" ether daddr <MAC> meta mark set <MARK> comment "tc_mark_<MAC>_down"
    }
}
```

**Mark preservation note (LOW confidence):** The SKB mark field is part of the socket buffer and persists across netfilter hooks within the same packet's lifecycle. Marks set in bridge hooks should be visible to subsequent TC qdiscs on eth1. However, this was not definitively verified in official documentation — the BRIDGE_ISOLATION_PLAN.md explicitly states "TC qdisc changes are NOT needed", implying marks set at bridge input/output are seen by the HTB qdiscs on eth1/eth0. This matches general Linux networking behavior (SKB mark is persistent), but validate with a post-transition bandwidth limit test.

### NAT / MASQUERADE (inet nat postrouting — unchanged)

```nft
table inet nat {
    chain postrouting {
        type nat hook postrouting priority 100; policy accept;
        ip saddr 192.168.1.0/24 ip daddr != 192.168.1.0/24 masquerade comment "bridge_lan_masq"
    }
}
```

This table is already present in TonbilAiOS and requires no migration — NAT lives in inet family and was always processed by the IP routing stack, not the bridge forward path.

---

## br_netfilter — The Critical Module

### What It Does

`br_netfilter` makes the kernel "pretend" that bridged frames are being routed. This causes bridged packets to pass through the IP stack's Netfilter hooks (ip family prerouting, forward, postrouting). This is a legacy compatibility shim for iptables-based bridge firewalls.

### Why NOT to Load It in This Project

1. It creates double-processing: packets would hit both bridge hooks AND inet/ip hooks
2. nftables bridge family (kernel 5.3+) provides native bridge filtering with conntrack — br_netfilter is not needed
3. If loaded, `net.bridge.bridge-nf-call-iptables` becomes available; if accidentally set to 1, it would route all bridge frames through inet nftables rules — potentially matching existing firewall rules unexpectedly
4. The kernel documentation explicitly says: "br_netfilter is a legacy feature... its use is discouraged"

### Detection

```bash
lsmod | grep br_netfilter  # should return empty after transition
sysctl net.bridge.bridge-nf-call-iptables 2>/dev/null  # should fail: key not found
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| nftables bridge family forward hook DROP | ebtables drop rule | Never — ebtables is deprecated on Debian 12 (Bookworm); nftables bridge family is the direct replacement |
| nftables bridge family forward hook DROP | `bridge link set dev eth1 isolated on` (VLAN isolation) | Only if VLAN-aware bridging is configured; most efficient method but requires bridge vlan_filtering=1 which may not be set on Pi |
| nftables bridge family forward hook DROP | tc ingress matchall DROP on br0 | Alternative that works regardless of nftables; simpler but loses ability to use nftables rules for exceptions |
| `inet nat postrouting masquerade` | `bridge postrouting srcnat` | Never — bridge family does not support nat chain type; srcnat in bridge context is still filter type and cannot perform real NAT |
| sysctl.d persistent file | Writing to /etc/sysctl.conf | Use sysctl.d — cleaner, modular, avoids merge conflicts with system defaults |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `table bridge nat` or `bridge postrouting nat` | Bridge family only supports filter chain type; attempting to create a nat chain in bridge table fails with an error | `table inet nat` with postrouting hook |
| Loading `br_netfilter` module | Causes bridged traffic to double-process through ip/inet nftables rules; creates unpredictable interactions with existing firewall rules | Do not load — use nftables bridge family natively |
| `nft add chain bridge accounting per_device` with forward hook (old pattern) | After L2 isolation, forward hook never fires for LAN↔WAN traffic; counters never increment | Replace with `upload` (input hook) and `download` (output hook) chains |
| `nft add chain bridge accounting tc_mark` with forward hook (old pattern) | Same reason — forward hook dead for isolated traffic | Replace with `tc_mark_up` (input hook) and `tc_mark_down` (output hook) |
| Setting `net.bridge.bridge-nf-call-iptables=1` | Enables legacy path that interferes with native bridge filtering | Leave at 0 (default when br_netfilter not loaded) |
| `priority 0` in bridge family chains | Value 0 = NF_BR_PRI_BRNF, the br_netfilter interception point; can cause ordering conflicts | Use `-200` (filter priority) for accounting/marking chains |

---

## Stack Patterns by Variant

**If br_netfilter is currently loaded on the Pi:**
- Unload it with `modprobe -r br_netfilter` before applying isolation rules
- Remove any `net.bridge.bridge-nf-call-*` entries from sysctl files
- Because it causes bridge traffic to also hit inet/ip rules, potentially breaking existing firewall logic

**If the bridge table named `masquerade_fix` exists (old TonbilAiOS MAC-rewrite):**
- Delete it: `nft delete table bridge masquerade_fix`
- Because router mode sends packets from Pi's own IP/MAC; modem sees Pi's MAC directly; MAC rewriting is not only unnecessary but would cause incorrect source MACs on WAN

**If accounting chain migration fails (old forward chain still running):**
- The old forward chain receives no traffic after isolation — counters freeze at last value before transition
- This is a silent failure: bandwidth monitoring appears operational but shows stale data
- Detection: check if counters increment after traffic; if not, the chain was not migrated

**If TC marks do not survive bridge→IP stack transition:**
- Fallback: move TC marking to `inet mangle` forward hook using ip saddr/daddr instead of ether saddr/daddr
- This works because after isolation, all traffic is routed through IP stack and inet forward fires
- Cost: loses per-device tracking for devices with same IP but different MAC (edge case)

---

## Version Compatibility

| Kernel Feature | Min Kernel | Raspberry Pi OS Version | Notes |
|----------------|-----------|------------------------|-------|
| nftables bridge family | 3.18 | Any current Pi OS | Basic bridge filtering |
| Bridge conntrack (kernel-native, replaces br_netfilter) | 5.3 | Pi OS Bullseye (5.10) or later | Needed for stateful bridge filtering |
| inet family NAT | 5.2 | Pi OS Bullseye (5.10) or later | Already used in TonbilAiOS |
| Bridge input/output hooks | 4.x | All current Pi OS | Standard hooks |
| meta mark in bridge chains | 3.14 | All current Pi OS | mark set works in bridge filter |

Raspberry Pi OS Bookworm (current) ships kernel 6.1+. All features above are available.

---

## Installation

No new packages required. All technologies are already present on the Pi:

```bash
# Verify nft version
nft --version  # should be >= 0.9.3 for bridge conntrack support

# Verify kernel version
uname -r  # should be >= 5.3

# Verify br_netfilter is NOT loaded (desired state)
lsmod | grep br_netfilter  # expect: empty output

# Apply persistent sysctl
sudo tee /etc/sysctl.d/99-bridge-isolation.conf > /dev/null << 'EOF'
net.ipv4.ip_forward=1
net.ipv4.conf.all.send_redirects=0
net.ipv4.conf.br0.send_redirects=0
EOF
sudo systemctl restart systemd-sysctl
```

---

## Sources

- [nftables wiki — Bridge filtering](https://wiki.nftables.org/wiki-nftables/index.php/Bridge_filtering) — hook types, chain types, conntrack kernel version (HIGH confidence)
- [nftables wiki — Netfilter hooks](https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks) — bridge family priority table, NF_BR_PRI constants (HIGH confidence)
- [nftables wiki — Nftables families](https://wiki.nftables.org/wiki-nftables/index.php/Nftables_families) — filter-only bridge family, no conntrack note (HIGH confidence)
- [nftables wiki — Configuring chains](https://wiki.nftables.org/wiki-nftables/index.php/Configuring_chains) — chain type support matrix per family (HIGH confidence)
- [nftables wiki — Performing NAT](https://wiki.nftables.org/wiki-nftables/index.php/Performing_Network_Address_Translation_(NAT)) — inet nat support since kernel 5.2, masquerade only in postrouting (HIGH confidence)
- [nft manpage — netfilter.org](https://www.netfilter.org/projects/nftables/manpage.html) — bridge priority values, reject statement hook restriction (HIGH confidence)
- [Vincent Bernat — Proper isolation of a Linux bridge (2017)](https://vincent.bernat.ch/en/blog/2017-linux-bridge-isolation) — br_netfilter ordering, VLAN filtering approach, sysctl.conf issue (MEDIUM confidence — older but technically accurate)
- [libvirt wiki — net.bridge.bridge-nf-call](https://wiki.libvirt.org/Net.bridge.bridge-nf-call_and_sysctl.conf.html) — boot-order problem, why to disable br_netfilter (MEDIUM confidence)
- [Linux kernel docs — Ethernet Bridging](https://docs.kernel.org/networking/bridge.html) — br_netfilter is legacy, discouraged (HIGH confidence)
- [DataDog security rules — send_redirects](https://docs.datadoghq.com/security/default_rules/xccdf-org-ssgproject-content-rule-sysctl-net-ipv4-conf-all-send-redirects/) — send_redirects=0 for router mode (MEDIUM confidence)
- [nftables wiki — Classification to TC structure](https://wiki.nftables.org/wiki-nftables/index.php/Classification_to_tc_structure_example) — TC marking uses ip family filter hook, not bridge (MEDIUM confidence, suggests fallback approach)
- Mark preservation across bridge→inet families: NOT definitively documented in official sources (LOW confidence — treat as hypothesis requiring post-transition validation)

---

*Stack research for: TonbilAiOS bridge isolation milestone*
*Researched: 2026-02-25*
