# Phase 5: DHCP Gateway and Validation — Research

**Researched:** 2026-03-03
**Domain:** dnsmasq DHCP gateway migration + end-to-end router mode validation
**Confidence:** HIGH — all findings based on direct codebase reading; no external dependencies required

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DHCP-01 | dnsmasq config contains `dhcp-option=3,192.168.1.2` | `generate_pool_config()` in `linux_dhcp_driver.py` already produces `dhcp-option=3,{gateway}` — only DB gateway value needs to change |
| DHCP-02 | `dhcp_pools.gateway` in MariaDB is `192.168.1.2` | `DhcpPool.gateway` column exists; update via existing PATCH `/api/v1/dhcp/pools/{pool_id}` endpoint which calls `driver.configure_dhcp_pool()` and regenerates config |
| VALD-01 | Modem ARP table shows only Pi's MAC | Validated via `tcpdump -i eth0 arp` on Pi — a manual/live check post-deploy |
| VALD-02 | Existing conntrack ESTABLISHED connections remain | Conntrack entries survive DHCP gateway change; NAT MASQUERADE is already active (Phase 1) |
| VALD-03 | Pi internet access works (curl test) | Already verified in Phase 1; ensure_bridge_isolation() is idempotent and runs on every backend start |
| VALD-04 | DNS resolution works from LAN device | dns_proxy.py already listens on port 53; validated by `dig @192.168.1.2 example.com` from a LAN client |
| VALD-05 | Bridge accounting counters increment | upload/download chains from Phase 2 are live; verified by reading `nft list chain bridge accounting upload` during traffic |
| VALD-06 | `nft list chain bridge filter forward` shows drop rules | Drop rules from Phase 1 persist via nftables.service (Phase 4); persisted in /etc/nftables.conf |
| VALD-07 | veth namespace test device using gateway 192.168.1.2 can reach internet | Requires scripted veth+netns setup with manual IP/GW assignment; tests routing without DHCP dependency |
</phase_requirements>

---

## Summary

Phase 5 has two logical parts. Part A (DHCP-01, DHCP-02) is a single data change: update the gateway field in the `dhcp_pools` MariaDB table from `192.168.1.1` to `192.168.1.2`, which causes `generate_pool_config()` to emit `dhcp-option=3,192.168.1.2` when the config is next regenerated. The existing code path is fully correct — `linux_dhcp_driver.py` line 52-53 already handles gateway injection into pool config. The entire DHCP change is two SQL rows or one PATCH API call plus a dnsmasq reload.

Part B (VALD-01 through VALD-07) is a validation checklist that confirms the complete transition is working end-to-end. These are manual/live checks run after deploying to Pi — they cannot run on local files. The plan must produce a deployment checklist document (or verification script) that the user can execute after `sudo systemctl restart tonbilaios-backend`. Six of the seven validations (VALD-01 through VALD-06) verify that Phases 1-4 code is working correctly in live conditions. VALD-07 is the only one with a non-trivial implementation: it requires creating a veth pair and network namespace to simulate a new LAN client.

**Critical insight: Phase 5 is almost entirely a data migration + verification exercise.** The code infrastructure was built in Phases 1-4. Phase 5 plans should focus on: (1) safely updating the DHCP gateway with lease pre-staging, and (2) producing a deterministic validation script the user can run.

**Primary recommendation:** Two plans — Plan 05-01 updates the DHCP config (short-lease pre-staging → gateway change → dnsmasq reload), and Plan 05-02 produces the validation checklist with the veth namespace test command sequence.

---

## Standard Stack

### Core (no library installs required — all existing in codebase or OS)

| Tool | Purpose | Why Standard |
|------|---------|--------------|
| `linux_dhcp_driver.py` `generate_pool_config()` | Generates `dhcp-option=3,{gateway}` line | Already exists; only input data changes |
| `linux_dhcp_driver.py` `write_pool_config()` | Writes `/etc/dnsmasq.d/pool-{id}.conf` | Already exists and tested |
| `linux_dhcp_driver.py` `trigger_reload()` | Writes `.reload-trigger` to cause dnsmasq reload via systemd path unit | Already exists |
| `api/v1/dhcp.py` `PATCH /pools/{pool_id}` | Updates pool in DB + calls `driver.configure_dhcp_pool()` | Full code path already exists; no new code needed |
| `nft list chain bridge filter forward` | Verifies VALD-06 drop rules | Standard nft command |
| `tcpdump -i eth0 arp` | Verifies VALD-01 modem sees only Pi MAC | Standard Linux tool |
| `ip netns` + `veth` | Creates isolated namespace for VALD-07 test | Standard Linux iproute2 tools |

