package com.tonbil.aifirewall.feature.security

import android.graphics.BitmapFactory
import android.util.Base64
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.QrCode2
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material.icons.outlined.Stop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.RadioButton
import androidx.compose.material3.RadioButtonDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.AiInsightDto
import com.tonbil.aifirewall.data.remote.dto.BlocklistDto
import com.tonbil.aifirewall.data.remote.dto.DdosCountersDto
import com.tonbil.aifirewall.data.remote.dto.DdosProtectionStatusDto
import com.tonbil.aifirewall.data.remote.dto.DnsRuleDto
import com.tonbil.aifirewall.data.remote.dto.DnsStatsDto
import com.tonbil.aifirewall.data.remote.dto.FirewallRuleCreateDto
import com.tonbil.aifirewall.data.remote.dto.FirewallRuleDto
import com.tonbil.aifirewall.data.remote.dto.FirewallStatsDto
import com.tonbil.aifirewall.data.remote.dto.FlowStatsDto
import com.tonbil.aifirewall.data.remote.dto.LiveFlowDto
import com.tonbil.aifirewall.data.remote.dto.SecurityStatsDto
import com.tonbil.aifirewall.data.remote.dto.TopDomainDto
import com.tonbil.aifirewall.data.remote.dto.VpnPeerConfigDto
import com.tonbil.aifirewall.data.remote.dto.VpnPeerDto
import com.tonbil.aifirewall.data.remote.dto.VpnStatsDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import java.util.Locale
import org.koin.androidx.compose.koinViewModel

private val tabs = listOf("DNS", "Firewall", "VPN", "DDoS", "Trafik", "AI")

@Composable
fun SecurityScreen(viewModel: SecurityViewModel = koinViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val snackbarHostState = remember { SnackbarHostState() }

    // Show action message as snackbar
    LaunchedEffect(uiState.actionMessage) {
        uiState.actionMessage?.let { message ->
            snackbarHostState.showSnackbar(message)
            viewModel.clearActionMessage()
        }
    }

    Scaffold(
        snackbarHost = {
            SnackbarHost(hostState = snackbarHostState) { data ->
                Snackbar(
                    snackbarData = data,
                    containerColor = colors.glassBg,
                    contentColor = colors.neonCyan,
                    shape = RoundedCornerShape(8.dp),
                )
            }
        },
        containerColor = Color.Transparent,
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background),
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
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
                            0 -> DnsTab(viewModel, uiState.dnsStats, uiState.blocklists, uiState.dnsRules)
                            1 -> FirewallTab(viewModel, uiState.firewallStats, uiState.firewallRules)
                            2 -> VpnTab(viewModel, uiState.vpnStats, uiState.vpnPeers)
                            3 -> DdosTab(uiState.ddosProtections, uiState.ddosCounters)
                            4 -> TrafficTab(uiState.liveFlows, uiState.flowStats)
                            5 -> AiTab(uiState.insights, uiState.securityStats)
                        }
                    }
                }
            }

            // Loading overlay
            if (uiState.isActionLoading) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color.Black.copy(alpha = 0.5f)),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(
                        color = colors.neonCyan,
                        modifier = Modifier.size(48.dp),
                    )
                }
            }
        }
    }

    // Dialogs
    if (uiState.showAddDnsRuleDialog) {
        AddDnsRuleDialog(
            onDismiss = { viewModel.hideAddDnsRuleDialog() },
            onCreate = { domain, action -> viewModel.createDnsRule(domain, action) },
        )
    }

    if (uiState.showAddBlocklistDialog) {
        AddBlocklistDialog(
            onDismiss = { viewModel.hideAddBlocklistDialog() },
            onCreate = { name, url -> viewModel.createBlocklist(name, url) },
        )
    }

    if (uiState.showAddFirewallRuleDialog) {
        AddFirewallRuleDialog(
            onDismiss = { viewModel.hideAddFirewallRuleDialog() },
            onCreate = { dto -> viewModel.createFirewallRule(dto) },
        )
    }

    if (uiState.showAddVpnPeerDialog) {
        AddVpnPeerDialog(
            onDismiss = { viewModel.hideAddVpnPeerDialog() },
            onCreate = { name -> viewModel.addVpnPeer(name) },
        )
    }

    if (uiState.showVpnPeerConfigDialog != null) {
        VpnPeerConfigDialog(
            peerName = uiState.showVpnPeerConfigDialog!!,
            config = uiState.vpnPeerConfig,
            onDismiss = { viewModel.hideVpnPeerConfig() },
        )
    }
}

