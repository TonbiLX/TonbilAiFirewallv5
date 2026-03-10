package com.tonbil.aifirewall.feature.systemmonitor

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.FanConfigDto
import com.tonbil.aifirewall.data.remote.dto.FanConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.SystemInfoDto
import com.tonbil.aifirewall.data.remote.dto.SystemMetricsResponseDto
import com.tonbil.aifirewall.data.repository.SystemRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SystemMonitorUiState(
    val info: SystemInfoDto = SystemInfoDto(),
    val metrics: SystemMetricsResponseDto = SystemMetricsResponseDto(),
    val fan: FanConfigDto = FanConfigDto(),
    val isLoading: Boolean = true,
    val error: String? = null,
    val actionMessage: String? = null,
)

class SystemMonitorViewModel(
    private val systemRepository: SystemRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SystemMonitorUiState())
    val uiState: StateFlow<SystemMonitorUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = it.info.hostname.isEmpty(), error = null) }
            try {
                coroutineScope {
                    val info = async { systemRepository.getSystemInfo() }
                    val metrics = async { systemRepository.getSystemMetrics() }
                    val fan = async { systemRepository.getFanConfig() }
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            info = info.await().getOrElse { it.info },
                            metrics = metrics.await().getOrElse { it.metrics },
                            fan = fan.await().getOrElse { it.fan },
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

    fun updateFan(dto: FanConfigUpdateDto) {
        viewModelScope.launch {
            systemRepository.updateFanConfig(dto)
                .onSuccess { updated ->
                    _uiState.update { it.copy(fan = updated, actionMessage = "Fan ayarlari guncellendi") }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }
}
