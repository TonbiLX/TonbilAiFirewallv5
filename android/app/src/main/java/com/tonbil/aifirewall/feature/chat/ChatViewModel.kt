package com.tonbil.aifirewall.feature.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.ChatMessageDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ChatUiState(
    val messages: List<ChatMessageDto> = emptyList(),
    val isLoading: Boolean = true,
    val isSending: Boolean = false,
    val error: String? = null,
    val inputText: String = "",
    val actionMessage: String? = null,
)

class ChatViewModel(private val repo: SecurityRepository) : ViewModel() {

    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state.asStateFlow()

    init {
        loadHistory()
    }

    fun loadHistory() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            repo.getChatHistory()
                .onSuccess { history ->
                    _state.update { it.copy(messages = history, isLoading = false) }
                }
                .onFailure { e ->
                    _state.update { it.copy(isLoading = false, error = e.message ?: "Gecmis yuklenemedi") }
                }
        }
    }

    fun send() {
        val text = _state.value.inputText.trim()
        if (text.isBlank() || _state.value.isSending) return

        // Add user message to UI immediately
        val userMsg = ChatMessageDto(role = "user", content = text)
        _state.update {
            it.copy(
                messages = it.messages + userMsg,
                inputText = "",
                isSending = true,
            )
        }

        viewModelScope.launch {
            repo.sendChat(text)
                .onSuccess { response ->
                    val assistantMsg = ChatMessageDto(role = "assistant", content = response.reply)
                    _state.update {
                        it.copy(
                            messages = it.messages + assistantMsg,
                            isSending = false,
                        )
                    }
                }
                .onFailure { e ->
                    val errorMsg = ChatMessageDto(role = "assistant", content = "Hata: ${e.message}")
                    _state.update {
                        it.copy(
                            messages = it.messages + errorMsg,
                            isSending = false,
                        )
                    }
                }
        }
    }

    fun clearHistory() {
        viewModelScope.launch {
            repo.clearChatHistory()
                .onSuccess {
                    _state.update { it.copy(messages = emptyList(), actionMessage = "Gecmis temizlendi") }
                }
                .onFailure { e ->
                    _state.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun setInputText(v: String) = _state.update { it.copy(inputText = v) }
    fun clearActionMessage() = _state.update { it.copy(actionMessage = null) }
}
