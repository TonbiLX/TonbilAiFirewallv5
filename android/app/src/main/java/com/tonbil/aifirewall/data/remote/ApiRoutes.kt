package com.tonbil.aifirewall.data.remote

object ApiRoutes {
    const val BASE_URL = "http://wall.tonbilx.com/api/v1/"
    const val LOCAL_URL = "http://192.168.1.2/api/v1/"

    // ========== Auth ==========
    const val AUTH_LOGIN = "auth/login"
    const val AUTH_ME = "auth/me"
    const val AUTH_LOGOUT = "auth/logout"
    const val AUTH_CHECK = "auth/check"
    const val AUTH_SETUP = "auth/setup"
    const val AUTH_PROFILE = "auth/profile"
    const val AUTH_CHANGE_PASSWORD = "auth/change-password"

    // ========== Dashboard ==========
    const val DASHBOARD_SUMMARY = "dashboard/summary"

    // ========== Devices ==========
    const val DEVICES = "devices"
    const val DEVICES_SCAN = "devices/scan"
    fun deviceDetail(id: Int) = "$DEVICES/$id"
    fun deviceBlock(id: Int) = "$DEVICES/$id/block"
    fun deviceUnblock(id: Int) = "$DEVICES/$id/unblock"
    fun deviceConnectionHistory(id: Int) = "$DEVICES/$id/connection-history"
    fun deviceBandwidth(id: Int) = "$DEVICES/$id/bandwidth"

    // ========== Profiles ==========
    const val PROFILES = "profiles"
    fun profileDetail(id: Int) = "$PROFILES/$id"

    // ========== DNS ==========
    const val DNS_STATS = "dns/stats"
    const val DNS_BLOCKLISTS = "dns/blocklists"
    const val DNS_BLOCKLISTS_REFRESH_ALL = "dns/blocklists/refresh-all"
    const val DNS_RULES = "dns/rules"
    const val DNS_QUERIES = "dns/queries"
    const val DNS_QUERIES_EXTERNAL_SUMMARY = "dns/queries/external-summary"
    fun dnsLookup(domain: String) = "dns/lookup/$domain"
    fun blocklistDetail(id: Int) = "$DNS_BLOCKLISTS/$id"
    fun blocklistToggle(id: Int) = "$DNS_BLOCKLISTS/$id/toggle"
    fun blocklistRefresh(id: Int) = "$DNS_BLOCKLISTS/$id/refresh"
    fun dnsRuleDetail(id: Int) = "$DNS_RULES/$id"

    // ========== DHCP ==========
    const val DHCP_STATS = "dhcp/stats"
    const val DHCP_POOLS = "dhcp/pools"
    const val DHCP_LEASES = "dhcp/leases"
    const val DHCP_LEASES_LIVE = "dhcp/leases/live"
    const val DHCP_LEASES_STATIC = "dhcp/leases/static"
    const val DHCP_SERVICE_STATUS = "dhcp/service/status"
    fun dhcpPoolDetail(id: Int) = "$DHCP_POOLS/$id"
    fun dhcpPoolToggle(id: Int) = "$DHCP_POOLS/$id/toggle"
    fun dhcpStaticLeaseDelete(mac: String) = "$DHCP_LEASES_STATIC/$mac"
    fun dhcpLeaseDelete(mac: String) = "$DHCP_LEASES/$mac"

    // ========== Firewall ==========
    const val FIREWALL_STATS = "firewall/stats"
    const val FIREWALL_RULES = "firewall/rules"
    const val FIREWALL_CONNECTIONS = "firewall/connections"
    const val FIREWALL_CONNECTIONS_COUNT = "firewall/connections/count"
    const val FIREWALL_SCAN = "firewall/scan"
    fun firewallRuleDetail(id: Int) = "$FIREWALL_RULES/$id"
    fun firewallRuleToggle(id: Int) = "$FIREWALL_RULES/$id/toggle"

    // ========== VPN (WireGuard Server) ==========
    const val VPN_STATS = "vpn/stats"
    const val VPN_PEERS = "vpn/peers"
    const val VPN_CONFIG = "vpn/config"
    const val VPN_START = "vpn/start"
    const val VPN_STOP = "vpn/stop"
    fun vpnPeerDelete(name: String) = "$VPN_PEERS/$name"
    fun vpnPeerQr(name: String) = "$VPN_PEERS/$name/qr"
    fun vpnPeerConfig(name: String) = "$VPN_PEERS/$name/config"

