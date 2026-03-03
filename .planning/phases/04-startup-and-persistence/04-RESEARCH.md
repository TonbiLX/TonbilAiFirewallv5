# Phase 4: Startup and Persistence — Research

**Researched:** 2026-03-03
**Domain:** Linux boot persistence — systemd, nftables, sysctl.d, modules-load.d, FastAPI lifespan
**Confidence:** HIGH (all critical findings verified with official docs or multiple corroborating sources)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| STRT-01 | `main.py` lifespan calls `ensure_bridge_isolation()` instead of `ensure_bridge_masquerade()` | Pattern documented in current codebase; swap is a one-line change at line ~330 |
| STRT-02 | sysctl settings written to `/etc/sysctl.d/99-bridge-isolation.conf` | sysctl.d file format verified via Debian manpages; naming convention and content established |
| STRT-03 | nftables rules persisted to `/etc/nftables.conf` via `persist_nftables()` + `nftables.service` enabled | `persist_nftables()` already exists in codebase; service enable pattern verified on Pi OS Bookworm |
| STRT-04 | `br_netfilter` loaded at boot via `/etc/modules-load.d/99-bridge-isolation.conf` | modules-load.d mechanism verified; critical boot ordering dependency documented |
</phase_requirements>

---

## Summary

Phase 4 makes the router-mode configuration survive reboots. The work has three parallel concerns: (1) the FastAPI lifespan swap from `ensure_bridge_masquerade()` to `ensure_bridge_isolation()`, (2) kernel persistence via `sysctl.d` and `modules-load.d` files, and (3) nftables ruleset persistence via `/etc/nftables.conf` and the `nftables.service` systemd unit.

The most dangerous aspect of this phase is the boot ordering dependency between `br_netfilter` and the sysctl that depends on it. If `br_netfilter` is not loaded before `systemd-sysctl.service` runs, the `net.bridge.bridge-nf-call-iptables=1` setting silently fails — the parameter does not exist in `/proc/sys/net/bridge/` until the module is present. The fix is simple: adding `br_netfilter` to `/etc/modules-load.d/` ensures `systemd-modules-load.service` loads it before `systemd-sysctl.service` applies parameters. This ordering is guaranteed by systemd's unit dependency graph.

The nftables persistence story has one critical discovery: on Raspberry Pi OS Bookworm, `nftables.service` is **installed but not enabled by default**. All the `nft` commands work in the current session, but the ruleset is ephemeral. The `persist_nftables()` function already writes `/etc/nftables.conf` correctly (with `flush ruleset` header), but this is useless unless `nftables.service` is enabled. A one-time `systemctl enable nftables.service` call during phase execution is mandatory.

The existing `persist_nftables()` writes the complete live ruleset (all tables: `bridge filter`, `bridge accounting`, `bridge masquerade_fix` if present, `inet tonbilai`, `inet nat`) in a single `nft list ruleset` snapshot. The `flush ruleset` header ensures atomic replacement on boot — the kernel processes the file as a single transaction. This correctly preserves all bridge and inet tables in one file.

**Primary recommendation:** Write three files (`sysctl.d`, `modules-load.d` conf, and a one-time `systemctl enable nftables`), swap the lifespan call, and test with `sudo reboot`. The entire phase is one plan.

---

## Standard Stack

