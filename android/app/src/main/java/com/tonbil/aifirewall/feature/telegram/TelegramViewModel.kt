package com.tonbil.aifirewall.feature.telegram

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.TelegramConfigDto
import com.tonbil.aifirewall.data.remote.dto.TelegramConfigUpdateDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class TelegramUiState(
    val config: TelegramConfigDto = TelegramConfigDto(),
    val isLoading: Boolean = true,
    val isSaving: Boolean = false,
    val isTesting: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    // Local edit state
    val editBotToken: String = "",
    val editChatId: String = "",
    val editEnabled: Boolean = false,
    val editNotifyThreats: Boolean = true,
    val editNotifyDevices: Boolean = true,
    val editNotifyDdos: Boolean = true,
    val isDirty: Boolean = false,
)

class TelegramViewModel(private val repo: SecurityRepository) : ViewModel() {

    private val _state = MutableStateFlow(TelegramUiState())
    val state: StateFlow<TelegramUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            repo.getTelegramConfig()
                .onSuccess { config ->
                    _state.update {
                        it.copy(
                            config = config,
                            isLoading = false,
                            editBotToken = config.botToken,
                            editChatId = config.chatId,
                            editEnabled = config.enabled,
                            editNotifyThreats = config.notifyThreats,
                            editNotifyDevices = config.notifyDevices,
                            editNotifyDdos = config.notifyDdos,
                            isDirty = false,
                        )
                    }
                }
                .onFailure { e ->
                    _state.update { it.copy(isLoading = false, error = e.message ?: "Yukleme hatasi") }
                }
        }
    }

    fun save() {
        val s = _state.value
        viewModelScope.launch {
            _state.update { it.copy(isSaving = true) }
            repo.updateTelegramConfig(
                TelegramConfigUpdateDto(
                    botToken = s.editBotToken.ifBlank { null },
                    chatId = s.editChatId.ifBlank { null },
                    enabled = s.editEnabled,
                    notifyThreats = s.editNotifyThreats,
                    notifyDevices = s.editNotifyDevices,
                    notifyDdos = s.editNotifyDdos,
                )
            )
                .onSuccess { updated ->
                    _state.update {
                        it.copy(
                            config = updated,
                            isSaving = false,
                            actionMessage = "Ayarlar kaydedildi",
                            isDirty = false,
                        )
                    }
                }
                .onFailure { e ->
                    _state.update { it.copy(isSaving = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun test() {
        viewModelScope.launch {
            _state.update { it.copy(isTesting = true) }
            repo.testTelegram()
                .onSuccess { msg ->
                    _state.update { it.copy(isTesting = false, actionMessage = "Test mesaji gonderildi") }
                }
                .onFailure { e ->
                    _state.update { it.copy(isTesting = false, actionMessage = "Test hatasi: ${e.message}") }
                }
        }
    }

    fun setBotToken(v: String) = _state.update { it.copy(editBotToken = v, isDirty = true) }
    fun setChatId(v: String) = _state.update { it.copy(editChatId = v, isDirty = true) }
    fun setEnabled(v: Boolean) = _state.update { it.copy(editEnabled = v, isDirty = true) }
    fun setNotifyThreats(v: Boolean) = _state.update { it.copy(editNotifyThreats = v, isDirty = true) }
    fun setNotifyDevices(v: Boolean) = _state.update { it.copy(editNotifyDevices = v, isDirty = true) }
    fun setNotifyDdos(v: Boolean) = _state.update { it.copy(editNotifyDdos = v, isDirty = true) }
    fun clearActionMessage() = _state.update { it.copy(actionMessage = null) }
}
