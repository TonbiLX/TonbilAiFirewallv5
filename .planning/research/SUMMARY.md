# Project Research Summary

**Project:** TonbilAiOS Bridge Isolation — Transparent Bridge to Router Mode Transition
**Domain:** Linux bridge networking / nftables firewall / Raspberry Pi router
**Researched:** 2026-02-25
**Confidence:** HIGH (core nftables bridge semantics from official docs; br_netfilter sysctl ordering from confirmed community post-mortems; codebase inspected directly)

## Executive Summary

TonbilAiOS is being migrated from transparent bridge mode (modem sees all LAN device MACs) to proper router mode (modem sees only Pi's MAC). This is achieved by dropping L2 forwarding in the nftables bridge family's `forward` hook, enabling NAT MASQUERADE in the `inet nat postrouting` hook, and enabling IP forwarding so the Pi's routing stack handles all LAN-to-WAN traffic. The transition is a carefully ordered sequence of 5 phases — the ordering is non-negotiable because each phase depends on the previous one, and applying steps out of order causes connectivity loss or silent accounting failures.

The most important architectural insight from the research is the hook migration: after L2 forwarding is dropped, the `bridge forward` hook never fires for LAN traffic. All bandwidth accounting and TC mark chains that were on the `forward` hook must be recreated on the `input` hook (upload, LAN→Pi) and `output` hook (download, Pi→LAN). This is a mandatory rewrite of `linux_nftables.py` accounting functions and `linux_tc.py` mark functions. The NAT and firewall rules in the `inet` family require no changes — they already operate at the routing layer and will receive more traffic after isolation, not less.

The top risk is loss of SSH connectivity during the transition. The Pi is only reachable via a jump host at `pi.tonbil.com:2323`, and if the transition is applied in the wrong order (isolation drop before MASQUERADE and ip_forward are confirmed), the SSH path to the Pi can drop with no remote recovery. The mitigation is strict step ordering (ip_forward → br_netfilter → MASQUERADE → verify → drop rules → accounting migration → TC migration → lifespan swap → DHCP change) and pre-staging a rollback script at `/tmp/rollback.sh` on the Pi before starting. All other pitfalls — silent accounting failures, sysctl loss after reboot, DHCP gateway disconnect — are medium severity and recoverable if the transition checklist is followed.

## Key Findings

### Recommended Stack

No new packages are required. All necessary kernel features are already present on Raspberry Pi OS Bookworm (kernel 6.1+). The stack consists of nftables bridge family (`filter` chain type, `forward`/`input`/`output` hooks) for L2 isolation, dropping, and MAC-based accounting; `inet nat` (already used by TonbilAiOS) for MASQUERADE; and sysctl.d for persistent kernel parameter management. The `br_netfilter` module must be loaded and `net.bridge.bridge-nf-call-iptables=1` must be set so bridge-traversing packets also reach the inet Netfilter hooks (required for existing `inet tonbilai forward` MAC-block rules to see LAN traffic after isolation).

**Core technologies:**
- **nftables bridge family, forward hook:** L2 isolation — drop all eth1↔eth0 frame forwarding; only option (ebtables is deprecated on Debian 12)
- **nftables bridge family, input/output hooks:** Bandwidth accounting and TC marking after isolation kills the forward path; these hooks fire when packets enter/exit the Pi's IP stack
- **nftables inet family, nat postrouting:** MASQUERADE — already present; requires only LAN subnet confirmation; bridge family cannot do NAT
- **br_netfilter module + bridge-nf-call-iptables=1:** Forces bridged frames to also pass inet hooks; required for existing MAC-based blocking in `inet tonbilai forward` to remain functional after isolation
- **sysctl.d (99-bridge-isolation.conf):** Persistent ip_forward, send_redirects=0; must also add `br_netfilter` to `/etc/modules-load.d/` for correct boot-time load order
- **`nft -f -` stdin mode:** Atomic rule application — both drop directions must be added in one transaction to avoid asymmetric isolation window

**Critical version note:** Bridge conntrack (native, without br_netfilter) requires kernel 5.3+. Pi OS Bookworm has kernel 6.1+. All features are available.

### Expected Features

Research identified 11 mandatory (P1) features for a functional transition, 4 robustness features (P2), and 3 deferred features (P3/v2+).

**Must have (table stakes — P1):**
- Bridge L2 forward drop (both eth1→eth0 and eth0→eth1) — core isolation
- br_netfilter load + bridge-nf-call-iptables=1 — without this, MASQUERADE is a no-op for LAN traffic
- ip_forward=1 (verified and persisted) — prerequisite for any routing
- NAT MASQUERADE rule for LAN subnet (192.168.1.0/24) — internet access for LAN devices
- Remove bridge masquerade_fix table — old MAC rewrite conflicts with router mode
- ICMP redirect disable (all + br0) — prevents Pi from telling clients to bypass it
- Bridge accounting hook migration: forward → input (upload) + output (download) — counters go dead without this
- TC mark chain migration: forward → input (tc_mark_up) + output (tc_mark_down) — bandwidth limiting goes dead without this
- main.py lifespan swap (ensure_bridge_masquerade → ensure_bridge_isolation) — every backend restart undoes transition otherwise
- DHCP gateway change (.1 → .2) using short-lease pre-staging
- sysctl persistence + nftables persistence (rulesets survive reboot)

**Should have (robustness — P2):**
- Software rollback function `remove_bridge_isolation()` — must be pre-staged before transition starts
- Validation test suite (7-step checklist from BRIDGE_ISOLATION_PLAN.md)
- Atomic nftables rule application via `nft -f -`
- Per-interface ICMP redirect disable (eth0 in addition to all + br0)

**Defer (v2+):**
- Counter value preservation during hook migration (prevents cosmetic counter-reset in dashboard)
- DHCP lease force-renewal (most home users tolerate natural expiry)
- Conntrack flush after gateway change (causes TCP RST storm; must be user-triggered)
- Mode status API endpoint (low value; mode detectable by checking for bridge_isolation comment in ruleset)

**Anti-features (do not implement):**
- Remove bridge entirely (br0 is needed for MAC-based accounting)
- VLAN segmentation in this milestone (separate milestone)
- UI toggle for bridge/router mode (one-way migration; toggle creates false parity impression)
- IPv6 NAT66 (unnecessary, non-standard for this topology)

### Architecture Approach

The transition changes the packet path for LAN traffic from pure L2 bridging (forward hook only, Pi's IP stack not involved) to full L3 routing (IP stack routes all packets, bridge hooks see only ingress/egress on eth1). This keeps br0 in place as the network interface for MAC visibility — removing br0 would require changes to 5+ subsystems. The bridge family handles MAC-layer concerns (accounting, TC marking, L2 isolation). The inet family handles IP-layer concerns (NAT, device blocking, VPN, DDoS). These two domains do not overlap for LAN↔WAN flows after isolation.

**Major components and required changes:**
1. **`hal/linux_nftables.py` — isolation + accounting** — Add `ensure_bridge_isolation()` and `remove_bridge_isolation()`; rewrite `ensure_bridge_accounting_chain()`, `add_device_counter()`, `remove_device_counter()`, `read_device_counters()`, `sync_device_counters()` to target upload/download chains on input/output hooks instead of per_device on forward hook
2. **`hal/linux_tc.py` — TC mark chains** — Rewrite `_ensure_tc_mark_chain()`, `add_device_limit()`, `remove_device_limit()`, `_remove_nft_mark_rule()` to target tc_mark_up/tc_mark_down chains on input/output hooks; HTB qdisc setup on eth0/eth1 unchanged
3. **`main.py` lifespan()** — One-line swap from `ensure_bridge_masquerade` to `ensure_bridge_isolation`; `_restore_bandwidth_limits()` call unchanged (it uses TC functions which will reference new chain names)
4. **DHCP config (dnsmasq + DB)** — Update dhcp-option=3 from .1 to .2; update dhcp_pools.gateway in MariaDB; short-lease pre-staging required
5. **sysctl.d + modules-load.d** — Create `/etc/sysctl.d/99-bridge-isolation.conf`; add `br_netfilter` to `/etc/modules-load.d/`; verify nftables.service is enabled

**Components unaffected:** inet tonbilai (DDoS, device block, VPN forward), inet nat prerouting (DNS redirect), WireGuard wg0, dns_proxy.py, flow_tracker.py, traffic_monitor.py, device_discovery.py, TC HTB qdiscs on eth0/eth1, Telegram, AI workers.

**Critical coupling risk:** `linux_tc.py` adds TC mark chains to the `bridge accounting` table owned by `linux_nftables.py`. Both files must agree on chain names. Recommendation: make `ensure_bridge_accounting_chain()` in linux_nftables.py responsible for creating ALL chains in the table (upload, download, tc_mark_up, tc_mark_down) so there is a single authoritative setup point.

### Critical Pitfalls

1. **SSH lockout during transition** — If isolation drop rules are applied before ip_forward=1 and MASQUERADE are confirmed working, Pi's routing breaks and the SSH jump host connection drops with no remote recovery path. Prevention: strict ordering (ip_forward → br_netfilter → MASQUERADE → verify curl works → drop rules); pre-stage `/tmp/rollback.sh` on Pi; use tmux session.

2. **Accounting counters silently drop to zero** — After hook migration to input/output, if br_netfilter is not loaded or ip_forward is not set, LAN traffic never reaches the input/output hooks. Counter values freeze at zero — indistinguishable from "no traffic" in backend logs because `check=False` is used on counter reads. Prevention: verify `lsmod | grep br_netfilter` and `sysctl net.ipv4.ip_forward` before applying isolation; watch counters increment in real-time for 30 seconds post-migration as a success gate.

3. **br_netfilter sysctl silently lost after reboot** — `net.bridge.bridge-nf-call-iptables=1` in sysctl.d fails silently at boot if the `br_netfilter` module is not loaded first. The module creates the sysctl namespace; without it, systemd-sysctl logs "unknown key" and skips the setting. Prevention: add `br_netfilter` to `/etc/modules-load.d/br_netfilter.conf` so it loads before systemd-sysctl runs; always verify with an actual reboot.

4. **DHCP gateway change disconnects all active devices** — Changing dnsmasq gateway from .1 to .2 only affects new DHCP leases. Existing leases (24h default) keep .1 as gateway. After isolation, .1 (modem) cannot route back to LAN devices (their MACs are hidden), causing silent internet failure for hours. Prevention: shorten lease time to 5 minutes before the gateway change, wait for full renewal cycle, then change gateway, then restore lease time.

5. **Removing masquerade_fix table before isolation is active breaks existing sessions** — Deleting the MAC rewrite table while LAN traffic still flows through the bridge forward path immediately drops active TCP connections. Prevention: delete masquerade_fix only AFTER isolation drop rules are active and NAT MASQUERADE is verified working; connections have already been disrupted by the drop rules at that point.

6. **nftables ruleset not persisted — isolation disappears on reboot** — If `nftables.service` is not enabled, the ruleset loaded at runtime is lost on reboot. Pi silently reverts to transparent bridge mode. Prevention: verify `systemctl is-enabled nftables`; after transition, reboot Pi and re-check that both bridge_isolation drop rules are present before declaring completion.

## Implications for Roadmap

Based on research, the transition must follow a strict 5-phase sequence. The ordering is driven by hard dependencies discovered in the architecture research — applying phases out of order causes connectivity loss, not just suboptimal behavior.

### Phase 1: nftables HAL — Bridge Isolation Core Functions

**Rationale:** This is the foundation everything else depends on. `ensure_bridge_isolation()` and `remove_bridge_isolation()` must exist and be tested before any live transition step. The rollback path must be validated before the forward path is applied on a live network.
**Delivers:** New HAL functions in `linux_nftables.py` — isolation setup, isolation teardown, MASQUERADE verification, masquerade_fix cleanup; comment-anchored rule pattern for deletion
**Addresses:** Bridge L2 forward drop (P1), software rollback (P2), atomic rule application (P2), remove masquerade_fix (P1), NAT MASQUERADE (P1)
**Avoids:** SSH lockout pitfall (rollback pre-staged), masquerade_fix deletion ordering pitfall
**Research flag:** Standard pattern — well-documented nftables bridge family semantics; no additional research needed

### Phase 2: Bridge Accounting Chain Migration

**Rationale:** After Phase 1 kills L2 forwarding, the existing `per_device forward` chain sees zero traffic. Accounting must be migrated in the same deployment or bandwidth data becomes meaningless. This phase depends on Phase 1 because the input/output hooks only receive LAN traffic after L2 forwarding is dropped.
**Delivers:** Rewritten accounting functions in `linux_nftables.py` — upload chain (input hook, iifname eth1, ether saddr), download chain (output hook, oifname eth1, ether daddr); updated add/remove/read/sync functions; counter verification gate
**Addresses:** Bridge accounting hook migration (P1), counter verification as explicit success gate
**Avoids:** Silent zero-counter pitfall (br_netfilter and ip_forward pre-checks); check=False silent failure pattern (add explicit counter verification)
**Research flag:** Well-documented — the hook semantics are canonical nftables behavior; no additional research needed

### Phase 3: TC Mark Chain Migration

**Rationale:** Same hook dependency as Phase 2 — the `tc_mark forward` chain is dead after isolation. Bandwidth limiting fails silently without this migration. This phase is conceptually parallel to Phase 2 but operates in `linux_tc.py` with shared table dependency.
**Delivers:** Rewritten mark chain functions in `linux_tc.py` — tc_mark_up (input hook), tc_mark_down (output hook); ensures `ensure_bridge_accounting_chain()` in linux_nftables.py owns table creation for all chains to prevent split ownership
**Addresses:** TC mark chain migration (P1), HAL coupling risk (shared bridge accounting table)
**Avoids:** Anti-pattern of hardcoding chain names in both files; ensures HTB qdiscs on eth0/eth1 are not changed (they do not need changes)
**Research flag:** Standard pattern — SKB mark persistence across bridge→inet boundary is documented behavior; LOW confidence gap on mark preservation should be validated with a bandwidth test post-transition

### Phase 4: main.py Lifespan Swap + sysctl/modules Persistence

**Rationale:** This phase is the deployment trigger — changing `ensure_bridge_masquerade` to `ensure_bridge_isolation` in the startup sequence activates router mode on every backend restart. It must come after Phases 1-3 are fully implemented. The sysctl and module-load persistence is bundled here because it is required for reboot resilience and must be applied before the first live test reboot.
**Delivers:** Updated `main.py` lifespan(); `/etc/sysctl.d/99-bridge-isolation.conf` with ip_forward, send_redirects=0; `/etc/modules-load.d/br_netfilter.conf`; verification that nftables.service is enabled; post-reboot rule presence check
**Addresses:** main.py lifespan swap (P1), sysctl persistence (P1), nftables persistence (P1), br_netfilter module persistence (pitfall 5 prevention)
**Avoids:** Reboot regression pitfall; br_netfilter sysctl silently lost pitfall
**Research flag:** Standard pattern — sysctl.d and modules-load.d are standard Debian persistence mechanisms; no research needed

### Phase 5: DHCP Gateway Update

**Rationale:** DHCP gateway change must be last — it directs client traffic to Pi as router, which only works after isolation (Phase 1) and NAT (Phase 1) are live. If done earlier, clients route to Pi without proper NAT and lose internet. The short-lease pre-staging approach is mandatory to avoid multi-hour device disconnection.
**Delivers:** Updated dnsmasq config (dhcp-option=3,192.168.1.2); updated dhcp_pools.gateway in MariaDB; short-lease pre-staging procedure; post-change route table verification on test device
**Addresses:** DHCP gateway change (P1), ICMP redirect disable (all + br0 + eth0)
**Avoids:** DHCP gateway disconnection pitfall; asymmetric routing window
**Research flag:** Standard DHCP operation — no additional research needed; the short-lease pre-staging approach is industry-standard

### Phase Ordering Rationale

- **Phase 1 before all others:** `ensure_bridge_isolation()` is the primitive that everything else depends on. Without it tested, there is no safe way to proceed. The rollback function must be validated before the forward path is applied on a live system.
- **Phases 2 and 3 before Phase 4:** The accounting and TC mark functions must be correct before the lifespan swap activates them on every backend restart. A bad accounting chain setup would silently corrupt bandwidth data on every restart.
- **Phase 5 last:** DHCP gateway change is the only step visible to end users (devices). All kernel-level and backend changes must be stable before directing client traffic through Pi as router.
- **Phases 2 and 3 are technically parallelizable** (different files) but logically sequential (same conceptual problem). Implementing them together is more efficient and reduces the chance of table ownership conflicts.

### Research Flags

Phases needing deeper research during planning:
- **Phase 1 (rollback function):** The `remove_bridge_isolation()` function needs explicit handle-based deletion tested against the actual Pi ruleset. The comment-anchored pattern is correct in theory; validate that the handle numbers are stable after Pi reboots.
- **Phase 2/3 (mark preservation):** The LOW confidence item from STACK.md — TC marks set in bridge input/output hooks surviving to HTB qdiscs on eth1/eth0 — must be validated with an actual bandwidth limit test on the Pi post-transition before declaring Phase 3 complete.

Phases with well-documented standard patterns (no `/gsd:research-phase` needed):
- **Phase 4 (sysctl/modules persistence):** Standard Debian/systemd persistence mechanisms; thoroughly documented
- **Phase 5 (DHCP):** Standard dnsmasq configuration; short-lease pre-staging is established procedure

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core nftables bridge family semantics verified via official nftables wiki and kernel docs; all required features available on Pi OS Bookworm kernel 6.1+ |
| Features | HIGH | Feature set derived from direct codebase inspection of linux_nftables.py, linux_tc.py, main.py, and BRIDGE_ISOLATION_PLAN.md; dependency graph is authoritative |
| Architecture | HIGH | Packet path analysis based on Linux kernel/nftables documented hook behavior + direct code inspection; component boundaries are unambiguous |
| Pitfalls | HIGH | Critical pitfalls (SSH lockout, br_netfilter sysctl boot order, DHCP gateway window) confirmed via kernel docs, GitHub post-mortems, and community reproducers; not theoretical |

**Overall confidence:** HIGH

### Gaps to Address

- **TC mark preservation across bridge→inet transition (LOW confidence):** It is inferred from SKB mark being part of the socket buffer (which survives routing), not definitively confirmed in official docs. Validate with a live bandwidth limit test on a device after Phase 3 is applied. Fallback: move TC marking to `inet mangle forward` hook using IP saddr/daddr if bridge marks do not survive.
- **`inet tonbilai forward` MAC-block behavior after isolation:** Currently, `inet tonbilai forward` sees LAN traffic because br_netfilter routes it through inet hooks. After isolation, LAN traffic reaches inet via routing (not br_netfilter). Validate that the MAC-based device blocking rules in `inet tonbilai forward` still fire correctly for LAN devices after the transition. If br_netfilter is still loaded (required for bridge-nf-call-iptables=1), the behavior should be unchanged.
- **br0 interface naming stability:** Current code hardcodes `eth0`, `eth1`, `br0`. Confirm that Pi OS Bookworm udev rules do not rename these interfaces to `enp*` style names. Set `net.ifnames=0` / `biosdevname=0` in Pi bootconfig if needed.

## Sources

### Primary (HIGH confidence)
- nftables wiki — Bridge filtering: https://wiki.nftables.org/wiki-nftables/index.php/Bridge_filtering
- nftables wiki — Netfilter hooks (priority table): https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks
- nftables wiki — Nftables families (chain type matrix): https://wiki.nftables.org/wiki-nftables/index.php/Nftables_families
- nftables wiki — Performing NAT: https://wiki.nftables.org/wiki-nftables/index.php/Performing_Network_Address_Translation_(NAT)
- Linux kernel docs — Ethernet Bridging (br_netfilter is legacy): https://docs.kernel.org/networking/bridge.html
- nft manpage: https://www.netfilter.org/projects/nftables/manpage.html
- Codebase: `backend/app/hal/linux_nftables.py`, `linux_tc.py`, `main.py`, `BRIDGE_ISOLATION_PLAN.md` (direct inspection)
- ebtables bridge-nf documentation — br_netfilter requirement: https://ebtables.netfilter.org/documentation/bridge-nf.html
- nftables wiki — Configuring chains (priority ordering, drop verdict finality)

### Secondary (MEDIUM confidence)
- Vincent Bernat — Proper isolation of a Linux bridge (2017): https://vincent.bernat.ch/en/blog/2017-linux-bridge-isolation
- libvirt wiki — net.bridge.bridge-nf-call and sysctl.conf boot-order: https://wiki.libvirt.org/Net.bridge.bridge-nf-call_and_sysctl.conf.html
- nftables wiki — Classification to TC structure example (TC marking uses ip family, confirms fallback approach)
- DataDog security rules — send_redirects=0

### Tertiary (LOW confidence — validate during implementation)
- Mark preservation across bridge→inet families: inferred from SKB behavior, not definitively documented
- br_netfilter sysctl persistence: GitHub moby/moby discussion #48559 (multiple reproducers — HIGH community confidence despite being tertiary source)

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
