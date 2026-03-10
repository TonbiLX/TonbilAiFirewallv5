package com.tonbil.aifirewall.feature.vpnclient

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.VpnClientCreateDto
import com.tonbil.aifirewall.data.remote.dto.VpnClientImportDto
import com.tonbil.aifirewall.data.remote.dto.VpnClientServerDto
import com.tonbil.aifirewall.data.remote.dto.VpnClientStatsDto
import com.tonbil.aifirewall.data.remote.dto.VpnClientStatusDto
import com.tonbil.aifirewall.data.repository.VpnClientRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class VpnClientUiState(
    val servers: List<VpnClientServerDto> = emptyList(),
    val status: VpnClientStatusDto? = null,
    val stats: VpnClientStatsDto? = null,
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val showCreateDialog: Boolean = false,
    val showImportDialog: Boolean = false,
)

class VpnClientViewModel(private val repo: VpnClientRepository) : ViewModel() {

    private val _state = MutableStateFlow(VpnClientUiState())
    val state: StateFlow<VpnClientUiState> = _state.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val serversDeferred = async { repo.getServers() }
                    val statusDeferred = async { repo.getStatus() }
                    val statsDeferred = async { repo.getStats() }

                    _state.update {
                        it.copy(
                            servers = serversDeferred.await().getOrElse { emptyList() },
                            status = statusDeferred.await().getOrNull(),
                            stats = statsDeferred.await().getOrNull(),
                            isLoading = false,
                            isRefreshing = false,
                            error = serversDeferred.await().exceptionOrNull()?.message,
                        )
                    }
                }
            } catch (e: Exception) {
                _state.update {
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
        _state.update { it.copy(isRefreshing = true) }
        loadAll()
    }

    fun clearActionMessage() {
        _state.update { it.copy(actionMessage = null) }
    }

    fun createServer(dto: VpnClientCreateDto) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true, showCreateDialog = false) }
            repo.createServer(dto)
                .onSuccess {
                    _state.update { it.copy(actionMessage = "Sunucu eklendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _state.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun importServer(dto: VpnClientImportDto) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true, showImportDialog = false) }
            repo.importServer(dto)
                .onSuccess {
                    _state.update { it.copy(actionMessage = "Konfigurasyon iceri aktarildi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _state.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun deleteServer(id: Int) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true) }
            repo.deleteServer(id)
                .onSuccess {
                    _state.update { it.copy(actionMessage = "Sunucu silindi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _state.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun activate(id: Int) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true) }
            repo.activate(id)
                .onSuccess {
                    _state.update { it.copy(actionMessage = "VPN baglantisi kuruldu", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _state.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun deactivate(id: Int) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true) }
            repo.deactivate(id)
                .onSuccess {
                    _state.update { it.copy(actionMessage = "VPN baglantisi kesildi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _state.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun toggleCreateDialog(show: Boolean) {
        _state.update { it.copy(showCreateDialog = show) }
    }

    fun toggleImportDialog(show: Boolean) {
        _state.update { it.copy(showImportDialog = show) }
    }
}
