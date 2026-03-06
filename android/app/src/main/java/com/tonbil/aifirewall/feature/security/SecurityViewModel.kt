package com.tonbil.aifirewall.feature.security

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.*
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
    val actionMessage: String? = null,
    // DNS
    val dnsStats: DnsStatsDto? = null,
    val blocklists: List<BlocklistDto> = emptyList(),
    val dnsRules: List<DnsRuleDto> = emptyList(),
    // Firewall
    val firewallStats: FirewallStatsDto? = null,
    val firewallRules: List<FirewallRuleDto> = emptyList(),
    // VPN
    val vpnStats: VpnStatsDto? = null,
    val vpnPeers: List<VpnPeerDto> = emptyList(),
    // DDoS
    val ddosProtections: List<DdosProtectionStatusDto> = emptyList(),
    val ddosCounters: DdosCountersDto? = null,
    // Traffic
    val liveFlows: List<LiveFlowDto> = emptyList(),
    val flowStats: FlowStatsDto? = null,
    // AI Insights
    val insights: List<AiInsightDto> = emptyList(),
    val securityStats: SecurityStatsDto? = null,
    // Dialog states
    val showAddDnsRuleDialog: Boolean = false,
    val showAddBlocklistDialog: Boolean = false,
    val showAddFirewallRuleDialog: Boolean = false,
    val showAddVpnPeerDialog: Boolean = false,
    val showVpnPeerConfigDialog: String? = null, // peer name
    val vpnPeerConfig: VpnPeerConfigDto? = null,
    val isActionLoading: Boolean = false,
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
                    val bl = async { securityRepository.getBlocklists() }
                    val rules = async { securityRepository.getDnsRules() }
                    val fw = async { securityRepository.getFirewallStats() }
                    val fwRules = async { securityRepository.getFirewallRules() }
                    val vpn = async { securityRepository.getVpnStats() }
                    val peers = async { securityRepository.getVpnPeers() }
                    val ddos = async { securityRepository.getDdosStatus() }
                    val ddosC = async { securityRepository.getDdosCounters() }
                    val flows = async { securityRepository.getLiveFlows() }
                    val fStats = async { securityRepository.getFlowStats() }
                    val ins = async { securityRepository.getInsights() }
                    val sec = async { securityRepository.getSecurityStats() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            dnsStats = dns.await().getOrNull(),
                            blocklists = bl.await().getOrElse { emptyList() },
                            dnsRules = rules.await().getOrElse { emptyList() },
                            firewallStats = fw.await().getOrNull(),
                            firewallRules = fwRules.await().getOrElse { emptyList() },
                            vpnStats = vpn.await().getOrNull(),
                            vpnPeers = peers.await().getOrElse { emptyList() },
                            ddosProtections = ddos.await().getOrElse { emptyList() },
                            ddosCounters = ddosC.await().getOrNull(),
                            liveFlows = flows.await().getOrElse { emptyList() },
                            flowStats = fStats.await().getOrNull(),
                            insights = ins.await().getOrElse { emptyList() },
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

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }

    // ========== DNS Actions ==========

    fun showAddDnsRuleDialog() = _uiState.update { it.copy(showAddDnsRuleDialog = true) }
    fun hideAddDnsRuleDialog() = _uiState.update { it.copy(showAddDnsRuleDialog = false) }

    fun createDnsRule(domain: String, action: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddDnsRuleDialog = false) }
            securityRepository.createDnsRule(DnsRuleCreateDto(domain, action))
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "DNS kurali eklendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun deleteDnsRule(id: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.deleteDnsRule(id)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "DNS kurali silindi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun showAddBlocklistDialog() = _uiState.update { it.copy(showAddBlocklistDialog = true) }
    fun hideAddBlocklistDialog() = _uiState.update { it.copy(showAddBlocklistDialog = false) }

    fun createBlocklist(name: String, url: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddBlocklistDialog = false) }
            securityRepository.createBlocklist(BlocklistCreateDto(name, url))
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Blocklist eklendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun toggleBlocklist(id: Int) {
        viewModelScope.launch {
            securityRepository.toggleBlocklist(id)
                .onSuccess { refresh() }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun deleteBlocklist(id: Int) {
        viewModelScope.launch {
            securityRepository.deleteBlocklist(id)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Blocklist silindi") }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    // ========== FIREWALL Actions ==========

    fun showAddFirewallRuleDialog() = _uiState.update { it.copy(showAddFirewallRuleDialog = true) }
    fun hideAddFirewallRuleDialog() = _uiState.update { it.copy(showAddFirewallRuleDialog = false) }

    fun createFirewallRule(dto: FirewallRuleCreateDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddFirewallRuleDialog = false) }
            securityRepository.createFirewallRule(dto)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Firewall kurali eklendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun toggleFirewallRule(id: Int) {
        viewModelScope.launch {
            securityRepository.toggleFirewallRule(id)
                .onSuccess { refresh() }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun deleteFirewallRule(id: Int) {
        viewModelScope.launch {
            securityRepository.deleteFirewallRule(id)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Firewall kurali silindi") }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    // ========== VPN Actions ==========

    fun showAddVpnPeerDialog() = _uiState.update { it.copy(showAddVpnPeerDialog = true) }
    fun hideAddVpnPeerDialog() = _uiState.update { it.copy(showAddVpnPeerDialog = false) }

    fun startVpn() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.startVpn()
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "VPN baslatildi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun stopVpn() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.stopVpn()
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "VPN durduruldu", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun addVpnPeer(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddVpnPeerDialog = false) }
            securityRepository.addVpnPeer(VpnPeerCreateDto(name))
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "VPN peer eklendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun deleteVpnPeer(name: String) {
        viewModelScope.launch {
            securityRepository.deleteVpnPeer(name)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "VPN peer silindi") }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun showVpnPeerConfig(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(showVpnPeerConfigDialog = name) }
            securityRepository.getVpnPeerConfig(name)
                .onSuccess { config ->
                    _uiState.update { it.copy(vpnPeerConfig = config) }
                }
                .onFailure {
                    _uiState.update { it.copy(showVpnPeerConfigDialog = null, actionMessage = "Config alinamadi") }
                }
        }
    }

    fun hideVpnPeerConfig() = _uiState.update { it.copy(showVpnPeerConfigDialog = null, vpnPeerConfig = null) }
}