    // ========== VPN Client (External VPN) ==========
    const val VPN_CLIENT_SERVERS = "vpn-client/servers"
    const val VPN_CLIENT_IMPORT = "vpn-client/servers/import"
    const val VPN_CLIENT_STATUS = "vpn-client/status"
    const val VPN_CLIENT_STATS = "vpn-client/stats"
    fun vpnClientServerDetail(id: Int) = "vpn-client/servers/$id"
    fun vpnClientActivate(id: Int) = "vpn-client/servers/$id/activate"
    fun vpnClientDeactivate(id: Int) = "vpn-client/servers/$id/deactivate"

    // ========== DDoS ==========
    const val DDOS_STATUS = "ddos/status"
    const val DDOS_COUNTERS = "ddos/counters"
    const val DDOS_CONFIG = "ddos/config"
    const val DDOS_APPLY = "ddos/apply"
    const val DDOS_FLUSH_ATTACKERS = "ddos/flush-attackers"
    const val DDOS_ATTACK_MAP = "ddos/attack-map"
    fun ddosToggle(name: String) = "ddos/toggle/$name"

    // ========== Security Settings ==========
    const val SECURITY_STATS = "security/stats"
    const val SECURITY_CONFIG = "security/config"
    const val SECURITY_RELOAD = "security/reload"
    const val SECURITY_RESET = "security/reset"
    const val SECURITY_DEFAULTS = "security/defaults"

    // ========== Content Categories ==========
    const val CONTENT_CATEGORIES = "content-categories"
    fun contentCategoryDetail(id: Int) = "$CONTENT_CATEGORIES/$id"

    // ========== Services (Per-Device Service Blocking) ==========
    const val SERVICES = "services"
    const val SERVICES_GROUPS = "services/groups"
    fun deviceServices(deviceId: Int) = "services/devices/$deviceId"
    fun deviceServiceToggle(deviceId: Int) = "services/devices/$deviceId/toggle"
    fun deviceServiceBulk(deviceId: Int) = "services/devices/$deviceId/bulk"

    // ========== Device Custom Rules ==========
    const val DEVICE_RULES = "device-rules"
    fun deviceRuleCreate(deviceId: Int) = "device-rules/devices/$deviceId"
    fun deviceRuleDetail(ruleId: Int) = "device-rules/$ruleId"

    // ========== IP Management ==========
    const val IP_MGMT_STATS = "ip-management/stats"
    const val IP_MGMT_TRUSTED = "ip-management/trusted"
    const val IP_MGMT_BLOCKED = "ip-management/blocked"
    const val IP_MGMT_UNBLOCK = "ip-management/unblock"
    const val IP_MGMT_BULK_UNBLOCK = "ip-management/blocked/bulk-unblock"
    const val IP_MGMT_BULK_DURATION = "ip-management/blocked/bulk-duration"
    const val IP_MGMT_DURATION = "ip-management/blocked/duration"
    fun ipMgmtTrustedDelete(id: Int) = "ip-management/trusted/$id"

    // ========== IP Reputation ==========
    const val IP_REP_CONFIG = "ip-reputation/config"
    const val IP_REP_SUMMARY = "ip-reputation/summary"
    const val IP_REP_IPS = "ip-reputation/ips"
    const val IP_REP_CACHE = "ip-reputation/cache"
    const val IP_REP_TEST = "ip-reputation/test"
    const val IP_REP_BLACKLIST = "ip-reputation/blacklist"
    const val IP_REP_BLACKLIST_FETCH = "ip-reputation/blacklist/fetch"
    const val IP_REP_BLACKLIST_CONFIG = "ip-reputation/blacklist/config"
    const val IP_REP_API_USAGE = "ip-reputation/api-usage"
    const val IP_REP_BLACKLIST_API_USAGE = "ip-reputation/blacklist/api-usage"

    // ========== System Monitor ==========
    const val SYSTEM_INFO = "system-monitor/info"
    const val SYSTEM_METRICS = "system-monitor/metrics"
    const val SYSTEM_FAN = "system-monitor/fan"

    // ========== System Management ==========
    const val SYSTEM_OVERVIEW = "system-management/overview"
    const val SYSTEM_SERVICES = "system-management/services"
    const val SYSTEM_REBOOT = "system-management/reboot"
    const val SYSTEM_SHUTDOWN = "system-management/shutdown"
    const val SYSTEM_BOOT_INFO = "system-management/boot-info"
    const val SYSTEM_SAFE_MODE = "system-management/reset-safe-mode"
    const val SYSTEM_JOURNAL = "system-management/journal"
    fun systemServiceAction(name: String, action: String) = "system-management/services/$name/$action"

