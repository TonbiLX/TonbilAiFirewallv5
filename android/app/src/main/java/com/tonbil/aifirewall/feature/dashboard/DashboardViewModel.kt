package com.tonbil.aifirewall.feature.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.WebSocketManager
import com.tonbil.aifirewall.data.remote.WebSocketState
import com.tonbil.aifirewall.data.remote.dto.TopClientDto
import com.tonbil.aifirewall.data.remote.dto.TopDomainDto
import com.tonbil.aifirewall.data.repository.DashboardRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class BandwidthPoint(
    val timestamp: Long,
    val uploadBps: Long,
    val downloadBps: Long,
)

data class DashboardUiState(
    val connectionStatus: WebSocketState = WebSocketState.DISCONNECTED,
    val isLoading: Boolean = true,
    val error: String? = null,
    // Cihaz
    val totalDevices: Int = 0,
    val onlineDevices: Int = 0,
    val blockedDevices: Int = 0,
    // DNS
    val totalQueries24h: Int = 0,
    val blockedQueries24h: Int = 0,
    val blockPercentage: Float = 0f,
    val queriesPerMin: Int = 0,
    // Bandwidth
    val totalUploadBps: Long = 0,
    val totalDownloadBps: Long = 0,
    val bandwidthHistory: List<BandwidthPoint> = emptyList(),
    // VPN
    val vpnEnabled: Boolean = false,
    val vpnConnectedPeers: Int = 0,
    val vpnTotalPeers: Int = 0,
    // Top lists
    val topQueriedDomains: List<TopDomainDto> = emptyList(),
    val topBlockedDomains: List<TopDomainDto> = emptyList(),
    val topClients: List<TopClientDto> = emptyList(),
)

private const val MAX_BANDWIDTH_POINTS = 60 // Son 3 dakika (3sn aralik)

class DashboardViewModel(
    private val dashboardRepository: DashboardRepository,
    private val webSocketManager: WebSocketManager,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init {
        loadSummary()
        webSocketManager.connect(viewModelScope)

        // Collect WebSocket messages for live updates
        viewModelScope.launch {
            webSocketManager.messages.collect { update ->
                _uiState.update { state ->
                    val newPoint = BandwidthPoint(
                        timestamp = System.currentTimeMillis(),
                        uploadBps = update.bandwidth.totalUploadBps,
                        downloadBps = update.bandwidth.totalDownloadBps,
                    )
                    val history = (state.bandwidthHistory + newPoint).takeLast(MAX_BANDWIDTH_POINTS)

                    state.copy(
                        onlineDevices = update.deviceCount,
                        // DNS
                        totalQueries24h = update.dns.totalQueries24h,
                        blockedQueries24h = update.dns.blockedQueries24h,
                        blockPercentage = update.dns.blockPercentage,
                        queriesPerMin = update.dns.queriesPerMin,
                        // Bandwidth
                        totalUploadBps = update.bandwidth.totalUploadBps,
                        totalDownloadBps = update.bandwidth.totalDownloadBps,
                        bandwidthHistory = history,
                        // VPN
                        vpnEnabled = update.vpn.enabled,
                        vpnConnectedPeers = update.vpn.connectedPeers,
                        vpnTotalPeers = update.vpn.totalPeers,
                    )
                }
            }
        }

        // Collect connection state
        viewModelScope.launch {
            webSocketManager.connectionState.collect { wsState ->
                _uiState.update { it.copy(connectionStatus = wsState) }
            }
        }
    }

    private fun loadSummary() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            dashboardRepository.getSummary()
                .onSuccess { summary ->
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            error = null,
                            totalDevices = summary.devices.total,
                            onlineDevices = summary.devices.online,
                            blockedDevices = summary.devices.blocked,
                            totalQueries24h = summary.dns.totalQueries24h,
                            blockedQueries24h = summary.dns.blockedQueries24h,
                            blockPercentage = summary.dns.blockPercentage,
                            vpnEnabled = summary.vpn.enabled,
                            vpnConnectedPeers = summary.vpn.connectedPeers,
                            vpnTotalPeers = summary.vpn.totalPeers,
                            topQueriedDomains = summary.topQueriedDomains,
                            topBlockedDomains = summary.topBlockedDomains,
                            topClients = summary.topClients,
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            error = e.message ?: "Bilinmeyen hata",
                        )
                    }
                }
        }
    }

    fun refresh() {
        loadSummary()
    }

    override fun onCleared() {
        super.onCleared()
        webSocketManager.disconnect()
    }
}
