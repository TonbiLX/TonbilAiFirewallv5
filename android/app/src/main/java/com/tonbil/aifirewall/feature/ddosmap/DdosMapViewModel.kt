package com.tonbil.aifirewall.feature.ddosmap

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.DdosAttackMapDto
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

data class DdosMapUiState(
    val attackMap: DdosAttackMapDto = DdosAttackMapDto(),
    val counters: DdosCountersDto? = null,
    val status: List<DdosProtectionStatusDto> = emptyList(),
    val isLoading: Boolean = true,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
)

class DdosMapViewModel(
    private val securityRepository: SecurityRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DdosMapUiState())
    val uiState: StateFlow<DdosMapUiState> = _uiState.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val mapDeferred = async { securityRepository.getDdosAttackMap() }
                    val countersDeferred = async { securityRepository.getDdosCounters() }
                    val statusDeferred = async { securityRepository.getDdosStatus() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            attackMap = mapDeferred.await().getOrElse { DdosAttackMapDto() },
                            counters = countersDeferred.await().getOrNull(),
                            status = statusDeferred.await().getOrElse { emptyList() },
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

    fun flushAttackers() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.flushAttackers()
                .onSuccess {
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Saldiranlar temizlendi")
                    }
                    loadAll()
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}")
                    }
                }
        }
    }

    fun clearActionMessage() = _uiState.update { it.copy(actionMessage = null) }
}
