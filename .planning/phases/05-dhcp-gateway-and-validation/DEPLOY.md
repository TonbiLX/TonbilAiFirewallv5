# DHCP Gateway Change Deployment Procedure
# Phase 05: DHCP Gateway Update — 192.168.1.1 → 192.168.1.2

## Purpose

After bridge isolation (Phases 1–4), the Pi (192.168.1.2) is the router. All LAN devices must
receive 192.168.1.2 as their default gateway and DNS server instead of the modem (192.168.1.1).
This document describes the step-by-step procedure to update the live Pi DHCP pools safely.

---

## Pre-Requisites

Before starting, verify all of the following:

- Pi is running `tonbilaios-backend` (`sudo systemctl status tonbilaios-backend`)
- Bridge isolation is active (Phases 1–4 deployed and confirmed)
- Pi is the default gateway for the LAN (`ip route` on any LAN device shows `default via 192.168.1.2`)
- SSH access is available: `ssh -J admin@pi.tonbil.com:2323 admin@192.168.1.2` (password: benbuyum9087)
- You have an API token or access to SQL on the Pi

---

## Step 1: Verify Current State

SSH into the Pi and query the current DHCP pool configuration:

```bash
mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios \
  -e "SELECT id, name, gateway, dns_servers, lease_time_seconds FROM dhcp_pools;"
```

Expected output: `gateway` column shows `192.168.1.1` for all pools.

If gateway already shows `192.168.1.2`, this procedure has already been applied — stop here.

---

## Step 2: Short-Lease Pre-Staging (Reduce Lease to 5 Minutes)

Before changing the gateway, reduce the DHCP lease time so devices renew quickly and pick up
the new gateway. This avoids a long wait for devices to switch over.

### Via API (preferred — triggers automatic dnsmasq reload):

```bash
# Get an auth token first
TOKEN=$(curl -s -X POST http://192.168.1.2:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Reduce lease time for pool 1 (Ana AG)
curl -X PATCH http://192.168.1.2:8000/api/v1/dhcp/pools/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lease_time_seconds": 300}'

# Reduce lease time for pool 2 (Misafir AG) if it exists
curl -X PATCH http://192.168.1.2:8000/api/v1/dhcp/pools/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lease_time_seconds": 300}'
```

### Via SQL alternative (requires backend restart to regenerate dnsmasq config):

```bash
mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios \
  -e "UPDATE dhcp_pools SET lease_time_seconds=300, updated_at=NOW();"

sudo systemctl restart tonbilaios-backend
```

**Wait 5–10 minutes** for all connected devices to renew their leases with the short TTL. After
this waiting period, all devices will renew leases every 5 minutes, so the gateway change will
propagate within one renewal cycle.

---

## Step 3: Change Gateway to 192.168.1.2

### Via API (preferred — triggers automatic dnsmasq reload via generate_pool_config + SIGHUP):

```bash
# Update pool 1 (Ana AG)
curl -X PATCH http://192.168.1.2:8000/api/v1/dhcp/pools/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"gateway": "192.168.1.2", "dns_servers": ["192.168.1.2"]}'

# Update pool 2 (Misafir AG) if it exists
curl -X PATCH http://192.168.1.2:8000/api/v1/dhcp/pools/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"gateway": "192.168.1.2", "dns_servers": ["192.168.1.2"]}'
```

### Via SQL alternative (requires backend restart):

```bash
mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios \
  -e "UPDATE dhcp_pools SET gateway='192.168.1.2', dns_servers=JSON_ARRAY('192.168.1.2'), updated_at=NOW();"

sudo systemctl restart tonbilaios-backend
```

---

## Step 4: Verify dnsmasq Config Files

Confirm the dnsmasq config files have been regenerated with the new gateway:

```bash
cat /etc/dnsmasq.d/pool-1.conf | grep dhcp-option
```

Expected output:
```
dhcp-option=3,192.168.1.2
dhcp-option=6,192.168.1.2
```

- `dhcp-option=3` is the default gateway (router option)
- `dhcp-option=6` is the DNS server option

---

## Step 5: Verify Database State

Confirm the database now reflects the new gateway:

```bash
mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios \
  -e "SELECT id, name, gateway, dns_servers, lease_time_seconds FROM dhcp_pools;"
```

Expected: `gateway` column shows `192.168.1.2` for all pools.

---

## Step 6: Test from a LAN Device

Force a DHCP lease renewal on a LAN device and verify it receives the new gateway:

**On a Linux/Mac device:**
```bash
# Force lease renewal
sudo dhclient -r && sudo dhclient

# Verify new default gateway
ip route show | grep default
# Expected: default via 192.168.1.2 dev <interface>

# Verify internet connectivity
curl -s https://example.com | head -5
```

**On Windows:**
```cmd
ipconfig /release
ipconfig /renew
ipconfig /all
REM Check "Default Gateway" field — should show 192.168.1.2
```

---

## Step 7: Restore Lease Time to 24 Hours

After confirming all devices are working correctly with the new gateway, restore the standard lease time:

### Via API:
```bash
# Restore pool 1 (Ana AG)
curl -X PATCH http://192.168.1.2:8000/api/v1/dhcp/pools/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lease_time_seconds": 86400}'

# Restore pool 2 (Misafir AG) if it exists
curl -X PATCH http://192.168.1.2:8000/api/v1/dhcp/pools/2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lease_time_seconds": 86400}'
```

### Via SQL alternative:
```bash
mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios \
  -e "UPDATE dhcp_pools SET lease_time_seconds=86400, updated_at=NOW() WHERE name='Ana AG';"

mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios \
  -e "UPDATE dhcp_pools SET lease_time_seconds=3600, updated_at=NOW() WHERE name='Misafir AG';"

sudo systemctl restart tonbilaios-backend
```

Note: Misafir AG has a standard 1-hour lease (3600s), not 24 hours.

---

## Rollback Procedure

If devices lose internet connectivity after the gateway change:

```bash
# Revert via SQL (fast)
mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios \
  -e "UPDATE dhcp_pools SET gateway='192.168.1.1', dns_servers=JSON_ARRAY('192.168.1.1'), updated_at=NOW();"

sudo systemctl restart tonbilaios-backend
```

Then force a lease renewal on affected devices (Step 6 above).

**Root cause to investigate before re-applying:**
- Verify bridge isolation is actually active (`nft list ruleset | grep br0`)
- Verify Pi NAT masquerade is working (`nft list table ip nat`)
- Verify Pi can reach the internet directly (`curl -s https://example.com` from Pi)

---

## Important Notes

1. **API vs SQL:** The PATCH API endpoint triggers the full config regeneration path automatically:
   `DB update → generate_pool_config() → write_pool_config() → dnsmasq SIGHUP`. Direct SQL
   updates require a backend restart (`sudo systemctl restart tonbilaios-backend`) to regenerate
   dnsmasq config files.

2. **Existing connections:** Active connections survive the gateway change. conntrack entries are
   maintained by the NAT MASQUERADE rule which has been active since Phase 1. Only new DHCP
   leases will receive the new gateway.

3. **Short-lease pre-staging is critical:** Without it, devices with 24-hour leases will continue
   using 192.168.1.1 as gateway for up to 24 hours after the change, causing connectivity issues
   if modem routing is disabled.

4. **DNS propagation:** Devices receiving 192.168.1.2 as DNS will now use the Pi's built-in
   DNS proxy (dnsmasq + dns_proxy.py) for all DNS resolution, enabling profile-based filtering.
