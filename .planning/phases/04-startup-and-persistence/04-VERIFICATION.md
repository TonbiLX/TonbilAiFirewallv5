---
phase: 04-startup-and-persistence
verified: 2026-03-03T17:55:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 4: Startup and Persistence Verification Report

**Phase Goal:** The router mode configuration survives backend restarts and Pi reboots — no manual intervention is needed to re-apply isolation after a restart
**Verified:** 2026-03-03T17:55:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `main.py` lifespan calls `ensure_bridge_isolation()` instead of `ensure_bridge_masquerade()` on backend startup | VERIFIED | Line 330 of `main.py`: `await ensure_bridge_isolation()`; `ensure_bridge_masquerade` does not appear anywhere in `main.py` |
| 2 | `main.py` lifespan calls `ensure_bridge_isolation_persistence()` after isolation succeeds | VERIFIED | Line 331 of `main.py`: `await ensure_bridge_isolation_persistence()`; called in the same try block immediately after isolation |
| 3 | sysctl persistence file content contains ip_forward=1, bridge-nf-call-iptables=1, send_redirects=0 | VERIFIED | `_write_sysctl_persistence()` (lines 1350-1370) writes all four params to `/etc/sysctl.d/99-bridge-isolation.conf` via `sudo tee` |
| 4 | modules-load.d file contains br_netfilter | VERIFIED | `_write_modules_persistence()` (lines 1373-1389) writes `br_netfilter` to `/etc/modules-load.d/99-bridge-isolation.conf` via `sudo tee` |
| 5 | nftables.service is enabled for boot | VERIFIED | `_enable_nftables_service()` (lines 1392-1403) runs `sudo systemctl enable nftables.service` |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/hal/linux_nftables.py` | `ensure_bridge_isolation_persistence()` function with sysctl.d, modules-load.d, and nftables.service enable | VERIFIED | Four new async functions found: `_write_sysctl_persistence`, `_write_modules_persistence`, `_enable_nftables_service`, `ensure_bridge_isolation_persistence`. 72 lines of substantive implementation. Python AST parse: valid. |
| `backend/app/main.py` | Lifespan swap from `ensure_bridge_masquerade` to `ensure_bridge_isolation` + persistence | VERIFIED | Lines 326-334: bridge isolation try/except block with both `await` calls present. `ensure_bridge_masquerade` fully absent. Python AST parse: valid. |

**Artifact Level Summary:**

| Artifact | Level 1: Exists | Level 2: Substantive | Level 3: Wired | Final Status |
|----------|-----------------|----------------------|----------------|--------------|
| `linux_nftables.py` | Yes | Yes (72-line block, full `sudo tee` + `systemctl` implementations) | Yes (called from `main.py` via import) | VERIFIED |
| `main.py` | Yes | Yes (live import + two sequential `await` calls) | Yes (called in lifespan, both functions imported from `linux_nftables`) | VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/main.py` | `backend/app/hal/linux_nftables.py` | `from app.hal.linux_nftables import ensure_bridge_isolation, ensure_bridge_isolation_persistence` | WIRED | Line 329 of `main.py` matches the expected import pattern exactly |
| `ensure_bridge_isolation_persistence()` | `/etc/sysctl.d/99-bridge-isolation.conf` | `sudo tee` | WIRED | `_write_sysctl_persistence()` uses `asyncio.create_subprocess_exec("sudo", "tee", "/etc/sysctl.d/99-bridge-isolation.conf", ...)` |
| `ensure_bridge_isolation_persistence()` | `/etc/modules-load.d/99-bridge-isolation.conf` | `sudo tee` | WIRED | `_write_modules_persistence()` uses `asyncio.create_subprocess_exec("sudo", "tee", "/etc/modules-load.d/99-bridge-isolation.conf", ...)` |
| `ensure_bridge_isolation_persistence()` | `nftables.service` | `systemctl enable` | WIRED | `_enable_nftables_service()` uses `asyncio.create_subprocess_exec("sudo", "systemctl", "enable", "nftables.service", ...)` |
| `ensure_bridge_isolation()` (Step 7) | `/etc/nftables.conf` | `persist_nftables()` | WIRED | Line 1346 of `linux_nftables.py`: `await persist_nftables()` — nftables rules persisted to disk before persistence helpers run |