### Core (system tools — no library installs required)

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `/etc/sysctl.d/*.conf` | systemd sysctl.d(5) | Persistent kernel parameter configuration | Standard Debian mechanism; read by `systemd-sysctl.service` on boot |
| `/etc/modules-load.d/*.conf` | systemd modules-load.d(5) | Kernel module auto-load at boot | Standard Debian mechanism; read by `systemd-modules-load.service` on boot |
| `/etc/nftables.conf` | nftables | Ruleset loaded by `nftables.service` on boot | Default path for Debian `nftables.service` unit |
| `nftables.service` | Debian package | Loads `/etc/nftables.conf` on boot via `nft -f` | Installed on Pi OS Bookworm; must be explicitly enabled |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `sudo tee` | coreutils | Write root-owned system files from Python | Used by existing `persist_nftables()` — same pattern for sysctl.d/modules-load.d |
| `systemctl enable nftables.service` | systemd | Enable nftables.service so it starts on boot | One-time operation; idempotent |
| `asyncio.create_subprocess_exec` | Python stdlib | Run `systemctl enable` from lifespan | Already used throughout codebase |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `/etc/sysctl.d/99-bridge-isolation.conf` | Runtime-only sysctl via `sysctl -w` | Runtime-only does not survive reboot — already done in `ensure_bridge_isolation()` |
| `/etc/modules-load.d/99-bridge-isolation.conf` | `udev` rule for br_netfilter | udev rule is the official "recommended" approach but requires extra file and is less readable |
| `nftables.service` | Custom ExecStartPre in backend service | Hand-rolling a system service is worse than using the OS-provided mechanism |

---

## Architecture Patterns

### Boot Sequence — Correct Ordering

```
Boot sequence (relevant units):
  1. systemd-modules-load.service     ← reads /etc/modules-load.d/
     └── loads br_netfilter
  2. systemd-sysctl.service           ← reads /etc/sysctl.d/
     └── applies net.bridge.bridge-nf-call-iptables=1 (br_netfilter now present)
     └── applies net.ipv4.ip_forward=1
     └── applies net.ipv4.conf.all.send_redirects=0
     └── applies net.ipv4.conf.br0.send_redirects=0
  3. nftables.service                 ← reads /etc/nftables.conf
     └── nft -f /etc/nftables.conf (flush ruleset + all tables atomically)
  4. tonbilaios-backend.service       ← After=network.target
     └── lifespan: calls ensure_bridge_isolation() (idempotent — rules already present)
```

Steps 1 and 2 are guaranteed in order by systemd's dependency graph. Steps 3 and 4 happen later in boot; `ensure_bridge_isolation()` must remain idempotent so calling it on an already-isolated system is a no-op.

### Pattern 1: sysctl.d Persistence File

**What:** A `.conf` file in `/etc/sysctl.d/` with all sysctl parameters that must survive reboot.
**When to use:** Any sysctl that `ensure_bridge_isolation()` sets via `sysctl -w`.

```
# /etc/sysctl.d/99-bridge-isolation.conf
# TonbilAiOS: Bridge isolation (router mode) kernel parameters
# Requires br_netfilter in /etc/modules-load.d/99-bridge-isolation.conf

net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.br0.send_redirects = 0
```

Naming convention: `99-` prefix puts this file after vendor defaults (`10-` range for `/usr/`) so local config wins. [Source: Debian manpages sysctl.d(5), "range 60-90 for /etc/"]

### Pattern 2: modules-load.d Persistence File

**What:** A plain-text `.conf` file listing one module name per line.
**When to use:** `br_netfilter` must load before `systemd-sysctl.service` reads the sysctl.d file.

```
# /etc/modules-load.d/99-bridge-isolation.conf
# TonbilAiOS: br_netfilter required for bridge-nf-call-iptables sysctl
br_netfilter
```

**Critical:** This is the ONLY correct approach for `net.bridge.*` parameters. Without the module loaded before `systemd-sysctl.service` runs, the bridge sysctl parameters do not exist in `/proc/sys/net/bridge/` and are silently skipped. [Source: Debian manpages sysctl.d(5) — "systemd-sysctl.service runs during early boot and will not configure such parameters if they become available after it has run"]

### Pattern 3: nftables.conf Persistence

**What:** `persist_nftables()` already does this correctly — it writes `nft list ruleset` output to `/etc/nftables.conf` with `flush ruleset` prefix.
**When to use:** After any nftables change that must survive reboot (already called in `ensure_bridge_isolation()`).

The `flush ruleset` header is critical: it ensures the entire ruleset is replaced atomically when `nftables.service` loads the file on boot. Without it, old rules may persist alongside new rules.

