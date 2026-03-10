package com.tonbil.aifirewall.feature.deviceservices

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.DeviceServiceDto
import com.tonbil.aifirewall.data.remote.dto.ServiceGroupDto
import com.tonbil.aifirewall.data.remote.dto.ServiceToggleDto
import com.tonbil.aifirewall.data.repository.DeviceServiceRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class DeviceServicesUiState(
    val services: List<DeviceServiceDto> = emptyList(),
    val groups: List<ServiceGroupDto> = emptyList(),
    val selectedGroup: String? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
    val togglingServiceId: Int? = null,
)

class DeviceServicesViewModel(
    private val deviceId: Int,
    private val repo: DeviceServiceRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(DeviceServicesUiState())
    val state: StateFlow<DeviceServicesUiState> = _state

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            val services = repo.getDeviceServices(deviceId).getOrDefault(emptyList())
            val groups = repo.getGroups().getOrDefault(emptyList())
            _state.value = _state.value.copy(
                services = services,
                groups = groups,
                isLoading = false,
            )
        }
    }

    fun toggleService(serviceId: Int, blocked: Boolean) {
        viewModelScope.launch {
            _state.value = _state.value.copy(togglingServiceId = serviceId)
            repo.toggleService(deviceId, ServiceToggleDto(serviceId, blocked))
                .onSuccess {
                    // Optimistik guncelleme: API yanitini beklemeden UI'i guncelle
                    val updatedServices = _state.value.services.map { svc ->
                        if (svc.serviceId == serviceId) svc.copy(blocked = blocked) else svc
                    }
                    _state.value = _state.value.copy(
                        services = updatedServices,
                        togglingServiceId = null,
                    )
                }
                .onFailure {
                    _state.value = _state.value.copy(
                        error = it.message,
                        togglingServiceId = null,
                    )
                }
        }
    }

    fun selectGroup(group: String?) {
        _state.value = _state.value.copy(selectedGroup = group)
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }

    // Secili gruba gore filtrelenmis servisler
    fun filteredServices(): List<DeviceServiceDto> {
        val group = _state.value.selectedGroup ?: return _state.value.services
        return _state.value.services.filter { it.group == group }
    }
}
