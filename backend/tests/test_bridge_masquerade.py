"""
Unit tests for bridge masquerade functions in app.hal.linux_nftables.

Tested functions
----------------
_get_br0_mac()              - reads br0 MAC via cat /sys/class/net/br0/address
_get_wan_bridge_port()      - detects WAN bridge port via ls / ip route / ip neigh / bridge fdb
ensure_bridge_masquerade()  - installs bridge MAC-rewrite table + inet nat MASQUERADE rule
remove_bridge_masquerade()  - removes both of the above rules

All subprocess calls are replaced by AsyncMock objects so the suite can run
on any OS (including Windows CI) without real Linux commands.

Run with:
    cd C:\\Nextcloud2\\TonbilAiFirewallV41\\backend
    python -m pytest tests/test_bridge_masquerade.py -v
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Make "app" importable when running pytest from the backend directory
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.hal.linux_nftables import (
    _get_br0_mac,
    _get_wan_bridge_port,
    ensure_bridge_masquerade,
    remove_bridge_masquerade,
    BRIDGE_MASQ_TABLE,
    BRIDGE_MASQ_CHAIN,
)
from tests.conftest import make_proc


# ===========================================================================
# Helpers
# ===========================================================================

# Convenience alias: module path to patch
_MOD = "app.hal.linux_nftables"


def _patch_create_subprocess_exec(*procs):
    """Return a context-manager that patches asyncio.create_subprocess_exec inside
    the module under test, yielding successive *procs* for each call made.

    Usage::
        with _patch_create_subprocess_exec(proc1, proc2) as mock_cse:
            ...
    """
    side_effects = list(procs)
    mock_fn = AsyncMock(side_effect=side_effects)
    return patch(f"{_MOD}.asyncio.create_subprocess_exec", mock_fn)


# ===========================================================================
# Tests for _get_br0_mac()
# ===========================================================================

class TestGetBr0Mac:
    """Tests for _get_br0_mac() — reads br0 interface MAC address."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_valid_mac_is_returned(self):
        """When /sys/class/net/br0/address contains a well-formed MAC, return it."""
        valid_mac = "dc:a6:32:01:02:03"
        proc = make_proc(stdout=f"{valid_mac}\n".encode())

        with _patch_create_subprocess_exec(proc):
            result = await _get_br0_mac()

        assert result == valid_mac

    @pytest.mark.asyncio(loop_scope="function")
    async def test_valid_mac_uppercase_is_returned(self):
        """MAC addresses with uppercase hex digits are accepted by the regex."""
        valid_mac = "DC:A6:32:AB:CD:EF"
        proc = make_proc(stdout=f"{valid_mac}\n".encode())

        with _patch_create_subprocess_exec(proc):
            result = await _get_br0_mac()

        assert result == valid_mac

    @pytest.mark.asyncio(loop_scope="function")
    async def test_invalid_mac_format_returns_none(self):
        """When the output is not a valid MAC (e.g. garbage), return None."""
        proc = make_proc(stdout=b"not-a-mac-address\n")

        with _patch_create_subprocess_exec(proc):
            result = await _get_br0_mac()

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_output_returns_none(self):
        """Empty stdout (file missing, zero-byte read) should return None."""
        proc = make_proc(stdout=b"")

        with _patch_create_subprocess_exec(proc):
            result = await _get_br0_mac()

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_short_mac_returns_none(self):
        """A MAC with only 4 octets fails the regex and returns None."""
        proc = make_proc(stdout=b"dc:a6:32:01\n")

        with _patch_create_subprocess_exec(proc):
            result = await _get_br0_mac()

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_subprocess_exception_returns_none(self):
        """If create_subprocess_exec itself raises, the function catches it and returns None."""
        with patch(
            f"{_MOD}.asyncio.create_subprocess_exec",
            side_effect=OSError("No such file"),
        ):
            result = await _get_br0_mac()

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_communicate_exception_returns_none(self):
        """If communicate() raises mid-flight, the function catches it and returns None."""
        proc = AsyncMock()
        proc.communicate = AsyncMock(side_effect=OSError("Broken pipe"))

        with patch(f"{_MOD}.asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
            result = await _get_br0_mac()

        assert result is None

    @pytest.mark.asyncio(loop_scope="function")
    async def test_subprocess_called_with_correct_args(self):
        """Verify that 'cat /sys/class/net/br0/address' is the command executed."""
        valid_mac = "aa:bb:cc:dd:ee:ff"
        proc = make_proc(stdout=f"{valid_mac}\n".encode())

        mock_cse = AsyncMock(return_value=proc)
        with patch(f"{_MOD}.asyncio.create_subprocess_exec", mock_cse):
            await _get_br0_mac()

        mock_cse.assert_called_once_with(
            "cat",
            "/sys/class/net/br0/address",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_whitespace_stripped_before_validation(self):
        """Output is stripped; a MAC surrounded by spaces/newlines is still valid."""
        valid_mac = "11:22:33:44:55:66"
        proc = make_proc(stdout=f"  {valid_mac}  \n".encode())

        with _patch_create_subprocess_exec(proc):
            result = await _get_br0_mac()

        assert result == valid_mac


# ===========================================================================
# Tests for _get_wan_bridge_port()
# ===========================================================================

class TestGetWanBridgePort:
    """Tests for _get_wan_bridge_port() — detects WAN-side bridge port."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_single_port_returned_directly(self):
        """When bridge has exactly one port, return it without any further lookups."""
        ls_proc = make_proc(stdout=b"eth0\n")

        with _patch_create_subprocess_exec(ls_proc) as mock_cse:
            result = await _get_wan_bridge_port()

        assert result == "eth0"
        # Only one subprocess call should have been made (the 'ls' call)
        assert mock_cse.call_count == 1

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_ports_returns_eth0_fallback(self):
        """When the brif directory is empty, fall back to 'eth0'."""
        ls_proc = make_proc(stdout=b"")

        with _patch_create_subprocess_exec(ls_proc):
            result = await _get_wan_bridge_port()

        assert result == "eth0"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_ports_gateway_detected_returns_correct_port(self):
        """
        Given two ports (eth0, wlan0) and a gateway on eth0 side,
        _get_wan_bridge_port must return 'eth0'.

        Subprocess call sequence:
        1. ls /sys/class/net/br0/brif/    -> "eth0 wlan0"
        2. ip route show default           -> "default via 192.168.1.1 dev br0"
        3. ip neigh show 192.168.1.1 dev br0 -> "192.168.1.1 lladdr aa:bb:cc:11:22:33 REACHABLE"
        4. bridge fdb show br br0          -> "aa:bb:cc:11:22:33 dev eth0 master br0 permanent"
        """
        ls_proc = make_proc(stdout=b"eth0 wlan0\n")
        route_proc = make_proc(stdout=b"default via 192.168.1.1 dev br0\n")
        neigh_proc = make_proc(stdout=b"192.168.1.1 lladdr aa:bb:cc:11:22:33 REACHABLE\n")
        fdb_proc = make_proc(
            stdout=b"aa:bb:cc:11:22:33 dev eth0 master br0 permanent\n"
                   b"ff:ff:ff:ff:ff:ff dev wlan0 master br0 permanent\n"
        )

        with _patch_create_subprocess_exec(ls_proc, route_proc, neigh_proc, fdb_proc):
            result = await _get_wan_bridge_port()

        assert result == "eth0"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_ports_gateway_on_wlan0(self):
        """When the gateway MAC is learned on wlan0, return 'wlan0'."""
        ls_proc = make_proc(stdout=b"eth0 wlan0\n")
        route_proc = make_proc(stdout=b"default via 10.0.0.1 dev br0\n")
        neigh_proc = make_proc(stdout=b"10.0.0.1 lladdr 00:11:22:33:44:55 REACHABLE\n")
        fdb_proc = make_proc(
            stdout=b"00:11:22:33:44:55 dev wlan0 master br0 permanent\n"
                   b"aa:bb:cc:dd:ee:ff dev eth0 master br0 permanent\n"
        )

        with _patch_create_subprocess_exec(ls_proc, route_proc, neigh_proc, fdb_proc):
            result = await _get_wan_bridge_port()

        assert result == "wlan0"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_ports_no_default_route_returns_eth0(self):
        """If 'ip route show default' returns no 'via …', fall back to 'eth0'."""
        ls_proc = make_proc(stdout=b"eth0 wlan0\n")
        route_proc = make_proc(stdout=b"")  # no default route output

        with _patch_create_subprocess_exec(ls_proc, route_proc):
            result = await _get_wan_bridge_port()

        assert result == "eth0"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_ports_no_arp_entry_returns_eth0(self):
        """If 'ip neigh' returns no lladdr, fall back to 'eth0'."""
        ls_proc = make_proc(stdout=b"eth0 wlan0\n")
        route_proc = make_proc(stdout=b"default via 192.168.1.1 dev br0\n")
        neigh_proc = make_proc(stdout=b"192.168.1.1 FAILED\n")  # no lladdr

        with _patch_create_subprocess_exec(ls_proc, route_proc, neigh_proc):
            result = await _get_wan_bridge_port()

        assert result == "eth0"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_ports_mac_not_in_fdb_returns_eth0(self):
        """If the gateway MAC is not found in the bridge FDB, fall back to 'eth0'."""
        ls_proc = make_proc(stdout=b"eth0 wlan0\n")
        route_proc = make_proc(stdout=b"default via 192.168.1.1 dev br0\n")
        neigh_proc = make_proc(stdout=b"192.168.1.1 lladdr de:ad:be:ef:00:01 REACHABLE\n")
        fdb_proc = make_proc(stdout=b"ff:ff:ff:ff:ff:ff dev eth0 master br0\n")  # different MAC

        with _patch_create_subprocess_exec(ls_proc, route_proc, neigh_proc, fdb_proc):
            result = await _get_wan_bridge_port()

        assert result == "eth0"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ls_subprocess_raises_returns_eth0(self):
        """If the initial 'ls' call throws an OSError, fall back to 'eth0'."""
        with patch(
            f"{_MOD}.asyncio.create_subprocess_exec",
            side_effect=OSError("ls not available"),
        ):
            result = await _get_wan_bridge_port()

        assert result == "eth0"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_ip_route_raises_returns_eth0(self):
        """If the 'ip route' subprocess raises mid-sequence, fall back to 'eth0'."""
        ls_proc = make_proc(stdout=b"eth0 wlan0\n")

        call_count = 0

        async def cse_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ls_proc
            raise OSError("ip not found")

        with patch(f"{_MOD}.asyncio.create_subprocess_exec", side_effect=cse_side_effect):
            result = await _get_wan_bridge_port()

        assert result == "eth0"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_three_ports_correct_wan_identified(self):
        """With three bridge ports the function should still pinpoint the WAN port."""
        ls_proc = make_proc(stdout=b"eth0 eth1 eth2\n")
        route_proc = make_proc(stdout=b"default via 172.16.0.1 dev br0\n")
        neigh_proc = make_proc(stdout=b"172.16.0.1 lladdr 52:54:00:ab:cd:ef REACHABLE\n")
        fdb_proc = make_proc(
            stdout=b"52:54:00:ab:cd:ef dev eth2 master br0 permanent\n"
                   b"aa:bb:cc:dd:ee:ff dev eth0 master br0\n"
                   b"11:22:33:44:55:66 dev eth1 master br0\n"
        )

        with _patch_create_subprocess_exec(ls_proc, route_proc, neigh_proc, fdb_proc):
            result = await _get_wan_bridge_port()

        assert result == "eth2"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_correct_subprocess_commands_issued_for_single_port(self):
        """Verify the exact command arguments used when only one port exists."""
        ls_proc = make_proc(stdout=b"eth0\n")

        mock_cse = AsyncMock(return_value=ls_proc)
        with patch(f"{_MOD}.asyncio.create_subprocess_exec", mock_cse):
            await _get_wan_bridge_port()

        mock_cse.assert_called_once_with(
            "ls",
            "/sys/class/net/br0/brif/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )


# ===========================================================================
# Tests for ensure_bridge_masquerade()
# ===========================================================================

class TestEnsureBridgeMasquerade:
    """Tests for ensure_bridge_masquerade() — sets up bridge MAC-rewrite + MASQUERADE."""

    # ------------------------------------------------------------------
    # Shared mock builders
    # ------------------------------------------------------------------

    def _build_nft_proc(self, returncode: int = 0, stderr: bytes = b"") -> AsyncMock:
        """Create a mock nft -f - subprocess."""
        return make_proc(stdout=b"", stderr=stderr, returncode=returncode)

    # ------------------------------------------------------------------
    # Fresh install: no existing rules
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fresh_install_creates_bridge_table_and_masquerade_rule(self):
        """
        When the ruleset contains neither BRIDGE_MASQ_TABLE nor 'bridge_lan_masq',
        both the bridge table and the MASQUERADE rule must be created.
        """
        br0_mac = "dc:a6:32:01:02:03"
        lan_subnet = "192.168.1.0/24"
        empty_ruleset = ""  # nothing pre-existing

        # Subprocess proc objects in call order for asyncio.create_subprocess_exec:
        # 1 & 2 are consumed by _get_br0_mac and _get_wan_bridge_port internally.
        # But we patch those helpers directly to isolate ensure_bridge_masquerade.
        nft_bridge_proc = self._build_nft_proc(returncode=0)
        nft_masq_proc = self._build_nft_proc(returncode=0)
        persist_nft_list_proc = make_proc(stdout=b"# current ruleset", returncode=0)
        persist_tee_proc = make_proc(returncode=0)
        nat_chain_mock = AsyncMock()

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value=lan_subnet)),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value=empty_ruleset)),
            patch(
                f"{_MOD}.asyncio.create_subprocess_exec",
                AsyncMock(side_effect=[nft_bridge_proc, nft_masq_proc, persist_nft_list_proc, persist_tee_proc]),
            ),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", nat_chain_mock),
        ):
            await ensure_bridge_masquerade()
            # Verify ensure_nat_postrouting_chain was called (required before masq rule)
            nat_chain_mock.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fresh_install_nft_stdin_contains_bridge_mac(self):
        """
        The nft -f - command that creates the bridge table must encode
        the real br0 MAC and the detected WAN interface into the script.
        """
        br0_mac = "dc:a6:32:aa:bb:cc"
        wan_iface = "eth0"
        captured_stdin: list[bytes] = []

        async def fake_cse(*args, **kwargs):
            proc = AsyncMock()
            proc.returncode = 0
            proc.communicate = AsyncMock(return_value=(b"", b""))
            return proc

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value=wan_iface)),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", side_effect=fake_cse),
        ):
            # Intercept communicate() to capture what stdin was fed
            original_fake_cse = fake_cse
            stdin_payloads: list[bytes] = []

            async def capturing_cse(*args, **kwargs):
                proc = AsyncMock()
                proc.returncode = 0

                async def cap_communicate(input=None):
                    if input:
                        stdin_payloads.append(input)
                    return (b"", b"")

                proc.communicate = cap_communicate
                return proc

            with patch(f"{_MOD}.asyncio.create_subprocess_exec", side_effect=capturing_cse):
                await ensure_bridge_masquerade()

        # The first stdin payload must contain the br0 MAC and WAN interface
        assert any(br0_mac.encode() in payload for payload in stdin_payloads), (
            f"br0 MAC '{br0_mac}' not found in any nft stdin payload: {stdin_payloads}"
        )
        assert any(wan_iface.encode() in payload for payload in stdin_payloads), (
            f"WAN iface '{wan_iface}' not found in any nft stdin payload: {stdin_payloads}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_fresh_install_nft_stdin_contains_lan_subnet(self):
        """The MASQUERADE rule stdin payload must contain the LAN subnet."""
        br0_mac = "dc:a6:32:aa:bb:cc"
        lan_subnet = "10.10.20.0/24"
        stdin_payloads: list[bytes] = []

        async def capturing_cse(*args, **kwargs):
            proc = AsyncMock()
            proc.returncode = 0

            async def cap_communicate(input=None):
                if input:
                    stdin_payloads.append(input)
                return (b"", b"")

            proc.communicate = cap_communicate
            return proc

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value=lan_subnet)),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", side_effect=capturing_cse),
        ):
            await ensure_bridge_masquerade()

        assert any(lan_subnet.encode() in payload for payload in stdin_payloads), (
            f"LAN subnet '{lan_subnet}' not found in nft stdin payloads: {stdin_payloads}"
        )

    # ------------------------------------------------------------------
    # Already-existing rules: should skip creation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_already_existing_bridge_table_skips_creation(self):
        """
        When the ruleset already contains BRIDGE_MASQ_TABLE,
        no nft -f - subprocess must be spawned for the bridge table.
        """
        br0_mac = "dc:a6:32:01:02:03"
        # Ruleset contains both the bridge table and the masquerade comment
        existing_ruleset = (
            f"table {BRIDGE_MASQ_TABLE} {{ ... }}\n"
            f'add rule ... masquerade comment "bridge_lan_masq"'
        )
        cse_mock = AsyncMock()

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value=existing_ruleset)),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", cse_mock),
        ):
            await ensure_bridge_masquerade()

        # No nft -f - process should have been created (rules already present)
        cse_mock.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_bridge_table_exists_but_masquerade_rule_missing_creates_only_masq(self):
        """
        When BRIDGE_MASQ_TABLE already exists but 'bridge_lan_masq' is absent,
        only the MASQUERADE rule subprocess should be spawned.

        Because BRIDGE_MASQ_TABLE is present in the ruleset, no bridge-table
        subprocess is created. But 'bridge_lan_masq' is absent, so
        ensure_nat_postrouting_chain() and the masquerade nft subprocess
        must both be called.
        """
        br0_mac = "dc:a6:32:01:02:03"
        ruleset_with_table_only = f"table {BRIDGE_MASQ_TABLE} {{ ... }}"
        nft_masq_proc = self._build_nft_proc(returncode=0)
        nat_chain_mock = AsyncMock()

        async def capturing_cse(*args, **kwargs):
            return nft_masq_proc

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value=ruleset_with_table_only)),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", nat_chain_mock),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", side_effect=capturing_cse),
        ):
            await ensure_bridge_masquerade()
            # Assert inside the with-block so the mock is still active
            nat_chain_mock.assert_awaited_once()

    # ------------------------------------------------------------------
    # br0 MAC unavailable: should return early
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_br0_mac_returns_early_without_any_nft_call(self):
        """
        When _get_br0_mac() returns None, ensure_bridge_masquerade must
        return immediately without touching nft or _run_system_cmd.
        """
        run_system_cmd_mock = AsyncMock()
        run_nft_mock = AsyncMock()
        cse_mock = AsyncMock()

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=None)),
            patch(f"{_MOD}._run_system_cmd", run_system_cmd_mock),
            patch(f"{_MOD}.run_nft", run_nft_mock),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", cse_mock),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
        ):
            await ensure_bridge_masquerade()

        run_system_cmd_mock.assert_not_called()
        run_nft_mock.assert_not_called()
        cse_mock.assert_not_called()

    # ------------------------------------------------------------------
    # modprobe and sysctl are always called when MAC is available
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_modprobe_and_sysctl_called_on_setup(self):
        """
        modprobe br_netfilter and sysctl bridge-nf-call-iptables=1 must be
        invoked via _run_system_cmd on every call (idempotent system commands).
        """
        br0_mac = "dc:a6:32:01:02:03"
        existing_ruleset = (
            f"table {BRIDGE_MASQ_TABLE} {{ ... }}\n"
            f'bridge_lan_masq'
        )
        run_system_cmd_mock = AsyncMock(return_value="")

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", run_system_cmd_mock),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value=existing_ruleset)),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", AsyncMock()),
        ):
            await ensure_bridge_masquerade()

        calls = run_system_cmd_mock.call_args_list
        modprobe_call = call(["sudo", "modprobe", "br_netfilter"], check=False)
        sysctl_call = call(
            ["sudo", "sysctl", "-w", "net.bridge.bridge-nf-call-iptables=1"],
            check=False,
        )
        assert modprobe_call in calls, f"modprobe call missing from: {calls}"
        assert sysctl_call in calls, f"sysctl call missing from: {calls}"

    # ------------------------------------------------------------------
    # persist_nftables always called at the end
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_persist_nftables_always_called(self):
        """persist_nftables() must be the final operation regardless of rule state."""
        br0_mac = "dc:a6:32:01:02:03"
        existing_ruleset = (
            f"table {BRIDGE_MASQ_TABLE} {{ ... }}\n"
            f'bridge_lan_masq'
        )
        persist_mock = AsyncMock()

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value=existing_ruleset)),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", persist_mock),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", AsyncMock()),
        ):
            await ensure_bridge_masquerade()

        persist_mock.assert_awaited_once()

    # ------------------------------------------------------------------
    # nft command failure: should log error but not raise
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_nft_bridge_table_failure_logs_error_and_does_not_raise(self):
        """
        If the nft -f - subprocess for the bridge table returns a non-zero
        exit code, the function must log an error but must NOT propagate an
        exception (so the masquerade rule step can still proceed).
        """
        br0_mac = "dc:a6:32:01:02:03"
        nft_fail_proc = self._build_nft_proc(returncode=1, stderr=b"syntax error")
        nft_masq_proc = self._build_nft_proc(returncode=0)

        call_index = 0

        async def cse_side_effect(*args, **kwargs):
            nonlocal call_index
            call_index += 1
            return nft_fail_proc if call_index == 1 else nft_masq_proc

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", side_effect=cse_side_effect),
        ):
            # Must not raise even though nft failed
            await ensure_bridge_masquerade()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_nft_masquerade_rule_failure_logs_error_and_does_not_raise(self):
        """
        If the nft -f - subprocess for the MASQUERADE rule returns non-zero,
        the function logs an error but must call persist_nftables() and return
        normally.
        """
        br0_mac = "dc:a6:32:01:02:03"
        nft_bridge_proc = self._build_nft_proc(returncode=0)
        nft_masq_proc = self._build_nft_proc(returncode=1, stderr=b"masquerade error")

        call_index = 0

        async def cse_side_effect(*args, **kwargs):
            nonlocal call_index
            call_index += 1
            return nft_bridge_proc if call_index == 1 else nft_masq_proc

        persist_mock = AsyncMock()

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", persist_mock),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", side_effect=cse_side_effect),
        ):
            await ensure_bridge_masquerade()

        persist_mock.assert_awaited_once()

    # ------------------------------------------------------------------
    # Dependency helpers are called with correct arguments
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_detect_lan_subnet_is_called(self):
        """_detect_lan_subnet() must be awaited during ensure_bridge_masquerade."""
        br0_mac = "dc:a6:32:01:02:03"
        detect_mock = AsyncMock(return_value="192.168.2.0/24")

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", detect_mock),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", AsyncMock(return_value=make_proc())),
        ):
            await ensure_bridge_masquerade()

        detect_mock.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_get_wan_bridge_port_is_called(self):
        """_get_wan_bridge_port() must be awaited during ensure_bridge_masquerade."""
        br0_mac = "dc:a6:32:01:02:03"
        wan_port_mock = AsyncMock(return_value="eth0")

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", wan_port_mock),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", AsyncMock(return_value=make_proc())),
        ):
            await ensure_bridge_masquerade()

        wan_port_mock.assert_awaited_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_run_nft_list_ruleset_called_to_check_existing_state(self):
        """run_nft(['list', 'ruleset']) must be called to check what already exists."""
        br0_mac = "dc:a6:32:01:02:03"
        run_nft_mock = AsyncMock(return_value="")

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", run_nft_mock),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", AsyncMock(return_value=make_proc())),
        ):
            await ensure_bridge_masquerade()

        run_nft_mock.assert_any_call(["list", "ruleset"], check=False)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_nft_process_invoked_with_stdin_pipe(self):
        """The nft -f - process must be created with stdin=PIPE so the script can be fed."""
        br0_mac = "dc:a6:32:01:02:03"
        created_kwargs: list[dict] = []

        async def capturing_cse(*args, **kwargs):
            created_kwargs.append(kwargs)
            proc = AsyncMock()
            proc.returncode = 0
            proc.communicate = AsyncMock(return_value=(b"", b""))
            return proc

        with (
            patch(f"{_MOD}._get_br0_mac", AsyncMock(return_value=br0_mac)),
            patch(f"{_MOD}._get_wan_bridge_port", AsyncMock(return_value="eth0")),
            patch(f"{_MOD}._detect_lan_subnet", AsyncMock(return_value="192.168.1.0/24")),
            patch(f"{_MOD}._run_system_cmd", AsyncMock(return_value="")),
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.ensure_nat_postrouting_chain", AsyncMock()),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
            patch(f"{_MOD}.asyncio.create_subprocess_exec", side_effect=capturing_cse),
        ):
            await ensure_bridge_masquerade()

        assert len(created_kwargs) >= 1
        for kw in created_kwargs:
            assert kw.get("stdin") == asyncio.subprocess.PIPE, (
                f"Expected stdin=PIPE for nft process, got: {kw}"
            )


# ===========================================================================
# Tests for remove_bridge_masquerade()
# ===========================================================================

class TestRemoveBridgeMasquerade:
    """Tests for remove_bridge_masquerade() — removes bridge table and masquerade rule."""

    # ------------------------------------------------------------------
    # Successful removal
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_deletes_bridge_table_via_run_nft(self):
        """run_nft must be called with 'delete table <BRIDGE_MASQ_TABLE>'."""
        run_nft_mock = AsyncMock(return_value="")
        persist_mock = AsyncMock()

        with (
            patch(f"{_MOD}.run_nft", run_nft_mock),
            patch(f"{_MOD}.persist_nftables", persist_mock),
        ):
            await remove_bridge_masquerade()

        # The very first call must delete the bridge table
        first_call_args = run_nft_mock.call_args_list[0]
        assert first_call_args == call(
            ["delete", "table", BRIDGE_MASQ_TABLE], check=False
        ), f"Unexpected first run_nft call: {first_call_args}"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_deletes_masquerade_rule_by_handle_when_found(self):
        """
        When the postrouting chain output contains a 'bridge_lan_masq' line with
        a handle, run_nft must be called to delete that specific rule by handle.
        """
        chain_output = (
            'add rule inet nat postrouting ip saddr 192.168.1.0/24 '
            'masquerade comment "bridge_lan_masq" # handle 42\n'
        )

        call_count = 0

        async def run_nft_side_effect(args, check=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ""  # delete table call
            if call_count == 2:
                return chain_output  # list chain call
            return ""  # delete rule call

        persist_mock = AsyncMock()

        with (
            patch(f"{_MOD}.run_nft", side_effect=run_nft_side_effect),
            patch(f"{_MOD}.persist_nftables", persist_mock),
        ):
            await remove_bridge_masquerade()

        # The last non-persist call should have deleted handle 42
        # We verify by counting: 3 run_nft calls minimum (delete table, list chain, delete rule)
        assert call_count >= 3, f"Expected at least 3 run_nft calls, got {call_count}"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_delete_rule_uses_correct_handle_number(self):
        """The handle extracted from the chain output is used verbatim in the delete call."""
        chain_output = (
            'ip saddr 10.0.0.0/8 masquerade comment "bridge_lan_masq" # handle 99\n'
        )
        deleted_handles: list[str] = []

        call_count = 0

        async def run_nft_side_effect(args, check=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ""
            if call_count == 2:
                return chain_output
            # Third call is the delete rule; capture the handle
            if "handle" in args:
                handle_idx = args.index("handle")
                deleted_handles.append(args[handle_idx + 1])
            return ""

        with (
            patch(f"{_MOD}.run_nft", side_effect=run_nft_side_effect),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
        ):
            await remove_bridge_masquerade()

        assert "99" in deleted_handles, f"Handle '99' not found in delete calls: {deleted_handles}"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_persist_nftables_called_after_removal(self):
        """persist_nftables() must be called at the end of remove_bridge_masquerade."""
        persist_mock = AsyncMock()

        with (
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.persist_nftables", persist_mock),
        ):
            await remove_bridge_masquerade()

        persist_mock.assert_awaited_once()

    # ------------------------------------------------------------------
    # No existing masquerade rule
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_no_masquerade_rule_no_delete_rule_call(self):
        """
        When the chain listing does not contain 'bridge_lan_masq', the function
        must not attempt to delete any rule handle (just deletes the table and persists).
        """
        delete_rule_calls: list = []
        call_count = 0

        async def run_nft_side_effect(args, check=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ""  # delete table
            if call_count == 2:
                return "# postrouting chain with no bridge_lan_masq"  # list chain
            delete_rule_calls.append(args)
            return ""

        with (
            patch(f"{_MOD}.run_nft", side_effect=run_nft_side_effect),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
        ):
            await remove_bridge_masquerade()

        assert delete_rule_calls == [], (
            f"Expected no delete-rule calls, but got: {delete_rule_calls}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_empty_chain_output_handled_gracefully(self):
        """
        When run_nft returns an empty string for the chain listing,
        remove_bridge_masquerade must complete without error.
        """
        with (
            patch(f"{_MOD}.run_nft", AsyncMock(return_value="")),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
        ):
            # Must not raise
            await remove_bridge_masquerade()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_none_chain_output_handled_gracefully(self):
        """
        When run_nft returns None (edge case from a failed check=False call),
        the function must not raise AttributeError or similar.
        """
        call_count = 0

        async def run_nft_side_effect(args, check=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ""  # delete table — return empty, not None
            return None  # list chain returns None

        with (
            patch(f"{_MOD}.run_nft", side_effect=run_nft_side_effect),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
        ):
            # Must not raise
            await remove_bridge_masquerade()

    # ------------------------------------------------------------------
    # Multiple masquerade rules (defensive: only one should normally exist)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_multiple_bridge_lan_masq_lines_all_deleted(self):
        """
        If somehow multiple 'bridge_lan_masq' rules are present (unusual but
        defensive), all matching handles must be deleted.
        """
        chain_output = (
            'masquerade comment "bridge_lan_masq" # handle 10\n'
            'masquerade comment "bridge_lan_masq" # handle 11\n'
        )
        deleted_handles: list[str] = []
        call_count = 0

        async def run_nft_side_effect(args, check=True):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ""
            if call_count == 2:
                return chain_output
            if "handle" in args:
                handle_idx = args.index("handle")
                deleted_handles.append(args[handle_idx + 1])
            return ""

        with (
            patch(f"{_MOD}.run_nft", side_effect=run_nft_side_effect),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
        ):
            await remove_bridge_masquerade()

        assert "10" in deleted_handles, f"Handle 10 not deleted. Got: {deleted_handles}"
        assert "11" in deleted_handles, f"Handle 11 not deleted. Got: {deleted_handles}"

    # ------------------------------------------------------------------
    # Correct run_nft argument sequences
    # ------------------------------------------------------------------

    @pytest.mark.asyncio(loop_scope="function")
    async def test_list_chain_called_with_correct_args(self):
        """The second run_nft call must list inet nat postrouting chain with -a flag."""
        all_calls: list = []

        async def run_nft_side_effect(args, check=True):
            all_calls.append(list(args))
            return ""

        with (
            patch(f"{_MOD}.run_nft", side_effect=run_nft_side_effect),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
        ):
            await remove_bridge_masquerade()

        expected_list_call = ["-a", "list", "chain", "inet", "nat", "postrouting"]
        assert expected_list_call in all_calls, (
            f"Expected list-chain call {expected_list_call} not found in: {all_calls}"
        )

    @pytest.mark.asyncio(loop_scope="function")
    async def test_delete_rule_uses_correct_chain_path(self):
        """The delete rule call must reference 'inet nat postrouting'."""
        chain_output = (
            'masquerade comment "bridge_lan_masq" # handle 7\n'
        )
        all_calls: list = []
        call_count = 0

        async def run_nft_side_effect(args, check=True):
            nonlocal call_count
            call_count += 1
            all_calls.append(list(args))
            if call_count == 2:
                return chain_output
            return ""

        with (
            patch(f"{_MOD}.run_nft", side_effect=run_nft_side_effect),
            patch(f"{_MOD}.persist_nftables", AsyncMock()),
        ):
            await remove_bridge_masquerade()

        # Find the delete rule call
        delete_calls = [c for c in all_calls if c[:2] == ["delete", "rule"]]
        assert delete_calls, f"No delete-rule call found in: {all_calls}"
        delete_call = delete_calls[0]
        assert "inet" in delete_call
        assert "nat" in delete_call
        assert "postrouting" in delete_call
        assert "7" in delete_call


# ===========================================================================
# Integration-style: constants and module-level attributes
# ===========================================================================

class TestModuleConstants:
    """Verify that the module exposes the expected public constants."""

    def test_bridge_masq_table_constant(self):
        assert BRIDGE_MASQ_TABLE == "bridge masquerade_fix"

    def test_bridge_masq_chain_constant(self):
        assert BRIDGE_MASQ_CHAIN == "mac_rewrite"

    def test_nft_bin_constant(self):
        from app.hal.linux_nftables import NFT_BIN
        assert NFT_BIN == "/usr/sbin/nft"