The format that `nft list ruleset` produces is the correct input format for `nft -f`. All families (bridge, inet) are output in a single `nft list ruleset` call and written to one file — this is correct behavior and matches how `nftables.service` loads rules.

### Pattern 4: Enable nftables.service

**What:** `systemctl enable nftables.service` — one-time, idempotent.
**When to use:** Must be called from the lifespan or during installation setup. Without this, `/etc/nftables.conf` is updated but never loaded on boot.

**Confirmed Pi OS Bookworm behavior:** On Raspberry Pi OS Bookworm, `nftables.service` is **installed but disabled by default**. All `nft` commands work at runtime, but the service does not start on boot unless explicitly enabled. [Source: Raspberry Pi Forums — "nftables appears to be running. All the commands work. But the nftables service is not enabled so all the nft commands are just fake."]

### Pattern 5: Lifespan Swap in main.py

**What:** Replace the `ensure_bridge_masquerade()` call with `ensure_bridge_isolation()` in the FastAPI lifespan.

**Current code (lines ~329-334 in main.py):**
```python
try:
    from app.hal.linux_nftables import ensure_bridge_masquerade
    await ensure_bridge_masquerade()
    logger.info("Bridge masquerade kurallari hazir (modem uyumlulugu)")
except Exception as e:
    logger.error(f"Bridge masquerade kurulum hatasi: {e}")
```

**Target code:**
```python
try:
    from app.hal.linux_nftables import ensure_bridge_isolation
    await ensure_bridge_isolation()
    logger.info("Bridge isolation kurallari hazir (router modu)")
except Exception as e:
    logger.error(f"Bridge isolation kurulum hatasi: {e}")
```

`ensure_bridge_isolation()` is already idempotent (comment anchors prevent double-application). The lifespan calling it on every backend restart is correct and intentional — it ensures state is re-applied even if the backend was restarted without a full reboot.

### Pattern 6: Writing System Files from Python

The existing `persist_nftables()` uses `sudo tee` to write root-owned files. Use the same pattern:

```python
async def _write_sysctl_persistence():
    content = (
        "# TonbilAiOS bridge isolation kernel parameters\n"
        "net.ipv4.ip_forward = 1\n"
        "net.bridge.bridge-nf-call-iptables = 1\n"
        "net.ipv4.conf.all.send_redirects = 0\n"
        "net.ipv4.conf.br0.send_redirects = 0\n"
    )
    proc = await asyncio.create_subprocess_exec(
        "sudo", "tee", "/etc/sysctl.d/99-bridge-isolation.conf",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate(input=content.encode())
```

### Anti-Patterns to Avoid

- **Writing sysctl.d without modules-load.d:** `net.bridge.bridge-nf-call-iptables` silently does nothing if `br_netfilter` isn't loaded when systemd-sysctl runs.
- **Using `nft save` or `iptables-save` style commands:** `nft list ruleset` piped to `/etc/nftables.conf` is the correct nftables approach — no separate save utility needed.
- **Using `iif`/`oif` (interface index) instead of `iifname`/`oifname` (name string):** Index-based rules fail at boot if the interface doesn't exist yet during rule loading. The existing code already uses `iifname`/`oifname` correctly — do not change this.
- **Relying on `ensure_bridge_isolation()` alone for persistence:** The function applies rules at runtime but does not guarantee reboot survival. Both `nftables.service` enable AND `sysctl.d`/`modules-load.d` files are required.
- **Calling `systemctl enable nftables.service` on every restart:** This is idempotent, but should be done once during setup, not in a tight loop. The lifespan should check if it needs to enable, or enable idempotently.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Module auto-load at boot | Custom systemd unit with `ExecStart=modprobe br_netfilter` | `/etc/modules-load.d/` conf file | `systemd-modules-load.service` reads this natively; drop-in unit would be fragile |
| sysctl persistence | rc.local or custom ExecStartPre in tonbilaios service | `/etc/sysctl.d/` conf file | `systemd-sysctl.service` applies these correctly at boot before any network service |
| nftables boot persistence | Custom ExecStartPre/ExecStart in tonbilaios.service | `nftables.service` + `/etc/nftables.conf` | OS-provided mechanism; survives package updates |
| Firewall rule ordering relative to network | Custom service with `After=network-online.target` workarounds | `iifname`/`oifname` string match in rules | String-based interface matching works even when interface doesn't exist at rule load time |

