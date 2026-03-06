package com.tonbil.aifirewall.feature.security

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
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
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
import com.tonbil.aifirewall.data.remote.dto.DdosCountersDto
import com.tonbil.aifirewall.data.remote.dto.DdosProtectionStatusDto
import com.tonbil.aifirewall.data.remote.dto.DnsStatsDto
import com.tonbil.aifirewall.data.remote.dto.FirewallStatsDto
import com.tonbil.aifirewall.data.remote.dto.SecurityStatsDto
import com.tonbil.aifirewall.data.remote.dto.TopDomainDto
import com.tonbil.aifirewall.data.remote.dto.VpnPeerDto
import com.tonbil.aifirewall.data.remote.dto.VpnStatsDto
import java.util.Locale
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

private val tabs = listOf("DNS", "Firewall", "VPN", "DDoS", "Tehdit")

@Composable
fun SecurityScreen(viewModel: SecurityViewModel = koinViewModel()) {
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
                imageVector = Icons.Outlined.Security,
                contentDescription = null,
                tint = colors.neonCyan,
                modifier = Modifier.size(28.dp),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "Guvenlik",
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
        ScrollableTabRow(
            selectedTabIndex = uiState.selectedTab,
            containerColor = Color.Transparent,
            contentColor = colors.neonCyan,
            edgePadding = 8.dp,
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
                    0 -> DnsTab(uiState.dnsStats)
                    1 -> FirewallTab(uiState.firewallStats)
                    2 -> VpnTab(uiState.vpnStats, uiState.vpnPeers)
                    3 -> DdosTab(uiState.ddosProtections, uiState.ddosCounters)
                    4 -> ThreatTab(uiState.securityStats)
                }
            }
        }
    }
}

@Composable
private fun DnsTab(stats: DnsStatsDto?) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // Stats row
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Toplam Sorgu",
                    value = formatCount(stats?.totalQueries24h ?: 0),
                    color = colors.neonCyan,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Engellenen",
                    value = formatCount(stats?.blockedQueries24h ?: 0),
                    color = colors.neonRed,
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
                    label = "Engel Orani",
                    value = "%${String.format("%.1f", stats?.blockPercentage ?: 0f)}",
                    color = colors.neonMagenta,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Blocklist Domain",
                    value = formatCount(stats?.totalBlocklistDomains ?: 0),
                    color = colors.neonAmber,
                )
            }
        }
        // Top blocked domains
        if (stats != null && stats.topBlockedDomains.isNotEmpty()) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "En Cok Engellenen",
                        style = MaterialTheme.typography.titleSmall,
                        color = colors.neonRed,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    stats.topBlockedDomains.take(10).forEach { domain ->
                        DomainRow(domain, colors.neonRed)
                    }
                }
            }
        }
        // Top queried domains
        if (stats != null && stats.topQueriedDomains.isNotEmpty()) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "En Cok Sorgulanan",
                        style = MaterialTheme.typography.titleSmall,
                        color = colors.neonCyan,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    stats.topQueriedDomains.take(10).forEach { domain ->
                        DomainRow(domain, colors.neonCyan)
                    }
                }
            }
        }
    }
}

@Composable
private fun FirewallTab(stats: FirewallStatsDto?) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Toplam Kural",
                    value = "${stats?.totalRules ?: 0}",
                    color = colors.neonCyan,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Aktif Kural",
                    value = "${stats?.activeRules ?: 0}",
                    color = colors.neonGreen,
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
                    label = "Gelen Kurallar",
                    value = "${stats?.inboundRules ?: 0}",
                    color = colors.neonAmber,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Giden Kurallar",
                    value = "${stats?.outboundRules ?: 0}",
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
                    label = "Engellenen Paket",
                    value = formatCount(stats?.blockedPackets24h ?: 0),
                    color = colors.neonRed,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Aktif Baglanti",
                    value = "${stats?.activeConnections ?: 0}",
                    color = colors.neonCyan,
                )
            }
        }
        if (stats != null && stats.openPorts.isNotEmpty()) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Acik Portlar",
                        style = MaterialTheme.typography.titleSmall,
                        color = colors.neonAmber,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = stats.openPorts.joinToString(", "),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            }
        }
    }
}

