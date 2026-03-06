package com.tonbil.aifirewall.feature.devices

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.WebSocketManager
import com.tonbil.aifirewall.data.remote.dto.DeviceResponseDto
import com.tonbil.aifirewall.data.remote.dto.WsDeviceBandwidthDto
import com.tonbil.aifirewall.data.repository.DeviceRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DevicesUiState(
    val devices: List<DeviceResponseDto> = emptyList(),
    val bandwidthMap: Map<String, WsDeviceBandwidthDto> = emptyMap(),
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
)

class DevicesViewModel(
    private val deviceRepository: DeviceRepository,
    private val webSocketManager: WebSocketManager,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DevicesUiState())
    val uiState: StateFlow<DevicesUiState> = _uiState.asStateFlow()

    init {
        loadDevices()

        // Collect WS bandwidth updates
        viewModelScope.launch {
            webSocketManager.messages.collect { update ->
                _uiState.update { state ->
                    state.copy(bandwidthMap = update.bandwidth.devices)
                }
            }
        }
    }

    private fun loadDevices() {
        viewModelScope.launch {
            deviceRepository.getDevices()
                .onSuccess { devices ->
                    _uiState.update {
                        it.copy(
                            devices = devices,
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                        )
                    }
                }
                .onFailure { e ->
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
        loadDevices()
    }

    fun toggleBlock(device: DeviceResponseDto) {
        viewModelScope.launch {
            val result = if (device.isBlocked) {
                deviceRepository.unblockDevice(device.id)
            } else {
                deviceRepository.blockDevice(device.id)
            }
            result.onSuccess { loadDevices() }
        }
    }
}