### The DHCP Config Regeneration Path (HIGH confidence — traced through code)

```
PATCH /api/v1/dhcp/pools/{pool_id} (gateway: "192.168.1.2")
    ↓
dhcp.py update_pool() → sets pool.gateway = "192.168.1.2" in DB
    ↓
driver.configure_dhcp_pool(pool_dict)  # LinuxNetworkDriver
    ↓
linux_driver.py configure_dhcp_pool() → generate_pool_config(pool) + write_pool_config()
    ↓
generate_pool_config() → "dhcp-option=3,192.168.1.2"
    ↓
write_pool_config() → /etc/dnsmasq.d/pool-{id}.conf
    ↓
trigger_reload() → .reload-trigger → systemd PathChanged → dnsmasq SIGHUP
```

All steps verified by reading the source. No new code is required for DHCP-01 and DHCP-02.

---

## Architecture Patterns

### Pattern 1: Short-Lease Pre-Staging Before Gateway Change

**What:** Temporarily reduce DHCP lease time to 5 minutes before changing the gateway. Wait for all existing leases to expire. Only then change the gateway to 192.168.1.2.

**Why:** Without pre-staging, existing devices retain their old lease (gateway 192.168.1.1) for up to 24 hours after the gateway change. They will fail to route during that window. Short lease forces rapid lease renewal, guaranteeing all devices get the new gateway quickly.

**Sequence:**
1. PATCH `/api/v1/dhcp/pools/{id}` with `lease_time_seconds: 300` (5 minutes)
2. Wait 5-10 minutes for devices to renew (or manually `dhclient -r` on test device)
3. PATCH `/api/v1/dhcp/pools/{id}` with `gateway: "192.168.1.2"`
4. Verify dnsmasq config file contains `dhcp-option=3,192.168.1.2`
5. After validating, restore lease time to 86400 (24 hours)

**Implementation note:** Both PATCHes call the existing `update_pool()` endpoint — no code changes needed. The pre-staging is a deployment procedure, not a code change.

### Pattern 2: Database Update — Direct SQL Alternative

If the backend is not running at deploy time, the DB can be updated directly:

```sql
-- Run on Pi: mysql -u tonbilai -p tonbilaios
UPDATE dhcp_pools SET gateway='192.168.1.2', updated_at=NOW() WHERE id=1;
```

After this, restart the backend (`sudo systemctl restart tonbilaios-backend`). The lifespan calls `start_dhcp_worker()` which syncs pool configs on startup.

**Important:** Verify that `dhcp_worker.py` regenerates pool configs on startup, or trigger the config write manually via the API after restart.

### Pattern 3: VALD-07 veth Namespace Test

**What:** Create a virtual network interface pair in a separate network namespace, assign it an IP and gateway of 192.168.1.2, and verify internet access.

**Why:** Tests routing without a real DHCP lease renewal. Confirms the Pi's IP forwarding + NAT path works for new router-mode clients before any real device re-leases.

**Command sequence (run as root on Pi):**

```bash
# 1. Create network namespace and veth pair
ip netns add testns
ip link add veth0 type veth peer name veth1
ip link set veth1 netns testns

# 2. Bring up the host-side veth0 on br0 (or assign it directly)
ip link set veth0 up
ip link set veth0 master br0

# 3. Configure the namespace side
ip netns exec testns ip link set lo up
ip netns exec testns ip link set veth1 up
ip netns exec testns ip addr add 192.168.1.250/24 dev veth1
ip netns exec testns ip route add default via 192.168.1.2

# 4. Test internet access from the namespace
ip netns exec testns curl -s --max-time 10 https://example.com

# 5. Test DNS from namespace
ip netns exec testns dig @192.168.1.2 example.com

# 6. Cleanup
ip netns del testns
ip link del veth0
```

**Expected results:**
- curl returns HTTP 200 content → routing via 192.168.1.2 works (VALD-07)
- dig returns valid A record → DNS proxy is reachable via gateway (VALD-04 cross-check)