**Key insight:** All four persistence requirements have a standard Linux/systemd mechanism. None require custom scripts or new systemd units.

---

## Common Pitfalls

### Pitfall 1: br_netfilter Boot Order — The Silent Failure

**What goes wrong:** After reboot, `sysctl net.bridge.bridge-nf-call-iptables` returns an error ("cannot stat") or retains its default value of 0. This means bridge traffic does NOT pass through the inet hook, breaking the existing MAC-block rules in `inet tonbilai forward`.

**Why it happens:** `/etc/sysctl.d/99-bridge-isolation.conf` is processed by `systemd-sysctl.service` early in boot. If `br_netfilter` is not loaded yet at that point, the sysctl path `/proc/sys/net/bridge/bridge-nf-call-iptables` does not exist and the parameter is silently skipped.

**How to avoid:** `br_netfilter` MUST be in `/etc/modules-load.d/99-bridge-isolation.conf`. `systemd-modules-load.service` runs before `systemd-sysctl.service` in the boot sequence, guaranteeing the module is present when sysctls are applied.

**Warning signs:**
- After reboot: `cat /proc/sys/net/bridge/bridge-nf-call-iptables` returns error or 0
- After reboot: `lsmod | grep br_netfilter` shows module not loaded
- After reboot: MAC-based firewall rules appear in `nft list ruleset` but do NOT block anything

### Pitfall 2: nftables.service Not Enabled

**What goes wrong:** After reboot, `nft list ruleset` shows only the default empty ruleset. All isolation rules, accounting chains, and mark chains are gone.

**Why it happens:** On Raspberry Pi OS Bookworm, `nftables.service` is installed but disabled. `persist_nftables()` writes `/etc/nftables.conf` correctly, but the service never loads it on boot.

**How to avoid:** Run `sudo systemctl enable nftables.service` once. Verify with `systemctl is-enabled nftables`.

**Warning signs:**
- After reboot: `nft list ruleset` shows empty or default minimal ruleset
- `systemctl is-enabled nftables` returns `disabled`

### Pitfall 3: ensure_bridge_isolation() Called Before nftables.service Loads on Restart

**What goes wrong:** `tonbilaios-backend.service` starts (After=network.target) and calls `ensure_bridge_isolation()`. The rules are applied. Then `nftables.service` also starts (race condition) and loads `/etc/nftables.conf`, overwriting the live ruleset with the saved state.

**Why it doesn't happen (but could):** The current `tonbilaios.service` has `After=network.target`. The `nftables.service` has `Before=network-pre.target` (loads before networking). By the time `tonbilaios-backend.service` starts, `nftables.service` has already run. The ordering is: nftables.service → network-pre.target → network.target → tonbilaios-backend.service. So `nftables.service` loads saved rules FIRST, then `ensure_bridge_isolation()` is called, which is a no-op because the rules are already present (idempotent). No race condition.

**Warning signs:** Would manifest as `ensure_bridge_isolation()` finding rules already present via comment anchors and logging "bridge_isolation rules already present."

### Pitfall 4: Stale sysctl.d File After Rollback

**What goes wrong:** If `remove_bridge_isolation()` is called to return to transparent bridge mode, the `/etc/sysctl.d/99-bridge-isolation.conf` and `/etc/modules-load.d/99-bridge-isolation.conf` files persist. On next reboot, `ip_forward=1` and `bridge-nf-call-iptables=1` are still applied even though bridge isolation is inactive.

**Impact:** Low severity for `ip_forward=1` (harmless in bridge mode). The `bridge-nf-call-iptables=1` causes bridge traffic to traverse the inet filter, which is not harmful in transparent bridge mode but adds unnecessary overhead.

