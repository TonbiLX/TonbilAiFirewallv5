---
phase: 05-dhcp-gateway-and-validation
plan: "01"
subsystem: dhcp
tags: [dhcp, gateway, seed-data, defaults, deployment]
dependency_graph:
  requires: [04-01]
  provides: [DHCP-01, DHCP-02]
  affects: [dns_proxy, dnsmasq, device-onboarding]
tech_stack:
  added: []
  patterns:
    - SQLAlchemy Column default update
    - Pydantic schema default update
    - Seed data canonical gateway
key_files:
  created:
    - .planning/phases/05-dhcp-gateway-and-validation/DEPLOY.md
  modified:
    - backend/app/seed/scenarios.py
    - backend/app/models/dhcp_pool.py
    - backend/app/schemas/dhcp_pool.py
decisions:
  - "DHCP gateway defaults updated to 192.168.1.2 throughout codebase (seed, model, schema)"
  - "linux_dhcp_driver.py left unchanged — already reads gateway from pool dict with no hardcoded default"
  - "Short-lease pre-staging (300s) documented as mandatory step before live gateway change to minimize device-side switchover window"
metrics:
  duration: "4 min"
  completed: "2026-03-03"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 3
---

# Phase 05 Plan 01: DHCP Gateway Default Update Summary

**One-liner:** Updated all DHCP gateway and DNS defaults from modem IP (192.168.1.1) to Pi router IP (192.168.1.2) in seed data, model, and schema; produced step-by-step DEPLOY.md for live Pi database migration with short-lease pre-staging.

## What Was Built

After bridge isolation (Phases 1-4), the Pi (192.168.1.2) is the router for all LAN traffic.
Code defaults still pointed to 192.168.1.1 (the modem). This plan corrected all code defaults
and produced a safe deployment procedure for the live Pi database change.

### Changes Made

**backend/app/seed/scenarios.py** (commit ac22cdd):
- `DEFAULT_DHCP_POOLS["Ana AG"]["gateway"]`: `"192.168.1.1"` → `"192.168.1.2"`
- `DEFAULT_DHCP_POOLS["Ana AG"]["dns_servers"]`: `["192.168.1.1"]` → `["192.168.1.2"]`
- `DEFAULT_DHCP_POOLS["Misafir AG"]["gateway"]`: `"192.168.1.1"` → `"192.168.1.2"`
- `DEFAULT_DHCP_POOLS["Misafir AG"]["dns_servers"]`: `["192.168.1.1"]` → `["192.168.1.2"]`

**backend/app/models/dhcp_pool.py** (commit ac22cdd):
- `dns_servers` column `default`: `["192.168.1.1"]` → `["192.168.1.2"]`
- Gateway column comment updated from `"192.168.1.1"` to `"192.168.1.2"`

**backend/app/schemas/dhcp_pool.py** (commit ac22cdd):
- `DhcpPoolCreate.dns_servers` default: `["192.168.1.1"]` → `["192.168.1.2"]`
- `DhcpPoolResponse.dns_servers` default: `["192.168.1.1"]` → `["192.168.1.2"]`

**.planning/phases/05-dhcp-gateway-and-validation/DEPLOY.md** (commit c859e0d):
- 239-line deployment procedure covering 7 steps + rollback
- Pre-requisite checklist (bridge isolation, SSH access, backend running)
- Step 2: short-lease pre-staging (300s) with 5-10 min wait
- Step 3: gateway change via API (auto-reload) or SQL + restart
- Steps 4-5: dnsmasq config and DB verification commands
- Step 6: end-device test (Linux/Mac and Windows instructions)
- Step 7: restore standard lease times (86400s Ana AG, 3600s Misafir AG)
- Rollback: SQL revert + restart + root cause checklist

### Not Changed (Intentionally)

- `backend/app/hal/linux_dhcp_driver.py`: Already reads gateway from pool dict with
  `pool.get("gateway", "")` — no hardcoded default, no change needed.
- `backend/app/api/v1/dhcp.py`: Config regeneration path is correct as-is.
- Existing live Pi database: Changed only via DEPLOY.md procedure, not automated.

## Decisions Made

1. **linux_dhcp_driver.py unchanged:** The driver correctly reads gateway from the pool dict at
   runtime. No hardcoded default exists, so no change was required.

2. **Short-lease pre-staging is mandatory:** Without reducing lease time before the gateway
   change, devices with 24-hour leases would continue using 192.168.1.1 for up to 24 hours,
   causing connectivity failures if the modem stops routing for LAN devices.

3. **API method preferred over SQL:** The PATCH endpoint triggers the full config regeneration
   pipeline automatically (DB → generate_pool_config → write_pool_config → dnsmasq SIGHUP).
   SQL updates require a manual `sudo systemctl restart tonbilaios-backend` to regenerate files.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | ac22cdd | feat(05-01): update DHCP gateway and DNS defaults from 192.168.1.1 to 192.168.1.2 |
| Task 2 | c859e0d | docs(05-01): add DEPLOY.md for live Pi DHCP gateway change procedure |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- backend/app/seed/scenarios.py: FOUND, gateway/dns_servers updated to 192.168.1.2
- backend/app/models/dhcp_pool.py: FOUND, dns_servers default updated to 192.168.1.2
- backend/app/schemas/dhcp_pool.py: FOUND, both DhcpPoolCreate and DhcpPoolResponse updated
- .planning/phases/05-dhcp-gateway-and-validation/DEPLOY.md: FOUND (239 lines, min 30 required)
- Commit ac22cdd: FOUND
- Commit c859e0d: FOUND
- No remaining 192.168.1.1 in gateway/dns_servers fields across all three modified files: CONFIRMED
