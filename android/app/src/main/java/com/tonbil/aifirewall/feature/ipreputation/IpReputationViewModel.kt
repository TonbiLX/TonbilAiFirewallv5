package com.tonbil.aifirewall.feature.ipreputation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistConfigDto
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistDto
import com.tonbil.aifirewall.data.remote.dto.IpRepCheckDto
import com.tonbil.aifirewall.data.remote.dto.IpRepConfigDto
import com.tonbil.aifirewall.data.remote.dto.IpRepConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.IpRepSummaryDto
import com.tonbil.aifirewall.data.remote.dto.IpRepTestDto
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
    val blacklist: List<IpRepBlacklistDto> = emptyList(),
    val blacklistConfig: IpRepBlacklistConfigDto? = null,
    // IP list sort/filter
    val ipSortField: IpSortField = IpSortField.SCORE,
    val ipSortAscending: Boolean = false,
    val ipMinScoreFilter: Int? = null,
    // Test result
    val lastTestResult: IpRepTestDto? = null,
    val isBlacklistFetching: Boolean = false,
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
                            blacklist = blacklistDeferred.await().getOrElse { emptyList() },
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
                .onSuccess { updated ->
                    _uiState.update { it.copy(config = updated, actionMessage = "Ayarlar kaydedildi", isActionLoading = false) }
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
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Onbellek temizlendi", isActionLoading = false) }
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
                    _uiState.update {
                        it.copy(
                            lastTestResult = result,
                            actionMessage = if (result.success) "API testi basarili" else "API testi basarisiz: ${result.message}",
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
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Kara liste guncellendi", isBlacklistFetching = false) }
                    // Reload blacklist entries
                    repository.getBlacklist()
                        .onSuccess { entries ->
                            _uiState.update { it.copy(blacklist = entries) }
                        }
                    repository.getBlacklistConfig()
                        .onSuccess { cfg ->
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
                .onSuccess { updated ->
                    _uiState.update { it.copy(blacklistConfig = updated, actionMessage = "Kara liste ayarlari kaydedildi", isActionLoading = false) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    // ========== IP list sort/filter ==========

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

    fun setMinScoreFilter(minScore: Int?) {
        viewModelScope.launch {
            _uiState.update { it.copy(ipMinScoreFilter = minScore) }
            repository.getIps(minScore)
                .onSuccess { list ->
                    _uiState.update { state ->
                        state.copy(ips = sortIps(list, state.ipSortField, state.ipSortAscending))
                    }
                }
        }
    }

    private fun sortIps(
        list: List<IpRepCheckDto>,
        field: IpSortField,
        ascending: Boolean,
    ): List<IpRepCheckDto> {
        val comparator: Comparator<IpRepCheckDto> = when (field) {
            IpSortField.SCORE -> compareBy { it.score }
            IpSortField.IP -> compareBy { it.ipAddress }
            IpSortField.COUNTRY -> compareBy { it.countryName ?: "" }
            IpSortField.LAST_CHECKED -> compareBy { it.checkedAt ?: "" }
        }
        return if (ascending) list.sortedWith(comparator) else list.sortedWith(comparator.reversed())
    }
}
