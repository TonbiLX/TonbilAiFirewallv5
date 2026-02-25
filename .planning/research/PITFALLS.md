# Pitfalls Research

**Domain:** Bridge-to-Router Transition on Live Raspberry Pi (nftables)
**Researched:** 2026-02-25
**Confidence:** HIGH (nftables hook behavior from official wiki; bridge semantics from kernel docs and Netfilter engineers; SSH/DHCP lockout patterns from community post-mortems)

---

## Critical Pitfalls

### Pitfall 1: Drop Verdict in Forward Chain Silently Kills Accounting Counters

**What goes wrong:**
The isolation rules use `drop` in `bridge filter forward` (priority -200). The accounting chains (`bridge accounting upload/download`) use `hook input`/`hook output` at priority -2. The plan assumes routed traffic arrives at these hooks after isolation drops L2 forwarding.

However, there are two failure modes here. First: if the isolation drop fires *before* `br_netfilter` + `ip_forward` routes the packet through the IP stack, the packet never reaches the `input`/`output` hooks at all — counters stay at zero silently. Second: within the same forward hook, if the `bridge filter forward` chain (priority -200) drops the packet, no chain at a higher numerical priority on the same hook is evaluated — a drop verdict is **final** and immediate per nftables semantics.

The plan's logic is sound IF the packet path after isolation is: bridge forward DROP → packet re-enters IP stack as routed → sees bridge input/output hooks. But if `br_netfilter` is not active, or if the kernel routes it differently, accounting sees nothing.

**Why it happens:**
The team migrates accounting from `hook forward` to `hook input/output` assuming the bridge isolation drop causes re-routing through the IP stack. This is true — but only when `br_netfilter` is loaded and `net.ipv4.ip_forward=1` is active. If either is missing at the moment of migration, traffic silently bypasses all counters.

**How to avoid:**
1. Verify `br_netfilter` is loaded (`lsmod | grep br_netfilter`) BEFORE adding isolation drop rules.
2. Verify `net.ipv4.ip_forward=1` is set BEFORE testing accounting.
3. After migrating to input/output hooks, immediately run `sudo nft list chain bridge accounting upload` and watch counters increment within 5 seconds. If they stay at zero while devices are active on the network, accounting is broken — do NOT proceed.
4. Run verification test: ping from a LAN device to internet, watch counter; if counter doesn't move, stop and diagnose before continuing.

**Warning signs:**
- `nft list chain bridge accounting upload` shows counters frozen at 0 while devices are active
- `bandwidth_monitor.py` logs show all devices at 0 bytes
- Dashboard bandwidth widgets show zero for all devices
- No error in backend logs (silent failure because `check=False` is used on counter read calls)

**Phase to address:** Phase covering Step 2 (accounting migration) — must include counter verification as an explicit success gate before marking the phase complete.

---

### Pitfall 2: nftables Ruleset Not Persisted Across Reboot — Isolation Rules Disappear

**What goes wrong:**
After adding bridge isolation rules via `nft add rule ...`, they exist in kernel memory. The `persist_nftables()` function writes them to `/etc/nftables.conf`. But if `systemd nftables.service` is not enabled, or if another process (e.g., fail2ban, Docker, firewalld) flushes the ruleset after boot, the isolation rules are gone on next restart — the system silently reverts to transparent bridge mode.

This is not just a cosmetic bug: the Pi reboots, modem can now see all LAN device MACs again, and the security guarantee of bridge isolation is gone — with no error, no alert, no log.

**Why it happens:**
On Debian/Raspberry Pi OS, `nftables.service` may not be enabled by default. The Pi's backend (`tonbilaios-backend`) startup calls `ensure_bridge_isolation()` which re-adds rules — but only if the service starts successfully. If the service crashes on startup (e.g., DB not ready), the isolation rules are not restored.

**How to avoid:**
1. Explicitly verify `systemctl is-enabled nftables` returns `enabled` as part of the migration checklist.
2. After running `persist_nftables()`, reboot the Pi and check that rules survived: `sudo nft list chain bridge filter forward` should show both `bridge_isolation_lan_wan` and `bridge_isolation_wan_lan` rules.
3. Add a boot-time verification in `main.py`: if isolation rules are not present at startup, `ensure_bridge_isolation()` re-applies them (already planned in Step 4) — confirm this works after a fresh reboot.
4. Do NOT rely on `main.py` alone for persistence — systemd nftables.service must also be the fallback in case the FastAPI service itself doesn't start.

