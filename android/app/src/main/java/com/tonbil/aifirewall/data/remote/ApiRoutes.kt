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
        return "${wsBase}ws?token=$token"
    }
}
