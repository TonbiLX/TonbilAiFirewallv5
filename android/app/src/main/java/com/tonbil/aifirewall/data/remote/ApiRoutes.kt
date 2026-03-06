package com.tonbil.aifirewall.data.remote

object ApiRoutes {
    const val BASE_URL = "http://wall.tonbilx.com/api/v1/"
    const val LOCAL_URL = "http://192.168.1.2/api/v1/"

    const val DASHBOARD_SUMMARY = "dashboard/summary"
    const val AUTH_LOGIN = "auth/login"
    const val AUTH_ME = "auth/me"
    const val AUTH_LOGOUT = "auth/logout"
    const val DEVICES = "devices"
    const val PROFILES = "profiles"

    // Security & Stats
    const val DNS_STATS = "dns/stats"
    const val DNS_BLOCKLISTS = "dns/blocklists"
    const val FIREWALL_STATS = "firewall/stats"
    const val FIREWALL_CONNECTIONS_COUNT = "firewall/connections/count"
    const val VPN_STATS = "vpn/stats"
    const val VPN_PEERS = "vpn/peers"
    const val DDOS_STATUS = "ddos/status"
    const val DDOS_COUNTERS = "ddos/counters"
    const val SECURITY_STATS = "security/stats"
    const val DHCP_STATS = "dhcp/stats"
    const val DHCP_LEASES_LIVE = "dhcp/leases/live"

    // DNS Management
    const val DNS_RULES = "dns/rules"

    // Traffic Flows
    const val TRAFFIC_FLOWS_LIVE = "traffic/flows/live"
    const val TRAFFIC_FLOWS_STATS = "traffic/flows/stats"
    const val TRAFFIC_TOTAL = "traffic/total"

    // Firewall Rules
    const val FIREWALL_RULES = "firewall/rules"

    // AI Insights
    const val INSIGHTS = "insights"
    const val INSIGHTS_CRITICAL_COUNT = "insights/critical-count"

    // WiFi
    const val WIFI_STATUS = "wifi/status"
    const val WIFI_CLIENTS = "wifi/clients"

    // Telegram
    const val TELEGRAM_CONFIG = "telegram/config"

    // System
    const val SYSTEM_OVERVIEW = "system-management/overview"
    const val SYSTEM_SERVICES = "system-management/services"

    // Chat
    const val CHAT_SEND = "chat/send"
    const val CHAT_HISTORY = "chat/history"

    fun deviceDetail(id: Int) = "$DEVICES/$id"
    fun deviceBlock(id: Int) = "$DEVICES/$id/block"
    fun deviceUnblock(id: Int) = "$DEVICES/$id/unblock"
    fun deviceConnectionHistory(id: Int) = "$DEVICES/$id/connection-history"
    fun deviceDnsQueries(id: Int) = "traffic/per-device/$id/dns-queries"
    fun deviceTrafficSummary(id: Int) = "traffic/per-device/$id/connections"

    fun wsUrl(serverDiscovery: ServerDiscovery, token: String): String {
        val baseUrl = serverDiscovery.activeUrl
        val wsBase = baseUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            .removeSuffix("/")
        return "${wsBase}/ws?token=$token"
    }
}
