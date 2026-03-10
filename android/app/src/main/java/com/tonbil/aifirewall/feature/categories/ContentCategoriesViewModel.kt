package com.tonbil.aifirewall.feature.categories

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.BlocklistDto
import com.tonbil.aifirewall.data.remote.dto.ContentCategoryCreateDto
import com.tonbil.aifirewall.data.remote.dto.ContentCategoryDto
import com.tonbil.aifirewall.data.remote.dto.ContentCategoryUpdateDto
import com.tonbil.aifirewall.data.repository.ContentCategoryRepository
import com.tonbil.aifirewall.data.repository.SecurityRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class ContentCategoriesUiState(
    val categories: List<ContentCategoryDto> = emptyList(),
    val blocklists: List<BlocklistDto> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
    val showCreateDialog: Boolean = false,
    val editingCategory: ContentCategoryDto? = null,
)

class ContentCategoriesViewModel(
    private val repo: ContentCategoryRepository,
    private val securityRepo: SecurityRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(ContentCategoriesUiState())
    val state: StateFlow<ContentCategoriesUiState> = _state

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            val cats = repo.getCategories().getOrDefault(emptyList())
            val bls = securityRepo.getBlocklists().getOrDefault(emptyList())
            _state.value = _state.value.copy(
                categories = cats,
                blocklists = bls,
                isLoading = false,
            )
        }
    }

    fun createCategory(dto: ContentCategoryCreateDto) {
        viewModelScope.launch {
            repo.createCategory(dto)
                .onSuccess { loadAll() }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }

    fun updateCategory(id: Int, dto: ContentCategoryUpdateDto) {
        viewModelScope.launch {
            repo.updateCategory(id, dto)
                .onSuccess { loadAll() }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }

    fun deleteCategory(id: Int) {
        viewModelScope.launch {
            repo.deleteCategory(id)
                .onSuccess { loadAll() }
                .onFailure { _state.value = _state.value.copy(error = it.message) }
        }
    }

    fun toggleCreateDialog(show: Boolean) {
        _state.value = _state.value.copy(showCreateDialog = show, error = null)
    }

    fun setEditing(cat: ContentCategoryDto?) {
        _state.value = _state.value.copy(editingCategory = cat, error = null)
    }

    fun clearError() {
        _state.value = _state.value.copy(error = null)
    }
}
