package com.tonbil.aifirewall.feature.aisettings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.AiConfigDto
import com.tonbil.aifirewall.data.remote.dto.AiConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.AiProviderDto
import com.tonbil.aifirewall.data.remote.dto.AiStatsDto
import com.tonbil.aifirewall.data.remote.dto.AiTestResponseDto
import com.tonbil.aifirewall.data.repository.AiSettingsRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AiSettingsUiState(
    val config: AiConfigDto = AiConfigDto(),
    val providers: List<AiProviderDto> = emptyList(),
    val stats: AiStatsDto = AiStatsDto(),
    val isLoading: Boolean = true,
    val isActionLoading: Boolean = false,
    val isTestLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val testResult: AiTestResponseDto? = null,
    // Local edit state (temp values before save)
    val editProvider: String = "",
    val editApiKey: String = "",
    val editModel: String = "",
    val editChatEnabled: Boolean = true,
    val editTemperature: Float = 0.7f,
    val editMaxTokens: String = "1000",
    val editDailyLimit: String = "100",
    val editLogAnalysisEnabled: Boolean = true,
    val editLogAnalysisInterval: String = "60",
    val isDirty: Boolean = false,
)

class AiSettingsViewModel(private val repo: AiSettingsRepository) : ViewModel() {

    private val _state = MutableStateFlow(AiSettingsUiState())
    val state: StateFlow<AiSettingsUiState> = _state.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val configDeferred = async { repo.getConfig() }
                    val providersDeferred = async { repo.getProviders() }
                    val statsDeferred = async { repo.getStats() }

                    val config = configDeferred.await().getOrNull() ?: AiConfigDto()
                    val providers = providersDeferred.await().getOrElse { emptyList() }
                    val stats = statsDeferred.await().getOrNull() ?: AiStatsDto()

                    _state.update {
                        it.copy(
                            config = config,
                            providers = providers,
                            stats = stats,
                            isLoading = false,
                            // Sync edit fields from loaded config
                            editProvider = config.provider,
                            editApiKey = config.apiKey,
                            editModel = config.model,
                            editChatEnabled = config.chatEnabled,
                            editTemperature = config.temperature,
                            editMaxTokens = config.maxTokens.toString(),
                            editDailyLimit = config.dailyLimit.toString(),
                            editLogAnalysisEnabled = config.logAnalysisEnabled,
                            editLogAnalysisInterval = config.logAnalysisInterval.toString(),
                            isDirty = false,
                        )
                    }
                }
            } catch (e: Exception) {
                _state.update {
                    it.copy(isLoading = false, error = e.message ?: "Yukleme hatasi")
                }
            }
        }
    }

    fun updateConfig(dto: AiConfigUpdateDto) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true) }
            repo.updateConfig(dto)
                .onSuccess { updated ->
                    _state.update {
                        it.copy(
                            config = updated,
                            isActionLoading = false,
                            actionMessage = "Ayarlar kaydedildi",
                            isDirty = false,
                        )
                    }
                }
                .onFailure { e ->
                    _state.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun saveCurrentEdits() {
        val s = _state.value
        updateConfig(
            AiConfigUpdateDto(
                provider = s.editProvider,
                apiKey = s.editApiKey.ifBlank { null },
                model = s.editModel,
                chatEnabled = s.editChatEnabled,
                temperature = s.editTemperature,
                maxTokens = s.editMaxTokens.toIntOrNull(),
                dailyLimit = s.editDailyLimit.toIntOrNull(),
                logAnalysisEnabled = s.editLogAnalysisEnabled,
                logAnalysisInterval = s.editLogAnalysisInterval.toIntOrNull(),
            )
        )
    }

    fun test() {
        viewModelScope.launch {
            _state.update { it.copy(isTestLoading = true, testResult = null) }
            repo.test()
                .onSuccess { result ->
                    _state.update {
                        it.copy(
                            isTestLoading = false,
                            testResult = result,
                            actionMessage = if (result.success) "Test basarili (${result.responseTimeMs}ms)" else "Test basarisiz: ${result.message}",
                        )
                    }
                }
                .onFailure { e ->
                    _state.update { it.copy(isTestLoading = false, actionMessage = "Test hatasi: ${e.message}") }
                }
        }
    }

    fun resetCounter() {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true) }
            repo.resetCounter()
                .onSuccess { msg ->
                    _state.update { it.copy(isActionLoading = false, actionMessage = msg.message) }
                    refreshStats()
                }
                .onFailure { e ->
                    _state.update { it.copy(isActionLoading = false, actionMessage = "Sifirlanamadi: ${e.message}") }
                }
        }
    }

    private fun refreshStats() {
        viewModelScope.launch {
            repo.getStats().onSuccess { stats ->
                _state.update { it.copy(stats = stats) }
            }
        }
    }

    // Edit field setters
    fun setProvider(v: String) = _state.update { it.copy(editProvider = v, editModel = "", isDirty = true) }
    fun setApiKey(v: String) = _state.update { it.copy(editApiKey = v, isDirty = true) }
    fun setModel(v: String) = _state.update { it.copy(editModel = v, isDirty = true) }
    fun setChatEnabled(v: Boolean) = _state.update { it.copy(editChatEnabled = v, isDirty = true) }
    fun setTemperature(v: Float) = _state.update { it.copy(editTemperature = v, isDirty = true) }
    fun setMaxTokens(v: String) = _state.update { it.copy(editMaxTokens = v, isDirty = true) }
    fun setDailyLimit(v: String) = _state.update { it.copy(editDailyLimit = v, isDirty = true) }
    fun setLogAnalysisEnabled(v: Boolean) = _state.update { it.copy(editLogAnalysisEnabled = v, isDirty = true) }
    fun setLogAnalysisInterval(v: String) = _state.update { it.copy(editLogAnalysisInterval = v, isDirty = true) }
    fun clearTestResult() = _state.update { it.copy(testResult = null) }
    fun clearActionMessage() = _state.update { it.copy(actionMessage = null) }
}
