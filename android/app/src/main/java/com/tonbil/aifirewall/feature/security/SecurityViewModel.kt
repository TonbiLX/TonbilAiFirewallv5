package com.tonbil.aifirewall.feature.security

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.DdosCountersDto
import com.tonbil.aifirewall.data.remote.dto.DdosProtectionStatusDto
import com.tonbil.aifirewall.data.remote.dto.DnsStatsDto
import com.tonbil.aifirewall.data.remote.dto.FirewallStatsDto
import com.tonbil.aifirewall.data.remote.dto.SecurityStatsDto
import com.tonbil.aifirewall.data.remote.dto.VpnPeerDto
import com.tonbil.aifirewall.data.remote.dto.VpnStatsDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SecurityUiState(
    val selectedTab: Int = 0,
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    // DNS
    val dnsStats: DnsStatsDto? = null,
    // Firewall
    val firewallStats: FirewallStatsDto? = null,
    // VPN
    val vpnStats: VpnStatsDto? = null,
    val vpnPeers: List<VpnPeerDto> = emptyList(),
    // DDoS
    val ddosProtections: List<DdosProtectionStatusDto> = emptyList(),
    val ddosCounters: DdosCountersDto? = null,
    // Security
    val securityStats: SecurityStatsDto? = null,
)

class SecurityViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SecurityUiState())
    val uiState: StateFlow<SecurityUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    private fun loadAll() {
        viewModelScope.launch {
            try {
                coroutineScope {
                    val dns = async { securityRepository.getDnsStats() }
                    val fw = async { securityRepository.getFirewallStats() }
                    val vpn = async { securityRepository.getVpnStats() }
                    val peers = async { securityRepository.getVpnPeers() }
                    val ddos = async { securityRepository.getDdosStatus() }
                    val ddosC = async { securityRepository.getDdosCounters() }
                    val sec = async { securityRepository.getSecurityStats() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            dnsStats = dns.await().getOrNull(),
                            firewallStats = fw.await().getOrNull(),
                            vpnStats = vpn.await().getOrNull(),
                            vpnPeers = peers.await().getOrElse { emptyList() },
                            ddosProtections = ddos.await().getOrElse { emptyList() },
                            ddosCounters = ddosC.await().getOrNull(),
                            securityStats = sec.await().getOrNull(),
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