// ── Tab 0: DNS ──────────────────────────────────────────────────────────────────

@Composable
private fun DnsTab(
    viewModel: SecurityViewModel,
    stats: DnsStatsDto?,
    blocklists: List<BlocklistDto>,
    dnsRules: List<DnsRuleDto>,
) {
    val colors = CyberpunkTheme.colors

    Box(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Stats row 1
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
            // Stats row 2
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    MiniStatCard(
                        modifier = Modifier.weight(1f),
                        label = "Engel Orani",
                        value = "%${String.format(Locale.getDefault(), "%.1f", stats?.blockPercentage ?: 0f)}",
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
            // Blocklist list
            if (blocklists.isNotEmpty()) {
                item {
                    GlassCard(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                text = "Engelleme Listeleri",
                                style = MaterialTheme.typography.titleSmall,
                                color = colors.neonCyan,
                                modifier = Modifier.weight(1f),
                            )
                            IconButton(
                                onClick = { viewModel.showAddBlocklistDialog() },
                                modifier = Modifier.size(32.dp),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.Add,
                                    contentDescription = "Blocklist Ekle",
                                    tint = colors.neonCyan,
                                    modifier = Modifier.size(18.dp),
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        blocklists.forEach { bl ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 4.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Switch(
                                    checked = bl.enabled,
                                    onCheckedChange = { viewModel.toggleBlocklist(bl.id) },
                                    modifier = Modifier.size(width = 40.dp, height = 24.dp),
                                    colors = SwitchDefaults.colors(
                                        checkedThumbColor = colors.neonGreen,
                                        checkedTrackColor = colors.neonGreen.copy(alpha = 0.3f),
                                        uncheckedThumbColor = colors.neonRed,
                                        uncheckedTrackColor = colors.neonRed.copy(alpha = 0.3f),
                                    ),
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = bl.name,
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurface,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    Text(
                                        text = "${formatCount(bl.domainCount)} domain",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                    )
                                }
                                if (bl.lastUpdated != null) {
                                    Text(
                                        text = bl.lastUpdated,
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                                    )
                                }
                                IconButton(
                                    onClick = { viewModel.deleteBlocklist(bl.id) },
                                    modifier = Modifier.size(32.dp),
                                ) {
                                    Icon(
                                        imageVector = Icons.Outlined.Delete,
                                        contentDescription = "Sil",
                                        tint = colors.neonRed,
                                        modifier = Modifier.size(18.dp),
                                    )
                                }
                            }
                        }
                    }
                }
            }
            // DNS Rules
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = "DNS Kurallari",
                            style = MaterialTheme.typography.titleSmall,
                            color = colors.neonAmber,
                            modifier = Modifier.weight(1f),
                        )
                        IconButton(
                            onClick = { viewModel.showAddDnsRuleDialog() },
                            modifier = Modifier.size(32.dp),
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.Add,
                                contentDescription = "DNS Kural Ekle",
                                tint = colors.neonAmber,
                                modifier = Modifier.size(18.dp),
                            )
                        }
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    if (dnsRules.isNotEmpty()) {
                        dnsRules.forEach { rule ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 2.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(
                                    text = rule.domain,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurface,
                                    modifier = Modifier.weight(1f),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                NeonBadge(
                                    text = if (rule.action == "block") "Engel" else "Izin",
                                    color = if (rule.action == "block") colors.neonRed else colors.neonGreen,
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                IconButton(
                                    onClick = { viewModel.deleteDnsRule(rule.id) },
                                    modifier = Modifier.size(28.dp),
                                ) {
                                    Icon(
                                        imageVector = Icons.Outlined.Close,
                                        contentDescription = "Sil",
                                        tint = colors.neonRed,
                                        modifier = Modifier.size(16.dp),
                                    )
                                }
                            }
                        }
                    } else {
                        Text(
                            text = "Henuz kural eklenmedi",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        )
                    }
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
            // Bottom spacer for FAB
            item { Spacer(modifier = Modifier.height(72.dp)) }
        }

        // FAB
        FloatingActionButton(
            onClick = { viewModel.showAddDnsRuleDialog() },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(16.dp),
            containerColor = colors.neonCyan,
            contentColor = Color.Black,
        ) {
            Icon(imageVector = Icons.Outlined.Add, contentDescription = "Ekle")
        }
    }
}