**Accounting check during veth test:**
```bash
# On Pi host side — run before and after curl in namespace
nft list chain bridge accounting upload
nft list chain bridge accounting download
# Byte counters should increment for veth0's MAC
```

### Pattern 4: ARP Verification (VALD-01)

**What:** Capture ARP traffic on eth0 (WAN-side) with tcpdump to verify modem only sees Pi's MAC.

```bash
# Run on Pi — capture 30 seconds of ARP on WAN side
sudo tcpdump -i eth0 -n -e arp -c 20 2>/dev/null
# All ARP sender hardware addresses should be Pi's eth0 MAC
# Pi's eth0 MAC: cat /sys/class/net/eth0/address
```

**Expected:** Every ARP packet on eth0 has the Pi's MAC as sender hardware address. No LAN device MACs appear. This is the definitive proof that isolation is working.

### Pattern 5: Conntrack Stability Check (VALD-02)

**What:** Before changing DHCP gateway, note the number of ESTABLISHED connections. After the change, verify connections remain.

```bash
# Before gateway change
sudo conntrack -L --state ESTABLISHED | wc -l

# After gateway change (wait 60 seconds)
sudo conntrack -L --state ESTABLISHED | wc -l
# Count should be similar — existing connections survive
```

**Why connections survive:** The Pi has been routing traffic with NAT MASQUERADE since Phase 1. The gateway change only affects new DHCP leases; existing conntrack entries use the Pi's existing routing (already through Pi). The modem already sees Pi's IP (192.168.1.2) as the source due to MASQUERADE.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DHCP gateway config | Custom config file writer | Existing `generate_pool_config()` + `write_pool_config()` | Already handles `dhcp-option=3,{gateway}` correctly |
| dnsmasq reload | `systemctl restart dnsmasq` | Existing `trigger_reload()` via systemd path unit | Graceful SIGHUP preserves existing leases; restart drops them |
| DB gateway update | Raw SQL scripts | PATCH `/api/v1/dhcp/pools/{id}` via curl/browser | Full validation path including HAL config write |
| Interface-level validation | Complex Python test harness | Shell commands in a documented checklist | One-shot validation; simpler to understand and debug |

**Key insight:** All code needed for Phase 5 already exists. This phase is about running the right commands in the right order, not writing new application logic.

---

## Common Pitfalls

### Pitfall 1: Changing Gateway Without Short-Lease Pre-Staging

**What goes wrong:** Existing devices keep their old lease (gateway 192.168.1.1) for hours or days. They continue routing through 192.168.1.1 (modem), which no longer works because Pi's bridge isolation drops L2 forwarding. Devices lose internet access until lease expires.

**Why it happens:** DHCP clients do not check for gateway changes between lease renewals. A lease with `gateway=192.168.1.1` and TTL 23h59m will route through 192.168.1.1 for all of that remaining time.

**How to avoid:** Always short-lease (5 min) → wait for renewal → change gateway → verify → restore lease time.

**Warning signs:** After gateway change, new `dhclient` on test device works but existing devices lose internet.

### Pitfall 2: Updating DB But Not Regenerating dnsmasq Config

**What goes wrong:** The `dhcp_pools.gateway` is `192.168.1.2` in MariaDB, but the dnsmasq config file `/etc/dnsmasq.d/pool-1.conf` still contains `dhcp-option=3,192.168.1.1`. New leases are issued with old gateway.

**Why it happens:** Direct SQL update does not trigger `configure_dhcp_pool()`. The config file is only regenerated when the API endpoint calls `driver.configure_dhcp_pool()`.

**How to avoid:**
1. Use the PATCH API endpoint (triggers config regeneration automatically), OR
2. After direct SQL update, restart backend AND verify config file content

**Detection:**
```bash
cat /etc/dnsmasq.d/pool-1.conf | grep dhcp-option
# Must show: dhcp-option=3,192.168.1.2
```

### Pitfall 3: veth0 Not Added to br0 — Namespace Gets No Routing

**What goes wrong:** The veth namespace test fails with "Network unreachable" because veth0 on the host side is not connected to the bridge (br0). Pi cannot route traffic from the namespace.

**Why it happens:** `ip link add veth0 type veth peer name veth1` creates a point-to-point link, not a bridge member. Traffic from veth1 goes to veth0 but has nowhere to go unless veth0 is in br0.

**How to avoid:** Add `ip link set veth0 master br0` after creating the veth pair. Verify with `bridge link show`.

