# Roadmap: TonbilAiOS Bridge Isolation

## Overview

TonbilAiOS is being migrated from transparent bridge mode (modem sees all LAN device MACs) to proper router mode (modem sees only Pi's MAC). The transition modifies `linux_nftables.py`, `linux_tc.py`, `main.py`, dnsmasq config, and kernel persistence files across 5 strictly ordered phases. Ordering is non-negotiable: each phase is a hard prerequisite for the next. The NAT and IP forwarding foundation must exist before isolation drop rules are applied; accounting and TC mark chains must be migrated before the lifespan swap activates them on every restart; DHCP gateway is changed last so clients never route through Pi before routing is proven working.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Bridge Isolation Core** - HAL functions for L2 isolation, NAT MASQUERADE, masquerade_fix removal, and software rollback
- [x] **Phase 2: Accounting Chain Migration** - Rewrite bridge accounting from forward hook to input/output hooks
- [ ] **Phase 3: TC Mark Chain Migration** - Rewrite TC mark chains from forward hook to input/output hooks
- [ ] **Phase 4: Startup and Persistence** - Lifespan swap, sysctl persistence, module persistence, nftables persistence
- [ ] **Phase 5: DHCP Gateway and Validation** - Gateway change from .1 to .2 and 7-step transition validation

## Phase Details

### Phase 1: Bridge Isolation Core
**Goal**: The HAL contains tested functions to apply and safely reverse bridge isolation — isolation can be activated and rolled back without SSH lockout
**Depends on**: Nothing (first phase)
**Requirements**: ISOL-01, ISOL-02, ISOL-03, ISOL-04, ISOL-05, ISOL-06, ISOL-07, ROLL-01, ROLL-02, ROLL-03
**Success Criteria** (what must be TRUE):
  1. `ensure_bridge_isolation()` applies L2 forward drop rules atomically via `nft -f -` and can be called idempotently without error
  2. Running `ensure_bridge_isolation()` followed by `curl` from a Pi shell confirms internet access (NAT MASQUERADE and ip_forward are working)
  3. `remove_bridge_isolation()` removes all isolation rules by handle and restores ICMP redirects, returning the system to transparent bridge mode
  4. The `bridge_masquerade_fix` table is absent from the nftables ruleset after isolation is applied
  5. All six sysctl values (ip_forward, send_redirects on all interfaces, bridge-nf-call-iptables) are set correctly and verified before drop rules are applied
**Plans**: 1 plan

Plans:
- [x] 01-01-PLAN.md — Add ensure_bridge_isolation() and remove_bridge_isolation() to linux_nftables.py

### Phase 2: Accounting Chain Migration
**Goal**: Bridge bandwidth counters correctly accumulate on the input/output hooks so device traffic accounting works after L2 forwarding is disabled
**Depends on**: Phase 1
**Requirements**: ACCT-01, ACCT-02, ACCT-03, ACCT-04, ACCT-05, ACCT-06, ACCT-07
**Success Criteria** (what must be TRUE):
  1. `ensure_bridge_accounting_chain()` creates `upload` (input hook, iifname eth1, ether saddr) and `download` (output hook, oifname eth1, ether daddr) chains in the bridge accounting table
  2. `add_device_counter(mac)` adds counter rules to both upload and download chains for the given MAC
  3. `remove_device_counter(mac)` removes counter rules from both chains without affecting other devices
  4. `read_device_counters()` returns merged upload and download byte totals per MAC from both chains
  5. Counter byte values increase when a device sends and receives traffic after isolation is active
**Plans**: 1 plan

Plans:
- [x] 02-01-PLAN.md — Rewrite accounting chain functions in linux_nftables.py + update bandwidth_monitor.py for nft-reset semantics

### Phase 3: TC Mark Chain Migration
**Goal**: Per-device bandwidth limits remain enforced after isolation because TC mark chains operate on the input/output hooks where LAN traffic now flows
**Depends on**: Phase 2
**Requirements**: TCMK-01, TCMK-02, TCMK-03, TCMK-04, TCMK-05
**Success Criteria** (what must be TRUE):
  1. `tc_mark_up` chain exists on the input hook (iifname eth1, ether saddr MAC, meta mark set) and `tc_mark_down` chain exists on the output hook (oifname eth1, ether daddr MAC, meta mark set)
  2. `add_device_limit(mac, rate, ceil)` adds mark rules to both tc_mark_up and tc_mark_down chains
  3. `remove_device_limit(mac)` removes mark rules from both chains without affecting other devices
  4. A device with a 5 Mbps limit cannot sustain above 5 Mbps download after isolation is active (live bandwidth test confirms HTB qdisc enforces the mark)
**Plans**: 1 plan

Plans:
- [ ] 03-01-PLAN.md — Rewrite _ensure_tc_mark_chain(), add_device_limit(), and _remove_nft_mark_rule() in linux_tc.py for split tc_mark_up/tc_mark_down chains on input/output hooks

### Phase 4: Startup and Persistence
**Goal**: The router mode configuration survives backend restarts and Pi reboots — no manual intervention is needed to re-apply isolation after a restart
**Depends on**: Phase 3
**Requirements**: STRT-01, STRT-02, STRT-03, STRT-04
**Success Criteria** (what must be TRUE):
  1. `main.py` lifespan calls `ensure_bridge_isolation()` instead of `ensure_bridge_masquerade()` on backend startup
  2. After `sudo reboot`, the nftables ruleset contains the bridge_isolation forward drop rules (verified via `nft list ruleset`)
  3. After reboot, `sysctl net.ipv4.ip_forward` returns 1 and `sysctl net.bridge.bridge-nf-call-iptables` returns 1
  4. `lsmod | grep br_netfilter` shows the module loaded immediately after boot without manual modprobe
**Plans**: TBD

Plans:
- [ ] 04-01: Update main.py lifespan and write sysctl.d/modules-load.d persistence files

### Phase 5: DHCP Gateway and Validation
**Goal**: All LAN devices use Pi as their default gateway and the complete transition is verified end-to-end — the modem ARP table shows only Pi's MAC
**Depends on**: Phase 4
**Requirements**: DHCP-01, DHCP-02, VALD-01, VALD-02, VALD-03, VALD-04, VALD-05, VALD-06, VALD-07
**Success Criteria** (what must be TRUE):
  1. dnsmasq config contains `dhcp-option=3,192.168.1.2` and dhcp_pools.gateway in MariaDB is `192.168.1.2`
  2. `tcpdump -i eth0 arp` on the Pi shows only Pi's own MAC in ARP replies toward the modem
  3. A test device connected to the LAN can reach the internet (curl https://example.com succeeds) after receiving a new DHCP lease with gateway .2
  4. DNS resolution works from a LAN device (dig @192.168.1.2 example.com returns a valid answer)
  5. Bridge accounting upload/download counters increment for the test device during the internet test
  6. `nft list chain bridge filter forward` shows the eth1→eth0 and eth0→eth1 drop rules
  7. A veth namespace test device using gateway 192.168.1.2 can reach the internet, confirming routing works for new clients
**Plans**: TBD

Plans:
- [ ] 05-01: Update DHCP gateway (dnsmasq + DB) with short-lease pre-staging
- [ ] 05-02: Execute 7-step validation checklist and document results

## Progress

**Execution Order:**
Phases execute in strict numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Bridge Isolation Core | 1/1 | Complete | 2026-02-25 |
| 2. Accounting Chain Migration | 1/1 | Complete | 2026-02-25 |
| 3. TC Mark Chain Migration | 0/1 | Not started | - |
| 4. Startup and Persistence | 0/1 | Not started | - |
| 5. DHCP Gateway and Validation | 0/2 | Not started | - |
