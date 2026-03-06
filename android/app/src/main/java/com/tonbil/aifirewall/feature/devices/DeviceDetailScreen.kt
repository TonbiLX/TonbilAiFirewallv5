package com.tonbil.aifirewall.feature.devices

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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.ArrowDownward
import androidx.compose.material.icons.outlined.ArrowUpward
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.ShieldMoon
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.pullToRefresh
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkColors
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceDetailScreen(
    deviceId: String,
    viewModel: DeviceDetailViewModel = koinViewModel { parametersOf(deviceId.toInt()) },
    onBack: () -> Unit,
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val pullToRefreshState = rememberPullToRefreshState()
    val tabs = listOf("Genel", "Trafik", "DNS")

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .pullToRefresh(
                isRefreshing = uiState.isRefreshing,
                state = pullToRefreshState,
                onRefresh = { viewModel.refresh() },
            ),
    ) {
        when {
            uiState.isLoading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(color = colors.neonCyan)
                }
            }
            uiState.error != null && uiState.device == null -> {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    GlassCard(modifier = Modifier.fillMaxWidth()) {
                        Text(
                            text = uiState.error ?: "",
                            color = colors.neonRed,
                            style = MaterialTheme.typography.bodyLarge,
                        )
                    }
                }
            }
            else -> {
                val device = uiState.device ?: return@Box

                Column(modifier = Modifier.fillMaxSize()) {
                    // Top bar
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 8.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        IconButton(onClick = onBack) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Outlined.ArrowBack,
                                contentDescription = "Geri",
                                tint = colors.neonCyan,
                            )
                        }
                        Text(
                            text = device.hostname ?: "Bilinmeyen Cihaz",
                            style = MaterialTheme.typography.titleLarge,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.weight(1f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        IconButton(onClick = { viewModel.toggleBlock() }) {
                            Icon(
                                imageVector = if (device.isBlocked) Icons.Outlined.ShieldMoon else Icons.Outlined.Shield,
                                contentDescription = if (device.isBlocked) "Engeli Kaldir" else "Engelle",
                                tint = if (device.isBlocked) colors.neonRed else colors.neonGreen,
                            )
                        }
                    }

                    // Tabs
                    TabRow(
                        selectedTabIndex = uiState.selectedTab,
                        containerColor = Color.Transparent,
                        contentColor = colors.neonCyan,
                    ) {
                        tabs.forEachIndexed { index, title ->
                            Tab(
                                selected = uiState.selectedTab == index,
                                onClick = { viewModel.selectTab(index) },
                                text = {
                                    Text(
                                        text = title,
                                        color = if (uiState.selectedTab == index) colors.neonCyan
                                        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                    )
                                },
                            )
                        }
                    }

                    // Tab content
                    when (uiState.selectedTab) {
                        0 -> OverviewTab(uiState, viewModel, colors)
                        1 -> TrafficTab(uiState, colors)
                        2 -> DnsTab(uiState, colors)
                    }
                }
            }
        }

        PullToRefreshDefaults.Indicator(
            state = pullToRefreshState,
            isRefreshing = uiState.isRefreshing,
            modifier = Modifier.align(Alignment.TopCenter),
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun OverviewTab(
    uiState: DeviceDetailUiState,
    viewModel: DeviceDetailViewModel,
    colors: CyberpunkColors,
) {
    val device = uiState.device ?: return

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // Device info card
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Cihaz Bilgileri",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonCyan,
                )
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("Hostname", device.hostname ?: "Bilinmeyen")
                InfoRow("IP Adresi", device.ipAddress ?: "-")
                InfoRow("MAC Adresi", device.macAddress)
                if (!device.manufacturer.isNullOrBlank()) {
                    InfoRow("Uretici", device.manufacturer)
                }
                Spacer(modifier = Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(
                                if (device.isOnline) colors.neonGreen
                                else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                            ),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (device.isOnline) "Cevrimici" else "Cevrimdisi",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (device.isOnline) colors.neonGreen else
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                }
                if (device.lastSeen != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    InfoRow("Son Gorunme", device.lastSeen)
                }
            }
        }

        // Bandwidth card
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Anlik Bant Genisligi",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonCyan,
                )
                Spacer(modifier = Modifier.height(8.dp))
                if (uiState.bandwidth != null) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly,
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Outlined.ArrowDownward,
                                contentDescription = null,
                                tint = colors.neonCyan,
                                modifier = Modifier.size(20.dp),
                            )
                            Text(
                                text = formatBps(uiState.bandwidth.downloadBps),
                                style = MaterialTheme.typography.titleMedium,
                                color = colors.neonCyan,
                            )
                            Text(
                                text = "Indirme",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            )
                        }
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Outlined.ArrowUpward,
                                contentDescription = null,
                                tint = colors.neonMagenta,
                                modifier = Modifier.size(20.dp),
                            )
                            Text(
                                text = formatBps(uiState.bandwidth.uploadBps),
                                style = MaterialTheme.typography.titleMedium,
                                color = colors.neonMagenta,
                            )
                            Text(
                                text = "Yukleme",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            )
                        }
                    }
                } else {
                    Text(
                        text = "Veri bekleniyor...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                }
            }
        }

        // Profile selector
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Profil",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonCyan,
                )
                Spacer(modifier = Modifier.height(8.dp))

                var expanded by remember { mutableStateOf(false) }
                val currentProfile = uiState.profiles.find { it.id == device.profileId }

                ExposedDropdownMenuBox(
                    expanded = expanded,
                    onExpandedChange = { expanded = it },
                ) {
                    TextField(
                        value = currentProfile?.name ?: "Profil Yok",
                        onValueChange = {},
                        readOnly = true,
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable),
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = colors.glassBg,
                            unfocusedContainerColor = colors.glassBg,
                            focusedTextColor = MaterialTheme.colorScheme.onSurface,
                            unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
                        ),
                    )
                    ExposedDropdownMenu(
                        expanded = expanded,
                        onDismissRequest = { expanded = false },
                    ) {
                        DropdownMenuItem(
                            text = { Text("Profil Yok") },
                            onClick = {
                                viewModel.assignProfile(null)
                                expanded = false
                            },
                        )
                        uiState.profiles.forEach { profile ->
                            DropdownMenuItem(
                                text = { Text(profile.name) },
                                onClick = {
                                    viewModel.assignProfile(profile.id)
                                    expanded = false
                                },
                            )
                        }
                    }
                }
            }
        }

        // Connection history
        if (uiState.connectionHistory.isNotEmpty()) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Baglanti Gecmisi",
                        style = MaterialTheme.typography.titleMedium,
                        color = colors.neonCyan,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    uiState.connectionHistory.take(5).forEach { entry ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                        ) {
                            Text(
                                text = entry.connectedAt ?: entry.timestamp ?: "-",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
                                modifier = Modifier.weight(1f),
                            )
                            if (entry.durationSeconds != null) {
                                Text(
                                    text = formatDuration(entry.durationSeconds),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = colors.neonAmber,
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TrafficTab(
    uiState: DeviceDetailUiState,
    colors: CyberpunkColors,
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // Traffic summary card
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Trafik Ozeti",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonCyan,
                )
                Spacer(modifier = Modifier.height(8.dp))

                val summary = uiState.trafficSummary
                if (summary != null) {
                    InfoRow("Toplam Akis", "${summary.totalFlows}")
                    InfoRow("Aktif Akis", "${summary.activeFlows}")
                    InfoRow("Gelen", formatBytes(summary.totalBytesIn))
                    InfoRow("Giden", formatBytes(summary.totalBytesOut))
                } else {
                    Text(
                        text = "Trafik verisi yok",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                }
            }
        }

        // Top services
        val topServices = uiState.trafficSummary?.topServices ?: emptyList()
        if (topServices.isNotEmpty()) {
            item {
                Text(
                    text = "En Cok Kullanilan Servisler",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(bottom = 4.dp),
                )
            }
            items(topServices) { service ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = service.service,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                        Text(
                            text = formatBytes(service.bytes),
                            style = MaterialTheme.typography.bodyMedium,
                            color = colors.neonMagenta,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun DnsTab(
    uiState: DeviceDetailUiState,
    colors: CyberpunkColors,
) {
    val blockedCount = uiState.dnsLogs.count { it.blocked }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        // Summary
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        text = "DNS Sorgulari",
                        style = MaterialTheme.typography.titleMedium,
                        color = colors.neonCyan,
                    )
                    Text(
                        text = "$blockedCount engellendi",
                        style = MaterialTheme.typography.labelMedium,
                        color = colors.neonRed,
                    )
                }
            }
        }

        if (uiState.dnsLogs.isEmpty()) {
            item {
                Text(
                    text = "DNS sorgu verisi yok",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    modifier = Modifier.padding(16.dp),
                )
            }
        }

        items(uiState.dnsLogs) { log ->
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    // Domain + type
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = log.domain,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            // Query type badge
                            Box(
                                modifier = Modifier
                                    .clip(CircleShape)
                                    .background(colors.neonCyan.copy(alpha = 0.15f))
                                    .padding(horizontal = 6.dp, vertical = 2.dp),
                            ) {
                                Text(
                                    text = log.queryType,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = colors.neonCyan,
                                )
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = log.timestamp,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                            )
                        }
                    }

                    // Blocked badge
                    Box(
                        modifier = Modifier
                            .clip(CircleShape)
                            .background(
                                if (log.blocked) colors.neonRed.copy(alpha = 0.15f)
                                else colors.neonGreen.copy(alpha = 0.15f)
                            )
                            .padding(horizontal = 8.dp, vertical = 4.dp),
                    ) {
                        Text(
                            text = if (log.blocked) "Engel" else "Izin",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (log.blocked) colors.neonRed else colors.neonGreen,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

private fun formatBps(bps: Long): String {
    return when {
        bps >= 1_000_000_000 -> String.format("%.1f Gbps", bps / 1_000_000_000.0)
        bps >= 1_000_000 -> String.format("%.1f Mbps", bps / 1_000_000.0)
        bps >= 1_000 -> String.format("%.1f Kbps", bps / 1_000.0)
        else -> "$bps bps"
    }
}

private fun formatBytes(bytes: Long): String {
    return when {
        bytes >= 1_073_741_824 -> String.format("%.1f GB", bytes / 1_073_741_824.0)
        bytes >= 1_048_576 -> String.format("%.1f MB", bytes / 1_048_576.0)
        bytes >= 1_024 -> String.format("%.1f KB", bytes / 1_024.0)
        else -> "$bytes B"
    }
}

private fun formatDuration(seconds: Int): String {
    return when {
        seconds >= 3600 -> "${seconds / 3600}s ${(seconds % 3600) / 60}dk"
        seconds >= 60 -> "${seconds / 60}dk ${seconds % 60}sn"
        else -> "${seconds}sn"
    }
}
