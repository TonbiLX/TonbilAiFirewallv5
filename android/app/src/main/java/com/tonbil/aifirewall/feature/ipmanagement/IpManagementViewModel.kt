package com.tonbil.aifirewall.feature.ipmanagement

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.BlockedIpCreateDto
import com.tonbil.aifirewall.data.remote.dto.BlockedIpDto
import com.tonbil.aifirewall.data.remote.dto.IpBulkUnblockDto
import com.tonbil.aifirewall.data.remote.dto.IpMgmtStatsDto
import com.tonbil.aifirewall.data.remote.dto.IpUnblockDto
import com.tonbil.aifirewall.data.remote.dto.TrustedIpCreateDto
import com.tonbil.aifirewall.data.remote.dto.TrustedIpDto
import com.tonbil.aifirewall.data.repository.IpManagementRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class IpManagementUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val selectedTab: Int = 0,
    // Data
    val stats: IpMgmtStatsDto? = null,
    val trustedIps: List<TrustedIpDto> = emptyList(),
    val blockedIps: List<BlockedIpDto> = emptyList(),
    // Selection (bulk unblock)
    val selectedBlockedIps: Set<String> = emptySet(),
    // Dialogs
    val showAddTrustedDialog: Boolean = false,
    val showBlockIpDialog: Boolean = false,
)

class IpManagementViewModel(
    private val repository: IpManagementRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(IpManagementUiState())
    val uiState: StateFlow<IpManagementUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = it.trustedIps.isEmpty() && it.blockedIps.isEmpty()) }
            try {
                coroutineScope {
                    val statsDeferred = async { repository.getStats() }
                    val trustedDeferred = async { repository.getTrustedIps() }
                    val blockedDeferred = async { repository.getBlockedIps() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            stats = statsDeferred.await().getOrNull(),
                            trustedIps = trustedDeferred.await().getOrElse { emptyList() },
                            blockedIps = blockedDeferred.await().getOrElse { emptyList() },
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
        _uiState.update { it.copy(selectedTab = index, selectedBlockedIps = emptySet()) }
    }

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }

    // ========== Dialog controls ==========

    fun showAddTrustedDialog() = _uiState.update { it.copy(showAddTrustedDialog = true) }
    fun hideAddTrustedDialog() = _uiState.update { it.copy(showAddTrustedDialog = false) }

    fun showBlockIpDialog() = _uiState.update { it.copy(showBlockIpDialog = true) }
    fun hideBlockIpDialog() = _uiState.update { it.copy(showBlockIpDialog = false) }

    // ========== Trusted IP actions ==========

    fun addTrusted(dto: TrustedIpCreateDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddTrustedDialog = false) }
            repository.addTrustedIp(dto)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Guvenilir IP eklendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun deleteTrusted(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.deleteTrustedIp(id)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Guvenilir IP silindi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    // ========== Blocked IP actions ==========

    fun blockIp(dto: BlockedIpCreateDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showBlockIpDialog = false) }
            repository.blockIp(dto)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "IP engellendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun unblockIp(ipAddress: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.unblockIp(IpUnblockDto(ipAddress))
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "IP engeli kaldirildi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun bulkUnblock(ips: List<String>) {
        if (ips.isEmpty()) return
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.bulkUnblock(IpBulkUnblockDto(ips))
                .onSuccess {
                    _uiState.update {
                        it.copy(
                            actionMessage = "${ips.size} IP engelinden kaldirildi",
                            isActionLoading = false,
                            selectedBlockedIps = emptySet(),
                        )
                    }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    // ========== Selection (bulk) ==========

    fun toggleBlockedSelection(ipAddress: String) {
        _uiState.update { state ->
            val current = state.selectedBlockedIps.toMutableSet()
            if (ipAddress in current) current.remove(ipAddress) else current.add(ipAddress)
            state.copy(selectedBlockedIps = current)
        }
    }

    fun clearSelection() {
        _uiState.update { it.copy(selectedBlockedIps = emptySet()) }
    }

    fun selectAllBlocked() {
        _uiState.update { state ->
            state.copy(selectedBlockedIps = state.blockedIps.map { it.ipAddress }.toSet())
        }
    }
}
