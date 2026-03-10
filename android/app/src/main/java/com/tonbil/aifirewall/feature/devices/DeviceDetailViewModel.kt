package com.tonbil.aifirewall.feature.devices

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.WebSocketManager
import com.tonbil.aifirewall.data.remote.dto.ConnectionHistoryDto
import com.tonbil.aifirewall.data.remote.dto.DeviceResponseDto
import com.tonbil.aifirewall.data.remote.dto.DeviceTrafficSummaryDto
import com.tonbil.aifirewall.data.remote.dto.DeviceBandwidthDto
import com.tonbil.aifirewall.data.remote.dto.DeviceUpdateDto
import com.tonbil.aifirewall.data.remote.dto.DnsQueryLogDto
import com.tonbil.aifirewall.data.remote.dto.LiveFlowDto
import com.tonbil.aifirewall.data.remote.dto.ProfileResponseDto
import com.tonbil.aifirewall.data.remote.dto.WsDeviceBandwidthDto
import com.tonbil.aifirewall.data.repository.DeviceRepository
import com.tonbil.aifirewall.data.repository.ProfileRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DeviceDetailUiState(
    val device: DeviceResponseDto? = null,
    val profiles: List<ProfileResponseDto> = emptyList(),
    val connectionHistory: List<ConnectionHistoryDto> = emptyList(),
    val dnsLogs: List<DnsQueryLogDto> = emptyList(),
    val trafficSummary: DeviceTrafficSummaryDto? = null,
    val bandwidth: WsDeviceBandwidthDto? = null,
    val liveFlows: List<LiveFlowDto> = emptyList(),
    val isLiveFlowsLoading: Boolean = false,
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val selectedTab: Int = 0,
)

class DeviceDetailViewModel(
    private val deviceId: Int,
    private val deviceRepository: DeviceRepository,
    private val profileRepository: ProfileRepository,
    private val webSocketManager: WebSocketManager,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DeviceDetailUiState())
    val uiState: StateFlow<DeviceDetailUiState> = _uiState.asStateFlow()

    init {
        loadAll()

        // Collect WS bandwidth for this device
        viewModelScope.launch {
            webSocketManager.messages.collect { update ->
                _uiState.update { state ->
                    state.copy(
                        bandwidth = update.bandwidth.devices[deviceId.toString()]
                    )
                }
            }
        }
    }

    private fun loadAll() {
        viewModelScope.launch {
            try {
                coroutineScope {
                    val deviceDeferred = async { deviceRepository.getDevice(deviceId) }
                    val profilesDeferred = async { profileRepository.getProfiles() }
                    val historyDeferred = async { deviceRepository.getConnectionHistory(deviceId) }
                    val trafficDeferred = async { deviceRepository.getTrafficSummary(deviceId) }
                    val liveFlowsDeferred = async { deviceRepository.getDeviceLiveFlows(deviceId) }

                    val deviceResult = deviceDeferred.await()
                    val profilesResult = profilesDeferred.await()
                    val historyResult = historyDeferred.await()
                    val trafficResult = trafficDeferred.await()
                    val liveFlowsResult = liveFlowsDeferred.await()

                    // DNS logs need the device IP, so load after device
                    val dnsResult = deviceResult.getOrNull()?.ipAddress?.let { ip ->
                        deviceRepository.getDnsLogs(deviceId, ip)
                    }

                    _uiState.update { state ->
                        state.copy(
                            device = deviceResult.getOrNull(),
                            profiles = profilesResult.getOrElse { emptyList() },
                            connectionHistory = historyResult.getOrElse { emptyList() },
                            trafficSummary = trafficResult.getOrNull(),
                            dnsLogs = dnsResult?.getOrElse { emptyList() } ?: emptyList(),
                            liveFlows = liveFlowsResult.getOrElse { emptyList() },
                            isLoading = false,
                            isRefreshing = false,
                            error = if (deviceResult.isFailure)
                                deviceResult.exceptionOrNull()?.message ?: "Bilinmeyen hata"
                            else null,
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

    fun loadDeviceLiveFlows() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLiveFlowsLoading = true) }
            deviceRepository.getDeviceLiveFlows(deviceId)
                .onSuccess { flows ->
                    _uiState.update { it.copy(liveFlows = flows, isLiveFlowsLoading = false) }
                }
                .onFailure {
                    _uiState.update { it.copy(isLiveFlowsLoading = false) }
                }
        }
    }

    fun refresh() {
        _uiState.update { it.copy(isRefreshing = true) }
        loadAll()
    }

    fun selectTab(index: Int) {
        _uiState.update { it.copy(selectedTab = index) }
    }

    fun assignProfile(profileId: Int?) {
        viewModelScope.launch {
            deviceRepository.updateDevice(
                deviceId,
                DeviceUpdateDto(profileId = profileId),
            ).onSuccess { loadAll() }
        }
    }

    fun toggleBlock() {
        val device = _uiState.value.device ?: return
        viewModelScope.launch {
            val result = if (device.isBlocked) {
                deviceRepository.unblockDevice(device.id)
            } else {
                deviceRepository.blockDevice(device.id)
            }
            result.onSuccess { loadAll() }
        }
    }

    fun updateHostname(name: String) {
        viewModelScope.launch {
            deviceRepository.updateDevice(deviceId, DeviceUpdateDto(hostname = name))
                .onSuccess { loadAll() }
        }
    }

    fun updateBandwidth(mbps: Float?) {
        viewModelScope.launch {
            deviceRepository.updateBandwidth(deviceId, DeviceBandwidthDto(bandwidthLimitMbps = mbps))
                .onSuccess { loadAll() }
        }
    }

    fun toggleIptv() {
        val device = _uiState.value.device ?: return
        viewModelScope.launch {
            deviceRepository.updateDevice(deviceId, DeviceUpdateDto(isIptv = !device.isIptv))
                .onSuccess { loadAll() }
        }
    }
}
