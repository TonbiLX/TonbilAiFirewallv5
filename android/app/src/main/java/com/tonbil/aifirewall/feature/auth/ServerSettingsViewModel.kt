package com.tonbil.aifirewall.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.local.ServerConfig
import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.ServerDiscovery
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

sealed class ConnectionResult {
    data class Success(val url: String) : ConnectionResult()
    data class Failure(val message: String) : ConnectionResult()
}

data class ServerSettingsUiState(
    val serverUrl: String = "",
    val isTestingConnection: Boolean = false,
    val connectionResult: ConnectionResult? = null,
    val isAutoDiscovering: Boolean = false,
)

class ServerSettingsViewModel(
    private val serverDiscovery: ServerDiscovery,
    private val serverConfig: ServerConfig,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ServerSettingsUiState())
    val uiState: StateFlow<ServerSettingsUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            val currentUrl = serverConfig.serverUrlFlow.firstOrNull() ?: ApiRoutes.BASE_URL
            _uiState.update { it.copy(serverUrl = currentUrl) }
        }
    }

    fun onUrlChange(value: String) {
        _uiState.update { it.copy(serverUrl = value, connectionResult = null) }
    }

    fun testConnection() {
        val url = _uiState.value.serverUrl.trim()
        if (url.isBlank()) {
            _uiState.update { it.copy(connectionResult = ConnectionResult.Failure("URL bos olamaz")) }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isTestingConnection = true, connectionResult = null) }

            try {
                val success = serverDiscovery.testConnection(url)
                if (success) {
                    serverDiscovery.switchToUrl(url)
                    _uiState.update {
                        it.copy(
                            isTestingConnection = false,
                            connectionResult = ConnectionResult.Success(url),
                        )
                    }
                } else {
                    _uiState.update {
                        it.copy(
                            isTestingConnection = false,
                            connectionResult = ConnectionResult.Failure("Baglanti kurulamadi"),
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isTestingConnection = false,
                        connectionResult = ConnectionResult.Failure(
                            e.message ?: "Baglanti hatasi"
                        ),
                    )
                }
            }
        }
    }

    fun autoDiscover() {
        viewModelScope.launch {
            _uiState.update { it.copy(isAutoDiscovering = true, connectionResult = null) }

            try {
                val foundUrl = serverDiscovery.discoverServer()
                if (foundUrl != null) {
                    _uiState.update {
                        it.copy(
                            isAutoDiscovering = false,
                            serverUrl = foundUrl,
                            connectionResult = ConnectionResult.Success(foundUrl),
                        )
                    }
                } else {
                    _uiState.update {
                        it.copy(
                            isAutoDiscovering = false,
                            connectionResult = ConnectionResult.Failure("Sunucu bulunamadi"),
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isAutoDiscovering = false,
                        connectionResult = ConnectionResult.Failure(
                            e.message ?: "Kesif hatasi"
                        ),
                    )
                }
            }
        }
    }

    fun useLocalNetwork() {
        _uiState.update { it.copy(serverUrl = ApiRoutes.LOCAL_URL) }
        testConnection()
    }

    fun useRemoteServer() {
        _uiState.update { it.copy(serverUrl = ApiRoutes.BASE_URL) }
        testConnection()
    }
}