// ── Tab 1: Firewall ─────────────────────────────────────────────────────────────

@Composable
private fun FirewallTab(
    viewModel: SecurityViewModel,
    stats: FirewallStatsDto?,
    firewallRules: List<FirewallRuleDto>,
) {
    val colors = CyberpunkTheme.colors

    Box(modifier = Modifier.fillMaxSize()) {
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
            // Open ports
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
            // Firewall rules list
            if (firewallRules.isNotEmpty()) {
                item {
                    Text(
                        text = "Guvenlik Duvari Kurallari",
                        style = MaterialTheme.typography.titleSmall,
                        color = colors.neonCyan,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                }
                items(firewallRules) { rule ->
                    GlassCard(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Switch(
                                checked = rule.enabled,
                                onCheckedChange = { viewModel.toggleFirewallRule(rule.id) },
                                modifier = Modifier.size(width = 40.dp, height = 24.dp),
                                colors = SwitchDefaults.colors(
                                    checkedThumbColor = colors.neonGreen,
                                    checkedTrackColor = colors.neonGreen.copy(alpha = 0.3f),
                                    uncheckedThumbColor = colors.neonRed,
                                    uncheckedTrackColor = colors.neonRed.copy(alpha = 0.3f),
                                ),
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = rule.name,
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onSurface,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                ) {
                                    NeonBadge(
                                        text = if (rule.direction == "inbound") "Gelen" else "Giden",
                                        color = if (rule.direction == "inbound") colors.neonAmber else colors.neonMagenta,
                                    )
                                    Text(
                                        text = rule.protocol.uppercase(Locale.getDefault()),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                                    )
                                    if (rule.port != null) {
                                        Text(
                                            text = ":${rule.port}",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = colors.neonCyan,
                                        )
                                    }
                                }
                            }
                            NeonBadge(
                                text = when (rule.action) {
                                    "accept" -> "Kabul"
                                    "drop" -> "Dusur"
                                    "reject" -> "Reddet"
                                    else -> rule.action.replaceFirstChar { it.titlecase(Locale.getDefault()) }
                                },
                                color = when (rule.action) {
                                    "accept" -> colors.neonGreen
                                    "drop" -> colors.neonRed
                                    "reject" -> colors.neonAmber
                                    else -> colors.neonCyan
                                },
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            IconButton(
                                onClick = { viewModel.deleteFirewallRule(rule.id) },
                                modifier = Modifier.size(32.dp),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.Delete,
                                    contentDescription = "Sil",
                                    tint = colors.neonRed,
                                    modifier = Modifier.size(18.dp),
                                )
                            }
                        }
                    }
                }
            }
            // Bottom spacer for FAB
            item { Spacer(modifier = Modifier.height(72.dp)) }
        }

        // FAB
        FloatingActionButton(
            onClick = { viewModel.showAddFirewallRuleDialog() },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(16.dp),
            containerColor = colors.neonCyan,
            contentColor = Color.Black,
        ) {
            Icon(imageVector = Icons.Outlined.Add, contentDescription = "Kural Ekle")
        }
    }
}

// ── Tab 2: VPN ──────────────────────────────────────────────────────────────────

