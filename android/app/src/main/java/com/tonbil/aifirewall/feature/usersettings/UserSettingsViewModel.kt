package com.tonbil.aifirewall.feature.usersettings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.AuthChangePasswordDto
import com.tonbil.aifirewall.data.remote.dto.AuthProfileUpdateDto
import com.tonbil.aifirewall.data.remote.dto.UserInfo
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class UserSettingsUiState(
    val displayName: String = "",
    val username: String = "",
    val isLoading: Boolean = true,
    val isSaving: Boolean = false,
    val error: String? = null,
    val successMessage: String? = null,
    val passwordChangeSuccess: Boolean = false,
    val showPasswordDialog: Boolean = false,
)

class UserSettingsViewModel(
    private val httpClient: HttpClient,
) : ViewModel() {

    private val _uiState = MutableStateFlow(UserSettingsUiState())
    val uiState: StateFlow<UserSettingsUiState> = _uiState.asStateFlow()

    init {
        loadProfile()
    }

    fun loadProfile() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                val user: UserInfo = httpClient.get(ApiRoutes.AUTH_ME).body()
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        username = user.username,
                        displayName = user.displayName ?: "",
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = e.message ?: "Profil yuklenemedi") }
            }
        }
    }

    fun updateProfile(name: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, error = null, successMessage = null) }
            try {
                httpClient.put(ApiRoutes.AUTH_PROFILE) {
                    contentType(ContentType.Application.Json)
                    setBody(AuthProfileUpdateDto(displayName = name.ifBlank { null }))
                }
                _uiState.update {
                    it.copy(
                        isSaving = false,
                        displayName = name,
                        successMessage = "Profil guncellendi",
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isSaving = false, error = "Guncelleme hatasi: ${e.message}") }
            }
        }
    }

    fun changePassword(current: String, new: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, error = null, passwordChangeSuccess = false) }
            try {
                httpClient.post(ApiRoutes.AUTH_CHANGE_PASSWORD) {
                    contentType(ContentType.Application.Json)
                    setBody(AuthChangePasswordDto(currentPassword = current, newPassword = new))
                }
                _uiState.update {
                    it.copy(
                        isSaving = false,
                        passwordChangeSuccess = true,
                        showPasswordDialog = false,
                        successMessage = "Sifre basariyla degistirildi",
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isSaving = false, error = "Sifre degistirilemedi: ${e.message}") }
            }
        }
    }

    fun showPasswordDialog() = _uiState.update { it.copy(showPasswordDialog = true, error = null) }
    fun hidePasswordDialog() = _uiState.update { it.copy(showPasswordDialog = false) }
    fun clearMessages() = _uiState.update { it.copy(error = null, successMessage = null, passwordChangeSuccess = false) }
}
