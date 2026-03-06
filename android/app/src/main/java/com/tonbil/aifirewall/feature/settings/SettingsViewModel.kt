package com.tonbil.aifirewall.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.ServerDiscovery
import com.tonbil.aifirewall.data.remote.dto.DhcpLeaseDto
import com.tonbil.aifirewall.data.remote.dto.DhcpStatsDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val selectedTab: Int = 0,
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    // DHCP
    val dhcpStats: DhcpStatsDto? = null,
    val dhcpLeases: List<DhcpLeaseDto> = emptyList(),
    // Server info
    val serverUrl: String = "",
)

class SettingsViewModel(
    private val securityRepository: SecurityRepository,
    private val serverDiscovery: ServerDiscovery,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        _uiState.update { it.copy(serverUrl = serverDiscovery.activeUrl) }
        loadAll()
    }

    private fun loadAll() {
        viewModelScope.launch {
            try {
                coroutineScope {
                    val dhcp = async { securityRepository.getDhcpStats() }
                    val leases = async { securityRepository.getDhcpLeases() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            dhcpStats = dhcp.await().getOrNull(),
                            dhcpLeases = leases.await().getOrElse { emptyList() },
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

    fun selectTab(index: Int) {
        _uiState.update { it.copy(selectedTab = index) }
    }

    fun refresh() {
        _uiState.update { it.copy(isRefreshing = true) }
        loadAll()
    }
}