@Composable
private fun VpnTab(
    viewModel: SecurityViewModel,
    stats: VpnStatsDto?,
    peers: List<VpnPeerDto>,
) {
    val colors = CyberpunkTheme.colors

    Box(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // VPN Status + Start/Stop
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Box(
                            modifier = Modifier
                                .size(10.dp)
                                .clip(CircleShape)
                                .background(
                                    if (stats?.serverEnabled == true) colors.neonGreen else colors.neonRed
                                ),
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = if (stats?.serverEnabled == true) "WireGuard Aktif" else "WireGuard Kapali",
                                style = MaterialTheme.typography.titleMedium,
                                color = if (stats?.serverEnabled == true) colors.neonGreen else colors.neonRed,
                            )
                            if (stats?.serverEnabled == true) {
                                Text(
                                    text = "Port: ${stats.listenPort}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                                )
                            }
                        }
                        if (stats?.serverEnabled == true) {
                            Button(
                                onClick = { viewModel.stopVpn() },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = colors.neonRed.copy(alpha = 0.2f),
                                    contentColor = colors.neonRed,
                                ),
                                shape = RoundedCornerShape(8.dp),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.Stop,
                                    contentDescription = "Durdur",
                                    modifier = Modifier.size(18.dp),
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Durdur", style = MaterialTheme.typography.labelMedium)
                            }
                        } else {
                            Button(
                                onClick = { viewModel.startVpn() },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = colors.neonGreen.copy(alpha = 0.2f),
                                    contentColor = colors.neonGreen,
                                ),
                                shape = RoundedCornerShape(8.dp),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.PlayArrow,
                                    contentDescription = "Baslat",
                                    modifier = Modifier.size(18.dp),
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("Baslat", style = MaterialTheme.typography.labelMedium)
                            }
                        }
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
                            Spacer(modifier = Modifier.width(4.dp))
                            // Config / QR button
                            IconButton(
                                onClick = { viewModel.showVpnPeerConfig(peer.name) },
                                modifier = Modifier.size(32.dp),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.QrCode2,
                                    contentDescription = "Config",
                                    tint = colors.neonCyan,
                                    modifier = Modifier.size(18.dp),
                                )
                            }
                            // Delete button
                            IconButton(
                                onClick = { viewModel.deleteVpnPeer(peer.name) },
                                modifier = Modifier.size(32.dp),
                            ) {
                                Icon(
                                    imageVector = Icons.Outlined.Delete,
                                    contentDescription = "Sil",
                                    tint = colors.neonRed,
                                    modifier = Modifier.size(18.dp),
                                )
                            }
                        }
                    }
                }
            }
            // Bottom spacer for FAB
            item { Spacer(modifier = Modifier.height(72.dp)) }
        }

        // FAB
        FloatingActionButton(
            onClick = { viewModel.showAddVpnPeerDialog() },
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(16.dp),
            containerColor = colors.neonCyan,
            contentColor = Color.Black,
        ) {
            Icon(imageVector = Icons.Outlined.Add, contentDescription = "Peer Ekle")
        }
    }
}

// ── Tab 3: DDoS ─────────────────────────────────────────────────────────────────

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

// ── Tab 4: Trafik ───────────────────────────────────────────────────────────────

@Composable
private fun TrafficTab(
    liveFlows: List<LiveFlowDto>,
    flowStats: FlowStatsDto?,
) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // Stats row 1
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Aktif Akis",
                    value = "${flowStats?.totalActive ?: 0}",
                    color = colors.neonCyan,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Benzersiz Hedef",
                    value = "${flowStats?.uniqueDestinations ?: 0}",
                    color = colors.neonMagenta,
                )
            }
        }
        // Stats row 2
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Gelen Veri",
                    value = formatBytes(flowStats?.totalBytesIn ?: 0),
                    color = colors.neonGreen,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Giden Veri",
                    value = formatBytes(flowStats?.totalBytesOut ?: 0),
                    color = colors.neonAmber,
                )
            }
        }
        item {
            MiniStatCard(
                modifier = Modifier.fillMaxWidth(),
                label = "Izlenen Cihaz",
                value = "${flowStats?.trackedDevices ?: 0}",
                color = colors.neonCyan,
            )
        }
        // Live flows list
        if (liveFlows.isNotEmpty()) {
            item {
                Text(
                    text = "Canli Akislar",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(liveFlows) { flow ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        // Direction arrow
                        Text(
                            text = if (flow.direction == "outbound") "\u2197" else "\u2199",
                            style = MaterialTheme.typography.titleMedium,
                            color = if (flow.direction == "outbound") colors.neonCyan else colors.neonMagenta,
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                NeonBadge(
                                    text = flow.protocol.uppercase(Locale.getDefault()),
                                    color = colors.neonCyan,
                                )
                                if (flow.appName != null) {
                                    NeonBadge(
                                        text = flow.appName,
                                        color = colors.neonMagenta,
                                    )
                                } else if (flow.serviceName != null) {
                                    Text(
                                        text = flow.serviceName,
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                    )
                                }
                            }
                            Text(
                                text = "${flow.srcIp}:${flow.srcPort} \u2192 ${flow.dstIp}:${flow.dstPort}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            if (flow.dstDomain != null) {
                                Text(
                                    text = flow.dstDomain,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = colors.neonCyan.copy(alpha = 0.8f),
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            Text(
                                text = "\u2193 ${formatBps(flow.bpsIn)}",
                                style = MaterialTheme.typography.labelSmall,
                                color = colors.neonGreen,
                            )
                            Text(
                                text = "\u2191 ${formatBps(flow.bpsOut)}",
                                style = MaterialTheme.typography.labelSmall,
                                color = colors.neonAmber,
                            )
                            FlowStateBadge(state = flow.state)
                        }
                    }
                }
            }
        }
    }
}

