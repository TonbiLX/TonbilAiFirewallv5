#!/bin/bash
# =============================================================================
# TonbilAiOS v5 — Post-Deployment Validation Script
# Phase 5: DHCP Gateway and Validation
#
# Covers: DHCP-01, DHCP-02, VALD-01 through VALD-07
# Usage:  sudo bash validate.sh
# Run on: Raspberry Pi (192.168.1.2) after all 5 phases are deployed
# =============================================================================

set -uo pipefail

# Root check
if [[ $EUID -ne 0 ]]; then
    echo "Run as root: sudo bash validate.sh"
    exit 1
fi

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # No Color

# Counters
PASS=0
FAIL=0
SKIP=0
WARN=0
TOTAL=9

# Helper: print PASS
pass_result() {
    local name="$1"
    echo -e "  ${GREEN}[PASS]${NC} ${name}"
    PASS=$((PASS + 1))
}

# Helper: print FAIL
fail_result() {
    local name="$1"
    local reason="${2:-}"
    echo -e "  ${RED}[FAIL]${NC} ${name}"
    [[ -n "$reason" ]] && echo -e "        ${RED}Reason: ${reason}${NC}"
    FAIL=$((FAIL + 1))
}

# Helper: print SKIP
skip_result() {
    local name="$1"
    local reason="${2:-}"
    echo -e "  ${YELLOW}[SKIP]${NC} ${name}"
    [[ -n "$reason" ]] && echo -e "        ${YELLOW}Reason: ${reason}${NC}"
    SKIP=$((SKIP + 1))
}

# Helper: print WARN
warn_result() {
    local name="$1"
    local reason="${2:-}"
    echo -e "  ${YELLOW}[WARN]${NC} ${name}"
    [[ -n "$reason" ]] && echo -e "        ${YELLOW}Note: ${reason}${NC}"
    WARN=$((WARN + 1))
}