@Composable
private fun VpnTab(stats: VpnStatsDto?, peers: List<VpnPeerDto>) {
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
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .clip(CircleShape)
                            .background(
                                if (stats?.serverEnabled == true) colors.neonGreen else colors.neonRed
                            ),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (stats?.serverEnabled == true) "WireGuard Aktif" else "WireGuard Kapali",
                        style = MaterialTheme.typography.titleMedium,
                        color = if (stats?.serverEnabled == true) colors.neonGreen else colors.neonRed,
                    )
                }
                if (stats?.serverEnabled == true) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Port: ${stats.listenPort}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
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
                    label = "Bagli Peer",
                    value = "${stats?.connectedPeers ?: 0}/${stats?.totalPeers ?: 0}",
                    color = colors.neonCyan,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Transfer",
                    value = "${formatBytes(stats?.totalTransferRx ?: 0)} / ${formatBytes(stats?.totalTransferTx ?: 0)}",
                    color = colors.neonMagenta,
                )
            }
        }
        if (peers.isNotEmpty()) {
            item {
                Text(
                    text = "Peer Listesi",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(peers) { peer ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(
                                    if (peer.connected) colors.neonGreen else colors.neonRed
                                ),
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = peer.name,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Text(
                                text = peer.allowedIps,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            )
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text(
                                text = formatBytes(peer.transferRx),
                                style = MaterialTheme.typography.labelSmall,
                                color = colors.neonCyan,
                            )
                            Text(
                                text = formatBytes(peer.transferTx),
                                style = MaterialTheme.typography.labelSmall,
                                color = colors.neonMagenta,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun DdosTab(
    protections: List<DdosProtectionStatusDto>,
    counters: DdosCountersDto?,
) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Toplam Engellenen Paket",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonRed,
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = formatCount((counters?.totalDroppedPackets ?: 0).toInt()),
                    style = MaterialTheme.typography.headlineLarge,
                    color = colors.neonRed,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = formatBytes(counters?.totalDroppedBytes ?: 0),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                )
            }
        }
        if (counters != null && counters.byProtection.isNotEmpty()) {
            val protList = counters.byProtection.entries.toList()
            val protColors = listOf(colors.neonRed, colors.neonAmber, colors.neonMagenta, colors.neonCyan, colors.neonGreen)
            // Show in 2-column grid
            items(protList.chunked(2)) { row ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    row.forEachIndexed { i, (name, counter) ->
                        val colorIdx = (protList.indexOf(row[0]) + i) % protColors.size
                        MiniStatCard(
                            modifier = Modifier.weight(1f),
                            label = name.replace("_", " ")
                                .replaceFirstChar { it.titlecase(Locale.getDefault()) },
                            value = formatCount(counter.packets.toInt()),
                            color = protColors[colorIdx],
                        )
                    }
                    if (row.size == 1) {
                        Spacer(modifier = Modifier.weight(1f))
                    }
                }
            }
        }
        if (protections.isNotEmpty()) {
            item {
                Text(
                    text = "Koruma Mekanizmalari",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(protections) { prot ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .clip(CircleShape)
                                .background(
                                    if (prot.enabled) colors.neonGreen else colors.neonRed
                                ),
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = prot.displayName.ifBlank { prot.name },
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.weight(1f),
                        )
                        Text(
                            text = if (prot.enabled) "Aktif" else "Kapali",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (prot.enabled) colors.neonGreen else colors.neonRed,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ThreatTab(stats: SecurityStatsDto?) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Engelli IP",
                    value = "${stats?.blockedIpCount ?: 0}",
                    color = colors.neonRed,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Oto Engel",
                    value = "${stats?.totalAutoBlocks ?: 0}",
                    color = colors.neonAmber,
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
                    label = "Dis Engel",
                    value = "${stats?.totalExternalBlocked ?: 0}",
                    color = colors.neonMagenta,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Suphe",
                    value = "${stats?.totalSuspicious ?: 0}",
                    color = colors.neonCyan,
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
                    label = "DGA Tespit",
                    value = "${stats?.dgaDetections ?: 0}",
                    color = colors.neonRed,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Engelli Subnet",
                    value = "${stats?.blockedSubnetCount ?: 0}",
                    color = colors.neonAmber,
                )
            }
        }
        if (stats?.lastThreatTime != null) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Son Tehdit",
                        style = MaterialTheme.typography.titleSmall,
                        color = colors.neonRed,
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = stats.lastThreatTime,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            }
        }
    }
}

// Shared UI components

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
private fun DomainRow(domain: TopDomainDto, color: Color) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = domain.domain,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = formatCount(domain.count),
            style = MaterialTheme.typography.labelSmall,
            color = color,
        )
    }
}

private fun formatCount(count: Int): String {
    return when {
        count >= 1_000_000 -> String.format("%.1fM", count / 1_000_000.0)
        count >= 1_000 -> String.format("%.1fK", count / 1_000.0)
        else -> count.toString()
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
