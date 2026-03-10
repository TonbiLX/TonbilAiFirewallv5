package com.tonbil.aifirewall.data.remote

import android.util.Log
import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.data.remote.dto.RealtimeUpdateDto
import com.tonbil.aifirewall.data.remote.dto.SecurityEventDto
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
    private val networkMonitor: NetworkMonitor,
) {
    private val json = Json { ignoreUnknownKeys = true; isLenient = true; coerceInputValues = true }

    private val _messages = MutableSharedFlow<RealtimeUpdateDto>(
        replay = 1,
        extraBufferCapacity = 5,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )
    val messages: SharedFlow<RealtimeUpdateDto> = _messages.asSharedFlow()

    private val _securityEvents = MutableSharedFlow<SecurityEventDto>(
        extraBufferCapacity = 10,
        onBufferOverflow = BufferOverflow.DROP_OLDEST,
    )
    val securityEvents: SharedFlow<SecurityEventDto> = _securityEvents.asSharedFlow()

    private val _connectionState = MutableStateFlow(WebSocketState.DISCONNECTED)
    val connectionState: StateFlow<WebSocketState> = _connectionState.asStateFlow()

    private var wsJob: Job? = null
    private var networkJob: Job? = null
    private var scope: CoroutineScope? = null
    private var retryDelay = INITIAL_RETRY_DELAY
    private var consecutiveFailures = 0

    fun connect(scope: CoroutineScope) {
        this.scope = scope
        startNetworkObserver(scope)
        reconnect()
    }

    fun disconnect() {
        wsJob?.cancel()
        wsJob = null
        networkJob?.cancel()
        networkJob = null
        _connectionState.value = WebSocketState.DISCONNECTED
        retryDelay = INITIAL_RETRY_DELAY
        consecutiveFailures = 0
    }

    fun forceReconnect() {
        retryDelay = INITIAL_RETRY_DELAY
        consecutiveFailures = 0
        reconnect()
    }

    private fun startNetworkObserver(scope: CoroutineScope) {
        networkJob?.cancel()
        networkJob = scope.launch {
            networkMonitor.networkEvents.collect { event ->
                Log.d(TAG, "Network event: $event")
                when (event) {
                    NetworkEvent.CONNECTED, NetworkEvent.NETWORK_CHANGED -> {
                        // Network changed — rediscover and WAIT for it before reconnecting
                        Log.d(TAG, "Network event: $event, rediscovering...")
                        val newUrl = serverDiscovery.resetAndRediscover()
                        Log.d(TAG, "Discovery result: $newUrl")
                        if (newUrl != null) {
                            forceReconnect()
                        }
                    }
                    NetworkEvent.DISCONNECTED -> {
                        _connectionState.value = WebSocketState.DISCONNECTED
                    }
                }
            }
        }
    }

    private fun reconnect() {
        wsJob?.cancel()
        val currentScope = scope ?: return
        val token = tokenManager.getToken() ?: run {
            Log.d(TAG, "No token available, skipping WebSocket connect")
            return
        }

        wsJob = currentScope.launch {
            while (isActive) {
                // Wait for network to be available
                if (!networkMonitor.isOnline.value) {
                    _connectionState.value = WebSocketState.DISCONNECTED
                    delay(1000)
                    continue
                }

                try {
                    _connectionState.value = WebSocketState.CONNECTING

                    // If no active URL, try to discover
                    if (serverDiscovery.activeUrl.isEmpty()) {
                        val discovered = serverDiscovery.discoverServer()
                        if (discovered == null) {
                            Log.d(TAG, "Server discovery failed, retrying in ${retryDelay}ms")
                            delay(retryDelay)
                            retryDelay = (retryDelay * 2).coerceAtMost(MAX_RETRY_DELAY)
                            continue
                        }
                    }

                    val wsUrl = ApiRoutes.wsUrl(serverDiscovery, token)
                    Log.d(TAG, "Connecting WebSocket to: $wsUrl")
                    client.webSocket(wsUrl) {
                        _connectionState.value = WebSocketState.CONNECTED
                        retryDelay = INITIAL_RETRY_DELAY
                        consecutiveFailures = 0
                        Log.d(TAG, "WebSocket connected")

                        for (frame in incoming) {
                            if (frame is Frame.Text) {
                                val text = frame.readText()
                                try {
                                    // Tip kontrolu icin minimal parse
                                    if (text.contains("\"security_event\"")) {
                                        val event = json.decodeFromString<SecurityEventDto>(text)
                                        _securityEvents.emit(event)
                                        Log.d(TAG, "Security event received: ${event.eventType}/${event.severity}")
                                    } else {
                                        val update = json.decodeFromString<RealtimeUpdateDto>(text)
                                        if (update.type == "realtime_update") {
                                            _messages.emit(update)
                                        }
                                    }
                                } catch (e: Exception) {
                                    Log.w(TAG, "Failed to parse WS frame: ${e.message}")
                                }
                            }
                        }
                    }
                } catch (e: Exception) {
                    Log.d(TAG, "WebSocket error: ${e.message}")
                    _connectionState.value = WebSocketState.DISCONNECTED
                    consecutiveFailures++

                    // After several failures, try rediscovering
                    if (consecutiveFailures >= 3) {
                        Log.d(TAG, "Multiple failures, rediscovering server...")
                        val newUrl = serverDiscovery.resetAndRediscover()
                        Log.d(TAG, "Rediscovery result: $newUrl")
                        consecutiveFailures = 0
                    }
                }

                delay(retryDelay)
                retryDelay = (retryDelay * 2).coerceAtMost(MAX_RETRY_DELAY)
            }
        }
    }

    companion object {
        private const val TAG = "WebSocketManager"
        private const val INITIAL_RETRY_DELAY = 2000L
        private const val MAX_RETRY_DELAY = 30000L
    }
}

enum class WebSocketState { DISCONNECTED, CONNECTING, CONNECTED }
