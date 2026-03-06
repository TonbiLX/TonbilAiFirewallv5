package com.tonbil.aifirewall.data.remote

object ApiRoutes {
    const val BASE_URL = "https://wall.tonbilx.com/api/v1/"
    const val LOCAL_URL = "http://192.168.1.2/api/v1/"

    const val DASHBOARD_SUMMARY = "dashboard/summary"
    const val AUTH_LOGIN = "auth/login"
    const val AUTH_ME = "auth/me"
    const val AUTH_LOGOUT = "auth/logout"
    const val AUTH_CHECK = "auth/check"
    const val DEVICES = "devices"
    const val PROFILES = "profiles"
    const val DNS_QUERY_LOGS = "dns/query-logs"
    const val TRAFFIC_FLOWS_DEVICE = "traffic/flows/device"

    fun deviceDetail(id: Int) = "$DEVICES/$id"
    fun deviceBlock(id: Int) = "$DEVICES/$id/block"
    fun deviceUnblock(id: Int) = "$DEVICES/$id/unblock"
    fun deviceConnectionHistory(id: Int) = "$DEVICES/$id/connection-history"
    fun deviceTrafficSummary(id: Int) = "$TRAFFIC_FLOWS_DEVICE/$id/summary"

    const val WS_URL = "wss://wall.tonbilx.com/api/v1/ws"

    fun wsUrl(serverDiscovery: ServerDiscovery, token: String): String {
        val baseUrl = serverDiscovery.activeUrl
        val wsBase = baseUrl
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            .removeSuffix("/")
        return "${wsBase}ws?token=$token"
    }
}
