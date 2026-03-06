package com.tonbil.aifirewall.data.remote

object ApiRoutes {
    const val BASE_URL = "http://wall.tonbilx.com/api/v1/"
    const val LOCAL_URL = "http://192.168.1.2/api/v1/"

    // Auth
    const val AUTH_LOGIN = "auth/login"
    const val AUTH_ME = "auth/me"
    const val AUTH_LOGOUT = "auth/logout"

    // Dashboard
    const val DASHBOARD_SUMMARY = "dashboard/summary"

    // Devices
    const val DEVICES = "devices"
    const val PROFILES = "profiles"

    // DNS
    const val DNS_STATS = "dns/stats"
    const val DNS_BLOCKLISTS = "dns/blocklists"
    const val DNS_RULES = "dns/rules"
    const val DNS_QUERIES = "dns/queries"

    // Firewall
    const val FIREWALL_STATS = "firewall/stats"
    const val FIREWALL_RULES = "firewall/rules"
    const val FIREWALL_CONNECTIONS_COUNT = "firewall/connections/count"

    // VPN
    const val VPN_STATS = "vpn/stats"
    const val VPN_PEERS = "vpn/peers"
    const val VPN_CONFIG = "vpn/config"
    const val VPN_START = "vpn/start"
    const val VPN_STOP = "vpn/stop"

    // DDoS
    const val DDOS_STATUS = "ddos/status"
    const val DDOS_COUNTERS = "ddos/counters"

    // Security
    const val SECURITY_STATS = "security/stats"
    const val SECURITY_CONFIG = "security/config"
    const val SECURITY_RELOAD = "security/reload"
    const val SECURITY_RESET = "security/reset"

    // DHCP
    const val DHCP_STATS = "dhcp/stats"
    const val DHCP_LEASES_LIVE = "dhcp/leases/live"
    const val DHCP_POOLS = "dhcp/pools"
    const val DHCP_LEASES_STATIC = "dhcp/leases/static"

    // Traffic
    const val TRAFFIC_FLOWS_LIVE = "traffic/flows/live"
    const val TRAFFIC_FLOWS_STATS = "traffic/flows/stats"
    const val TRAFFIC_TOTAL = "traffic/total"

    // Content Categories
    const val CONTENT_CATEGORIES = "content-categories"

    // AI Insights
    const val INSIGHTS = "insights"
    const val INSIGHTS_CRITICAL_COUNT = "insights/critical-count"

    // WiFi
    const val WIFI_STATUS = "wifi/status"
    const val WIFI_CONFIG = "wifi/config"
    const val WIFI_ENABLE = "wifi/enable"
    const val WIFI_DISABLE = "wifi/disable"
    const val WIFI_CLIENTS = "wifi/clients"

    // Telegram
    const val TELEGRAM_CONFIG = "telegram/config"
    const val TELEGRAM_TEST = "telegram/test"

    // System
    const val SYSTEM_OVERVIEW = "system-management/overview"
    const val SYSTEM_SERVICES = "system-management/services"

    // Chat
    const val CHAT_SEND = "chat/send"
    const val CHAT_HISTORY = "chat/history"

    // Device routes
    fun deviceDetail(id: Int) = "$DEVICES/$id"
    fun deviceBlock(id: Int) = "$DEVICES/$id/block"
    fun deviceUnblock(id: Int) = "$DEVICES/$id/unblock"
    fun deviceConnectionHistory(id: Int) = "$DEVICES/$id/connection-history"
    fun deviceDnsQueries(deviceId: Int) = "traffic/per-device/$deviceId/dns-queries"
    fun deviceTrafficSummary(deviceId: Int) = "traffic/per-device/$deviceId/connections"

    // DNS management
    fun blocklistToggle(id: Int) = "$DNS_BLOCKLISTS/$id/toggle"
    fun blocklistDetail(id: Int) = "$DNS_BLOCKLISTS/$id"
    fun dnsRuleDetail(id: Int) = "$DNS_RULES/$id"

    // Firewall management
    fun firewallRuleDetail(id: Int) = "$FIREWALL_RULES/$id"
    fun firewallRuleToggle(id: Int) = "$FIREWALL_RULES/$id/toggle"

    // VPN management
    fun vpnPeerDelete(name: String) = "$VPN_PEERS/$name"
    fun vpnPeerQr(name: String) = "$VPN_PEERS/$name/qr"
    fun vpnPeerConfig(name: String) = "$VPN_PEERS/$name/config"

    // DHCP management
    fun dhcpPoolDetail(id: Int) = "$DHCP_POOLS/$id"
    fun dhcpPoolToggle(id: Int) = "$DHCP_POOLS/$id/toggle"
    fun dhcpStaticLeaseDelete(mac: String) = "$DHCP_LEASES_STATIC/$mac"

    // Profile management
    fun profileDetail(id: Int) = "$PROFILES/$id"

    // Content categories
    fun contentCategoryDetail(id: Int) = "$CONTENT_CATEGORIES/$id"

    fun wsUrl(serverDiscovery: ServerDiscovery, token: String): String {
        val baseUrl = serverDiscovery.activeUrl
        val wsBase = baseUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            .removeSuffix("/")
        return "${wsBase}/ws?token=$token"
    }
}
