package com.tonbil.aifirewall.feature.systemlogs

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.tonbil.aifirewall.data.remote.dto.SystemLogPageDto
import com.tonbil.aifirewall.data.remote.dto.SystemLogSummaryDto
import com.tonbil.aifirewall.data.repository.SystemRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SystemLogsUiState(
    val logs: SystemLogPageDto = SystemLogPageDto(),
    val summary: SystemLogSummaryDto = SystemLogSummaryDto(),
    val isLoading: Boolean = true,
    val isRefreshing: Boolean = false,
    val error: String? = null,
    val currentPage: Int = 1,
    val pageSize: Int = 50,
    val severityFilter: String? = null,  // null = all
    val categoryFilter: String? = null, // null = all
)

class SystemLogsViewModel(private val repo: SystemRepository) : ViewModel() {

    private val _state = MutableStateFlow(SystemLogsUiState())
    val state: StateFlow<SystemLogsUiState> = _state.asStateFlow()

    init {
        loadAll()
    }

    fun loadAll() {
        viewModelScope.launch {
            val s = _state.value
            _state.update { it.copy(isLoading = true, error = null) }
            try {
                coroutineScope {
                    val logsDeferred = async {
                        repo.getLogs(
                            page = s.currentPage,
                            pageSize = s.pageSize,
                            severity = s.severityFilter,
                            category = s.categoryFilter,
                        )
                    }
                    val summaryDeferred = async { repo.getLogsSummary() }

                    val logs = logsDeferred.await().getOrNull() ?: SystemLogPageDto()
                    val summary = summaryDeferred.await().getOrNull() ?: SystemLogSummaryDto()

                    _state.update {
                        it.copy(
                            logs = logs,
                            summary = summary,
                            isLoading = false,
                            isRefreshing = false,
                        )
                    }
                }
            } catch (e: Exception) {
                _state.update {
                    it.copy(
                        isLoading = false,
                        isRefreshing = false,
                        error = e.message ?: "Loglar yuklenemedi",
                    )
                }
            }
        }
    }

    fun loadLogs() {
        viewModelScope.launch {
            val s = _state.value
            _state.update { it.copy(isLoading = true, error = null) }
            repo.getLogs(
                page = s.currentPage,
                pageSize = s.pageSize,
                severity = s.severityFilter,
                category = s.categoryFilter,
            ).onSuccess { logs ->
                _state.update { it.copy(logs = logs, isLoading = false, isRefreshing = false) }
            }.onFailure { e ->
                _state.update { it.copy(isLoading = false, isRefreshing = false, error = e.message) }
            }
        }
    }

    fun loadSummary() {
        viewModelScope.launch {
            repo.getLogsSummary().onSuccess { summary ->
                _state.update { it.copy(summary = summary) }
            }
        }
    }

    fun setPage(page: Int) {
        _state.update { it.copy(currentPage = page) }
        loadLogs()
    }

    fun setSeverity(severity: String?) {
        _state.update { it.copy(severityFilter = severity, currentPage = 1) }
        loadLogs()
    }

    fun setCategory(category: String?) {
        _state.update { it.copy(categoryFilter = category, currentPage = 1) }
        loadLogs()
    }

    fun refresh() {
        _state.update { it.copy(isRefreshing = true) }
        loadAll()
    }

    fun clearError() = _state.update { it.copy(error = null) }
}