**How to avoid:** `remove_bridge_isolation()` should optionally remove the persistence files, or the phase should document that rollback does not clean up kernel persistence files (acceptable for now given the project is moving toward permanent router mode).

### Pitfall 5: ensure_bridge_isolation() Not Idempotent After nftables.service Reload

**Why this is a non-issue (already solved):** `ensure_bridge_isolation()` uses comment anchors (`bridge_isolation_lan_wan`, `bridge_isolation_wan_lan`, `bridge_lan_masq`) to detect existing rules via `nft list ruleset` grep. After `nftables.service` loads the persisted ruleset on boot, these comments are preserved, so `ensure_bridge_isolation()` finds them and skips rule addition. The comment-based idempotency is boot-safe because `nft list ruleset` output includes comments.

---

## Code Examples

### Write sysctl.d File

```python
# Source: pattern from existing persist_nftables() in linux_nftables.py
async def _write_sysctl_persistence():
    """Write bridge isolation sysctl settings to /etc/sysctl.d/."""
    content = (
        "# TonbilAiOS: Bridge isolation (router mode) kernel parameters\n"
        "# Requires br_netfilter in /etc/modules-load.d/99-bridge-isolation.conf\n"
        "net.ipv4.ip_forward = 1\n"
        "net.bridge.bridge-nf-call-iptables = 1\n"
        "net.ipv4.conf.all.send_redirects = 0\n"
        "net.ipv4.conf.br0.send_redirects = 0\n"
    )
    proc = await asyncio.create_subprocess_exec(
        "sudo", "tee", "/etc/sysctl.d/99-bridge-isolation.conf",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=content.encode())
    if proc.returncode == 0:
        logger.info("sysctl persistence written: /etc/sysctl.d/99-bridge-isolation.conf")
    else:
        logger.error(f"sysctl persist failed: {stderr.decode().strip()}")
```

### Write modules-load.d File

```python
# Source: pattern from existing persist_nftables() in linux_nftables.py
async def _write_modules_persistence():
    """Write br_netfilter to /etc/modules-load.d/ for boot auto-load."""
    content = (
        "# TonbilAiOS: br_netfilter required for net.bridge.bridge-nf-call-iptables sysctl\n"
        "br_netfilter\n"
    )
    proc = await asyncio.create_subprocess_exec(
        "sudo", "tee", "/etc/modules-load.d/99-bridge-isolation.conf",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=content.encode())
    if proc.returncode == 0:
        logger.info("Module persistence written: /etc/modules-load.d/99-bridge-isolation.conf")
    else:
        logger.error(f"Module persist failed: {stderr.decode().strip()}")
```

### Enable nftables.service

```python
async def _enable_nftables_service():
    """Enable nftables.service so /etc/nftables.conf loads on boot.

    Idempotent — calling enable on an already-enabled service is a no-op.
    On Raspberry Pi OS Bookworm, nftables is installed but NOT enabled by default.
    """
    proc = await asyncio.create_subprocess_exec(
        "sudo", "systemctl", "enable", "nftables.service",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        logger.info("nftables.service enabled for boot persistence")
    else:
        logger.error(f"nftables.service enable failed: {stderr.decode().strip()}")
```

### Combined ensure_bridge_persistence() Function

All three persistence actions belong together — write a single function in `linux_nftables.py`:

```python
async def ensure_bridge_isolation_persistence():
    """Persist bridge isolation settings across reboots.

    Writes:
      /etc/sysctl.d/99-bridge-isolation.conf  — kernel params
      /etc/modules-load.d/99-bridge-isolation.conf — br_netfilter auto-load
      Enables nftables.service for /etc/nftables.conf boot load

    Safe to call multiple times. Called from main.py lifespan after
    ensure_bridge_isolation() succeeds.
    """
    await _write_sysctl_persistence()
    await _write_modules_persistence()
    await _enable_nftables_service()
    # nftables.conf is already written by persist_nftables() inside ensure_bridge_isolation()
```