**Warning signs:**
- After reboot, `nft list ruleset` does not contain `bridge_isolation` comment strings
- `sudo tcpdump -i eth0 arp -c 20` shows LAN device MACs in ARP traffic on the WAN port
- modem ARP table shows more than one MAC address (visible via Pi's `ip neigh show` on eth0)

**Phase to address:** Step 6 (Pi cleanup/apply) — add explicit post-reboot verification as a required step, not optional.

---

### Pitfall 3: DHCP Gateway Change Causes Immediate Lockout for All Active Devices

**What goes wrong:**
Step 5 changes `dnsmasq` gateway option from `.1` to `.2`. Devices with existing DHCP leases keep their old gateway (`.1`) until lease renewal. If the isolation drop rules are already active, those devices can no longer route through `.1` (modem), and they cannot reach `.2` (Pi) as gateway because their route table points to `.1`. Result: all active devices lose internet until they renew their DHCP lease.

Depending on dnsmasq lease time (typically 24 hours), this can mean a multi-hour internet outage for all LAN devices — with no indication in the Pi logs.

**Why it happens:**
DHCP clients only update their gateway at lease renewal, not when the server changes the gateway option. `systemctl reload dnsmasq` changes what new leases get, but existing leases are unaffected until they expire or DHCP RENEW fires (at T1, 50% of lease time).

**How to avoid:**
1. Before changing the gateway, shorten the DHCP lease time to a very short window (e.g., 5 minutes): `default-lease-time 300; max-lease-time 300;` in dnsmasq config.
2. Reload dnsmasq and wait 5-10 minutes for all devices to renew.
3. Then change gateway to `.2` and reload dnsmasq again.
4. Wait another 5 minutes for all devices to pick up the new gateway.
5. Restore normal lease time (e.g., 86400).
6. Verify with: `ip netns exec ns_test ip route show` shows `default via 192.168.1.2`.

Alternatively: force DHCP RELEASE on all devices (not feasible remotely), or schedule the change during a maintenance window.

**Warning signs:**
- After applying isolation rules + gateway change simultaneously, all LAN devices report "no internet" on the network
- `conntrack -L` shows no ESTABLISHED connections from LAN IPs
- Gateway still shows `.1` in device route tables

**Phase to address:** Step 5 (DHCP gateway change) — must be split into: (a) shorten lease time, (b) wait for renewal, (c) change gateway, (d) verify, (e) restore lease time. Not a single atomic step.

---

### Pitfall 4: SSH Access via Jump Host Lost During Transition Due to Conntrack Gap

**What goes wrong:**
The SSH jump host connects to Pi at `192.168.1.2` via the existing `br0` interface. During the transition — specifically between the moment bridge isolation drop rules are applied and MASQUERADE/NAT is confirmed working — there is a window where Pi's routing is undefined. If NAT is not yet in place, or `ip_forward` is not yet set, Pi cannot route return traffic from WAN back to the jump host's SSH session. The existing SSH connection may hang or drop.

More critically: once the SSH connection drops, there is NO recovery mechanism available remotely. The Pi can only be reached via `pi.tonbil.com:2323 → 192.168.1.2`. If that path is broken, there is no way to recover without physical access.

**Why it happens:**
The transition involves multiple sequential steps. If they are applied in the wrong order — isolation drop before MASQUERADE, or MASQUERADE before `ip_forward` — Pi's IP stack is briefly in an inconsistent state. The SSH session to the jump host is WAN-side traffic; it does not go through the bridge forward chain (it goes through `inet tonbilai input`), so the isolation rules themselves don't break it. However, if the outbound routing from Pi to the jump host fails (no default route, or NAT not working for Pi's own traffic), the session can die.

**How to avoid:**
1. Apply steps in this strict order: (a) `ip_forward=1`, (b) `br_netfilter` + `bridge-nf-call-iptables=1`, (c) MASQUERADE rule, (d) VERIFY Pi can reach internet (`curl google.com`), (e) add bridge isolation drop rules.
2. Never add the drop rules before verifying MASQUERADE is working.
3. Use a `tmux` or `screen` session on the Pi so that SSH session drops are recoverable if the tunnel briefly bounces.
4. Have `remove_bridge_isolation()` script pre-staged in `/tmp/rollback.sh` on the Pi before starting — so if something goes wrong, a new SSH session can run it immediately.
5. Test the rollback script in advance to confirm it works.

**Warning signs:**
- SSH session hangs for >30 seconds during step application
- `curl --connect-timeout 5 https://www.google.com` from Pi fails after adding drop rules
- `ip route` from Pi shows no default route

**Phase to address:** Step 6 (Pi manual apply) — define exact command ordering; rollback script must be pre-staged; tmux session required.

---

### Pitfall 5: `br_netfilter` sysctl Silently Lost After Reboot

**What goes wrong:**
`net.bridge.bridge-nf-call-iptables=1` is written to `/etc/sysctl.d/99-bridge-isolation.conf` (per Step 6). But `systemd-sysctl.service` runs at boot before `br_netfilter` is loaded by systemd. If `br_netfilter` is not in `/etc/modules-load.d/`, the sysctl setting silently has no effect — the module doesn't exist yet when sysctl tries to apply it. After reboot, bridge-nf is inactive, meaning nftables bridge rules and IP-level inspection don't interact correctly.

This is a well-documented and commonly hit issue on Raspberry Pi / Debian systems (confirmed in multiple GitHub issues and the Kubernetes/Raspbian ecosystem).

**Why it happens:**
The `br_netfilter` kernel module creates `/proc/sys/net/bridge/` entries. If the module is not loaded, that path doesn't exist. `sysctl -w net.bridge.bridge-nf-call-iptables=1` at boot silently fails with "No such file or directory" if the module isn't loaded first.

**How to avoid:**
1. Add `br_netfilter` to `/etc/modules-load.d/br_netfilter.conf` (one line: `br_netfilter`) so it loads at boot before systemd-sysctl runs.
2. Verify persistence after reboot: `lsmod | grep br_netfilter` should show the module; `sysctl net.bridge.bridge-nf-call-iptables` should return `1`.
3. Do NOT rely solely on `ensure_bridge_isolation()` calling `modprobe br_netfilter` at startup — that is the right defense, but systemd-managed sysctl must also be correct for the kernel to behave consistently from the very first boot second before FastAPI starts.

**Warning signs:**
- After reboot, `sysctl net.bridge.bridge-nf-call-iptables` returns `0` or "No such file"
- `lsmod | grep br_netfilter` returns empty
- Bridge accounting counters at zero immediately after reboot

**Phase to address:** Step 6 (Pi cleanup) — add `/etc/modules-load.d/br_netfilter.conf` creation to the command checklist.

---

### Pitfall 6: Removing `bridge masquerade_fix` Table Breaks Existing TCP Sessions

**What goes wrong:**
Step 6a removes the `bridge masquerade_fix` table via `nft delete table 'bridge masquerade_fix'`. This table currently does MAC rewriting. Deleting it while active TCP sessions exist through that path will cause those sessions to immediately break — conntrack entries reference the old translation, which is now gone.

Under transparent bridge mode, the modem sees individual device MACs. If `masquerade_fix` was providing any active L2 rewriting for in-flight connections, those connections drop the moment the table is deleted.

**Why it happens:**
Network state transitions during live operation always risk disrupting in-flight connections. The team may not realize that deleting the MAC rewrite table is not a graceful operation — it is immediate and affects all active flows that depended on it.

**How to avoid:**
1. Delete `masquerade_fix` AFTER adding the isolation drop rules — once forward-path traffic is dropped, no new connections go through the MAC rewrite path.
2. Accept that existing connections will briefly drop during the transition. Warn users before applying.
3. The order should be: (a) add isolation drop rules, (b) verify new routing works via NAT (new connections succeed), (c) then delete `masquerade_fix`. By then, no active connections rely on it.

**Warning signs:**
- Active SSH sessions from LAN to the internet drop immediately when `masquerade_fix` table is deleted
- `conntrack -L` shows connections moving to `TIME_WAIT` or disappearing

**Phase to address:** Step 6a — reorder: delete `masquerade_fix` AFTER, not before, isolation rules are applied and NAT is verified working.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `check=False` on accounting counter read calls | Silent failure instead of exception | Zero counters look like "no traffic" — impossible to distinguish from broken accounting | Never for accounting-critical paths; add explicit zero-counter alerting |
| Hardcoding `eth0`/`eth1` interface names | Simple code | Fails if Pi kernel renames interfaces (e.g., `enp1s0`) due to udev rules; bridge isolation rules add to wrong interfaces | Only acceptable if Pi's `net.ifnames=0` / `biosdevname=0` is verified persistent |
| Relying on `if "bridge_isolation" in ruleset` to detect existing rules | Avoids duplicate rules | Comment-based detection fails if nft rule was added manually without the exact comment string | Acceptable for now; document the dependency explicitly |
| Single-step DHCP gateway change | Simpler to execute | Disconnects all active LAN devices until next lease renewal | Never on a live production network; always use short-lease pre-staging |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| nftables comment strings in Python `run_nft()` | Passing `'"bridge_isolation_lan_wan"'` (Python double-quoted inside single) as a list arg — shell expands quotes differently when using `create_subprocess_exec` vs `shell=True` | With `create_subprocess_exec`, pass the comment string WITHOUT the outer shell quotes — `run_nft` constructs the argv directly; nft receives the literal string correctly |
| dnsmasq reload vs restart | `systemctl reload dnsmasq` does not flush existing leases — new gateway option applies only to new leases | Use `reload` for config update, but pre-shorten lease time so renewals happen quickly |
| `persist_nftables()` write to `/etc/nftables.conf` | Overwrites file atomically but if nftables.service is not enabled, the file is never read at boot | Always verify `systemctl is-enabled nftables` returns `enabled` and reboot to confirm |
| `conntrack -L` for post-transition verification | Shows entries from before the transition; ESTABLISHED counts may look healthy while NAT is actually broken for NEW connections | Test by initiating a NEW connection from a LAN device after the transition, not just checking existing conntrack entries |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Bridge accounting on input/output hooks misses non-IP traffic (ARP, etc.) | ARP flood from many devices shows zero accounting; but this is expected | Not a performance issue — document that bridge accounting counts IP traffic only | Not a scale issue; behavior is correct |
| Counter read scanning entire chain per call (`read_device_counters` parses full chain output) | Slow if many devices (>50 MACs) are tracked | Current approach is fine for home/SOHO scale (< 30 devices) | Will not break at Pi's expected device count |
| `sync_device_counters` called frequently with many MACs creates many nft subprocesses | High CPU on Pi if called every few seconds for 30+ devices | Keep sync interval at 5s minimum; the Pi's ARM CPU handles this at SOHO scale | Tested up to ~50 devices without issues in similar setups |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Applying isolation rules without verifying MASQUERADE is in place first | All LAN devices lose internet access (no NAT for outbound traffic) | Strict step ordering: MASQUERADE → verify → drop rules |
| Leaving `net.ipv4.conf.all.send_redirects=1` after adding isolation | Pi sends ICMP redirects telling LAN devices to route directly to modem, bypassing Pi — partial de-isolation | Disable redirects in Step 3 and persist via sysctl.d |
| Rolling back by just deleting drop rules without also restoring DHCP gateway to `.1` | Devices use Pi as gateway but Pi is no longer doing NAT properly in transparent mode — intermittent routing failures | Full rollback checklist: (1) delete drop rules, (2) restore gateway `.1`, (3) restore `masquerade_fix` table, (4) re-enable send_redirects |
| Skipping `remove_bridge_isolation()` pre-staging on Pi | If SSH lockout occurs, recovery requires physical access | Stage rollback script at `/tmp/rollback.sh` on Pi before starting any transition step |

---

## "Looks Done But Isn't" Checklist

- [ ] **Bridge isolation active:** `nft list chain bridge filter forward` shows BOTH `bridge_isolation_lan_wan` AND `bridge_isolation_wan_lan` drop rules — if only one is present, traffic still flows in one direction
- [ ] **Accounting working:** `nft list chain bridge accounting upload` shows counters incrementing — if frozen at 0 while devices are active, accounting migration failed silently
- [ ] **Sysctl persistent:** After reboot, `sysctl net.bridge.bridge-nf-call-iptables` returns `1` — if `0` or "No such file", br_netfilter module load persistence is missing
- [ ] **DHCP gateway adopted by all devices:** `ip route show` from a LAN device shows `default via 192.168.1.2` — NOT `.1`; old leases may still point to `.1` for hours
- [ ] **Pi's own internet works:** `curl --connect-timeout 5 https://www.google.com` from Pi returns 200 — Pi routing broken is silent from LAN's perspective
- [ ] **Rollback tested:** Run `remove_bridge_isolation()` then `ensure_bridge_isolation()` in sequence at least once to confirm the rollback cycle works before production use
- [ ] **masquerade_fix table removed cleanly:** `nft list ruleset | grep masquerade_fix` returns empty — if table still exists it's dead code that may conflict
- [ ] **TC marking in new chains:** `nft list chain bridge accounting tc_mark_up` shows mark rules; bandwidth limiting on a test device still works after transition

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SSH lockout after drop rules break routing | HIGH (requires physical Pi access if no recovery path) | (1) Connect keyboard/monitor to Pi OR use pre-staged `/tmp/rollback.sh`; (2) run rollback commands; (3) verify SSH reconnects; (4) diagnose root cause before retrying |
| Accounting counters at zero post-migration | LOW (no connectivity impact) | (1) Check br_netfilter loaded; (2) check ip_forward=1; (3) verify input/output chain hooks are correct; (4) if needed, delete and recreate accounting chains |
| All LAN devices lost internet (DHCP gateway issue) | MEDIUM (internet outage until DHCP renewal) | (1) Immediately run rollback to restore `.1` gateway in dnsmasq; (2) reload dnsmasq; (3) wait for device lease renewal; (4) redo with short-lease pre-staging approach |
| Sysctl br_netfilter not persistent after reboot | LOW (rules are still added by main.py on startup) | (1) Add `br_netfilter` to `/etc/modules-load.d/`; (2) verify with reboot; (3) sysctl.d file works correctly once module is pre-loaded |
| masquerade_fix deleted before isolation active | MEDIUM (brief connectivity disruption for LAN devices) | (1) Restore bridge masquerade_fix using `ensure_bridge_masquerade()`; (2) reorder transition steps per correct sequence |
| nftables rules lost after reboot | MEDIUM (silent re-isolation on next main.py start, but window of exposure) | (1) `systemctl enable nftables`; (2) verify `/etc/nftables.conf` contains isolation rules; (3) reboot to confirm persistence |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Drop kills accounting counters silently | Step 2 (accounting migration) | Watch counters increment in real time for 30 seconds after migration |
| Ruleset not persisted across reboot | Step 6 (cleanup/apply) + post-reboot check | Reboot Pi, re-check `nft list ruleset` before declaring done |
| DHCP gateway change disconnects all devices | Step 5 (DHCP) — must use short-lease pre-staging | Verify all test devices show `default via 192.168.1.2` in route table |
| SSH lockout during transition | Step 6 (apply ordering) | Pre-stage rollback; apply in strict order; tmux session |
| br_netfilter sysctl lost after reboot | Step 6 (sysctl persistence) | After reboot: `lsmod \| grep br_netfilter` and `sysctl net.bridge.bridge-nf-call-iptables` |
| Removing masquerade_fix breaks existing sessions | Step 6 (reordering) | Verify masquerade_fix removed AFTER isolation + NAT verified working |
| br_netfilter not active when drop rules applied | Step 1/6 (apply ordering) | `lsmod \| grep br_netfilter` before any nft commands |

---

## Sources

- [Netfilter hooks — nftables wiki](https://wiki.nftables.org/wiki-nftables/index.php/Netfilter_hooks) — Bridge family hook priorities and drop verdict finality (HIGH confidence)
- [Bridge filtering — nftables wiki](https://wiki.nftables.org/wiki-nftables/index.php/Bridge_filtering) — Forward vs input/output hook semantics (HIGH confidence)
- [Proper isolation of a Linux bridge — Vincent Bernat](https://vincent.bernat.ch/en/blog/2017-linux-bridge-isolation) — br_netfilter interaction, MAC bypass, ARP exploitation pitfalls (MEDIUM confidence — 2017, concepts stable)
- [br_netfilter sysctl persistence — GitHub moby/moby discussion #48559](https://github.com/moby/moby/discussions/48559) — Module-load timing dependency causing silent sysctl failure (HIGH confidence — multiple reproducers)
- [Configuring chains — nftables wiki](https://wiki.nftables.org/wiki-nftables/index.php/Configuring_chains) — Priority ordering, drop verdict is final (HIGH confidence)
- [DHCP lease time management — ManageEngine OpUtils](https://www.manageengine.com/products/oputils/tech-topics/dhcp-lease-time.html) — T1/T2 renewal timing and gateway change window (MEDIUM confidence)
- nftables bridge accounting forward hook code in `backend/app/hal/linux_nftables.py` — direct code inspection of existing `check=False` patterns and `BRIDGE_CHAIN = "per_device"` (HIGH confidence — first-hand)

---
*Pitfalls research for: TonbilAiOS Bridge Isolation Transition*
*Researched: 2026-02-25*
