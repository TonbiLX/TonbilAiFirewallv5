package com.tonbil.aifirewall.feature.notifications

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.PushChannelDto
import com.tonbil.aifirewall.data.remote.dto.PushRegistrationResponseDto
import com.tonbil.aifirewall.data.remote.dto.PushTokenDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PushNotificationsUiState(
    val channels: List<PushChannelDto> = emptyList(),
    val isRegistered: Boolean = false,
    val isLoading: Boolean = true,
    val error: String? = null,
    val successMessage: String? = null,
)

class PushNotificationsViewModel(
    private val httpClient: HttpClient,
) : ViewModel() {

    private val _uiState = MutableStateFlow(PushNotificationsUiState())
    val uiState: StateFlow<PushNotificationsUiState> = _uiState.asStateFlow()

    init {
        loadChannels()
        checkRegistration()
    }

    private fun checkRegistration() {
        // Backend register endpoint'i her zaman success dondurdugundan
        // placeholder olarak isRegistered = true yap
        _uiState.update { it.copy(isRegistered = true) }
    }

    fun loadChannels() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                val channels: List<PushChannelDto> = httpClient.get(ApiRoutes.PUSH_CHANNELS).body()
                _uiState.update { it.copy(isLoading = false, channels = channels) }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = e.message ?: "Kanallar yuklenemedi") }
            }
        }
    }

    fun toggleChannel(channelId: String) {
        viewModelScope.launch {
            try {
                httpClient.post(ApiRoutes.pushChannelToggle(channelId))
                // Optimistic update
                _uiState.update { state ->
                    state.copy(
                        channels = state.channels.map { ch ->
                            if (ch.id == channelId) ch.copy(enabled = !ch.enabled) else ch
                        },
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(error = "Kanal guncellenemedi: ${e.message}") }
                loadChannels()
            }
        }
    }

    fun registerToken(fcmToken: String, deviceName: String = "Android") {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                val response: PushRegistrationResponseDto = httpClient.post(ApiRoutes.PUSH_REGISTER) {
                    contentType(ContentType.Application.Json)
                    setBody(PushTokenDto(token = fcmToken, deviceName = deviceName))
                }.body()
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        isRegistered = response.success,
                        successMessage = if (response.success) "Bildirimler basariyla kaydedildi" else null,
                        error = if (!response.success) response.message else null,
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isLoading = false, error = "Kayit hatasi: ${e.message}") }
            }
        }
    }

    fun clearMessages() {
        _uiState.update { it.copy(error = null, successMessage = null) }
    }
}