// ── Tab 5: AI ───────────────────────────────────────────────────────────────────

@Composable
private fun AiTab(
    insights: List<AiInsightDto>,
    securityStats: SecurityStatsDto?,
) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // Security stats
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Engelli IP",
                    value = "${securityStats?.blockedIpCount ?: 0}",
                    color = colors.neonRed,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Oto Engel",
                    value = "${securityStats?.totalAutoBlocks ?: 0}",
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
                    value = "${securityStats?.totalExternalBlocked ?: 0}",
                    color = colors.neonMagenta,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Suphe",
                    value = "${securityStats?.totalSuspicious ?: 0}",
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
                    value = "${securityStats?.dgaDetections ?: 0}",
                    color = colors.neonRed,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Engelli Subnet",
                    value = "${securityStats?.blockedSubnetCount ?: 0}",
                    color = colors.neonAmber,
                )
            }
        }
        if (securityStats?.lastThreatTime != null) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Son Tehdit",
                        style = MaterialTheme.typography.titleSmall,
                        color = colors.neonRed,
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = securityStats.lastThreatTime,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            }
        }
        // AI Insights
        if (insights.isNotEmpty()) {
            item {
                Text(
                    text = "AI Analiz Sonuclari",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(insights.filter { !it.dismissed }) { insight ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        verticalAlignment = Alignment.Top,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        NeonBadge(
                            text = when (insight.severity) {
                                "critical" -> "Kritik"
                                "warning" -> "Uyari"
                                else -> "Bilgi"
                            },
                            color = when (insight.severity) {
                                "critical" -> colors.neonRed
                                "warning" -> colors.neonAmber
                                else -> colors.neonCyan
                            },
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = insight.title,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = insight.description,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                            )
                            if (insight.createdAt != null) {
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = insight.createdAt,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                                )
                            }
                        }
                    }
                }
            }
        } else {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "AI analiz sonucu bulunamadi",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                }
            }
        }
    }
}

// ── Dialogs ─────────────────────────────────────────────────────────────────────

