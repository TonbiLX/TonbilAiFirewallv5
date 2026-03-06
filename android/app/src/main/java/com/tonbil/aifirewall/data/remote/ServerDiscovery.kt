package com.tonbil.aifirewall.data.remote

import com.tonbil.aifirewall.data.local.ServerConfig
import io.ktor.client.HttpClient
import io.ktor.client.request.get
import io.ktor.client.statement.HttpResponse
import io.ktor.http.isSuccess
import kotlinx.coroutines.flow.firstOrNull

class ServerDiscovery(
    private val serverConfig: ServerConfig,
    private val testClient: HttpClient
) {
    var activeUrl: String = ApiRoutes.BASE_URL
        private set

    suspend fun getActiveUrl(): String {
        if (activeUrl.isNotEmpty()) return activeUrl
        return discoverServer() ?: ApiRoutes.BASE_URL
    }

    suspend fun testConnection(url: String): Boolean {
        return try {
            val response: HttpResponse = testClient.get("${url}${ApiRoutes.DASHBOARD_SUMMARY}")
            response.status.isSuccess()
        } catch (_: Exception) {
            false
        }
    }

    suspend fun discoverServer(): String? {
        // 1. Try last connected URL
        val lastUrl = serverConfig.getLastConnectedUrl().firstOrNull()
        if (lastUrl != null && testConnection(lastUrl)) {
            activeUrl = lastUrl
            return lastUrl
        }

        // 2. Try local network (192.168.1.2)
        if (testConnection(ApiRoutes.LOCAL_URL)) {
            activeUrl = ApiRoutes.LOCAL_URL
            serverConfig.setLastConnectedUrl(ApiRoutes.LOCAL_URL)
            return ApiRoutes.LOCAL_URL
        }

        // 3. Try remote (wall.tonbilx.com)
        if (testConnection(ApiRoutes.BASE_URL)) {
            activeUrl = ApiRoutes.BASE_URL
            serverConfig.setLastConnectedUrl(ApiRoutes.BASE_URL)
            return ApiRoutes.BASE_URL
        }

        return null
    }

    suspend fun switchToUrl(url: String) {
        activeUrl = url
        serverConfig.setServerUrl(url)
        serverConfig.setLastConnectedUrl(url)
    }
}