**Alternative approach:** Assign Pi's br0 IP as the routing hop:
```bash
ip netns exec testns ip route add 192.168.1.2 dev veth1
ip netns exec testns ip route add default via 192.168.1.2
```
This requires br0 to have a route back to veth1's IP.

### Pitfall 4: VALD-07 IP Conflict With Existing DHCP Devices

**What goes wrong:** The test namespace IP `192.168.1.250` is already assigned to a real device via DHCP, causing routing confusion.

**How to avoid:** Choose an IP outside the DHCP range. Default DHCP range is `192.168.1.100` to `192.168.1.200`. Use `192.168.1.250` or `192.168.1.240`. Verify the IP is unused before running the test.

### Pitfall 5: dns_proxy.py Not Listening on 192.168.1.2

**What goes wrong:** `dig @192.168.1.2 example.com` times out because the DNS proxy only listens on `0.0.0.0` or a different IP.

**Why it shouldn't happen:** `start_dns_proxy()` binds to `0.0.0.0:53` which accepts connections on all interfaces including br0 (which has IP 192.168.1.2). However, verify this assumption.

**Detection:**
```bash
sudo ss -tunlp | grep :53
# Should show dnsmasq (DHCP DNS) and possibly dns_proxy
# dns_proxy.py binds to 0.0.0.0:53 — check for conflicts
```

**Important:** dnsmasq may also bind to port 53. Check if there is a port conflict between dns_proxy.py and dnsmasq on the same port. If dnsmasq has `port=0` in its config (disabling its DNS), then dns_proxy.py has 53 to itself.

### Pitfall 6: tcpdump Shows LAN MACs on eth0 — Isolation Not Working

**What goes wrong:** VALD-01 fails — tcpdump on eth0 shows ARP packets with LAN device MACs as sender.

**Why it could happen:** The bridge isolation drop rules (`bridge filter forward` drop) were not persisted correctly, or nftables.service did not load `/etc/nftables.conf` on boot.

**How to detect and fix:**
```bash
# Check if drop rules are present (VALD-06)
sudo nft list chain bridge filter forward
# Should show: iifname "eth1" oifname "eth0" drop comment "bridge_isolation_lan_wan"

# If not present, re-run bridge isolation
sudo systemctl restart tonbilaios-backend
# ensure_bridge_isolation() runs on lifespan start and will re-apply
```

---

## Code Examples

### Tracing the DHCP Gateway Config Path

```python
# backend/app/hal/linux_dhcp_driver.py lines 32-60
# generate_pool_config() already handles gateway correctly:

def generate_pool_config(pool: Dict[str, Any]) -> str:
    lines = [f"# Pool: {pool.get('name', 'unnamed')} (ID: {pool.get('id', '?')})"]
    # ...
    # Gateway (option 3) — this is what we need to change
    gateway = pool.get("gateway", "")
    if gateway:
        lines.append(f"dhcp-option=3,{gateway}")  # → "dhcp-option=3,192.168.1.2"
    # ...
```

### PATCH API Call to Update Gateway (via curl)

```bash
# Run from any machine that can reach the Pi API
curl -X PATCH http://192.168.1.2:8000/api/v1/dhcp/pools/1 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"gateway": "192.168.1.2"}'
```

This triggers the full path: DB update → generate_pool_config() → write_pool_config() → trigger_reload().

### Verifying dnsmasq Config After Gateway Change

```bash
# On Pi — verify the generated config
cat /etc/dnsmasq.d/pool-1.conf

# Expected output:
# # Pool: Main Network (ID: 1)
# dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
# dhcp-option=3,192.168.1.2
# dhcp-option=6,192.168.1.2
```

### Full Validation Command Sequence

