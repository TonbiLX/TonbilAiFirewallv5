package com.tonbil.aifirewall.feature.systemlogs

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.data.remote.dto.SystemLogDto
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.GlassBg
import com.tonbil.aifirewall.ui.theme.NeonAmber
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SystemLogsScreen(
    onBack: () -> Unit,
    viewModel: SystemLogsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground),
    ) {
        TopAppBar(
            title = { Text("Sistem Loglari", color = TextPrimary) },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, "Geri", tint = NeonCyan)
                }
            },
            actions = {
                IconButton(onClick = { viewModel.refresh() }) {
                    Icon(Icons.Default.Refresh, "Yenile", tint = NeonCyan)
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkSurface),
        )

        if (state.isLoading && state.logs.items.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = NeonCyan)
            }
        } else {
            LazyColumn(
                modifier = Modifier.padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Summary
                item {
                    Spacer(Modifier.height(8.dp))
                    SummaryRow(state)
                }

                // Filters
                item {
                    FilterRow(
                        severity = state.severityFilter,
                        category = state.categoryFilter,
                        onSeverity = { viewModel.setSeverity(it) },
                        onCategory = { viewModel.setCategory(it) },
                    )
                }

                // Log items
                items(state.logs.items) { log ->
                    LogItem(log)
                }

                // Pagination
                item {
                    PaginationRow(
                        currentPage = state.currentPage,
                        totalPages = state.logs.totalPages,
                        onPage = { viewModel.setPage(it) },
                    )
                    Spacer(Modifier.height(16.dp))
                }
            }
        }
    }
}

@Composable
private fun SummaryRow(state: SystemLogsUiState) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        SummaryCard("Toplam", state.summary.totalLogs, NeonCyan, Modifier.weight(1f))
        SummaryCard("DNS", state.summary.totalDns, NeonGreen, Modifier.weight(1f))
        SummaryCard("Trafik", state.summary.totalTraffic, NeonMagenta, Modifier.weight(1f))
        SummaryCard("Engel", state.summary.totalBlocked, NeonRed, Modifier.weight(1f))
    }
}

@Composable
private fun SummaryCard(label: String, value: Int, color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(GlassBg)
            .padding(8.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(value.toString(), color = color, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Text(label, color = TextSecondary, fontSize = 11.sp)
        }
    }
}

@Composable
private fun FilterRow(
    severity: String?,
    category: String?,
    onSeverity: (String?) -> Unit,
    onCategory: (String?) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Default.FilterList, "Filtre", tint = TextSecondary, modifier = Modifier.size(20.dp))
        DropdownSelector(
            label = severity ?: "Tumu",
            options = listOf(null to "Tumu", "info" to "Info", "warning" to "Uyari", "critical" to "Kritik"),
            onSelect = onSeverity,
            modifier = Modifier.weight(1f),
        )
        DropdownSelector(
            label = category ?: "Tum Kategoriler",
            options = listOf(null to "Tumu", "dns" to "DNS", "traffic" to "Trafik", "insight" to "Icgoru", "security" to "Guvenlik"),
            onSelect = onCategory,
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun DropdownSelector(
    label: String,
    options: List<Pair<String?, String>>,
    onSelect: (String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    var expanded by remember { mutableStateOf(false) }
    Box(modifier = modifier) {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Text(label, color = TextPrimary, fontSize = 12.sp, maxLines = 1)
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { (value, display) ->
                DropdownMenuItem(
                    text = { Text(display) },
                    onClick = { onSelect(value); expanded = false },
                )
            }
        }
    }
}

@Composable
private fun LogItem(log: SystemLogDto) {
    val severityColor = when (log.severity.lowercase()) {
        "critical" -> NeonRed
        "warning" -> NeonAmber
        "info" -> NeonCyan
        else -> TextSecondary
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(GlassBg)
            .padding(12.dp),
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // Severity badge
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(severityColor.copy(alpha = 0.15f))
                        .padding(horizontal = 6.dp, vertical = 2.dp),
                ) {
                    Text(
                        text = log.severity.uppercase(),
                        color = severityColor,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
                // Category
                Text(log.category, color = NeonMagenta, fontSize = 11.sp)
                // Timestamp
                Text(
                    text = log.timestamp.take(19).replace("T", " "),
                    color = TextSecondary,
                    fontSize = 10.sp,
                )
            }
            Spacer(Modifier.height(4.dp))
            Text(
                text = log.message,
                color = TextPrimary,
                fontSize = 13.sp,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
            )
            if (log.sourceIp != null || log.domain != null) {
                Spacer(Modifier.height(4.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    log.sourceIp?.let { Text("IP: $it", color = TextSecondary, fontSize = 11.sp) }
                    log.domain?.let { Text(it, color = NeonCyan, fontSize = 11.sp) }
                }
            }
        }
    }
}

@Composable
private fun PaginationRow(currentPage: Int, totalPages: Int, onPage: (Int) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(onClick = { if (currentPage > 1) onPage(currentPage - 1) }, enabled = currentPage > 1) {
            Icon(Icons.Default.ChevronLeft, "Onceki", tint = if (currentPage > 1) NeonCyan else TextSecondary)
        }
        Spacer(Modifier.width(8.dp))
        Text("$currentPage / $totalPages", color = TextPrimary, fontSize = 14.sp)
        Spacer(Modifier.width(8.dp))
        IconButton(onClick = { if (currentPage < totalPages) onPage(currentPage + 1) }, enabled = currentPage < totalPages) {
            Icon(Icons.Default.ChevronRight, "Sonraki", tint = if (currentPage < totalPages) NeonCyan else TextSecondary)
        }
    }
}
