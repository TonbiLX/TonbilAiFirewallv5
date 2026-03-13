package com.tonbil.aifirewall.feature.profiles

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.ContentCategoryDto
import com.tonbil.aifirewall.data.remote.dto.ProfileCreateDto
import com.tonbil.aifirewall.data.remote.dto.ProfileResponseDto
import com.tonbil.aifirewall.data.repository.ContentCategoryRepository
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ProfilesUiState(
    val profiles: List<ProfileResponseDto> = emptyList(),
    val categories: List<ContentCategoryDto> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
    val actionMessage: String? = null,
    // Add/Edit dialog state
    val showAddDialog: Boolean = false,
    val addName: String = "",
    val addBandwidth: String = "",
    val addContentFilters: List<String> = emptyList(), // secili kategori key'leri
    val isAdding: Boolean = false,
    // Edit mode
    val editTarget: ProfileResponseDto? = null,
    // Delete confirmation
    val deleteTarget: ProfileResponseDto? = null,
    val isDeleting: Boolean = false,
)

class ProfilesViewModel(
    private val repo: SecurityRepository,
    private val categoryRepo: ContentCategoryRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ProfilesUiState())
    val state: StateFlow<ProfilesUiState> = _state.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            // Profiller ve kategorileri paralel yukle
            val profilesResult = repo.getProfiles()
            val categoriesResult = categoryRepo.getCategories()
            _state.update {
                it.copy(
                    isLoading = false,
                    profiles = profilesResult.getOrDefault(it.profiles),
                    categories = categoriesResult.getOrDefault(it.categories),
                    error = profilesResult.exceptionOrNull()?.message
                        ?: categoriesResult.exceptionOrNull()?.message,
                )
            }
        }
    }

    fun showAddDialog() = _state.update {
        it.copy(
            showAddDialog = true,
            addName = "",
            addBandwidth = "",
            addContentFilters = emptyList(),
            editTarget = null,
        )
    }

    fun showEditDialog(profile: ProfileResponseDto) = _state.update {
        it.copy(
            showAddDialog = true,
            editTarget = profile,
            addName = profile.name,
            addBandwidth = profile.bandwidthLimitMbps?.toString() ?: "",
            addContentFilters = profile.contentFilters,
        )
    }

    fun dismissAddDialog() = _state.update {
        it.copy(showAddDialog = false, editTarget = null, addContentFilters = emptyList())
    }

    fun setAddName(v: String) = _state.update { it.copy(addName = v) }
    fun setAddBandwidth(v: String) = _state.update { it.copy(addBandwidth = v) }

    // Kategori secimi: key listesine ekle/cikar
    fun toggleContentFilter(categoryKey: String) = _state.update { s ->
        val current = s.addContentFilters
        val updated = if (current.contains(categoryKey)) {
            current - categoryKey
        } else {
            current + categoryKey
        }
        s.copy(addContentFilters = updated)
    }

    fun createProfile() {
        val s = _state.value
        if (s.addName.isBlank()) return

        viewModelScope.launch {
            _state.update { it.copy(isAdding = true) }
            repo.createProfile(
                ProfileCreateDto(
                    name = s.addName.trim(),
                    bandwidthLimitMbps = s.addBandwidth.toFloatOrNull(),
                    contentFilters = s.addContentFilters,
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

    fun updateProfile() {
        val target = _state.value.editTarget ?: return
        val s = _state.value
        if (s.addName.isBlank()) return

        viewModelScope.launch {
            _state.update { it.copy(isAdding = true) }
            repo.updateProfile(
                target.id,
                ProfileCreateDto(
                    name = s.addName.trim(),
                    bandwidthLimitMbps = s.addBandwidth.toFloatOrNull(),
                    contentFilters = s.addContentFilters,
                )
            )
                .onSuccess {
                    _state.update {
                        it.copy(
                            isAdding = false,
                            showAddDialog = false,
                            editTarget = null,
                            actionMessage = "Profil guncellendi",
                        )
                    }
                    load()
                }
                .onFailure { e ->
                    _state.update { it.copy(isAdding = false, actionMessage = "Guncelleme hatasi: ${e.message}") }
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