@Composable
private fun AddDnsRuleDialog(
    onDismiss: () -> Unit,
    onCreate: (domain: String, action: String) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var domain by remember { mutableStateOf("") }
    var action by remember { mutableStateOf("block") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1025),
        shape = RoundedCornerShape(16.dp),
        title = {
            Text(
                text = "DNS Kurali Ekle",
                color = colors.neonCyan,
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = domain,
                    onValueChange = { domain = it },
                    label = { Text("Domain", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    placeholder = { Text("ornek.com", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = cyberpunkTextFieldColors(),
                )
                Text(
                    text = "Islem",
                    style = MaterialTheme.typography.labelMedium,
                    color = colors.neonCyan,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    Row(
                        modifier = Modifier
                            .selectable(
                                selected = action == "block",
                                onClick = { action = "block" },
                                role = Role.RadioButton,
                            ),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RadioButton(
                            selected = action == "block",
                            onClick = null,
                            colors = RadioButtonDefaults.colors(
                                selectedColor = colors.neonRed,
                                unselectedColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            ),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Engelle", color = colors.neonRed)
                    }
                    Row(
                        modifier = Modifier
                            .selectable(
                                selected = action == "allow",
                                onClick = { action = "allow" },
                                role = Role.RadioButton,
                            ),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        RadioButton(
                            selected = action == "allow",
                            onClick = null,
                            colors = RadioButtonDefaults.colors(
                                selectedColor = colors.neonGreen,
                                unselectedColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            ),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Izin Ver", color = colors.neonGreen)
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { if (domain.isNotBlank()) onCreate(domain.trim(), action) },
                enabled = domain.isNotBlank(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.neonCyan,
                    contentColor = Color.Black,
                    disabledContainerColor = colors.neonCyan.copy(alpha = 0.3f),
                    disabledContentColor = Color.Black.copy(alpha = 0.5f),
                ),
                shape = RoundedCornerShape(8.dp),
            ) {
                Text("Ekle", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f))
            }
        },
    )
}

@Composable
private fun AddBlocklistDialog(
    onDismiss: () -> Unit,
    onCreate: (name: String, url: String) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var name by remember { mutableStateOf("") }
    var url by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1025),
        shape = RoundedCornerShape(16.dp),
        title = {
            Text(
                text = "Blocklist Ekle",
                color = colors.neonCyan,
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Liste Adi", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    placeholder = { Text("Reklam Engelleme", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = cyberpunkTextFieldColors(),
                )
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("URL", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    placeholder = { Text("https://...", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = cyberpunkTextFieldColors(),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { if (name.isNotBlank() && url.isNotBlank()) onCreate(name.trim(), url.trim()) },
                enabled = name.isNotBlank() && url.isNotBlank(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.neonCyan,
                    contentColor = Color.Black,
                    disabledContainerColor = colors.neonCyan.copy(alpha = 0.3f),
                    disabledContentColor = Color.Black.copy(alpha = 0.5f),
                ),
                shape = RoundedCornerShape(8.dp),
            ) {
                Text("Ekle", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f))
            }
        },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddFirewallRuleDialog(
    onDismiss: () -> Unit,
    onCreate: (FirewallRuleCreateDto) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var name by remember { mutableStateOf("") }
    var direction by remember { mutableStateOf("inbound") }
    var protocol by remember { mutableStateOf("tcp") }
    var port by remember { mutableStateOf("") }
    var sourceIp by remember { mutableStateOf("") }
    var destIp by remember { mutableStateOf("") }
    var action by remember { mutableStateOf("drop") }

    // Dropdown states
    var directionExpanded by remember { mutableStateOf(false) }
    var protocolExpanded by remember { mutableStateOf(false) }
    var actionExpanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1025),
        shape = RoundedCornerShape(16.dp),
        title = {
            Text(
                text = "Firewall Kurali Ekle",
                color = colors.neonCyan,
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            Column(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Kural Adi", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = cyberpunkTextFieldColors(),
                )

                // Direction dropdown
                ExposedDropdownMenuBox(
                    expanded = directionExpanded,
                    onExpandedChange = { directionExpanded = it },
                ) {
                    OutlinedTextField(
                        value = if (direction == "inbound") "Gelen" else "Giden",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Yon", color = colors.neonCyan.copy(alpha = 0.7f)) },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = directionExpanded) },
                        modifier = Modifier
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable)
                            .fillMaxWidth(),
                        colors = cyberpunkTextFieldColors(),
                    )
                    ExposedDropdownMenu(
                        expanded = directionExpanded,
                        onDismissRequest = { directionExpanded = false },
                        containerColor = Color(0xFF1A1025),
                    ) {
                        DropdownMenuItem(
                            text = { Text("Gelen", color = colors.neonAmber) },
                            onClick = { direction = "inbound"; directionExpanded = false },
                        )
                        DropdownMenuItem(
                            text = { Text("Giden", color = colors.neonMagenta) },
                            onClick = { direction = "outbound"; directionExpanded = false },
                        )
                    }
                }

                // Protocol dropdown
                ExposedDropdownMenuBox(
                    expanded = protocolExpanded,
                    onExpandedChange = { protocolExpanded = it },
                ) {
                    OutlinedTextField(
                        value = protocol.uppercase(Locale.getDefault()),
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Protokol", color = colors.neonCyan.copy(alpha = 0.7f)) },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = protocolExpanded) },
                        modifier = Modifier
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable)
                            .fillMaxWidth(),
                        colors = cyberpunkTextFieldColors(),
                    )
                    ExposedDropdownMenu(
                        expanded = protocolExpanded,
                        onDismissRequest = { protocolExpanded = false },
                        containerColor = Color(0xFF1A1025),
                    ) {
                        listOf("tcp", "udp", "icmp").forEach { proto ->
                            DropdownMenuItem(
                                text = { Text(proto.uppercase(Locale.getDefault()), color = colors.neonCyan) },
                                onClick = { protocol = proto; protocolExpanded = false },
                            )
                        }
                    }
                }

                OutlinedTextField(
                    value = port,
                    onValueChange = { port = it },
                    label = { Text("Port (opsiyonel)", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    placeholder = { Text("80, 443", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = cyberpunkTextFieldColors(),
                )
                OutlinedTextField(
                    value = sourceIp,
                    onValueChange = { sourceIp = it },
                    label = { Text("Kaynak IP (opsiyonel)", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = cyberpunkTextFieldColors(),
                )
                OutlinedTextField(
                    value = destIp,
                    onValueChange = { destIp = it },
                    label = { Text("Hedef IP (opsiyonel)", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = cyberpunkTextFieldColors(),
                )

                // Action dropdown
                ExposedDropdownMenuBox(
                    expanded = actionExpanded,
                    onExpandedChange = { actionExpanded = it },
                ) {
                    OutlinedTextField(
                        value = when (action) {
                            "accept" -> "Kabul"
                            "drop" -> "Dusur"
                            "reject" -> "Reddet"
                            else -> action
                        },
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Islem", color = colors.neonCyan.copy(alpha = 0.7f)) },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = actionExpanded) },
                        modifier = Modifier
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable)
                            .fillMaxWidth(),
                        colors = cyberpunkTextFieldColors(),
                    )
                    ExposedDropdownMenu(
                        expanded = actionExpanded,
                        onDismissRequest = { actionExpanded = false },
                        containerColor = Color(0xFF1A1025),
                    ) {
                        DropdownMenuItem(
                            text = { Text("Kabul", color = colors.neonGreen) },
                            onClick = { action = "accept"; actionExpanded = false },
                        )
                        DropdownMenuItem(
                            text = { Text("Dusur", color = colors.neonRed) },
                            onClick = { action = "drop"; actionExpanded = false },
                        )
                        DropdownMenuItem(
                            text = { Text("Reddet", color = colors.neonAmber) },
                            onClick = { action = "reject"; actionExpanded = false },
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (name.isNotBlank()) {
                        onCreate(
                            FirewallRuleCreateDto(
                                name = name.trim(),
                                direction = direction,
                                protocol = protocol,
                                port = port.ifBlank { null },
                                sourceIp = sourceIp.ifBlank { null },
                                destIp = destIp.ifBlank { null },
                                action = action,
                                enabled = true,
                            )
                        )
                    }
                },
                enabled = name.isNotBlank(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.neonCyan,
                    contentColor = Color.Black,
                    disabledContainerColor = colors.neonCyan.copy(alpha = 0.3f),
                    disabledContentColor = Color.Black.copy(alpha = 0.5f),
                ),
                shape = RoundedCornerShape(8.dp),
            ) {
                Text("Ekle", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f))
            }
        },
    )
}

@Composable
private fun AddVpnPeerDialog(
    onDismiss: () -> Unit,
    onCreate: (name: String) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var name by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1025),
        shape = RoundedCornerShape(16.dp),
        title = {
            Text(
                text = "VPN Peer Ekle",
                color = colors.neonCyan,
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("Peer Adi", color = colors.neonCyan.copy(alpha = 0.7f)) },
                placeholder = { Text("telefon, laptop...", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = cyberpunkTextFieldColors(),
            )
        },
        confirmButton = {
            Button(
                onClick = { if (name.isNotBlank()) onCreate(name.trim()) },
                enabled = name.isNotBlank(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.neonCyan,
                    contentColor = Color.Black,
                    disabledContainerColor = colors.neonCyan.copy(alpha = 0.3f),
                    disabledContentColor = Color.Black.copy(alpha = 0.5f),
                ),
                shape = RoundedCornerShape(8.dp),
            ) {
                Text("Ekle", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f))
            }
        },
    )
}

@Composable
private fun VpnPeerConfigDialog(
    peerName: String,
    config: VpnPeerConfigDto?,
    onDismiss: () -> Unit,
) {
    val colors = CyberpunkTheme.colors

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1025),
        shape = RoundedCornerShape(16.dp),
        title = {
            Text(
                text = "$peerName - Config",
                color = colors.neonCyan,
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            if (config == null) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(100.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(color = colors.neonCyan)
                }
            } else {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    // QR Code
                    if (config.qrCodeBase64 != null) {
                        val bitmap = remember(config.qrCodeBase64) {
                            try {
                                val bytes = Base64.decode(config.qrCodeBase64, Base64.DEFAULT)
                                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                            } catch (_: Exception) {
                                null
                            }
                        }
                        if (bitmap != null) {
                            Image(
                                bitmap = bitmap.asImageBitmap(),
                                contentDescription = "QR Code",
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(220.dp)
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(Color.White)
                                    .padding(8.dp),
                            )
                        }
                    }

                    // Config text
                    Text(
                        text = "Yapilandirma",
                        style = MaterialTheme.typography.labelMedium,
                        color = colors.neonCyan,
                    )
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(
                                color = Color.Black.copy(alpha = 0.5f),
                                shape = RoundedCornerShape(8.dp),
                            )
                            .padding(12.dp),
                    ) {
                        Text(
                            text = config.configText,
                            style = MaterialTheme.typography.bodySmall.copy(
                                fontFamily = FontFamily.Monospace,
                                fontSize = 11.sp,
                            ),
                            color = colors.neonGreen,
                        )
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Kapat", color = colors.neonCyan)
            }
        },
    )
}

// ── Shared UI Components ────────────────────────────────────────────────────────

@Composable
private fun cyberpunkTextFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = CyberpunkTheme.colors.neonCyan,
    unfocusedBorderColor = CyberpunkTheme.colors.neonCyan.copy(alpha = 0.3f),
    cursorColor = CyberpunkTheme.colors.neonCyan,
    focusedTextColor = MaterialTheme.colorScheme.onSurface,
    unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
    focusedLabelColor = CyberpunkTheme.colors.neonCyan,
    unfocusedLabelColor = CyberpunkTheme.colors.neonCyan.copy(alpha = 0.5f),
)

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
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = formatCount(domain.count),
            style = MaterialTheme.typography.labelSmall,
            color = color,
        )
    }
}

@Composable
private fun NeonBadge(
    text: String,
    color: Color,
) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelSmall,
        color = color,
        fontWeight = FontWeight.Bold,
        modifier = Modifier
            .background(
                color = color.copy(alpha = 0.15f),
                shape = RoundedCornerShape(4.dp),
            )
            .padding(horizontal = 6.dp, vertical = 2.dp),
    )
}

