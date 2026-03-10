package com.tonbil.aifirewall.feature.systemmanagement

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.BootInfoDto
import com.tonbil.aifirewall.data.remote.dto.JournalDto
import com.tonbil.aifirewall.data.remote.dto.ServiceStatusDto
import com.tonbil.aifirewall.data.remote.dto.SystemOverviewFullDto
import com.tonbil.aifirewall.data.remote.dto.SystemRebootDto
import com.tonbil.aifirewall.data.repository.SystemRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SystemManagementUiState(
    val overview: SystemOverviewFullDto = SystemOverviewFullDto(),
    val services: List<ServiceStatusDto> = emptyList(),
    val bootInfo: BootInfoDto = BootInfoDto(),
    val journal: JournalDto = JournalDto(),
    val isLoading: Boolean = true,
    val error: String? = null,
    val actionMessage: String? = null,
    val isActionLoading: Boolean = false,
    val showJournal: Boolean = false,
    val showRebootConfirm: Boolean = false,
    val showShutdownConfirm: Boolean = false,
)

class SystemManagementViewModel(
    private val systemRepository: SystemRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SystemManagementUiState())
    val uiState: StateFlow<SystemManagementUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = it.services.isEmpty(), error = null) }
            try {
                coroutineScope {
                    val overview = async { systemRepository.getOverview() }
                    val services = async { systemRepository.getServices() }
                    val bootInfo = async { systemRepository.getBootInfo() }
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            overview = overview.await().getOrElse { it.overview },
                            services = services.await().getOrElse { it.services },
                            bootInfo = bootInfo.await().getOrElse { it.bootInfo },
                        )
                    }
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = e.message ?: "Bilinmeyen hata") }
            }
        }
    }

    fun restartService(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            systemRepository.restartService(name)
                .onSuccess { _uiState.update { it.copy(actionMessage = "$name yeniden baslatildi", isActionLoading = false) }; loadAll() }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun startService(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            systemRepository.startService(name)
                .onSuccess { _uiState.update { it.copy(actionMessage = "$name baslatildi", isActionLoading = false) }; loadAll() }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun stopService(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            systemRepository.stopService(name)
                .onSuccess { _uiState.update { it.copy(actionMessage = "$name durduruldu", isActionLoading = false) }; loadAll() }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun reboot() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showRebootConfirm = false) }
            systemRepository.reboot(SystemRebootDto(confirm = true))
                .onSuccess { _uiState.update { it.copy(actionMessage = "Yeniden baslama komutu gonderildi", isActionLoading = false) } }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun shutdown() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showShutdownConfirm = false) }
            systemRepository.shutdown(SystemRebootDto(confirm = true))
                .onSuccess { _uiState.update { it.copy(actionMessage = "Kapanma komutu gonderildi", isActionLoading = false) } }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun resetSafeMode() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            systemRepository.resetSafeMode()
                .onSuccess { _uiState.update { it.copy(actionMessage = "Guvenli mod sifirlandi", isActionLoading = false) }; loadAll() }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) } }
        }
    }

    fun loadJournal(lines: Int = 100) {
        viewModelScope.launch {
            systemRepository.getJournal(lines)
                .onSuccess { j -> _uiState.update { it.copy(journal = j, showJournal = true) } }
                .onFailure { e -> _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") } }
        }
    }

    fun showRebootConfirm() = _uiState.update { it.copy(showRebootConfirm = true) }
    fun hideRebootConfirm() = _uiState.update { it.copy(showRebootConfirm = false) }
    fun showShutdownConfirm() = _uiState.update { it.copy(showShutdownConfirm = true) }
    fun hideShutdownConfirm() = _uiState.update { it.copy(showShutdownConfirm = false) }
    fun hideJournal() = _uiState.update { it.copy(showJournal = false) }
    fun clearActionMessage() = _uiState.update { it.copy(actionMessage = null) }
}
