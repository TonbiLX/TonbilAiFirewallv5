package com.tonbil.aifirewall.feature.dnsfiltering

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.DnsStatsDto
import com.tonbil.aifirewall.data.remote.dto.SecurityConfigDto
import com.tonbil.aifirewall.data.remote.dto.SecurityConfigUpdateDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DnsFilteringUiState(
    val stats: DnsStatsDto? = null,
    val securityConfig: SecurityConfigDto? = null,
    val isLoading: Boolean = true,
    val isTogglingFilter: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val selectedTab: Int = 0,
)

class DnsFilteringViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DnsFilteringUiState())
    val uiState: StateFlow<DnsFilteringUiState> = _uiState.asStateFlow()

    // Computed: tum DNS guvenlik katmanlari acik mi?
    val isGlobalFilterActive: Boolean
        get() {
            val config = _uiState.value.securityConfig ?: return false
            return config.dnssecEnabled
                && config.dnsTunnelingEnabled
                && config.dohEnabled
                && config.threatAnalysis.dgaDetectionEnabled
        }

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val statsDeferred = async { securityRepository.getDnsStats() }
                    val configDeferred = async { securityRepository.getSecurityConfig() }

                    val statsResult = statsDeferred.await()
                    val configResult = configDeferred.await()

                    _uiState.update { state ->
                        state.copy(
                            isLoading = false,
                            stats = statsResult.getOrNull() ?: state.stats,
                            securityConfig = configResult.getOrNull() ?: state.securityConfig,
                            error = statsResult.exceptionOrNull()?.message
                                ?: configResult.exceptionOrNull()?.message,
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = e.message ?: "Yukleme hatasi") }
            }
        }
    }

    fun selectTab(index: Int) = _uiState.update { it.copy(selectedTab = index) }

    // DNS-02: Toplu toggle — tum DNS guvenlik katmanlarini tek seferde ac/kapa
    fun toggleGlobalFilter(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val update = SecurityConfigUpdateDto(
                dnssecEnabled = enabled,
                dnsTunnelingEnabled = enabled,
                dohEnabled = enabled,
                dgaDetectionEnabled = enabled,
            )
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = "DNS filtreleme ${if (enabled) "aktif" else "pasif"}",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    // Bireysel DNSSEC toggle
    fun toggleDnssec(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val update = SecurityConfigUpdateDto(dnssecEnabled = enabled)
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = "DNSSEC ${if (enabled) "aktif" else "pasif"}",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    // Bireysel DNS Tunneling toggle
    fun toggleDnsTunneling(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val update = SecurityConfigUpdateDto(dnsTunnelingEnabled = enabled)
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = "DNS Tunneling ${if (enabled) "aktif" else "pasif"}",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    // Bireysel DoH toggle
    fun toggleDoh(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val update = SecurityConfigUpdateDto(dohEnabled = enabled)
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = "DoH ${if (enabled) "aktif" else "pasif"}",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    // Bireysel DGA toggle
    fun toggleDga(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val update = SecurityConfigUpdateDto(dgaDetectionEnabled = enabled)
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = "DGA Tespiti ${if (enabled) "aktif" else "pasif"}",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    // Sinkhole toggle (DnsSecurityConfigDto icinden)
    fun toggleSinkhole(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val currentDns = _uiState.value.securityConfig?.dnsSecurity
            val updatedDns = currentDns?.copy(sinkholeEnabled = enabled)
                ?: com.tonbil.aifirewall.data.remote.dto.DnsSecurityConfigDto(sinkholeEnabled = enabled)
            val update = SecurityConfigUpdateDto(dnsSecurity = updatedDns)
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = "Sinkhole ${if (enabled) "aktif" else "pasif"}",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    // Rate limit toggle
    fun toggleRateLimit(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val currentDns = _uiState.value.securityConfig?.dnsSecurity
            val updatedDns = currentDns?.copy(rateLimitEnabled = enabled)
                ?: com.tonbil.aifirewall.data.remote.dto.DnsSecurityConfigDto(rateLimitEnabled = enabled)
            val update = SecurityConfigUpdateDto(dnsSecurity = updatedDns)
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = if (enabled) "Rate limit aktif" else "Rate limit devre disi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    // Rate limit guncelle
    fun updateRateLimit(perSec: Int) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val currentDns = _uiState.value.securityConfig?.dnsSecurity
            val updatedDns = currentDns?.copy(rateLimitPerSecond = perSec)
                ?: com.tonbil.aifirewall.data.remote.dto.DnsSecurityConfigDto(rateLimitPerSecond = perSec)
            val update = SecurityConfigUpdateDto(dnsSecurity = updatedDns)
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = "Rate limit guncellendi: $perSec/s",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    // DNSSEC modunu guncelle (enforce/log_only/disabled)
    fun updateDnssecMode(mode: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isTogglingFilter = true) }
            val update = SecurityConfigUpdateDto(dnssecMode = mode)
            securityRepository.updateSecurityConfig(update)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isTogglingFilter = false,
                            securityConfig = updated,
                            actionMessage = "DNSSEC modu: $mode",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isTogglingFilter = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    fun clearActionMessage() = _uiState.update { it.copy(actionMessage = null) }
}
