package com.tonbil.aifirewall.feature.vpnserver

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.VpnPeerConfigDto
import com.tonbil.aifirewall.data.remote.dto.VpnPeerCreateDto
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

data class VpnServerUiState(
    val stats: VpnStatsDto? = null,
    val peers: List<VpnPeerDto> = emptyList(),
    val isLoading: Boolean = true,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val showAddPeerDialog: Boolean = false,
    val showConfigDialog: Boolean = false,
    val peerConfig: VpnPeerConfigDto? = null,
    val configPeerName: String = "",
)

class VpnServerViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(VpnServerUiState())
    val uiState: StateFlow<VpnServerUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val statsDeferred = async { securityRepository.getVpnStats() }
                    val peersDeferred = async { securityRepository.getVpnPeers() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            stats = statsDeferred.await().getOrNull(),
                            peers = peersDeferred.await().getOrElse { emptyList() },
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

    fun startVpn() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.startVpn()
                .onSuccess {
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "VPN sunucusu baslatildi") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun stopVpn() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.stopVpn()
                .onSuccess {
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "VPN sunucusu durduruldu") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun addPeer(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddPeerDialog = false) }
            securityRepository.addVpnPeer(VpnPeerCreateDto(name = name))
                .onSuccess {
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "$name eklendi") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun deletePeer(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.deleteVpnPeer(name)
                .onSuccess {
                    _uiState.update { state ->
                        state.copy(
                            isActionLoading = false,
                            peers = state.peers.filter { it.name != name },
                            actionMessage = "$name silindi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun showPeerConfig(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.getVpnPeerConfig(name)
                .onSuccess { config ->
                    _uiState.update {
                        it.copy(
                            isActionLoading = false,
                            showConfigDialog = true,
                            peerConfig = config,
                            configPeerName = name,
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun hideConfigDialog() = _uiState.update { it.copy(showConfigDialog = false, peerConfig = null) }
    fun showAddPeerDialog() = _uiState.update { it.copy(showAddPeerDialog = true) }
    fun hideAddPeerDialog() = _uiState.update { it.copy(showAddPeerDialog = false) }
    fun clearActionMessage() = _uiState.update { it.copy(actionMessage = null) }
}
