package com.tonbil.aifirewall.feature.dhcp

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.DhcpLeaseDto
import com.tonbil.aifirewall.data.remote.dto.DhcpPoolDto
import com.tonbil.aifirewall.data.remote.dto.DhcpStatsDto
import com.tonbil.aifirewall.data.remote.dto.DhcpStaticLeaseCreateDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DhcpUiState(
    val stats: DhcpStatsDto? = null,
    val pools: List<DhcpPoolDto> = emptyList(),
    val leases: List<DhcpLeaseDto> = emptyList(),
    val isLoading: Boolean = true,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val showAddLeaseDialog: Boolean = false,
)

class DhcpViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DhcpUiState())
    val uiState: StateFlow<DhcpUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val statsDeferred = async { securityRepository.getDhcpStats() }
                    val poolsDeferred = async { securityRepository.getDhcpPools() }
                    val leasesDeferred = async { securityRepository.getDhcpLeases() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            stats = statsDeferred.await().getOrNull(),
                            pools = poolsDeferred.await().getOrElse { emptyList() },
                            leases = leasesDeferred.await().getOrElse { emptyList() },
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

    fun togglePool(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.toggleDhcpPool(id)
                .onSuccess { updated ->
                    _uiState.update { state ->
                        state.copy(
                            isActionLoading = false,
                            pools = state.pools.map { if (it.id == id) updated else it },
                            actionMessage = if (updated.enabled) "${updated.name} etkinlestirildi" else "${updated.name} devre disi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun deleteLease(mac: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.deleteStaticLease(mac)
                .onSuccess {
                    _uiState.update { state ->
                        state.copy(
                            isActionLoading = false,
                            leases = state.leases.filter { it.macAddress != mac },
                            actionMessage = "Kira silindi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun addStaticLease(mac: String, ip: String, hostname: String?) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddLeaseDialog = false) }
            securityRepository.createStaticLease(
                DhcpStaticLeaseCreateDto(
                    macAddress = mac,
                    ipAddress = ip,
                    hostname = hostname,
                )
            )
                .onSuccess {
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Statik kira eklendi") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun showAddLeaseDialog() = _uiState.update { it.copy(showAddLeaseDialog = true) }
    fun hideAddLeaseDialog() = _uiState.update { it.copy(showAddLeaseDialog = false) }
    fun clearActionMessage() = _uiState.update { it.copy(actionMessage = null) }
}
