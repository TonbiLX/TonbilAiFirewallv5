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

enum class DeviceFilter { ALL, ONLINE, OFFLINE }
enum class DeviceSort { NAME, IP, LAST_SEEN }

data class DevicesUiState(
    val devices: List<DeviceResponseDto> = emptyList(),
    val bandwidthMap: Map<String, WsDeviceBandwidthDto> = emptyMap(),
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val filter: DeviceFilter = DeviceFilter.ALL,
    val sort: DeviceSort = DeviceSort.NAME,
    val searchQuery: String = "",
) {
    val filteredDevices: List<DeviceResponseDto>
        get() {
            val searched = if (searchQuery.isBlank()) devices else {
                val q = searchQuery.lowercase()
                devices.filter { d ->
                    (d.hostname?.lowercase()?.contains(q) == true) ||
                        (d.ipAddress?.lowercase()?.contains(q) == true) ||
                        d.macAddress.lowercase().contains(q)
                }
            }
            val filtered = when (filter) {
                DeviceFilter.ALL -> searched
                DeviceFilter.ONLINE -> searched.filter { it.isOnline }
                DeviceFilter.OFFLINE -> searched.filter { !it.isOnline }
            }
            return when (sort) {
                DeviceSort.NAME -> filtered.sortedBy { it.hostname?.lowercase() ?: "zzz" }
                DeviceSort.IP -> filtered.sortedBy { it.ipAddress ?: "255.255.255.255" }
                DeviceSort.LAST_SEEN -> filtered.sortedByDescending { it.lastSeen ?: "" }
            }
        }
}

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

    fun setFilter(filter: DeviceFilter) {
        _uiState.update { it.copy(filter = filter) }
    }

    fun setSort(sort: DeviceSort) {
        _uiState.update { it.copy(sort = sort) }
    }

    fun setSearchQuery(query: String) {
        _uiState.update { it.copy(searchQuery = query) }
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