**Additional wiring note:** The ordering is correct — `ensure_bridge_isolation()` runs first (applies rules AND persists them to `/etc/nftables.conf` via Step 7), then `ensure_bridge_isolation_persistence()` enables `nftables.service` so that the already-persisted ruleset loads on next boot.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| STRT-01 | 04-01-PLAN.md | `main.py` lifespan fonksiyonu `ensure_bridge_masquerade()` yerine `ensure_bridge_isolation()` cagirmali | SATISFIED | `main.py` line 330: `await ensure_bridge_isolation()`; no reference to `ensure_bridge_masquerade` remains |
| STRT-02 | 04-01-PLAN.md | sysctl ayarlari `/etc/sysctl.d/99-bridge-isolation.conf`'a yazilmali | SATISFIED | `_write_sysctl_persistence()` writes all 4 required sysctl params (`ip_forward=1`, `bridge-nf-call-iptables=1`, `send_redirects=0` for both `all` and `br0`) |
| STRT-03 | 04-01-PLAN.md | nftables kurallari `/etc/nftables.conf`'a persist edilmeli | SATISFIED | `ensure_bridge_isolation()` Step 7 calls `persist_nftables()` (line 1346) which writes to `/etc/nftables.conf`; `nftables.service` then loads this file at boot |
| STRT-04 | 04-01-PLAN.md | br_netfilter modulu `/etc/modules-load.d/` ile otomatik yuklenecek sekilde ayarlanmali | SATISFIED | `_write_modules_persistence()` writes `br_netfilter` to `/etc/modules-load.d/99-bridge-isolation.conf` |

**Orphaned requirements check:** REQUIREMENTS.md maps STRT-01, STRT-02, STRT-03, STRT-04 to Phase 4. All four are claimed in 04-01-PLAN.md. No orphaned requirements.

**All 4 requirements: SATISFIED.**

---

### Anti-Patterns Found

| File | Lines | Pattern | Severity | Impact |
|------|-------|---------|----------|--------|
| — | — | — | — | No anti-patterns found in new or modified code sections |

Scanned lines 1350-1420 of `linux_nftables.py` and lines 326-334 of `main.py` for: TODO, FIXME, XXX, HACK, PLACEHOLDER, `return null`, `return {}`, `return []`, empty `pass` bodies. All clear.

---

### Human Verification Required

These items cannot be verified programmatically and require a live Pi to confirm:

#### 1. Post-reboot nftables ruleset

**Test:** Run `sudo reboot` on the Pi, then after boot: `sudo nft list ruleset`
**Expected:** The forward chain in the `bridge filter` table contains rules with comments `bridge_isolation_lan_wan` and `bridge_isolation_wan_lan`
**Why human:** Requires physical/SSH access to the Pi after reboot; cannot verify `nftables.service` actually loaded `/etc/nftables.conf` from local code inspection alone

#### 2. Post-reboot sysctl values

**Test:** After reboot: `sysctl net.ipv4.ip_forward` and `sysctl net.bridge.bridge-nf-call-iptables`
**Expected:** Both return `1`
**Why human:** Requires the Pi to apply `/etc/sysctl.d/99-bridge-isolation.conf` on boot; verifiable only on a live system

#### 3. Post-reboot br_netfilter module load

**Test:** After reboot: `lsmod | grep br_netfilter`
**Expected:** `br_netfilter` is listed (loaded without manual `modprobe`)
**Why human:** Requires the Pi to process `/etc/modules-load.d/99-bridge-isolation.conf` on boot

#### 4. Backend restart isolation re-application

**Test:** `sudo systemctl restart tonbilaios-backend`, then `sudo nft list ruleset`
**Expected:** Bridge isolation rules are present (idempotent re-apply on service restart)
**Why human:** Requires observing the backend lifespan execution on a running Pi

---

### Gaps Summary

No gaps. All must-haves from the PLAN frontmatter are fully implemented:

- All four new async functions exist in `linux_nftables.py` in the correct position (between `ensure_bridge_isolation()` and `remove_bridge_isolation()`)
- Both modified files have valid Python syntax
- `main.py` no longer references `ensure_bridge_masquerade` anywhere
- Both sequential `await` calls are present in the lifespan try block
- The STRT-03 persistence path (via `ensure_bridge_isolation()` Step 7 → `persist_nftables()`) was already established in Phase 1 and remains intact
- Both task commits (85991bf, 049ab92) verified as real commits in git history

The phase goal is code-complete. The three human verification items (items 1-4 above) are the only remaining validation steps, which are by nature live-system tests belonging to Phase 5 (VALD-* requirements).

---

_Verified: 2026-03-03T17:55:00Z_
_Verifier: Claude (gsd-verifier)_
