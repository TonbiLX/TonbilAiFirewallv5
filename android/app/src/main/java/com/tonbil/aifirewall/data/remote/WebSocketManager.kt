package com.tonbil.aifirewall.data.remote

import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.data.remote.dto.RealtimeUpdateDto
import io.ktor.client.HttpClient
import io.ktor.client.plugins.websocket.webSocket
import io.ktor.websocket.Frame
import io.ktor.websocket.readText
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json

class WebSocketManager(
    private val client: HttpClient,
    private val serverDiscovery: ServerDiscovery,
    private val tokenManager: TokenManager,
) {
    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    private val _messages = MutableSharedFlow<RealtimeUpdateDto>(
        replay = 1,
        extraBufferCapacity = 5,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )
    val messages: SharedFlow<RealtimeUpdateDto> = _messages.asSharedFlow()

    private val _connectionState = MutableStateFlow(WebSocketState.DISCONNECTED)
    val connectionState: StateFlow<WebSocketState> = _connectionState.asStateFlow()

    private var wsJob: Job? = null
    private var scope: CoroutineScope? = null

    fun connect(scope: CoroutineScope) {
        this.scope = scope
        reconnect()
    }

    fun disconnect() {
        wsJob?.cancel()
        wsJob = null
        _connectionState.value = WebSocketState.DISCONNECTED
    }

    private fun reconnect() {
        wsJob?.cancel()
        val currentScope = scope ?: return
        val token = tokenManager.getToken() ?: return

        wsJob = currentScope.launch {
            while (isActive) {
                try {
                    _connectionState.value = WebSocketState.CONNECTING
                    val wsUrl = ApiRoutes.wsUrl(serverDiscovery, token)
                    client.webSocket(wsUrl) {
                        _connectionState.value = WebSocketState.CONNECTED
                        for (frame in incoming) {
                            if (frame is Frame.Text) {
                                try {
                                    val update = json.decodeFromString<RealtimeUpdateDto>(frame.readText())
                                    if (update.type == "realtime_update") {
                                        _messages.emit(update)
                                    }
                                } catch (_: Exception) { /* skip malformed */ }
                            }
                        }
                    }
                } catch (_: Exception) {
                    _connectionState.value = WebSocketState.DISCONNECTED
                }
                // Reconnect after 3 seconds on disconnect
                delay(3000)
            }
        }
    }
}

enum class WebSocketState { DISCONNECTED, CONNECTING, CONNECTED }
