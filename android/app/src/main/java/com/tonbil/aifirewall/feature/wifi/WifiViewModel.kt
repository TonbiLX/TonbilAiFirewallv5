package com.tonbil.aifirewall.feature.wifi

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.WifiClientDto
import com.tonbil.aifirewall.data.remote.dto.WifiConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.WifiStatusDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class WifiUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val status: WifiStatusDto? = null,
    val clients: List<WifiClientDto> = emptyList(),
    // Config edit fields
    val editSsid: String = "",
    val editPassword: String = "",
    val editChannel: String = "",
    val isEditing: Boolean = false,
)

class WifiViewModel(
    private val repository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(WifiUiState())
    val uiState: StateFlow<WifiUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = it.status == null) }
            try {
                coroutineScope {
                    val statusDeferred = async { repository.getWifiStatus() }
                    val clientsDeferred = async { repository.getWifiClients() }

                    val status = statusDeferred.await().getOrNull()
                    val clients = clientsDeferred.await().getOrElse { emptyList() }

                    _uiState.update { state ->
                        state.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            status = status,
                            clients = clients,
                            editSsid = status?.ssid ?: "",
                            editChannel = if ((status?.channel ?: 0) > 0) status?.channel.toString() else "",
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = e.message ?: "Bilinmeyen hata",
                    )
                }
            }
        }
    }

    fun refresh() {
        _uiState.update { it.copy(isRefreshing = true) }
        loadAll()
    }

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }

    fun toggleWifi() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            val isRunning = _uiState.value.status?.running == true
            val result = if (isRunning) repository.disableWifi() else repository.enableWifi()
            result
                .onSuccess {
                    _uiState.update {
                        it.copy(
                            isActionLoading = false,
                            actionMessage = if (isRunning) "WiFi kapatildi" else "WiFi acildi",
                        )
                    }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    fun startEditing() {
        _uiState.update { it.copy(isEditing = true) }
    }

    fun cancelEditing() {
        _uiState.update { state ->
            state.copy(
                isEditing = false,
                editSsid = state.status?.ssid ?: "",
                editPassword = "",
                editChannel = if ((state.status?.channel ?: 0) > 0) state.status?.channel.toString() else "",
            )
        }
    }

    fun updateEditSsid(value: String) {
        _uiState.update { it.copy(editSsid = value) }
    }

    fun updateEditPassword(value: String) {
        _uiState.update { it.copy(editPassword = value) }
    }

    fun updateEditChannel(value: String) {
        _uiState.update { it.copy(editChannel = value) }
    }

    fun saveConfig() {
        val state = _uiState.value
        val dto = WifiConfigUpdateDto(
            ssid = state.editSsid.ifBlank { null },
            password = state.editPassword.ifBlank { null },
            channel = state.editChannel.toIntOrNull(),
        )
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.updateWifiConfig(dto)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isActionLoading = false,
                            isEditing = false,
                            status = updated,
                            editSsid = updated.ssid,
                            editPassword = "",
                            editChannel = if (updated.channel > 0) updated.channel.toString() else "",
                            actionMessage = "WiFi ayarlari kaydedildi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }
}