@Composable
private fun FlowStateBadge(state: String) {
    val colors = CyberpunkTheme.colors
    val badgeColor = when (state.uppercase(Locale.getDefault())) {
        "ESTABLISHED" -> colors.neonGreen
        "TIME_WAIT", "CLOSE_WAIT", "LAST_ACK", "CLOSING" -> MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
        "SYN_SENT", "SYN_RECV" -> colors.neonAmber
        else -> MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
    }
    Text(
        text = state,
        style = MaterialTheme.typography.labelSmall,
        color = badgeColor,
        modifier = Modifier.padding(top = 2.dp),
    )
}

// ── Format Helpers ──────────────────────────────────────────────────────────────

private fun formatCount(count: Int): String {
    return when {
        count >= 1_000_000 -> String.format(Locale.getDefault(), "%.1fM", count / 1_000_000.0)
        count >= 1_000 -> String.format(Locale.getDefault(), "%.1fK", count / 1_000.0)
        else -> count.toString()
    }
}

private fun formatBytes(bytes: Long): String {
    return when {
        bytes >= 1_073_741_824 -> String.format(Locale.getDefault(), "%.1f GB", bytes / 1_073_741_824.0)
        bytes >= 1_048_576 -> String.format(Locale.getDefault(), "%.1f MB", bytes / 1_048_576.0)
        bytes >= 1_024 -> String.format(Locale.getDefault(), "%.1f KB", bytes / 1_024.0)
        else -> "$bytes B"
    }
}

private fun formatBps(bps: Long): String {
    return when {
        bps >= 1_000_000 -> String.format(Locale.getDefault(), "%.1f Mbps", bps / 1_000_000.0)
        bps >= 1_000 -> String.format(Locale.getDefault(), "%.1f Kbps", bps / 1_000.0)
        else -> "$bps bps"
    }
}
