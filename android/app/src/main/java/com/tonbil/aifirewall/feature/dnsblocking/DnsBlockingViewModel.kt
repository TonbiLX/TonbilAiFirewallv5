package com.tonbil.aifirewall.feature.dnsblocking

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.BlocklistCreateDto
import com.tonbil.aifirewall.data.remote.dto.BlocklistDto
import com.tonbil.aifirewall.data.remote.dto.DnsRuleCreateDto
import com.tonbil.aifirewall.data.remote.dto.DnsRuleDto
import com.tonbil.aifirewall.data.remote.dto.DnsStatsDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DnsBlockingUiState(
    val stats: DnsStatsDto? = null,
    val blocklists: List<BlocklistDto> = emptyList(),
    val rules: List<DnsRuleDto> = emptyList(),
    val isLoading: Boolean = true,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val showAddBlocklistDialog: Boolean = false,
    val showAddRuleDialog: Boolean = false,
)

class DnsBlockingViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DnsBlockingUiState())
    val uiState: StateFlow<DnsBlockingUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val statsDeferred = async { securityRepository.getDnsStats() }
                    val blocklistsDeferred = async { securityRepository.getBlocklists() }
                    val rulesDeferred = async { securityRepository.getDnsRules() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            stats = statsDeferred.await().getOrNull(),
                            blocklists = blocklistsDeferred.await().getOrElse { emptyList() },
                            rules = rulesDeferred.await().getOrElse { emptyList() },
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(isLoading = false, error = e.message ?: "Bilinmeyen hata")
                }
            }
        }
    }

    fun toggleBlocklist(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.toggleBlocklist(id)
                .onSuccess { updated ->
                    _uiState.update { state ->
                        state.copy(
                            isActionLoading = false,
                            blocklists = state.blocklists.map { if (it.id == id) updated else it },
                            actionMessage = if (updated.enabled) "${updated.name} etkinlestirildi" else "${updated.name} devre disi birakildi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun deleteBlocklist(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.deleteBlocklist(id)
                .onSuccess {
                    _uiState.update { state ->
                        state.copy(
                            isActionLoading = false,
                            blocklists = state.blocklists.filter { it.id != id },
                            actionMessage = "Engelleme listesi silindi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun addBlocklist(name: String, url: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddBlocklistDialog = false) }
            securityRepository.createBlocklist(BlocklistCreateDto(name = name, url = url))
                .onSuccess {
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Liste eklendi") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun addRule(domain: String, action: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddRuleDialog = false) }
            securityRepository.createDnsRule(DnsRuleCreateDto(domain = domain, action = action))
                .onSuccess { newRule ->
                    _uiState.update { state ->
                        state.copy(
                            isActionLoading = false,
                            rules = state.rules + newRule,
                            actionMessage = "$domain kurali eklendi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun deleteRule(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.deleteDnsRule(id)
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
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun refreshAllBlocklists() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.refreshAllBlocklists()
                .onSuccess {
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Tum listeler guncelleniyor...") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun showAddBlocklistDialog() = _uiState.update { it.copy(showAddBlocklistDialog = true) }
    fun hideAddBlocklistDialog() = _uiState.update { it.copy(showAddBlocklistDialog = false) }
    fun showAddRuleDialog() = _uiState.update { it.copy(showAddRuleDialog = true) }
    fun hideAddRuleDialog() = _uiState.update { it.copy(showAddRuleDialog = false) }
    fun clearActionMessage() = _uiState.update { it.copy(actionMessage = null) }
}
