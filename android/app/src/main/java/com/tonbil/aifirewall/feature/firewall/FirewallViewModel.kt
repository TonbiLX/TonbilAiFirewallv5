package com.tonbil.aifirewall.feature.firewall

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.ConnectionCountDto
import com.tonbil.aifirewall.data.remote.dto.FirewallRuleCreateDto
import com.tonbil.aifirewall.data.remote.dto.FirewallRuleDto
import com.tonbil.aifirewall.data.remote.dto.FirewallStatsDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class FirewallUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val stats: FirewallStatsDto? = null,
    val connectionCount: ConnectionCountDto? = null,
    val rules: List<FirewallRuleDto> = emptyList(),
    val showAddDialog: Boolean = false,
)

class FirewallViewModel(
    private val repository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(FirewallUiState())
    val uiState: StateFlow<FirewallUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = it.stats == null) }
            try {
                coroutineScope {
                    val statsDeferred = async { repository.getFirewallStats() }
                    val rulesDeferred = async { repository.getFirewallRules() }
                    val connDeferred = async { repository.getConnectionCount() }

                    _uiState.update { state ->
                        state.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            stats = statsDeferred.await().getOrNull(),
                            rules = rulesDeferred.await().getOrElse { emptyList() },
                            connectionCount = connDeferred.await().getOrNull(),
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

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }

    fun showAddDialog() {
        _uiState.update { it.copy(showAddDialog = true) }
    }

    fun hideAddDialog() {
        _uiState.update { it.copy(showAddDialog = false) }
    }

    fun createRule(dto: FirewallRuleCreateDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.createFirewallRule(dto)
                .onSuccess {
                    _uiState.update {
                        it.copy(
                            isActionLoading = false,
                            showAddDialog = false,
                            actionMessage = "Kural olusturuldu",
                        )
                    }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    fun toggleRule(id: Int) {
        viewModelScope.launch {
            repository.toggleFirewallRule(id)
                .onSuccess { updated ->
                    _uiState.update { state ->
                        state.copy(
                            rules = state.rules.map { if (it.id == id) updated else it },
                            actionMessage = if (updated.enabled) "Kural etkinlestirildi" else "Kural devre disi birakildi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun deleteRule(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.deleteFirewallRule(id)
                .onSuccess {
                    _uiState.update { state ->
                        state.copy(
                            isActionLoading = false,
                            rules = state.rules.filter { it.id != id },
                            actionMessage = "Kural silindi",
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
}
