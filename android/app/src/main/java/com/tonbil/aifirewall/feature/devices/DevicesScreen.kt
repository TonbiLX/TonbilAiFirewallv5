package com.tonbil.aifirewall.feature.devices

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.FilterList
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.ShieldMoon
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Clear
import androidx.compose.material.icons.outlined.SortByAlpha
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.pullToRefresh
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.DeviceResponseDto
import com.tonbil.aifirewall.data.remote.dto.WsDeviceBandwidthDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DevicesScreen(
    viewModel: DevicesViewModel = koinViewModel(),
    onNavigateToDetail: (String) -> Unit = {},
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val pullToRefreshState = rememberPullToRefreshState()

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
            uiState.error != null -> {
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
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(
                            onClick = { viewModel.refresh() },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = colors.neonCyan,
                            ),
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.Refresh,
                                contentDescription = null,
                                modifier = Modifier.size(18.dp),
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Tekrar Dene")
                        }
                    }
                }
            }
            else -> {
                val onlineCount = uiState.devices.count { it.isOnline }
                val offlineCount = uiState.devices.size - onlineCount
                val displayDevices = uiState.filteredDevices

                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    // Header
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                text = "Cihazlar",
                                style = MaterialTheme.typography.headlineLarge,
                                color = colors.neonCyan,
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Box(
                                modifier = Modifier
                                    .clip(CircleShape)
                                    .background(colors.neonGreen.copy(alpha = 0.2f))
                                    .padding(horizontal = 10.dp, vertical = 4.dp),
                            ) {
                                Text(
                                    text = "$onlineCount aktif",
                                    style = MaterialTheme.typography.labelMedium,
                                    color = colors.neonGreen,
                                )
                            }
                        }
                    }

                    // Search bar
                    item {
                        OutlinedTextField(
                            value = uiState.searchQuery,
                            onValueChange = { viewModel.setSearchQuery(it) },
                            placeholder = { Text("Isim, IP veya MAC ara...") },
                            leadingIcon = {
                                Icon(
                                    imageVector = Icons.Outlined.Search,
                                    contentDescription = null,
                                    tint = colors.neonCyan,
                                )
                            },
                            trailingIcon = {
                                if (uiState.searchQuery.isNotEmpty()) {
                                    IconButton(onClick = { viewModel.setSearchQuery("") }) {
                                        Icon(
                                            imageVector = Icons.Outlined.Clear,
                                            contentDescription = "Temizle",
                                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                                        )
                                    }
                                }
                            },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = colors.neonCyan,
                                unfocusedBorderColor = colors.glassBorder,
                                focusedLeadingIconColor = colors.neonCyan,
                                cursorColor = colors.neonCyan,
                            ),
                        )
                    }

                    // Filter chips
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            FilterChip(
                                selected = uiState.filter == DeviceFilter.ALL,
                                onClick = { viewModel.setFilter(DeviceFilter.ALL) },
                                label = { Text("Tumu (${uiState.devices.size})") },
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = colors.neonCyan.copy(alpha = 0.2f),
                                    selectedLabelColor = colors.neonCyan,
                                ),
                            )
                            FilterChip(
                                selected = uiState.filter == DeviceFilter.ONLINE,
                                onClick = { viewModel.setFilter(DeviceFilter.ONLINE) },
                                label = { Text("Online ($onlineCount)") },
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = colors.neonGreen.copy(alpha = 0.2f),
                                    selectedLabelColor = colors.neonGreen,
                                ),
                            )
                            FilterChip(
                                selected = uiState.filter == DeviceFilter.OFFLINE,
                                onClick = { viewModel.setFilter(DeviceFilter.OFFLINE) },
                                label = { Text("Offline ($offlineCount)") },
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = colors.neonRed.copy(alpha = 0.2f),
                                    selectedLabelColor = colors.neonRed,
                                ),
                            )
                        }
                    }

                    // Sort chips
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.SortByAlpha,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                                modifier = Modifier.size(16.dp),
                            )
                            FilterChip(
                                selected = uiState.sort == DeviceSort.NAME,
                                onClick = { viewModel.setSort(DeviceSort.NAME) },
                                label = { Text("Isim") },
                            )
                            FilterChip(
                                selected = uiState.sort == DeviceSort.LAST_SEEN,
                                onClick = { viewModel.setSort(DeviceSort.LAST_SEEN) },
                                label = { Text("Son Gorulme") },
                            )
                            FilterChip(
                                selected = uiState.sort == DeviceSort.IP,
                                onClick = { viewModel.setSort(DeviceSort.IP) },
                                label = { Text("IP") },
                            )
                        }
                    }

                    // Device cards
                    items(
                        items = displayDevices,
                        key = { it.id },
                    ) { device ->
                        DeviceCard(
                            device = device,
                            bandwidth = uiState.bandwidthMap[device.id.toString()],
                            onToggleBlock = { viewModel.toggleBlock(device) },
                            onClick = { onNavigateToDetail(device.id.toString()) },
                        )
                    }
                }
            }
        }

        // Pull-to-refresh indicator
        PullToRefreshDefaults.Indicator(
            state = pullToRefreshState,
            isRefreshing = uiState.isRefreshing,
            modifier = Modifier.align(Alignment.TopCenter),
        )
    }
}

@Composable
private fun DeviceCard(
    device: DeviceResponseDto,
    bandwidth: WsDeviceBandwidthDto?,
    onToggleBlock: () -> Unit,
    onClick: () -> Unit,
) {
    val colors = CyberpunkTheme.colors

    GlassCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Online status indicator
            Box(
                modifier = Modifier
                    .size(12.dp)
                    .clip(CircleShape)
                    .background(
                        if (device.isOnline) colors.neonGreen else
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                    ),
            )

            Spacer(modifier = Modifier.width(12.dp))

            // Device info
            Column(modifier = Modifier.weight(1f)) {
                if (!device.manufacturer.isNullOrBlank()) {
                    Text(
                        text = device.manufacturer,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                }
                Text(
                    text = device.hostname ?: "Bilinmeyen Cihaz",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Text(
                    text = device.ipAddress ?: "-",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                )
            }

            // Bandwidth + block toggle
            Column(horizontalAlignment = Alignment.End) {
                if (bandwidth != null) {
                    Text(
                        text = formatBps(bandwidth.downloadBps),
                        style = MaterialTheme.typography.labelSmall,
                        color = colors.neonCyan,
                    )
                    Text(
                        text = formatBps(bandwidth.uploadBps),
                        style = MaterialTheme.typography.labelSmall,
                        color = colors.neonMagenta,
                    )
                }

                Spacer(modifier = Modifier.height(4.dp))

                IconButton(
                    onClick = onToggleBlock,
                    modifier = Modifier.size(32.dp),
                ) {
                    Icon(
                        imageVector = if (device.isBlocked) Icons.Outlined.ShieldMoon else Icons.Outlined.Shield,
                        contentDescription = if (device.isBlocked) "Engeli Kaldir" else "Engelle",
                        tint = if (device.isBlocked) colors.neonRed else colors.neonGreen,
                        modifier = Modifier.size(20.dp),
                    )
                }
            }
        }
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
