package com.tonbil.aifirewall.feature.profiles

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.ProfileCreateDto
import com.tonbil.aifirewall.data.remote.dto.ProfileResponseDto
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ProfilesUiState(
    val profiles: List<ProfileResponseDto> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
    val actionMessage: String? = null,
    // Add dialog state
    val showAddDialog: Boolean = false,
    val addName: String = "",
    val addBandwidth: String = "",
    val isAdding: Boolean = false,
    // Delete confirmation
    val deleteTarget: ProfileResponseDto? = null,
    val isDeleting: Boolean = false,
)

class ProfilesViewModel(private val repo: SecurityRepository) : ViewModel() {

    private val _state = MutableStateFlow(ProfilesUiState())
    val state: StateFlow<ProfilesUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            repo.getProfiles()
                .onSuccess { profiles ->
                    _state.update { it.copy(profiles = profiles, isLoading = false) }
                }
                .onFailure { e ->
                    _state.update { it.copy(isLoading = false, error = e.message ?: "Yukleme hatasi") }
                }
        }
    }

    fun showAddDialog() = _state.update { it.copy(showAddDialog = true, addName = "", addBandwidth = "") }
    fun dismissAddDialog() = _state.update { it.copy(showAddDialog = false) }
    fun setAddName(v: String) = _state.update { it.copy(addName = v) }
    fun setAddBandwidth(v: String) = _state.update { it.copy(addBandwidth = v) }

    fun createProfile() {
        val s = _state.value
        if (s.addName.isBlank()) return

        viewModelScope.launch {
            _state.update { it.copy(isAdding = true) }
            repo.createProfile(
                ProfileCreateDto(
                    name = s.addName.trim(),
                    bandwidthLimitMbps = s.addBandwidth.toFloatOrNull(),
                )
            )
                .onSuccess {
                    _state.update {
                        it.copy(isAdding = false, showAddDialog = false, actionMessage = "Profil olusturuldu")
                    }
                    load()
                }
                .onFailure { e ->
                    _state.update { it.copy(isAdding = false, actionMessage = "Hata: ${e.message}") }
                }
        }
    }

    fun showDeleteConfirm(profile: ProfileResponseDto) = _state.update { it.copy(deleteTarget = profile) }
    fun dismissDeleteConfirm() = _state.update { it.copy(deleteTarget = null) }

    fun deleteProfile() {
        val target = _state.value.deleteTarget ?: return
        viewModelScope.launch {
            _state.update { it.copy(isDeleting = true) }
            repo.deleteProfile(target.id)
                .onSuccess {
                    _state.update {
                        it.copy(isDeleting = false, deleteTarget = null, actionMessage = "'${target.name}' silindi")
                    }
                    load()
                }
                .onFailure { e ->
                    _state.update { it.copy(isDeleting = false, actionMessage = "Silinemedi: ${e.message}") }
                }
        }
    }

    fun clearActionMessage() = _state.update { it.copy(actionMessage = null) }
}
