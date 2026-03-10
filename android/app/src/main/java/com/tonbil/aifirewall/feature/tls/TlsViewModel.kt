package com.tonbil.aifirewall.feature.tls

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.TlsConfigDto
import com.tonbil.aifirewall.data.remote.dto.TlsConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.TlsLetsEncryptDto
import com.tonbil.aifirewall.data.remote.dto.TlsValidateDto
import com.tonbil.aifirewall.data.remote.dto.TlsValidateResponseDto
import com.tonbil.aifirewall.data.repository.TlsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class TlsUiState(
    val config: TlsConfigDto = TlsConfigDto(),
    val isLoading: Boolean = true,
    val isActionLoading: Boolean = false,
    val error: String? = null,
    val actionMessage: String? = null,
    val showCertDialog: Boolean = false,
    val showLetsEncryptDialog: Boolean = false,
    val validateResult: TlsValidateResponseDto? = null,
)

class TlsViewModel(private val repo: TlsRepository) : ViewModel() {

    private val _state = MutableStateFlow(TlsUiState())
    val state: StateFlow<TlsUiState> = _state.asStateFlow()

    init {
        loadConfig()
    }

    fun loadConfig() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            repo.getConfig()
                .onSuccess { config ->
                    _state.update { it.copy(config = config, isLoading = false) }
                }
                .onFailure { e ->
                    _state.update { it.copy(isLoading = false, error = e.message ?: "Yapilandirma yuklenemedi") }
                }
        }
    }

    fun updateConfig(dto: TlsConfigUpdateDto) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true) }
            repo.updateConfig(dto)
                .onSuccess { updated ->
                    _state.update {
                        it.copy(
                            config = updated,
                            isActionLoading = false,
                            actionMessage = "Ayarlar kaydedildi",
                        )
                    }
                }
                .onFailure { e ->
                    _state.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun validate(cert: String, key: String) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true, validateResult = null) }
            repo.validate(TlsValidateDto(cert = cert, key = key))
                .onSuccess { result ->
                    _state.update {
                        it.copy(
                            isActionLoading = false,
                            validateResult = result,
                            actionMessage = if (result.valid) "Sertifika gecerli" else "Sertifika gecersiz: ${result.message}",
                        )
                    }
                }
                .onFailure { e ->
                    _state.update { it.copy(isActionLoading = false, actionMessage = "Dogrulama hatasi: ${e.message}") }
                }
        }
    }

    fun uploadCert(cert: String, key: String) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true, showCertDialog = false) }
            repo.uploadCert(cert, key)
                .onSuccess { result ->
                    _state.update {
                        it.copy(
                            isActionLoading = false,
                            actionMessage = if (result.success) "Sertifika yuklendi" else "Yuklenemedi: ${result.message}",
                        )
                    }
                    if (result.success) loadConfig()
                }
                .onFailure { e ->
                    _state.update { it.copy(isActionLoading = false, actionMessage = "Yuklenemedi: ${e.message}") }
                }
        }
    }

    fun toggle() {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true) }
            repo.toggle()
                .onSuccess { msg ->
                    _state.update {
                        it.copy(
                            isActionLoading = false,
                            actionMessage = msg.message,
                        )
                    }
                    loadConfig()
                }
                .onFailure { e ->
                    _state.update { it.copy(isActionLoading = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun letsEncrypt(domain: String, email: String) {
        viewModelScope.launch {
            _state.update { it.copy(isActionLoading = true, showLetsEncryptDialog = false) }
            repo.letsEncrypt(TlsLetsEncryptDto(domain = domain, email = email))
                .onSuccess { msg ->
                    _state.update {
                        it.copy(
                            isActionLoading = false,
                            actionMessage = msg.message,
                        )
                    }
                    loadConfig()
                }
                .onFailure { e ->
                    _state.update { it.copy(isActionLoading = false, actionMessage = "Let's Encrypt hatasi: ${e.message}") }
                }
        }
    }

    fun showCertDialog() = _state.update { it.copy(showCertDialog = true) }
    fun hideCertDialog() = _state.update { it.copy(showCertDialog = false) }
    fun showLetsEncryptDialog() = _state.update { it.copy(showLetsEncryptDialog = true) }
    fun hideLetsEncryptDialog() = _state.update { it.copy(showLetsEncryptDialog = false) }
    fun clearActionMessage() = _state.update { it.copy(actionMessage = null) }
    fun clearValidateResult() = _state.update { it.copy(validateResult = null) }
}
