package com.tonbil.aifirewall.feature.systemtime

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.NtpServerDto
import com.tonbil.aifirewall.data.remote.dto.SetNtpServerDto
import com.tonbil.aifirewall.data.remote.dto.SetTimezoneDto
import com.tonbil.aifirewall.data.remote.dto.TimeStatusDto
import com.tonbil.aifirewall.data.remote.dto.TimezoneGroupDto
import com.tonbil.aifirewall.data.repository.SystemRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SystemTimeUiState(
    val status: TimeStatusDto = TimeStatusDto(),
    val timezones: List<TimezoneGroupDto> = emptyList(),
    val ntpServers: List<NtpServerDto> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
    val actionMessage: String? = null,
    val isActionLoading: Boolean = false,
    val showTimezoneDialog: Boolean = false,
)

class SystemTimeViewModel(
    private val systemRepository: SystemRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SystemTimeUiState())
    val uiState: StateFlow<SystemTimeUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = it.timezones.isEmpty(), error = null) }
            try {
                coroutineScope {
                    val status = async { systemRepository.getTimeStatus() }
                    val timezones = async { systemRepository.getTimezones() }
                    val ntpServers = async { systemRepository.getNtpServers() }
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            status = status.await().getOrElse { it.status },
                            timezones = timezones.await().getOrElse { it.timezones },
                            ntpServers = ntpServers.await().getOrElse { it.ntpServers },
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = e.message ?: "Bilinmeyen hata") }
            }
        }
    }

    fun setTimezone(tz: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showTimezoneDialog = false) }
            systemRepository.setTimezone(SetTimezoneDto(timezone = tz))
                .onSuccess { _uiState.update { it.copy(actionMessage = "Saat dilimi guncellendi: $tz", isActionLoading = false) }; loadAll() }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun setNtpServer(server: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            systemRepository.setNtpServer(SetNtpServerDto(server = server))
                .onSuccess { _uiState.update { it.copy(actionMessage = "NTP sunucusu guncellendi", isActionLoading = false) }; loadAll() }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun syncNow() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            systemRepository.syncTime()
                .onSuccess { _uiState.update { it.copy(actionMessage = "Saat senkronize edildi", isActionLoading = false) }; loadAll() }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun showTimezoneDialog() = _uiState.update { it.copy(showTimezoneDialog = true) }
    fun hideTimezoneDialog() = _uiState.update { it.copy(showTimezoneDialog = false) }
    fun clearActionMessage() = _uiState.update { it.copy(actionMessage = null) }
}
