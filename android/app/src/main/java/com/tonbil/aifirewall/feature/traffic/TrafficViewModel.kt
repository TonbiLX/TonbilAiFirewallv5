package com.tonbil.aifirewall.feature.traffic

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.FlowStatsDto
import com.tonbil.aifirewall.data.remote.dto.LiveFlowDto
import com.tonbil.aifirewall.data.remote.dto.TrafficHistoryDto
import com.tonbil.aifirewall.data.remote.dto.TrafficPerDeviceDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class TrafficUiState(
    val liveFlows: List<LiveFlowDto> = emptyList(),
    val flowStats: FlowStatsDto? = null,
    val largeTransfers: List<LiveFlowDto> = emptyList(),
    val history: TrafficHistoryDto? = null,
    val perDevice: List<TrafficPerDeviceDto> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
    val selectedTab: Int = 0,
    val historyPage: Int = 1,
    val historySearchQuery: String = "",
)

class TrafficViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(TrafficUiState())
    val uiState: StateFlow<TrafficUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val flows = async { securityRepository.getLiveFlows() }
                    val stats = async { securityRepository.getFlowStats() }
                    val large = async { securityRepository.getLargeTransfers() }
                    val hist = async { securityRepository.getTrafficHistory(page = _uiState.value.historyPage) }
                    val perDev = async { securityRepository.getTrafficPerDevice() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            liveFlows = flows.await().getOrElse { emptyList() },
                            flowStats = stats.await().getOrNull(),
                            largeTransfers = large.await().getOrElse { emptyList() },
                            history = hist.await().getOrNull(),
                            perDevice = perDev.await().getOrElse { emptyList() },
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = e.message ?: "Bilinmeyen hata",
                    )
                }
            }
        }
    }

    fun loadLiveFlows() {
        viewModelScope.launch {
            securityRepository.getLiveFlows()
                .onSuccess { flows ->
                    _uiState.update { it.copy(liveFlows = flows) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun loadLargeTransfers() {
        viewModelScope.launch {
            securityRepository.getLargeTransfers()
                .onSuccess { large ->
                    _uiState.update { it.copy(largeTransfers = large) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun loadHistory(page: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(historyPage = page) }
            securityRepository.getTrafficHistory(page = page)
                .onSuccess { hist ->
                    _uiState.update { it.copy(history = hist) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun loadPerDevice() {
        viewModelScope.launch {
            securityRepository.getTrafficPerDevice()
                .onSuccess { perDev ->
                    _uiState.update { it.copy(perDevice = perDev) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(error = e.message) }
                }
        }
    }

    fun selectTab(idx: Int) {
        _uiState.update { it.copy(selectedTab = idx) }
    }

    fun updateHistorySearchQuery(query: String) {
        _uiState.update { it.copy(historySearchQuery = query) }
    }
}