### main.py Lifespan Final Form

```python
# BEFORE (Phase 3 and earlier):
try:
    from app.hal.linux_nftables import ensure_bridge_masquerade
    await ensure_bridge_masquerade()
    logger.info("Bridge masquerade kurallari hazir (modem uyumlulugu)")
except Exception as e:
    logger.error(f"Bridge masquerade kurulum hatasi: {e}")

# AFTER (Phase 4):
try:
    from app.hal.linux_nftables import ensure_bridge_isolation, ensure_bridge_isolation_persistence
    await ensure_bridge_isolation()
    await ensure_bridge_isolation_persistence()
    logger.info("Bridge isolation ve persistence kurallari hazir (router modu)")
except Exception as e:
    logger.error(f"Bridge isolation kurulum hatasi: {e}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `iptables-save` / `iptables-restore` | `nft list ruleset` → `/etc/nftables.conf` | Debian 10 Buster (2019) | All families (bridge, inet) in one file |
| `rc.local` for module loading | `/etc/modules-load.d/` | systemd adoption (~2012, standard by 2020) | Declarative, ordered correctly by systemd |
| `/etc/sysctl.conf` direct edits | `/etc/sysctl.d/*.conf` drop-in files | Debian 7 Wheezy / systemd | Package-safe; multiple files, last writer wins |
| Custom firewall init scripts | `nftables.service` (systemd unit) | Debian 10 | Ordered before network-pre.target |

**Deprecated/outdated:**
- `iptables-save`/`iptables-restore` for Pi OS Bookworm: replaced by nftables
- `ebtables` for bridge filtering: replaced by nftables bridge family
- `/etc/network/if-pre-up.d/` scripts for nftables: replaced by `nftables.service`

---

## Open Questions

1. **Does `tonbilaios.service` need `After=nftables.service`?**
   - What we know: `nftables.service` has `Before=network-pre.target`; `tonbilaios.service` has `After=network.target`. This ordering guarantees nftables loads before the backend.
   - What's unclear: The exact Raspberry Pi OS Bookworm nftables.service unit file was not retrieved directly; the ordering assumptions are based on Debian's general nftables package behavior.
   - Recommendation: After enabling nftables.service on the Pi, verify ordering with `systemctl show nftables.service --property=Before,After,Wants`. If `Before=network-pre.target` is present, no change to `tonbilaios.service` is needed.

2. **Does the existing `nft list ruleset` output include the `bridge filter forward` chain?**
   - What we know: `nft list ruleset` outputs all families. `ensure_bridge_isolation()` creates `bridge filter forward` drop rules. The `persist_nftables()` function captures the full `nft list ruleset` output.
   - What's unclear: Whether `bridge filter forward` rules with `iifname "eth1"` survive the boot reload correctly (interface existence at load time).
   - Recommendation: After reboot verification, run `nft list chain bridge filter forward` and confirm the drop rules are present. This is the explicit Success Criterion 2 of Phase 4.

3. **Will `ensure_bridge_isolation_persistence()` need to be called on every backend restart or just once?**
   - What we know: Writing sysctl.d and modules-load.d files is idempotent (overwriting with same content). `systemctl enable` is idempotent.
   - Recommendation: Call on every backend start in the lifespan — the cost is three small file writes, and it ensures persistence even if a system update regenerates the files.

---

## Validation Architecture

> Validation for this phase is manual/live (no pytest). All success criteria require live Pi hardware.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Command | Notes |
|--------|----------|-----------|---------|-------|
| STRT-01 | Lifespan calls ensure_bridge_isolation() | Manual inspection | `grep ensure_bridge_isolation backend/app/main.py` | Code review |
| STRT-02 | sysctl settings survive reboot | Manual/live | After reboot: `sysctl net.ipv4.ip_forward`, `sysctl net.bridge.bridge-nf-call-iptables` | Requires Pi reboot |
| STRT-03 | nftables rules survive reboot | Manual/live | After reboot: `nft list chain bridge filter forward` | Requires Pi reboot |
| STRT-04 | br_netfilter loaded at boot | Manual/live | After reboot: `lsmod | grep br_netfilter` | Requires Pi reboot |

### Verification Sequence (post-deploy checklist)

```bash
# 1. Verify files exist
cat /etc/sysctl.d/99-bridge-isolation.conf
cat /etc/modules-load.d/99-bridge-isolation.conf
cat /etc/nftables.conf | head -5  # should start with "#!/usr/sbin/nft -f" and "flush ruleset"

# 2. Verify nftables.service enabled
systemctl is-enabled nftables.service  # should return "enabled"

# 3. Reboot
sudo reboot

# 4. After reboot — verify all four requirements
lsmod | grep br_netfilter                             # STRT-04: module loaded
sysctl net.ipv4.ip_forward                            # STRT-03: = 1
sysctl net.bridge.bridge-nf-call-iptables             # STRT-02: = 1
nft list chain bridge filter forward                  # STRT-03: drop rules present
curl -s https://example.com > /dev/null && echo OK    # internet still works
```

---

## Sources

### Primary (HIGH confidence)
- Debian manpages sysctl.d(5) Bookworm — https://manpages.debian.org/bookworm/systemd/sysctl.d.5.en.html — boot ordering between systemd-modules-load and systemd-sysctl; br_netfilter dependency; modules-load.d approach
- freedesktop.org sysctl.d(5) latest — https://www.freedesktop.org/software/systemd/man/latest/sysctl.d.html — udev rule approach vs modules-load.d; exact udev rule for br_netfilter
- systemd/systemd GitHub issue #21899 — https://github.com/systemd/systemd/issues/21899 — `iifname`/`oifname` vs `iif`/`oif` at boot; interface non-existence handling
- Debian bug #866902 nftables too late in boot — https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=866902 — `Before=network-pre.target` fix; service ordering

### Secondary (MEDIUM confidence)
- Raspberry Pi Forums — Bookworm nftables ignoring /etc/nftables.conf — https://forums.raspberrypi.com/viewtopic.php?p=2331908 — confirmed nftables.service disabled by default on Pi OS Bookworm
- naturalborncoder.com nftables on Debian (2024) — https://www.naturalborncoder.com/2024/10/installing-and-configuring-nftables-on-debian/ — `/etc/nftables.conf` format; `systemctl enable nftables.service`; "service shows as exited, this is normal"
- NixOS/nixpkgs issue #71227 — https://github.com/NixOS/nixpkgs/issues/71227 — `iif`/`oif` startup problems; migration to `iifname`/`oifname`
- Server-world.info Debian 12 nftables — https://www.server-world.info/en/note?os=Debian_12&p=nftables&f=1 — `systemctl enable --now nftables` pattern
- Oracle OLCNE br_netfilter documentation — https://docs.oracle.com/en/operating-systems/olcne/1.1/start/netfilter.html — `br_netfilter` in modules-load.d pattern

### Tertiary (LOW confidence, from training data)
- Boot ordering assertion that `systemd-modules-load.service` runs before `systemd-sysctl.service` is confirmed by the sysctl.d(5) manpage description but the exact systemd unit file dependency graph was not verified by fetching unit files directly.

---

## Metadata

**Confidence breakdown:**
- STRT-01 (lifespan swap): HIGH — trivial code change, fully understood from codebase reading
- STRT-02 (sysctl.d persistence): HIGH — verified format and naming from official Debian manpages
- STRT-03 (nftables.conf + service enable): HIGH — Pi OS Bookworm default-disabled confirmed; `persist_nftables()` format verified correct
- STRT-04 (modules-load.d for br_netfilter): HIGH — boot ordering dependency confirmed from official systemd docs; this is the most important finding
- Pitfalls: HIGH — br_netfilter silent failure is documented behavior from official manpages; nftables-disabled-by-default is confirmed from user report

**Research date:** 2026-03-03
**Valid until:** 2027-03-03 (stable Linux kernel/systemd mechanisms, unlikely to change)
