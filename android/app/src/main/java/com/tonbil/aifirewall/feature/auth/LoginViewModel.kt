package com.tonbil.aifirewall.feature.auth

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.data.remote.ServerDiscovery
import com.tonbil.aifirewall.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LoginUiState(
    val username: String = "",
    val password: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val isLoginSuccess: Boolean = false,
    val showBiometricPrompt: Boolean = false,
    val showBiometricOnly: Boolean = false,
    val passwordVisible: Boolean = false,
    val isDiscovering: Boolean = true,
    val serverFound: Boolean = false,
    val connectedUrl: String? = null,
)

class LoginViewModel(
    private val authRepository: AuthRepository,
    private val tokenManager: TokenManager,
    private val serverDiscovery: ServerDiscovery,
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    init {
        // If already logged in with biometric enabled, show biometric-only mode
        if (tokenManager.isLoggedIn() && tokenManager.isBiometricEnabled()) {
            _uiState.update { it.copy(showBiometricOnly = true) }
        }

        // Auto-discover server on startup
        viewModelScope.launch {
            _uiState.update { it.copy(isDiscovering = true) }
            val url = serverDiscovery.discoverServer()
            _uiState.update {
                it.copy(
                    isDiscovering = false,
                    serverFound = url != null,
                    connectedUrl = url,
                    errorMessage = if (url == null) "Sunucu bulunamadi. Sunucu Ayarlari'ndan baglanti yapin." else null,
                )
            }
        }
    }

    fun onUsernameChange(value: String) {
        _uiState.update { it.copy(username = value, errorMessage = null) }
    }

    fun onPasswordChange(value: String) {
        _uiState.update { it.copy(password = value, errorMessage = null) }
    }

    fun togglePasswordVisibility() {
        _uiState.update { it.copy(passwordVisible = !it.passwordVisible) }
    }

    fun login() {
        val state = _uiState.value
        if (state.username.isBlank() || state.password.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Kullanici adi ve sifre gerekli") }
            return
        }

        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }

            val result = authRepository.login(state.username, state.password)

            result.fold(
                onSuccess = {
                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            isLoginSuccess = true,
                        )
                    }
                },
                onFailure = { error ->
                    val message = when {
                        error.message?.contains("401") == true -> "Hatali kullanici adi veya sifre"
                        error.message?.contains("connect", ignoreCase = true) == true -> "Sunucuya baglanilamadi"
                        else -> error.message ?: "Giris basarisiz"
                    }
                    _uiState.update {
                        it.copy(isLoading = false, errorMessage = message)
                    }
                }
            )
        }
    }

    fun shouldOfferBiometric(context: Context): Boolean {
        return BiometricHelper.canAuthenticate(context) && !tokenManager.isBiometricEnabled()
    }

    fun onBiometricResult(enabled: Boolean) {
        tokenManager.setBiometricEnabled(enabled)
    }

    fun onBiometricLoginSuccess() {
        _uiState.update { it.copy(isLoginSuccess = true) }
    }

    fun switchToPasswordLogin() {
        _uiState.update { it.copy(showBiometricOnly = false) }
    }

    fun clearError() {
        _uiState.update { it.copy(errorMessage = null) }
    }

    fun retryDiscovery() {
        viewModelScope.launch {
            _uiState.update { it.copy(isDiscovering = true, errorMessage = null) }
            val url = serverDiscovery.discoverServer()
            _uiState.update {
                it.copy(
                    isDiscovering = false,
                    serverFound = url != null,
                    connectedUrl = url,
                    errorMessage = if (url == null) "Sunucu bulunamadi. Sunucu Ayarlari'ndan baglanti yapin." else null,
                )
            }
        }
    }
}