    // ========== System Time ==========
    const val SYSTEM_TIME_STATUS = "system-time/status"
    const val SYSTEM_TIME_TIMEZONES = "system-time/timezones"
    const val SYSTEM_TIME_NTP_SERVERS = "system-time/ntp-servers"
    const val SYSTEM_TIME_SET_TZ = "system-time/set-timezone"
    const val SYSTEM_TIME_SET_NTP = "system-time/set-ntp-server"
    const val SYSTEM_TIME_SYNC = "system-time/sync-now"

    // ========== TLS / DNS-over-TLS ==========
    const val TLS_CONFIG = "tls/config"
    const val TLS_VALIDATE = "tls/validate"
    const val TLS_UPLOAD = "tls/upload-cert"
    const val TLS_LETSENCRYPT = "tls/letsencrypt"
    const val TLS_TOGGLE = "tls/toggle"

    // ========== AI Settings ==========
    const val AI_CONFIG = "ai-settings/config"
    const val AI_TEST = "ai-settings/test"
    const val AI_PROVIDERS = "ai-settings/providers"
    const val AI_STATS = "ai-settings/stats"
    const val AI_RESET_COUNTER = "ai-settings/reset-counter"

    // ========== System Logs ==========
    const val SYSTEM_LOGS = "system-logs"
    const val SYSTEM_LOGS_SUMMARY = "system-logs/summary"

    // ========== AI Insights ==========
    const val INSIGHTS = "insights"
    const val INSIGHTS_CRITICAL_COUNT = "insights/critical-count"
    const val INSIGHTS_THREAT_STATS = "insights/threat-stats"
    const val INSIGHTS_BLOCKED_IPS = "insights/blocked-ips"
    const val INSIGHTS_BLOCK_IP = "insights/block-ip"
    const val INSIGHTS_UNBLOCK_IP = "insights/unblock-ip"
    fun insightDismiss(id: Int) = "insights/$id/dismiss"

    // ========== Traffic ==========
    const val TRAFFIC_FLOWS_LIVE = "traffic/flows/live"
    const val TRAFFIC_FLOWS_STATS = "traffic/flows/stats"
    const val TRAFFIC_LARGE_TRANSFERS = "traffic/flows/large-transfers"
    const val TRAFFIC_HISTORY = "traffic/flows/history"
    const val TRAFFIC_TOTAL = "traffic/total"
    const val TRAFFIC_PER_DEVICE = "traffic/per-device"
    const val TRAFFIC_REALTIME = "traffic/realtime"
    fun deviceTrafficHistory(deviceId: Int) = "traffic/per-device/$deviceId/history"
    fun deviceTrafficConnections(deviceId: Int) = "traffic/per-device/$deviceId/connections"
    fun deviceTopDestinations(deviceId: Int) = "traffic/per-device/$deviceId/top-destinations"
    fun deviceDnsQueries(deviceId: Int) = "traffic/per-device/$deviceId/dns-queries"
    fun deviceTrafficSummary(deviceId: Int) = "traffic/flows/device/$deviceId/summary"

    // ========== Telegram ==========
    const val TELEGRAM_CONFIG = "telegram/config"
    const val TELEGRAM_TEST = "telegram/test"

    // ========== WiFi ==========
    const val WIFI_STATUS = "wifi/status"
    const val WIFI_CONFIG = "wifi/config"
    const val WIFI_ENABLE = "wifi/enable"
    const val WIFI_DISABLE = "wifi/disable"
    const val WIFI_CLIENTS = "wifi/clients"
    const val WIFI_CHANNELS = "wifi/channels"
    const val WIFI_GUEST = "wifi/guest"
    const val WIFI_SCHEDULE = "wifi/schedule"
    const val WIFI_MAC_FILTER = "wifi/mac-filter"

    // ========== Chat ==========
    const val CHAT_SEND = "chat/send"
    const val CHAT_HISTORY = "chat/history"
    const val CHAT_HISTORY_DELETE = "chat/history"  // DELETE method

    // ========== Push Notifications ==========
    const val PUSH_REGISTER = "push/register"
    const val PUSH_CHANNELS = "push/channels"
    fun pushChannelToggle(channel: String) = "push/channels/$channel/toggle"

    // ========== WebSocket ==========
    fun wsUrl(serverDiscovery: ServerDiscovery, token: String): String {
        val baseUrl = serverDiscovery.activeUrl
        val wsBase = baseUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            .removeSuffix("/")
        return "${wsBase}/ws?token=$token"
    }
}