```bash
# ===== VALD-06: Drop rules present =====
sudo nft list chain bridge filter forward

# ===== VALD-03: Pi internet access =====
curl -s --max-time 10 https://example.com > /dev/null && echo "VALD-03: OK"

# ===== VALD-04: DNS resolution =====
dig @192.168.1.2 example.com +short

# ===== VALD-05: Accounting counters (run during active traffic) =====
sudo nft list chain bridge accounting upload | tail -20
sudo nft list chain bridge accounting download | tail -20

# ===== VALD-01: ARP capture (requires active LAN devices) =====
PI_ETH0_MAC=$(cat /sys/class/net/eth0/address)
echo "Pi eth0 MAC: $PI_ETH0_MAC"
sudo tcpdump -i eth0 -n -e arp -c 20 2>/dev/null
# All "Request who-has" sender MACs should be $PI_ETH0_MAC

# ===== VALD-02: Conntrack stability =====
sudo conntrack -L --state ESTABLISHED 2>/dev/null | wc -l

# ===== VALD-07: veth namespace test =====
# (See Pattern 3 above for full sequence)
ip netns add testns
ip link add veth0 type veth peer name veth1
ip link set veth1 netns testns
ip link set veth0 up
ip link set veth0 master br0
ip netns exec testns ip link set lo up
ip netns exec testns ip link set veth1 up
ip netns exec testns ip addr add 192.168.1.250/24 dev veth1
ip netns exec testns ip route add default via 192.168.1.2
ip netns exec testns curl -s --max-time 10 https://example.com > /dev/null && echo "VALD-07: OK"
ip netns del testns && ip link del veth0 2>/dev/null
```

---

## Plan Structure Recommendation

This phase should have two plans as pre-specified in ROADMAP.md:

**Plan 05-01: Update DHCP Gateway**

Files modified:
- None — this plan produces a deployment procedure document, not code changes.

OR: If the `dhcp_pools` table seed data file exists, update its default gateway there.

Tasks:
1. Audit whether dhcp_pools table has existing data that needs updating (check models/seeds)
2. Write the deployment procedure for short-lease pre-staging + gateway change
3. Verify no code changes are needed in `linux_dhcp_driver.py` (already handles gateway correctly)
4. If a seed/migration file exists, update default gateway from 192.168.1.1 to 192.168.1.2

**Plan 05-02: Validation Checklist**

Files produced:
- A validation script (`.planning/phases/05-dhcp-gateway-and-validation/validate.sh`) with the VALD-01 through VALD-07 commands

Tasks:
1. Write the validation shell script
2. Document expected output for each VALD check
3. Document failure recovery for each check

---

## State of the Art

| Area | Current Approach | Notes |
|------|-----------------|-------|
| DHCP gateway | 192.168.1.1 (modem) — needs update to 192.168.1.2 (Pi) | Single field in dhcp_pools table |
| dnsmasq reload | systemd PathChanged unit watches `/etc/dnsmasq.d/` | Graceful reload preserves existing leases |
| Bridge isolation | Active since Phase 1 — drop rules in bridge filter forward | Idempotent; re-applied on every backend start |
| NAT MASQUERADE | Active since Phase 1 — `bridge_lan_masq` comment anchor | Allows LAN devices to reach internet through Pi |
| Boot persistence | Active since Phase 4 — nftables.service + sysctl.d + modules-load.d | Rules survive reboot |

---

## Open Questions

1. **Does `dhcp_worker.py` regenerate pool configs on backend startup?**
   - What we know: `start_dhcp_worker()` is called in lifespan. The worker syncs DHCP leases from dnsmasq lease file to DB, but it's unclear if it also re-writes pool config files on startup.
   - What's unclear: If the DB is updated directly (SQL), does a backend restart re-write `/etc/dnsmasq.d/pool-1.conf` automatically?
   - Recommendation: Investigate `dhcp_worker.py` startup behavior. If it does NOT re-write configs, the PATCH API route is mandatory (cannot use direct SQL alone).

2. **Is there a port conflict between dnsmasq and dns_proxy.py on port 53?**
   - What we know: dnsmasq runs as DHCP server. It may or may not also serve DNS on port 53.
   - What's unclear: If dnsmasq binds to port 53, dns_proxy.py cannot bind to the same port. The dnsmasq config in `/etc/dnsmasq.d/` may have `port=0` to disable its DNS functionality.
   - Recommendation: Before validating VALD-04, verify with `ss -tunlp | grep :53` that dns_proxy.py is the one answering on port 53.

3. **What is the current value of `dhcp_pools.gateway` in the live Pi MariaDB?**
   - What we know: The `DhcpPool` model has `gateway = Column(String(15), nullable=False)` with model default `"192.168.1.1"`. The schema `DhcpPoolCreate` also defaults `dns_servers = ["192.168.1.1"]`.
   - What's unclear: Whether the live DB has gateway=192.168.1.1 or already something else.
   - Recommendation: The plan should include a verification step (`SELECT gateway FROM dhcp_pools;`) before making the change, to confirm the current state.

