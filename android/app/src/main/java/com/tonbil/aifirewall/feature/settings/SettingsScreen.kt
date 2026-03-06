package com.tonbil.aifirewall.feature.settings

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
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.DhcpLeaseDto
import com.tonbil.aifirewall.data.remote.dto.DhcpStatsDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

private val tabs = listOf("DHCP", "Sunucu", "Hakkinda")

@Composable
fun SettingsScreen(viewModel: SettingsViewModel = koinViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
    ) {
        // Header
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                imageVector = Icons.Outlined.Settings,
                contentDescription = null,
                tint = colors.neonCyan,
                modifier = Modifier.size(28.dp),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Ayarlar",
                style = MaterialTheme.typography.headlineMedium,
                color = colors.neonCyan,
                modifier = Modifier.weight(1f),
            )
            if (uiState.isRefreshing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = colors.neonCyan,
                    strokeWidth = 2.dp,
                )
            } else {
                IconButton(onClick = { viewModel.refresh() }) {
                    Icon(
                        imageVector = Icons.Outlined.Refresh,
                        contentDescription = "Yenile",
                        tint = colors.neonCyan,
                    )
                }
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
                            color = if (uiState.selectedTab == index)
                                colors.neonCyan else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                        )
                    },
                )
            }
        }

        // Content
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
                        )
                    }
                }
            }
            else -> {
                when (uiState.selectedTab) {
                    0 -> DhcpTab(uiState.dhcpStats, uiState.dhcpLeases)
                    1 -> ServerTab(uiState.serverUrl)
                    2 -> AboutTab()
                }
            }
        }
    }
}

@Composable
private fun DhcpTab(stats: DhcpStatsDto?, leases: List<DhcpLeaseDto>) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // dnsmasq status
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(
                                if (stats?.dnsmasqRunning == true) colors.neonGreen else colors.neonRed
                            ),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (stats?.dnsmasqRunning == true) "dnsmasq Calisiyor" else "dnsmasq Kapali",
                        style = MaterialTheme.typography.titleMedium,
                        color = if (stats?.dnsmasqRunning == true) colors.neonGreen else colors.neonRed,
                    )
                }
            }
        }
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Havuz",
                    value = "${stats?.activePools ?: 0}/${stats?.totalPools ?: 0}",
                    color = colors.neonCyan,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Atanan IP",
                    value = "${stats?.assignedIps ?: 0}/${stats?.totalIps ?: 0}",
                    color = colors.neonMagenta,
                )
            }
        }
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Statik",
                    value = "${stats?.staticLeases ?: 0}",
                    color = colors.neonAmber,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Dinamik",
                    value = "${stats?.dynamicLeases ?: 0}",
                    color = colors.neonGreen,
                )
            }
        }
        if (leases.isNotEmpty()) {
            item {
                Text(
                    text = "Aktif Kiralamalar",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(leases) { lease ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = lease.hostname ?: lease.macAddress,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Text(
                                text = lease.macAddress,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            )
                        }
                        Text(
                            text = lease.ipAddress,
                            style = MaterialTheme.typography.bodyMedium,
                            color = colors.neonCyan,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ServerTab(serverUrl: String) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                InfoRow("Sunucu URL", serverUrl, colors.neonCyan)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("Yerel Adres", "192.168.1.2", colors.neonGreen)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("Uzak Adres", "wall.tonbilx.com", colors.neonMagenta)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("API Versiyon", "v1", colors.neonAmber)
            }
        }
    }
}

@Composable
private fun AboutTab() {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Outlined.Info,
                        contentDescription = null,
                        tint = colors.neonCyan,
                        modifier = Modifier.size(32.dp),
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Column {
                        Text(
                            text = "TonbilAiOS",
                            style = MaterialTheme.typography.headlineSmall,
                            color = colors.neonCyan,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = "v5.0",
                            style = MaterialTheme.typography.bodyMedium,
                            color = colors.neonMagenta,
                        )
                    }
                }
                Spacer(modifier = Modifier.height(16.dp))
                InfoRow("Platform", "Raspberry Pi 4", colors.neonCyan)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("Backend", "FastAPI + Python", colors.neonGreen)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("Veritabani", "MariaDB", colors.neonAmber)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("Cache", "Redis", colors.neonMagenta)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("Firewall", "nftables", colors.neonRed)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("VPN", "WireGuard", colors.neonCyan)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("DNS", "dnsmasq + proxy", colors.neonGreen)
            }
        }
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Ozellikler",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonCyan,
                )
                Spacer(modifier = Modifier.height(8.dp))
                val features = listOf(
                    "AI tabanli tehdit analizi",
                    "DNS filtreleme ve engelleme",
                    "Per-cihaz profil yonetimi",
                    "DDoS koruma (nftables)",
                    "WireGuard VPN sunucusu",
                    "DHCP sunucusu",
                    "Bant genisligi izleme",
                    "Canli trafik akisi",
                    "Telegram bildirimleri",
                )
                features.forEach { feature ->
                    Row(
                        modifier = Modifier.padding(vertical = 2.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            modifier = Modifier
                                .size(4.dp)
                                .clip(CircleShape)
                                .background(colors.neonCyan),
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = feature,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                    }
                }
            }
        }
    }
}

// Shared

@Composable
private fun MiniStatCard(
    modifier: Modifier = Modifier,
    label: String,
    value: String,
    color: Color,
) {
    GlassCard(modifier = modifier) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge,
            color = color,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun InfoRow(label: String, value: String, color: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            modifier = Modifier.width(120.dp),
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = color,
        )
    }
}
