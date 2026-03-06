package com.tonbil.aifirewall.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.ServerDiscovery
import com.tonbil.aifirewall.data.remote.dto.*
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val selectedTab: Int = 0,
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    // Profiles
    val profiles: List<ProfileResponseDto> = emptyList(),
    // DHCP
    val dhcpStats: DhcpStatsDto? = null,
    val dhcpLeases: List<DhcpLeaseDto> = emptyList(),
    // WiFi
    val wifiStatus: WifiStatusDto? = null,
    val wifiClients: List<WifiClientDto> = emptyList(),
    // Telegram
    val telegramConfig: TelegramConfigDto? = null,
    // System
    val systemOverview: SystemOverviewDto? = null,
    val systemServices: List<ServiceStatusDto> = emptyList(),
    // Chat
    val chatHistory: List<ChatMessageDto> = emptyList(),
    val chatInput: String = "",
    val chatLoading: Boolean = false,
    // Server info
    val serverUrl: String = "",
)

class SettingsViewModel(
    private val securityRepository: SecurityRepository,
    private val serverDiscovery: ServerDiscovery,
) : ViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        _uiState.update { it.copy(serverUrl = serverDiscovery.activeUrl) }
        loadAll()
    }

    private fun loadAll() {
        viewModelScope.launch {
            try {
                coroutineScope {
                    val profiles = async { securityRepository.getProfiles() }
                    val dhcp = async { securityRepository.getDhcpStats() }
                    val leases = async { securityRepository.getDhcpLeases() }
                    val wifi = async { securityRepository.getWifiStatus() }
                    val wifiC = async { securityRepository.getWifiClients() }
                    val tg = async { securityRepository.getTelegramConfig() }
                    val sys = async { securityRepository.getSystemOverview() }
                    val svc = async { securityRepository.getSystemServices() }
                    val chat = async { securityRepository.getChatHistory() }

                    _uiState.update {
                        it.copy(
                            isLoading = false,
                            isRefreshing = false,
                            error = null,
                            profiles = profiles.await().getOrElse { emptyList() },
                            dhcpStats = dhcp.await().getOrNull(),
                            dhcpLeases = leases.await().getOrElse { emptyList() },
                            wifiStatus = wifi.await().getOrNull(),
                            wifiClients = wifiC.await().getOrElse { emptyList() },
                            telegramConfig = tg.await().getOrNull(),
                            systemOverview = sys.await().getOrNull(),
                            systemServices = svc.await().getOrElse { emptyList() },
                            chatHistory = chat.await().getOrElse { emptyList() },
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

    fun selectTab(index: Int) {
        _uiState.update { it.copy(selectedTab = index) }
    }

    fun refresh() {
        _uiState.update { it.copy(isRefreshing = true) }
        loadAll()
    }

    fun updateChatInput(text: String) {
        _uiState.update { it.copy(chatInput = text) }
    }

    fun sendChat() {
        val msg = _uiState.value.chatInput.trim()
        if (msg.isBlank()) return
        _uiState.update {
            it.copy(
                chatInput = "",
                chatLoading = true,
                chatHistory = it.chatHistory + ChatMessageDto(role = "user", content = msg),
            )
        }
        viewModelScope.launch {
            securityRepository.sendChat(msg)
                .onSuccess { resp ->
                    _uiState.update {
                        it.copy(
                            chatLoading = false,
                            chatHistory = it.chatHistory + ChatMessageDto(role = "assistant", content = resp.reply),
                        )
                    }
                }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(
                            chatLoading = false,
                            chatHistory = it.chatHistory + ChatMessageDto(role = "assistant", content = "Hata: ${e.message}"),
                        )
                    }
                }
        }
    }
}
