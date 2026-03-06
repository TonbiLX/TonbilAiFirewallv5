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
    val actionMessage: String? = null,
    val isActionLoading: Boolean = false,
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
    // Dialog states
    val showAddProfileDialog: Boolean = false,
    val showAddStaticLeaseDialog: Boolean = false,
    val showEditTelegramDialog: Boolean = false,
    val showEditWifiDialog: Boolean = false,
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

    fun clearActionMessage() {
        _uiState.update { it.copy(actionMessage = null) }
    }

    // ========== CHAT ==========

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

    // ========== PROFILE Actions ==========

    fun showAddProfileDialog() = _uiState.update { it.copy(showAddProfileDialog = true) }
    fun hideAddProfileDialog() = _uiState.update { it.copy(showAddProfileDialog = false) }

    fun createProfile(name: String, bandwidthLimit: Float?, contentFilters: List<String>) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddProfileDialog = false) }
            securityRepository.createProfile(
                ProfileCreateDto(name = name, bandwidthLimitMbps = bandwidthLimit, contentFilters = contentFilters)
            ).onSuccess {
                _uiState.update { it.copy(actionMessage = "Profil olusturuldu", isActionLoading = false) }
                refresh()
            }.onFailure { e ->
                _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
            }
        }
    }

    fun deleteProfile(id: Int) {
        viewModelScope.launch {
            securityRepository.deleteProfile(id)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Profil silindi") }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    // ========== DHCP Actions ==========

    fun showAddStaticLeaseDialog() = _uiState.update { it.copy(showAddStaticLeaseDialog = true) }
    fun hideAddStaticLeaseDialog() = _uiState.update { it.copy(showAddStaticLeaseDialog = false) }

    fun createStaticLease(mac: String, ip: String, hostname: String?) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showAddStaticLeaseDialog = false) }
            securityRepository.createStaticLease(DhcpStaticLeaseCreateDto(mac, ip, hostname))
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Statik IP atandi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun deleteStaticLease(mac: String) {
        viewModelScope.launch {
            securityRepository.deleteStaticLease(mac)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Statik IP silindi") }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    // ========== WIFI Actions ==========

    fun showEditWifiDialog() = _uiState.update { it.copy(showEditWifiDialog = true) }
    fun hideEditWifiDialog() = _uiState.update { it.copy(showEditWifiDialog = false) }

    fun toggleWifi() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            val isRunning = _uiState.value.wifiStatus?.running == true
            val result = if (isRunning) securityRepository.disableWifi() else securityRepository.enableWifi()
            result
                .onSuccess {
                    _uiState.update {
                        it.copy(
                            actionMessage = if (isRunning) "WiFi AP kapatildi" else "WiFi AP acildi",
                            isActionLoading = false,
                        )
                    }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun updateWifiConfig(ssid: String?, password: String?, channel: Int?) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showEditWifiDialog = false) }
            securityRepository.updateWifiConfig(WifiConfigUpdateDto(ssid, password, channel))
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "WiFi ayarlari guncellendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    // ========== TELEGRAM Actions ==========

    fun showEditTelegramDialog() = _uiState.update { it.copy(showEditTelegramDialog = true) }
    fun hideEditTelegramDialog() = _uiState.update { it.copy(showEditTelegramDialog = false) }

    fun updateTelegramConfig(dto: TelegramConfigUpdateDto) {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true, showEditTelegramDialog = false) }
            securityRepository.updateTelegramConfig(dto)
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Telegram guncellendi", isActionLoading = false) }
                    refresh()
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }

    fun testTelegram() {
        viewModelScope.launch {
            _uiState.update { it.copy(isActionLoading = true) }
            securityRepository.testTelegram()
                .onSuccess {
                    _uiState.update { it.copy(actionMessage = "Test mesaji gonderildi", isActionLoading = false) }
                }
                .onFailure { e ->
                    _uiState.update { it.copy(actionMessage = "Hata: ${e.message}", isActionLoading = false) }
                }
        }
    }
}
