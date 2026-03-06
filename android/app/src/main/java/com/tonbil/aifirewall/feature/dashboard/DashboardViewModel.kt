package com.tonbil.aifirewall.feature.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.ktor.client.HttpClient
import io.ktor.client.request.get
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DashboardUiState(
    val connectionStatus: String = "Baglaniyor...",
)

class DashboardViewModel(private val client: HttpClient) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init {
        checkConnection()
    }

    private fun checkConnection() {
        viewModelScope.launch {
            try {
                client.get("dashboard/summary")
                _uiState.value = _uiState.value.copy(
                    connectionStatus = "Bagli (wall.tonbilx.com)"
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    connectionStatus = "Baglanti hatasi: ${e.message}"
                )
            }
        }
    }
}
