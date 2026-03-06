package com.tonbil.aifirewall.data.remote

import com.tonbil.aifirewall.data.local.ServerConfig
import io.ktor.client.HttpClient
import io.ktor.client.request.get
import io.ktor.client.statement.HttpResponse
import io.ktor.http.isSuccess
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.firstOrNull

class ServerDiscovery(
    private val serverConfig: ServerConfig,
    private val testClient: HttpClient
) {
    var activeUrl: String = ""
        private set

    private val _isDiscovered = MutableStateFlow(false)
    val isDiscovered: StateFlow<Boolean> = _isDiscovered.asStateFlow()

    private val _isDiscovering = MutableStateFlow(false)
    val isDiscovering: StateFlow<Boolean> = _isDiscovering.asStateFlow()

    suspend fun getActiveUrl(): String {
        if (activeUrl.isNotEmpty()) return activeUrl
        return discoverServer() ?: ""
    }

    suspend fun testConnection(url: String): Boolean {
        return try {
            val testUrl = url.trimEnd('/') + "/"
            val response: HttpResponse = testClient.get("${testUrl}${ApiRoutes.DASHBOARD_SUMMARY}")
            // Any HTTP response means server is reachable (401/403 = needs auth, still alive)
            response.status.value in 200..499
        } catch (_: Exception) {
            false
        }
    }

    suspend fun discoverServer(): String? {
        _isDiscovering.value = true
        try {
            // 1. Try saved server URL
            val savedUrl = serverConfig.serverUrlFlow.firstOrNull()
            if (!savedUrl.isNullOrBlank() && savedUrl != ApiRoutes.BASE_URL && testConnection(savedUrl)) {
                activeUrl = savedUrl
                _isDiscovered.value = true
                return savedUrl
            }

            // 2. Try last connected URL
            val lastUrl = serverConfig.getLastConnectedUrl().firstOrNull()
            if (!lastUrl.isNullOrBlank() && testConnection(lastUrl)) {
                activeUrl = lastUrl
                _isDiscovered.value = true
                return lastUrl
            }

            // 3. Try local network (192.168.1.2)
            if (testConnection(ApiRoutes.LOCAL_URL)) {
                activeUrl = ApiRoutes.LOCAL_URL
                serverConfig.setLastConnectedUrl(ApiRoutes.LOCAL_URL)
                _isDiscovered.value = true
                return ApiRoutes.LOCAL_URL
            }

            // 4. Try remote (wall.tonbilx.com)
            if (testConnection(ApiRoutes.BASE_URL)) {
                activeUrl = ApiRoutes.BASE_URL
                serverConfig.setLastConnectedUrl(ApiRoutes.BASE_URL)
                _isDiscovered.value = true
                return ApiRoutes.BASE_URL
            }

            return null
        } finally {
            _isDiscovering.value = false
        }
    }

    suspend fun switchToUrl(url: String) {
        activeUrl = url
        _isDiscovered.value = true
        serverConfig.setServerUrl(url)
        serverConfig.setLastConnectedUrl(url)
    }

    suspend fun resetAndRediscover(): String? {
        activeUrl = ""
        _isDiscovered.value = false
        return discoverServer()
    }
}
