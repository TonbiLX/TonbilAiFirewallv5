package com.tonbil.aifirewall.feature.ddos

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.DdosCountersDto
import com.tonbil.aifirewall.data.remote.dto.DdosProtectionStatusDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DdosUiState(
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val protections: List<DdosProtectionStatusDto> = emptyList(),
    val counters: DdosCountersDto? = null,
    val showFlushConfirm: Boolean = false,
)

class DdosViewModel(
    private val repository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DdosUiState())
    val uiState: StateFlow<DdosUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = it.counters == null) }
            try {
                coroutineScope {
                    val statusDeferred = async { repository.getDdosStatus() }
                    val countersDeferred = async { repository.getDdosCounters() }

                    _uiState.update { state ->
                        state.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            protections = statusDeferred.await().getOrElse { emptyList() },
                            counters = countersDeferred.await().getOrNull(),
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

    fun refresh() {
        _uiState.update { it.copy(isRefreshing = true) }
        loadAll()
    }

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }

    fun toggleProtection(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.toggleDdosProtection(name)
                .onSuccess {
                    _uiState.update { state ->
                        state.copy(
                            isActionLoading = false,
                            protections = state.protections.map { p ->
                                if (p.name == name) p.copy(enabled = !p.enabled) else p
                            },
                            actionMessage = "Koruma durumu degistirildi",
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    fun applyChanges() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            repository.applyDdos()
                .onSuccess {
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Degisiklikler uygulandi")
                    }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    fun showFlushConfirm() {
        _uiState.update { it.copy(showFlushConfirm = true) }
    }

    fun hideFlushConfirm() {
        _uiState.update { it.copy(showFlushConfirm = false) }
    }

    fun flushAttackers() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showFlushConfirm = false) }
            repository.flushAttackers()
                .onSuccess {
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Saldirgan listesi temizlendi")
                    }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }
}
