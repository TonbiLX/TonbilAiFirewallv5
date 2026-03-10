package com.tonbil.aifirewall.feature.securitysettings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.AlertSettingsConfigDto
import com.tonbil.aifirewall.data.remote.dto.DnsSecurityConfigDto
import com.tonbil.aifirewall.data.remote.dto.SecurityConfigDto
import com.tonbil.aifirewall.data.remote.dto.SecurityConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.SecurityStatsDto
import com.tonbil.aifirewall.data.remote.dto.ThreatAnalysisConfigDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SecuritySettingsUiState(
    val config: SecurityConfigDto = SecurityConfigDto(),
    val stats: SecurityStatsDto? = null,
    val defaults: SecurityConfigDto? = null,
    val isLoading: Boolean = true,
    val isSaving: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val selectedTab: Int = 0,
)

class SecuritySettingsViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SecuritySettingsUiState())
    val uiState: StateFlow<SecuritySettingsUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val configDeferred = async { securityRepository.getSecurityConfig() }
                    val statsDeferred = async { securityRepository.getSecurityStats() }
                    val defaultsDeferred = async { securityRepository.getSecurityDefaults() }

                    val config = configDeferred.await().getOrNull() ?: SecurityConfigDto()
                    val stats = statsDeferred.await().getOrNull()
                    val defaults = defaultsDeferred.await().getOrNull()?.config

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            config = config,
                            stats = stats,
                            defaults = defaults,
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = e.message ?: "Bilinmeyen hata",
                    )
                }
            }
        }
    }

    fun selectTab(index: Int) {
        _uiState.update { it.copy(selectedTab = index) }
    }

    fun updateThreatAnalysis(updated: ThreatAnalysisConfigDto) {
        val newConfig = _uiState.value.config.copy(threatAnalysis = updated)
        _uiState.update { it.copy(config = newConfig) }
        saveConfig(SecurityConfigUpdateDto(threatAnalysis = updated))
    }

    fun updateDnsSecurity(updated: DnsSecurityConfigDto) {
        val newConfig = _uiState.value.config.copy(dnsSecurity = updated)
        _uiState.update { it.copy(config = newConfig) }
        saveConfig(SecurityConfigUpdateDto(dnsSecurity = updated))
    }

    fun updateAlertSettings(updated: AlertSettingsConfigDto) {
        val newConfig = _uiState.value.config.copy(alertSettings = updated)
        _uiState.update { it.copy(config = newConfig) }
        saveConfig(SecurityConfigUpdateDto(alertSettings = updated))
    }

    fun updateConfig(dto: SecurityConfigUpdateDto) {
        saveConfig(dto)
    }

    private fun saveConfig(dto: SecurityConfigUpdateDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true) }
            securityRepository.updateSecurityConfig(dto)
                .onSuccess { updated ->
                    _uiState.update {
                        it.copy(
                            isSaving = false,
                            config = updated,
                            actionMessage = "Ayarlar kaydedildi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(
                            isSaving = false,
                            actionMessage = "Kayit hatasi: ${e.message}",
                        )
                    }
                }
        }
    }

    fun reloadConfig() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true) }
            securityRepository.reloadSecurity()
                .onSuccess {
                    _uiState.update { it.copy(isSaving = false, actionMessage = "Yapilandirma yeniden yuklendi") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(
                            isSaving = false,
                            actionMessage = "Yeniden yukleme hatasi: ${e.message}",
                        )
                    }
                }
        }
    }

    fun resetToDefaults() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true) }
            securityRepository.resetSecurity()
                .onSuccess {
                    _uiState.update { it.copy(isSaving = false, actionMessage = "Varsayilan ayarlara donuldu") }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(
                            isSaving = false,
                            actionMessage = "Sifirla hatasi: ${e.message}",
                        )
                    }
                }
        }
    }

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }
}