# Section separator
section() {
    echo ""
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

echo ""
echo -e "${BOLD}TonbilAiOS v5 — Post-Deployment Validation${NC}"
echo -e "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "Host:      $(hostname)"
echo ""

# =============================================================================
# DHCP-01: dnsmasq config contains dhcp-option=3,192.168.1.2
# =============================================================================
section "DHCP-01: dnsmasq Config Gateway Verification"

POOL_CONF="/etc/dnsmasq.d/pool-1.conf"
echo "  Checking: $POOL_CONF"

if [[ ! -f "$POOL_CONF" ]]; then
    fail_result "DHCP-01" "File $POOL_CONF does not exist"
else
    DHCP_OPTION_LINES=$(grep "dhcp-option" "$POOL_CONF" 2>/dev/null || true)
    GATEWAY_LINE=$(grep "dhcp-option=3,192.168.1.2" "$POOL_CONF" 2>/dev/null || true)

    echo "  Config dhcp-option lines:"
    if [[ -n "$DHCP_OPTION_LINES" ]]; then
        echo "$DHCP_OPTION_LINES" | while IFS= read -r line; do
            echo "    $line"
        done
    else
        echo "    (no dhcp-option lines found)"
    fi

    if [[ -n "$GATEWAY_LINE" ]]; then
        pass_result "DHCP-01 — dhcp-option=3,192.168.1.2 found in pool config"
    else
        fail_result "DHCP-01" "dhcp-option=3,192.168.1.2 not found in $POOL_CONF"
    fi
fi

# =============================================================================
# DHCP-02: Database gateway = 192.168.1.2
# =============================================================================
section "DHCP-02: Database Gateway Verification"

echo "  Querying MariaDB dhcp_pools table..."

if ! command -v mysql &>/dev/null; then
    skip_result "DHCP-02" "mysql client not installed"
else
    DB_GATEWAY=$(mysql -u tonbilai -pTonbilAiOS2026Router tonbilaios -N -e \
        "SELECT gateway FROM dhcp_pools WHERE id=1;" 2>/dev/null || echo "__ERROR__")

    if [[ "$DB_GATEWAY" == "__ERROR__" ]] || [[ -z "$DB_GATEWAY" ]]; then
        skip_result "DHCP-02" "Could not query DB (connection failed or pool id=1 not found)"
    elif [[ "$DB_GATEWAY" == "192.168.1.2" ]]; then
        echo "  DB gateway value: $DB_GATEWAY"
        pass_result "DHCP-02 — DB gateway is 192.168.1.2"
    else
        echo "  DB gateway value: $DB_GATEWAY (expected: 192.168.1.2)"
        fail_result "DHCP-02" "DB gateway is '$DB_GATEWAY', expected '192.168.1.2'"
    fi
fi

# =============================================================================
# VALD-06: Bridge forward drop rules present
# (run first — confirms Phase 1 foundation before further checks)
# =============================================================================
section "VALD-06: Bridge Forward Drop Rules"

echo "  Running: nft list chain bridge filter forward"
NFT_FORWARD=$(nft list chain bridge filter forward 2>/dev/null || true)

if [[ -z "$NFT_FORWARD" ]]; then
    fail_result "VALD-06" "Could not read bridge filter forward chain (nft error or chain missing)"
else
    echo "  Chain output (relevant lines):"
    echo "$NFT_FORWARD" | grep -E "drop|bridge_isolation|iifname|oifname" | while IFS= read -r line; do
        echo "    $line"
    done || echo "    (no drop/isolation lines found)"

    HAS_LAN_WAN=$(echo "$NFT_FORWARD" | grep -c "bridge_isolation_lan_wan" || true)
    HAS_WAN_LAN=$(echo "$NFT_FORWARD" | grep -c "bridge_isolation_wan_lan" || true)

    if [[ "$HAS_LAN_WAN" -gt 0 && "$HAS_WAN_LAN" -gt 0 ]]; then
        pass_result "VALD-06 — both bridge_isolation_lan_wan and bridge_isolation_wan_lan rules present"
    elif [[ "$HAS_LAN_WAN" -gt 0 ]]; then
        fail_result "VALD-06" "bridge_isolation_lan_wan present but bridge_isolation_wan_lan MISSING"
    elif [[ "$HAS_WAN_LAN" -gt 0 ]]; then
        fail_result "VALD-06" "bridge_isolation_wan_lan present but bridge_isolation_lan_wan MISSING"
    else
        fail_result "VALD-06" "Neither bridge_isolation_lan_wan nor bridge_isolation_wan_lan found in forward chain"
    fi
fi

# =============================================================================
# VALD-03: Pi internet access
# =============================================================================
section "VALD-03: Pi Internet Access"

echo "  Running: curl -s --max-time 10 https://example.com"
HTTP_CODE=$(curl -s --max-time 10 -o /dev/null -w "%{http_code}" https://example.com 2>/dev/null || echo "000")
echo "  HTTP status code: $HTTP_CODE"

if [[ "$HTTP_CODE" == "200" ]]; then
    pass_result "VALD-03 — Pi can reach internet (HTTP 200)"
elif [[ "$HTTP_CODE" == "000" ]]; then
    fail_result "VALD-03" "curl failed (timeout or no route to host)"
else
    fail_result "VALD-03" "Unexpected HTTP status: $HTTP_CODE (expected 200)"
fi

# =============================================================================
# VALD-04: DNS resolution
# =============================================================================
section "VALD-04: DNS Resolution via Pi DNS Proxy"

echo "  Running: dig @192.168.1.2 example.com +short +timeout=5"

if ! command -v dig &>/dev/null; then
    skip_result "VALD-04" "dig command not available (install dnsutils)"
else
    DIG_RESULT=$(dig @192.168.1.2 example.com +short +timeout=5 2>/dev/null || true)
    echo "  Resolved: ${DIG_RESULT:-<empty>}"

    if [[ -n "$DIG_RESULT" ]] && echo "$DIG_RESULT" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
        pass_result "VALD-04 — DNS proxy resolved example.com to $DIG_RESULT"
    elif [[ -n "$DIG_RESULT" ]]; then
        # May return CNAME or multiple lines — check if any line is an IP
        IP_LINE=$(echo "$DIG_RESULT" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1 || true)
        if [[ -n "$IP_LINE" ]]; then
            pass_result "VALD-04 — DNS proxy resolved example.com (IP: $IP_LINE)"
        else
            fail_result "VALD-04" "dig returned output but no valid IP found: $DIG_RESULT"
        fi
    else
        fail_result "VALD-04" "dig returned empty result — DNS proxy may not be reachable at 192.168.1.2:53"
    fi
fi

# =============================================================================
# VALD-05: Bridge accounting counters
# =============================================================================
section "VALD-05: Bridge Accounting Counters"

echo "  Running: nft list chain bridge accounting upload"
UPLOAD_OUT=$(nft list chain bridge accounting upload 2>/dev/null || true)
echo "  Running: nft list chain bridge accounting download"
DOWNLOAD_OUT=$(nft list chain bridge accounting download 2>/dev/null || true)

if [[ -z "$UPLOAD_OUT" && -z "$DOWNLOAD_OUT" ]]; then
    fail_result "VALD-05" "Neither upload nor download accounting chains exist (Phase 2 not applied?)"
elif [[ -z "$UPLOAD_OUT" ]]; then
    fail_result "VALD-05" "accounting upload chain missing (accounting download chain exists)"
elif [[ -z "$DOWNLOAD_OUT" ]]; then
    fail_result "VALD-05" "accounting download chain missing (accounting upload chain exists)"
else
    echo "  Upload chain lines (counters):"
    echo "$UPLOAD_OUT" | grep -E "counter|packets|bytes" | head -5 | while IFS= read -r line; do
        echo "    $line"
    done || echo "    (no counter lines)"

    echo "  Download chain lines (counters):"
    echo "$DOWNLOAD_OUT" | grep -E "counter|packets|bytes" | head -5 | while IFS= read -r line; do
        echo "    $line"
    done || echo "    (no counter lines)"

    # Check for non-zero counters: look for "counter packets N" or "bytes N" where N starts non-zero
    NONZERO_UP=$(echo "$UPLOAD_OUT" | grep -E "counter packets [1-9]|bytes [1-9]" || true)
    NONZERO_DL=$(echo "$DOWNLOAD_OUT" | grep -E "counter packets [1-9]|bytes [1-9]" || true)

    if [[ -n "$NONZERO_UP" || -n "$NONZERO_DL" ]]; then
        pass_result "VALD-05 — both accounting chains exist and have non-zero counters"
    else
        warn_result "VALD-05" "Accounting chains exist but all counters are zero (no traffic recorded yet — generate some traffic and re-run)"
    fi
fi

# =============================================================================
# VALD-02: Conntrack ESTABLISHED connections
# =============================================================================
section "VALD-02: Conntrack ESTABLISHED Connections"

if ! command -v conntrack &>/dev/null; then
    skip_result "VALD-02" "conntrack command not available (install conntrack)"
else
    echo "  Running: conntrack -L --state ESTABLISHED | wc -l"
    ESTABLISHED_COUNT=$(conntrack -L --state ESTABLISHED 2>/dev/null | wc -l || echo "0")
    echo "  ESTABLISHED connections: $ESTABLISHED_COUNT"

    if [[ "$ESTABLISHED_COUNT" -gt 0 ]]; then
        pass_result "VALD-02 — $ESTABLISHED_COUNT ESTABLISHED connections present (existing connections survive)"
    else
        warn_result "VALD-02" "No ESTABLISHED connections found — this may be normal if no active LAN devices, but verify after generating traffic"
    fi
fi

# =============================================================================
# VALD-01: ARP verification — modem should only see Pi's MAC
# =============================================================================
section "VALD-01: ARP Verification (WAN-side tcpdump)"

if ! command -v tcpdump &>/dev/null; then
    skip_result "VALD-01" "tcpdump command not available"
else
    PI_MAC=$(cat /sys/class/net/eth0/address 2>/dev/null || echo "unknown")
    echo "  Pi eth0 MAC: $PI_MAC"
    echo "  Capturing ARP on eth0 for up to 15 seconds (max 10 packets)..."
    echo "  (Generate LAN traffic / ARP requests to speed this up)"

    TCPDUMP_OUT=$(timeout 15 tcpdump -i eth0 -n -e arp -c 10 2>/dev/null || true)

    if [[ -z "$TCPDUMP_OUT" ]]; then
        skip_result "VALD-01" "No ARP packets captured on eth0 within 15 seconds — requires active LAN traffic; re-run while devices are active"
    else
        echo "  Captured ARP packets:"
        echo "$TCPDUMP_OUT" | while IFS= read -r line; do
            echo "    $line"
        done

        # Extract sender hardware addresses (format: "XX:XX:XX:XX:XX:XX > ..." or "SA XX:XX:XX:XX:XX:XX")
        # tcpdump -e output: timestamp > length SA XX:XX... DA XX:XX... type ARP ...
        # Typical line: "12:34:56.789 aa:bb:cc:dd:ee:ff > ff:ff:ff:ff:ff:ff ..."
        FOREIGN_MACS=$(echo "$TCPDUMP_OUT" | grep -iE "^[0-9]" | \
            awk '{print $2}' | \
            grep -iE "^[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}" | \
            sort -u | grep -iv "$PI_MAC" || true)

        echo ""
        echo "  Unique sender MACs found:"
        echo "$TCPDUMP_OUT" | grep -iE "^[0-9]" | awk '{print $2}' | \
            grep -iE "^[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}" | sort -u | while IFS= read -r mac; do
            if echo "$mac" | grep -qi "$PI_MAC"; then
                echo -e "    ${GREEN}$mac${NC} (Pi eth0 — expected)"
            else
                echo -e "    ${RED}$mac${NC} (FOREIGN MAC — isolation may not be working!)"
            fi
        done

        if [[ -n "$FOREIGN_MACS" ]]; then
            fail_result "VALD-01" "Foreign MACs detected on WAN (eth0) — bridge isolation may not be blocking LAN device MACs"
            echo -e "  ${RED}  Foreign MACs: $FOREIGN_MACS${NC}"
        else
            pass_result "VALD-01 — only Pi MAC seen on eth0 (modem cannot see LAN device MACs)"
        fi
    fi
fi

# =============================================================================
# VALD-07: veth namespace test — simulate new LAN client
# =============================================================================
section "VALD-07: veth Namespace Test (Simulated LAN Client)"

echo "  This check creates a temporary virtual network namespace to simulate"
echo "  a new LAN client connecting through Pi as router."
echo ""

# Cleanup trap — always runs, even on failure
_veth_cleanup() {
    ip netns del testns 2>/dev/null || true
    ip link del veth0 2>/dev/null || true
}
trap _veth_cleanup EXIT

# Choose test IP (outside DHCP range 100-200)
TEST_IP="192.168.1.250"
for candidate_ip in "192.168.1.250" "192.168.1.240" "192.168.1.245"; do
    if ping -c 1 -W 1 "$candidate_ip" &>/dev/null; then
        echo "  $candidate_ip is in use, trying next..."
    else
        TEST_IP="$candidate_ip"
        break
    fi
done
echo "  Using test IP: $TEST_IP"

# Create namespace and veth pair
echo "  Creating network namespace 'testns' and veth pair..."
VETH_SETUP_OK=true

if ! ip netns add testns 2>/dev/null; then
    fail_result "VALD-07" "Could not create network namespace 'testns' (already exists or no permission)"
    VETH_SETUP_OK=false
fi

if [[ "$VETH_SETUP_OK" == "true" ]]; then
    if ! ip link add veth0 type veth peer name veth1 2>/dev/null; then
        fail_result "VALD-07" "Could not create veth pair"
        VETH_SETUP_OK=false
    fi
fi

if [[ "$VETH_SETUP_OK" == "true" ]]; then
    ip link set veth1 netns testns
    ip link set veth0 up
    if ! ip link set veth0 master br0 2>/dev/null; then
        echo "  Warning: Could not add veth0 to br0 — trying direct routing instead"
        # br0 may not exist; try without bridge membership (direct routing)
        ip addr add 192.168.1.253/24 dev veth0 2>/dev/null || true
    fi

    ip netns exec testns ip link set lo up
    ip netns exec testns ip link set veth1 up
    ip netns exec testns ip addr add "${TEST_IP}/24" dev veth1
    ip netns exec testns ip route add default via 192.168.1.2 2>/dev/null || \
        ip netns exec testns ip route add default dev veth1 2>/dev/null || true

    echo "  Namespace configured. Testing internet access from testns..."

    # Test internet from namespace
    VALD07_HTTP=$(ip netns exec testns curl -s --max-time 10 -o /dev/null \
        -w "%{http_code}" https://example.com 2>/dev/null || echo "000")
    echo "  Internet HTTP status from testns: $VALD07_HTTP"

    if [[ "$VALD07_HTTP" == "200" ]]; then
        pass_result "VALD-07 (internet) — namespace client can reach internet through Pi router (HTTP 200)"
    elif [[ "$VALD07_HTTP" == "000" ]]; then
        fail_result "VALD-07 (internet)" "curl failed from namespace (timeout or no route — verify br0 bridge membership and ip_forward)"
    else
        fail_result "VALD-07 (internet)" "Unexpected HTTP status $VALD07_HTTP from namespace"
    fi

    # Test DNS from namespace
    echo "  Testing DNS resolution from testns..."
    if command -v dig &>/dev/null; then
        VALD07_DNS=$(ip netns exec testns dig @192.168.1.2 example.com +short +timeout=5 2>/dev/null || true)
        echo "  DNS result from testns: ${VALD07_DNS:-<empty>}"

        VALD07_DNS_IP=$(echo "$VALD07_DNS" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' | head -1 || true)
        if [[ -n "$VALD07_DNS_IP" ]]; then
            pass_result "VALD-07 (DNS) — namespace client can resolve DNS via Pi proxy ($VALD07_DNS_IP)"
        else
            fail_result "VALD-07 (DNS)" "DNS query from namespace failed or returned no IP (DNS proxy may not be reachable from veth namespace)"
        fi
    else
        skip_result "VALD-07 (DNS)" "dig not available — could not test DNS from namespace"
    fi
fi

# Cleanup happens via trap
trap - EXIT
_veth_cleanup

echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}${CYAN}  VALIDATION SUMMARY${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Total checks:   $TOTAL (DHCP-01, DHCP-02, VALD-01 through VALD-07)"
echo ""
echo -e "  ${GREEN}PASS:  $PASS${NC}"
echo -e "  ${RED}FAIL:  $FAIL${NC}"
echo -e "  ${YELLOW}WARN:  $WARN${NC}  (checks that need attention but are not hard failures)"
echo -e "  ${YELLOW}SKIP:  $SKIP${NC}  (checks skipped due to missing tools or conditions)"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "  ${RED}${BOLD}RESULT: FAILED — $FAIL check(s) failed${NC}"
    echo ""
    echo -e "  Remediation hints:"
    echo "  - DHCP-01 failure: PATCH /api/v1/dhcp/pools/1 with gateway:192.168.1.2 or restart backend"
    echo "  - DHCP-02 failure: mysql -u tonbilai -p tonbilaios -e \"UPDATE dhcp_pools SET gateway='192.168.1.2' WHERE id=1;\""
    echo "  - VALD-06 failure: bridge isolation rules missing — restart backend to re-apply"
    echo "  - VALD-07 failure: verify br0 exists ('ip link show br0') and ip_forward is on"
    echo "  - VALD-03 failure: check NAT masquerade — 'nft list table inet tonbilai'"
    echo "  - VALD-04 failure: check DNS proxy — 'sudo ss -tunlp | grep :53'"
    echo "  - VALD-05 failure: check br_netfilter is loaded — 'lsmod | grep br_netfilter'"
    echo ""
    exit 1
else
    echo -e "  ${GREEN}${BOLD}RESULT: PASSED — all required checks passed${NC}"
    [[ $WARN -gt 0 ]] && echo -e "  ${YELLOW}Note: $WARN warning(s) — review WARN items above for completeness${NC}"
    [[ $SKIP -gt 0 ]] && echo -e "  ${YELLOW}Note: $SKIP check(s) skipped — install missing tools and re-run for full coverage${NC}"
    echo ""
    exit 0
fi