4. **Does the veth test require `veth0` to be in `br0`, or can it connect directly to Pi's routing stack?**
   - What we know: Pi has br0 as the bridge interface; eth0 (WAN) and eth1 (LAN) are bridge ports. Bridge isolation drops L2 forwarding between eth0 and eth1, but Pi's IP stack routes packets from br0.
   - What's unclear: Whether veth0 added to br0 is the correct topology, or whether a direct routed connection to Pi's br0 IP works better.
   - Recommendation: The veth test should use `ip link set veth0 master br0` to mirror how a real LAN device connects through eth1 → br0 → Pi IP stack → NAT → eth0 → internet.

---

## Validation Architecture

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Command | Notes |
|--------|----------|-----------|---------|-------|
| DHCP-01 | dnsmasq config has `dhcp-option=3,192.168.1.2` | Manual inspection | `cat /etc/dnsmasq.d/pool-1.conf | grep dhcp-option` | Verify after PATCH |
| DHCP-02 | DB gateway is 192.168.1.2 | Manual inspection | `mysql -e "SELECT gateway FROM dhcp_pools"` | Verify before and after |
| VALD-01 | Modem ARP shows only Pi MAC | Manual/live tcpdump | `sudo tcpdump -i eth0 -n -e arp -c 20` | Requires live LAN traffic |
| VALD-02 | Conntrack ESTABLISHED survive | Manual/live | `sudo conntrack -L --state ESTABLISHED | wc -l` | Compare before/after |
| VALD-03 | Pi internet works | Manual/live curl | `curl -s --max-time 10 https://example.com` | Run from Pi shell |
| VALD-04 | DNS resolution from LAN | Manual/live dig | `dig @192.168.1.2 example.com +short` | Run from LAN device or veth ns |
| VALD-05 | Accounting counters increment | Manual/live nft | `sudo nft list chain bridge accounting upload` | Run during active traffic |
| VALD-06 | Drop rules present | Manual nft | `sudo nft list chain bridge filter forward` | Check for `bridge_isolation_*` comments |
| VALD-07 | veth namespace test | Manual/live | Full veth+netns sequence (see Code Examples) | Requires root on Pi |

All validation checks are live/manual — none can be automated without Pi SSH access.

---

## Sources

### Primary (HIGH confidence — direct codebase reading)

- `backend/app/hal/linux_dhcp_driver.py` — `generate_pool_config()`, `write_pool_config()`, `trigger_reload()` functions; gateway is injected as `dhcp-option=3,{gateway}` from pool dict
- `backend/app/api/v1/dhcp.py` — `update_pool()` PATCH handler; full DB→HAL→config regeneration path traced
- `backend/app/models/dhcp_pool.py` — `DhcpPool` model; `gateway` field is `Column(String(15), nullable=False)` with default `"192.168.1.1"`
- `backend/app/hal/linux_nftables.py` — `ensure_bridge_isolation()` function confirming drop rules are placed in `bridge filter forward` chain with `bridge_isolation_lan_wan`/`bridge_isolation_wan_lan` comments
- `backend/app/main.py` — lifespan confirms `ensure_bridge_isolation()` and `ensure_bridge_isolation_persistence()` are called on every backend start
- `.planning/ROADMAP.md` — Phase 5 plan structure (05-01, 05-02) pre-specified

### Secondary (MEDIUM confidence)

- `.planning/phases/04-startup-and-persistence/04-RESEARCH.md` — nftables.service boot ordering; persistence mechanism confirmed working
- `.planning/STATE.md` — Decision log confirming "DHCP gateway .2: Pi is now the router, must be the gateway"

### Tertiary (LOW confidence, training knowledge)

- Linux `ip netns` / veth pair mechanics for VALD-07 — standard Linux networking; well-documented behavior, not project-specific

---

## Metadata

**Confidence breakdown:**
- DHCP-01, DHCP-02 (gateway change): HIGH — full code path traced, no new code needed
- VALD-01 through VALD-06: HIGH — all verify existing Phase 1-4 work; commands are standard Linux tools
- VALD-07 (veth namespace): MEDIUM — veth mechanics are standard but Pi-specific network topology (br0 membership) adds uncertainty
- Pitfalls: HIGH — pitfalls derived from direct code reading, not training data assumptions

**Research date:** 2026-03-03
**Valid until:** 2027-03-03 (DHCP and nftables fundamentals are stable)
