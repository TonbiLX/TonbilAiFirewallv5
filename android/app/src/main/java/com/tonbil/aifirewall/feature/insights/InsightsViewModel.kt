package com.tonbil.aifirewall.feature.insights

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.AiInsightDto
import com.tonbil.aifirewall.data.remote.dto.InsightBlockIpDto
import com.tonbil.aifirewall.data.remote.dto.InsightBlockedIpDto
import com.tonbil.aifirewall.data.remote.dto.InsightThreatStatsDto
import com.tonbil.aifirewall.data.remote.dto.InsightUnblockIpDto
import com.tonbil.aifirewall.data.repository.InsightsRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class InsightsUiState(
    val insights: List<AiInsightDto> = emptyList(),
    val threatStats: InsightThreatStatsDto? = null,
    val blockedIps: List<InsightBlockedIpDto> = emptyList(),
    val isLoading: Boolean = true,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val blockedIpsExpanded: Boolean = false,
    val showBlockIpDialog: Boolean = false,
)

class InsightsViewModel(
    private val insightsRepository: InsightsRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(InsightsUiState())
    val uiState: StateFlow<InsightsUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val insightsDeferred = async { insightsRepository.getInsights() }
                    val statsDeferred = async { insightsRepository.getThreatStats() }
                    val blockedDeferred = async { insightsRepository.getBlockedIps() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            insights = insightsDeferred.await().getOrElse { emptyList() },
                            threatStats = statsDeferred.await().getOrNull(),
                            blockedIps = blockedDeferred.await().getOrElse { emptyList() },
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

    fun dismiss(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            insightsRepository.dismiss(id)
                .onSuccess {
                    _uiState.update {
                        it.copy(
                            isActionLoading = false,
                            insights = it.insights.filter { ins -> ins.id != id },
                            actionMessage = "Insight kapatildi",
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

    fun blockIp(ip: String, reason: String?) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showBlockIpDialog = false) }
            insightsRepository.blockIp(InsightBlockIpDto(ipAddress = ip, reason = reason))
                .onSuccess {
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "$ip engellendi") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    fun unblockIp(ip: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            insightsRepository.unblockIp(InsightUnblockIpDto(ipAddress = ip))
                .onSuccess {
                    _uiState.update {
                        it.copy(
                            isActionLoading = false,
                            blockedIps = it.blockedIps.filter { b -> b.ipAddress != ip },
                            actionMessage = "$ip engeli kaldirildi",
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

    fun toggleBlockedIpsExpanded() {
        _uiState.update { it.copy(blockedIpsExpanded = !it.blockedIpsExpanded) }
    }

    fun showBlockIpDialog() = _uiState.update { it.copy(showBlockIpDialog = true) }
    fun hideBlockIpDialog() = _uiState.update { it.copy(showBlockIpDialog = false) }

    fun clearActionMessage() = _uiState.update { it.copy(actionMessage = null) }
}
