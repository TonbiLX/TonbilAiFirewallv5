package com.tonbil.aifirewall.feature.ipreputation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.IpRepApiUsageDataDto
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistApiUsageDataDto
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistConfigDto
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistResponseDto
import com.tonbil.aifirewall.data.remote.dto.IpRepCheckDto
import com.tonbil.aifirewall.data.remote.dto.IpRepConfigDto
import com.tonbil.aifirewall.data.remote.dto.IpRepConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.IpRepSummaryDto
import com.tonbil.aifirewall.data.remote.dto.IpRepTestResponseDto
import com.tonbil.aifirewall.data.repository.IpReputationRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class IpReputationUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val selectedTab: Int = 0,
    // Data
    val config: IpRepConfigDto? = null,
    val summary: IpRepSummaryDto? = null,
    val ips: List<IpRepCheckDto> = emptyList(),
    val blacklistResponse: IpRepBlacklistResponseDto? = null,
    val blacklistConfig: IpRepBlacklistConfigDto? = null,
    // IP list sort
    val ipSortField: IpSortField = IpSortField.SCORE,
    val ipSortAscending: Boolean = false,
    // Test result
    val lastTestResult: IpRepTestResponseDto? = null,
    val isBlacklistFetching: Boolean = false,
    // API Usage
    val apiUsage: IpRepApiUsageDataDto? = null,
    val isCheckingApiUsage: Boolean = false,
    val blacklistApiUsage: IpRepBlacklistApiUsageDataDto? = null,
    val isCheckingBlacklistApiUsage: Boolean = false,
)

enum class IpSortField { SCORE, IP, COUNTRY, LAST_CHECKED }

class IpReputationViewModel(
    private val repository: IpReputationRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(IpReputationUiState())
    val uiState: StateFlow<IpReputationUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = it.config == null && it.summary == null) }
            try {
                coroutineScope {
                    val configDeferred = async { repository.getConfig() }
                    val summaryDeferred = async { repository.getSummary() }
                    val ipsDeferred = async { repository.getIps() }
                    val blacklistDeferred = async { repository.getBlacklist() }
                    val blConfigDeferred = async { repository.getBlacklistConfig() }

                    _uiState.update { state ->
                        state.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            config = configDeferred.await().getOrNull(),
                            summary = summaryDeferred.await().getOrNull(),
                            ips = sortIps(
                                ipsDeferred.await().getOrElse { emptyList() },
                                state.ipSortField,
                                state.ipSortAscending,
                            ),
                            blacklistResponse = blacklistDeferred.await().getOrNull(),
                            blacklistConfig = blConfigDeferred.await().getOrNull(),
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

    fun selectTab(index: Int) {
        _uiState.update { it.copy(selectedTab = index) }
    }

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }

    // ========== Config update ==========

    fun updateConfig(dto: IpRepConfigUpdateDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.updateConfig(dto)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Ayarlar kaydedildi", isActionLoading = false) }
                    // Reload config (backend returns masked key)
                    repository.getConfig().onSuccess { cfg ->
                        _uiState.update { it.copy(config = cfg) }
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    // ========== Cache clear ==========

    fun clearCache() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.clearCache()
                .onSuccess { resp ->
                    _uiState.update { it.copy(actionMessage = resp.message, isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    // ========== API test ==========

    fun testApi() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, lastTestResult = null) }
            repository.test()
                .onSuccess { result ->
                    val isOk = result.status == "ok"
                    _uiState.update {
                        it.copy(
                            lastTestResult = result,
                            actionMessage = if (isOk) "API testi basarili" else "API testi basarisiz: ${result.message}",
                            isActionLoading = false,
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    // ========== Blacklist ==========

    fun fetchBlacklist() {
        viewModelScope.launch {
            _uiState.update { it.copy(isBlacklistFetching = true) }
            repository.fetchBlacklist()
                .onSuccess { resp ->
                    _uiState.update { it.copy(actionMessage = resp.message, isBlacklistFetching = false) }
                    // Reload blacklist + config
                    repository.getBlacklist().onSuccess { bl ->
                        _uiState.update { it.copy(blacklistResponse = bl) }
                    }
                    repository.getBlacklistConfig().onSuccess { cfg ->
                        _uiState.update { it.copy(blacklistConfig = cfg) }
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isBlacklistFetching = false) }
                }
        }
    }

    fun updateBlacklistConfig(dto: IpRepBlacklistConfigUpdateDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.updateBlacklistConfig(dto)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Kara liste ayarlari kaydedildi", isActionLoading = false) }
                    repository.getBlacklistConfig().onSuccess { cfg ->
                        _uiState.update { it.copy(blacklistConfig = cfg) }
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    // ========== API Usage ==========

    fun checkApiUsage() {
        viewModelScope.launch {
            _uiState.update { it.copy(isCheckingApiUsage = true) }
            repository.getApiUsage()
                .onSuccess { resp ->
                    _uiState.update { it.copy(apiUsage = resp.data, isCheckingApiUsage = false) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "API kullanim hatasi: ${e.message}", isCheckingApiUsage = false) }
                }
        }
    }

    fun checkBlacklistApiUsage() {
        viewModelScope.launch {
            _uiState.update { it.copy(isCheckingBlacklistApiUsage = true) }
            repository.getBlacklistApiUsage()
                .onSuccess { resp ->
                    _uiState.update { it.copy(blacklistApiUsage = resp.data, isCheckingBlacklistApiUsage = false) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Blacklist API hatasi: ${e.message}", isCheckingBlacklistApiUsage = false) }
                }
        }
    }

    // ========== IP list sort ==========

    fun sortIpBy(field: IpSortField) {
        _uiState.update { state ->
            val newAscending = if (state.ipSortField == field) !state.ipSortAscending else false
            state.copy(
                ipSortField = field,
                ipSortAscending = newAscending,
                ips = sortIps(state.ips, field, newAscending),
            )
        }
    }

    private fun sortIps(
        list: List<IpRepCheckDto>,
        field: IpSortField,
        ascending: Boolean,
    ): List<IpRepCheckDto> {
        val comparator: Comparator<IpRepCheckDto> = when (field) {
            IpSortField.SCORE -> compareBy { it.abuseScore }
            IpSortField.IP -> compareBy { it.ip }
            IpSortField.COUNTRY -> compareBy { it.country }
            IpSortField.LAST_CHECKED -> compareBy { it.checkedAt }
        }
        return if (ascending) list.sortedWith(comparator) else list.sortedWith(comparator.reversed())
    }
}
