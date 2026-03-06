# Project Research Summary

**Project:** TonbilAiOS v5 — Bridge Isolation Milestone
**Domain:** Linux bridge-to-router mode transition on Raspberry Pi (nftables, NAT, DHCP)
**Researched:** 2026-02-25
**Confidence:** HIGH

## Executive Summary

TonbilAiOS needs to transition from a transparent bridge (where the modem sees all LAN device MACs) to a proper router mode (where only the Pi's MAC is visible to the modem). This is a well-understood Linux networking pattern: drop L2 forwarding at the bridge level, force all traffic through the Pi's IP stack, and use MASQUERADE NAT for outbound traffic. The nftables bridge family provides all necessary hooks for this transition without requiring any new packages — everything is already available on the Pi's kernel (6.1+, Bookworm).

The recommended approach has a strict 5-phase ordering driven by hard dependencies: (1) create isolation drop rules + NAT, (2) migrate bandwidth accounting chains from the dead `forward` hook to `input/output` hooks, (3) migrate TC marking chains similarly, (4) swap the backend startup function + persistence, (5) change DHCP gateway from .1 to .2. Deviating from this order causes silent failures — most dangerously, accounting counters that read zero without any error, or SSH lockout that requires physical Pi access to recover.

The primary risks are: SSH lockout during the transition window (mitigated by strict step ordering and a pre-staged rollback script), silent accounting failure if `br_netfilter` or `ip_forward` is not active (mitigated by mandatory counter verification gates), and DHCP gateway change disconnecting all devices for hours (mitigated by a short-lease pre-staging technique). Mark preservation across bridge-to-inet family boundaries is the only LOW-confidence area and requires post-transition validation.

## Key Findings

### Recommended Stack

No new packages are required. All necessary kernel features are already present on Raspberry Pi OS Bookworm (kernel 6.1+). The stack consists of nftables bridge family (`filter` chain type, `forward`/`input`/`output` hooks) for L2 isolation, dropping, and MAC-based accounting; `inet nat` (already used by TonbilAiOS) for MASQUERADE; and sysctl.d for persistent kernel parameter management.

**Core technologies:**
- **nftables bridge family (forward hook):** L2 forwarding drop rules — the core isolation mechanism; ebtables is deprecated on Debian 12
- **nftables bridge family (input/output hooks):** Bandwidth accounting and TC mark replacement chains — mandatory because forward hook is dead after isolation
- **nftables inet family (nat):** MASQUERADE for LAN traffic — already present in TonbilAiOS, no changes needed
- **br_netfilter module:** Required so bridged frames also traverse inet hooks for MAC-based blocking in `inet tonbilai forward`
- **sysctl.d (99-bridge-isolation.conf):** ip_forward=1, send_redirects=0 — must survive reboots
- **`nft -f -` stdin mode:** Atomic rule application — both drop directions must be added in one transaction

**Critical version note:** Bridge family priority keyword `filter` maps to -200, not 0 as in inet family. This is a known difference, not a bug.

### Expected Features

**Must have (table stakes — P1):**
- Bridge L2 forward drop (both directions, atomic) — core isolation
- br_netfilter load + bridge-nf-call-iptables=1 — without this, MASQUERADE is a no-op
- ip_forward=1 (verified + persisted) — prerequisite for routing
- NAT MASQUERADE for LAN subnet — internet access for LAN devices
- Remove old masquerade_fix MAC rewrite table — conflicts with router mode
- ICMP redirect disable (all + br0 + eth0) — prevents clients bypassing Pi
- Bridge accounting hook migration (forward to input/output) — counters go dead otherwise
- TC mark chain migration (forward to input/output) — bandwidth limiting goes dead otherwise
- main.py lifespan swap — every backend restart undoes transition otherwise
- DHCP gateway change (.1 to .2) — clients must route through Pi
- sysctl + nftables persistence — reboot resilience

**Should have (robustness — P2):**
- Software rollback function (remove_bridge_isolation) — pre-staged before transition
- Validation test suite (7-step post-transition check)
- Atomic nftables rule application via `nft -f -`
- Mode status API endpoint

**Defer (v2+):**
- Counter value preservation during hook migration (HIGH effort, cosmetic benefit)
- DHCP lease force-renewal (most clients tolerate natural expiry)
- Conntrack flush after gateway change (causes TCP RST storm)
- VLAN segmentation, IPv6 NAT, UI bridge/router toggle

### Architecture Approach

The transition keeps br0 as the bridge interface but kills L2 forwarding between its ports, forcing all LAN-WAN traffic through the Pi's IP routing stack. Bridge family hooks handle MAC-layer concerns (accounting, TC marking) while inet family hooks handle IP-layer concerns (filtering, NAT, VPN). Both families remain active and do not overlap for LAN-WAN flows.

**Major components:**
1. **bridge filter forward** — DROP rules enforcing isolation (NEW)
2. **bridge accounting upload/download** — MAC-based byte counters on input/output hooks (REWRITE from single forward-hook chain)
3. **bridge accounting tc_mark_up/tc_mark_down** — SKB mark assignment on input/output hooks (REWRITE)
4. **inet nat postrouting** — MASQUERADE for LAN subnet (UNCHANGED)
5. **ensure_bridge_isolation()** in linux_nftables.py — HAL function orchestrating all kernel-level changes (NEW)

**Key pattern:** Comment-anchored rule identification. Every nftables rule carries a unique comment for targeted deletion via handle lookup.

**Critical coupling risk:** linux_tc.py adds TC mark chains to the `bridge accounting` table owned by linux_nftables.py. Both files must agree on chain names. Recommendation: make ensure_bridge_accounting_chain() own ALL chain creation.

### Critical Pitfalls

1. **SSH lockout during transition** — Wrong step ordering kills the only remote access path. Apply MASQUERADE before drop rules. Pre-stage rollback script. Use tmux.
2. **Silent accounting death** — After hook migration, if br_netfilter or ip_forward is missing, counters read zero with no error (check=False pattern). Must verify counter increment within 5 seconds as success gate.
3. **DHCP gateway change disconnects all devices** — Existing leases keep old gateway for up to 24h. Use short-lease pre-staging: reduce to 5min, wait, change gateway, restore.
4. **br_netfilter sysctl lost after reboot** — Module must be in /etc/modules-load.d/ so it loads before systemd-sysctl. Without this, bridge-nf-call-iptables silently fails.
5. **Removing masquerade_fix before NAT active** — Breaks all existing TCP sessions. Delete AFTER isolation drop + NAT verified.
6. **nftables rules not persisted** — nftables.service must be enabled. Post-reboot verification mandatory.

## Implications for Roadmap

Based on research, the transition must follow a strict 5-phase dependency chain. Applying phases out of order causes connectivity loss, not just suboptimal behavior.

### Phase 1: Bridge Isolation Core Functions
**Rationale:** Foundation for everything. ensure_bridge_isolation() and remove_bridge_isolation() must exist and be tested before any live transition. Rollback path validated before forward path.
**Delivers:** New HAL functions in linux_nftables.py — isolation setup, teardown, MASQUERADE verification, masquerade_fix cleanup
**Addresses:** L2 forward drop, NAT MASQUERADE, br_netfilter, ICMP redirect disable, masquerade_fix removal, software rollback
**Avoids:** SSH lockout (correct step ordering), masquerade_fix deletion ordering

### Phase 2: Bandwidth Accounting Chain Migration
**Rationale:** After Phase 1 kills L2 forwarding, the existing per_device forward chain sees zero traffic. Must migrate in same deployment or bandwidth data becomes meaningless.
**Delivers:** Rewritten accounting functions — upload chain (input hook, iifname eth1, ether saddr), download chain (output hook, oifname eth1, ether daddr); add/remove/read/sync functions; counter verification gate
**Addresses:** Bridge accounting hook migration (5+ function rewrites in linux_nftables.py)
**Avoids:** Silent zero-counter pitfall (mandatory counter increment verification)

### Phase 3: TC Marking Chain Migration
**Rationale:** Same hook dependency as Phase 2. TC marks on dead forward hook mean bandwidth limiting fails silently. Follows identical pattern to Phase 2.
**Delivers:** Rewritten mark chain functions in linux_tc.py — tc_mark_up (input hook), tc_mark_down (output hook); unified table ownership with linux_nftables.py
**Addresses:** TC mark chain migration, HAL coupling risk (shared bridge accounting table)
**Avoids:** Hardcoded chain name duplication anti-pattern; unnecessary HTB qdisc changes

### Phase 4: Backend Startup Swap + Persistence
**Rationale:** Deployment trigger. One-line swap in main.py activates router mode on every restart. Must come after Phases 1-3 are complete. Persistence bundled here for reboot resilience.
**Delivers:** Updated main.py lifespan(); /etc/sysctl.d/99-bridge-isolation.conf; /etc/modules-load.d/br_netfilter.conf; nftables.service enabled verification
**Addresses:** main.py lifespan swap, sysctl persistence, nftables persistence, br_netfilter module persistence
**Avoids:** Reboot regression, br_netfilter sysctl silently lost

### Phase 5: DHCP Gateway Update + Live Deployment
**Rationale:** Must be last. Directs client traffic to Pi as router, which only works after isolation + NAT are live. Short-lease pre-staging mandatory.
**Delivers:** Updated dnsmasq config (gateway .2); dhcp_pools.gateway in MariaDB; post-change verification
**Addresses:** DHCP gateway change, validation test suite execution
**Avoids:** Multi-hour device disconnection (short-lease pre-staging), asymmetric routing window

### Phase Ordering Rationale

- **Phase 1 first:** ensure_bridge_isolation() is the primitive everything depends on. Rollback must be validated before forward path applied on live network.
- **Phases 2-3 before Phase 4:** Accounting and TC functions must be correct before lifespan swap activates them on every restart.
- **Phase 5 last:** Only step visible to end users. All kernel and backend changes must be stable first.
- **Phases 2-3 parallelizable:** Different files, same pattern. Implementing together reduces table ownership conflict risk.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2/3:** The LOW-confidence mark preservation gap — TC marks set in bridge input/output hooks surviving to HTB qdiscs — must be validated with actual bandwidth test on Pi post-transition. If marks fail, fallback to inet mangle forward with IP-based matching.
- **Phase 1 (rollback):** remove_bridge_isolation() handle-based deletion needs validation against actual Pi ruleset.

Phases with standard patterns (skip research-phase):
- **Phase 4:** Standard Debian sysctl.d and modules-load.d persistence. No ambiguity.
- **Phase 5:** Standard dnsmasq configuration. Short-lease pre-staging is established procedure.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | nftables bridge family hooks/priorities verified via official wiki; all features on Pi OS Bookworm 6.1+ |
| Features | HIGH | Feature set from codebase inspection + BRIDGE_ISOLATION_PLAN.md; dependency graph verified against hook semantics |
| Architecture | HIGH | Packet paths verified against kernel/nftables docs + direct code inspection; component boundaries unambiguous |
| Pitfalls | HIGH | SSH lockout, br_netfilter boot order, DHCP gateway window confirmed via kernel docs and community post-mortems |

**Overall confidence:** HIGH

### Gaps to Address

- **TC mark preservation across bridge-to-inet (LOW confidence):** Inferred from SKB mark behavior, not definitively documented. Validate with live bandwidth limit test after Phase 3. Fallback: move TC marking to `inet mangle forward` using IP addresses.
- **inet tonbilai forward MAC-block after isolation:** Currently fires via br_netfilter. After isolation, traffic reaches inet via routing. Validate MAC-based device blocking still works. Should be fine if br_netfilter remains loaded.
- **br0/eth0/eth1 naming stability:** Code hardcodes interface names. Confirm Pi OS Bookworm udev does not rename to enp* style. Set net.ifnames=0 if needed.
- **Shared table ownership (linux_nftables.py vs linux_tc.py):** Both create chains in `bridge accounting`. Must centralize chain creation during Phase 2/3 implementation.

## Sources

### Primary (HIGH confidence)
- nftables wiki — Bridge filtering, Netfilter hooks, Configuring chains, Performing NAT, Nftables families
- nft manpage — netfilter.org (bridge priority values, drop verdict finality)
- Linux kernel docs — Ethernet Bridging (br_netfilter is legacy)
- ebtables bridge-nf documentation — br_netfilter requirement
- Codebase: linux_nftables.py, linux_tc.py, main.py, BRIDGE_ISOLATION_PLAN.md

### Secondary (MEDIUM confidence)
- Vincent Bernat — Proper isolation of a Linux bridge (2017, concepts stable)
- libvirt wiki — net.bridge.bridge-nf-call sysctl boot-order problem
- nftables wiki — Classification to TC structure (fallback TC marking approach)
- Thermalcircle — nftables packet flow and Netfilter hooks

### Tertiary (LOW confidence — validate during implementation)
- Mark preservation across bridge-to-inet families — inferred from SKB behavior, not definitively documented
- GitHub moby/moby discussion #48559 — br_netfilter module-load timing (HIGH community confidence despite tertiary source)

---
*Research completed: 2026-02-25*
*Ready for roadmap: yes*
