package com.tonbil.aifirewall.feature.devices

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
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
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.ArrowDownward
import androidx.compose.material.icons.outlined.ArrowUpward
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.ShieldMoon
import androidx.compose.material.icons.outlined.Speed
import androidx.compose.material.icons.outlined.Tv
import androidx.compose.material.icons.outlined.Block
import androidx.compose.material.icons.outlined.LockOpen
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Router
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.LiveTv
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.LiveFlowDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.feature.devices.DeviceBandwidthPoint
import com.tonbil.aifirewall.ui.theme.CyberpunkColors
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.GlassBg
import com.tonbil.aifirewall.ui.theme.GlassBorder
import com.tonbil.aifirewall.ui.theme.NeonAmber
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import com.tonbil.aifirewall.ui.theme.TextSecondary
import kotlinx.coroutines.delay
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceDetailScreen(
    deviceId: String,
    viewModel: DeviceDetailViewModel = koinViewModel { parametersOf(deviceId.toInt()) },
    onBack: () -> Unit,
    onNavigateToServices: (deviceId: Int, deviceName: String) -> Unit = { _, _ -> },
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val pullToRefreshState = rememberPullToRefreshState()
    val tabs = listOf("Genel", "Trafik", "DNS", "Yonetim")

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
                        1 -> TrafficTab(uiState, viewModel, colors)
                        2 -> DnsTab(uiState, colors)
                        3 -> ManagementTab(uiState, viewModel, colors, onNavigateToServices)
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
            GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonCyan) {
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
    viewModel: DeviceDetailViewModel,
    colors: CyberpunkColors,
) {
    // Auto-refresh live flows every 5 seconds
    LaunchedEffect(Unit) {
        while (true) {
            delay(5000L)
            viewModel.loadDeviceLiveFlows()
        }
    }

    var sortKey by remember { mutableStateOf("speed") }

    val sortedFlows = remember(uiState.liveFlows, sortKey) {
        when (sortKey) {
            "speed" -> uiState.liveFlows.sortedByDescending { maxOf(it.bpsIn, it.bpsOut) }
            "bytes" -> uiState.liveFlows.sortedByDescending { it.bytesIn + it.bytesOut }
            "protocol" -> uiState.liveFlows.sortedBy { it.protocol }
            "name" -> uiState.liveFlows.sortedBy { (it.dstDomain ?: it.dstIp).lowercase() }
            else -> uiState.liveFlows
        }
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        // Bandwidth chart card
        if (uiState.bandwidthHistory.size >= 2) {
            item {
                DeviceBandwidthChart(
                    history = uiState.bandwidthHistory,
                    currentUpload = uiState.bandwidth?.uploadBps ?: 0L,
                    currentDownload = uiState.bandwidth?.downloadBps ?: 0L,
                    colors = colors,
                )
            }
        }

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
                    InfoRow("Toplam Akis", "${summary.totalFlowsPeriod}")
                    InfoRow("Aktif Akis", "${summary.activeFlows}")
                    InfoRow("Gelen", formatBytes(summary.totalBytesReceived))
                    InfoRow("Giden", formatBytes(summary.totalBytesSent))
                } else {
                    Text(
                        text = "Trafik verisi yok",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                }
            }
        }

        // Live flows section header
        item {
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Canli Trafik Akislari",
                style = MaterialTheme.typography.titleMedium,
                color = colors.neonCyan,
                modifier = Modifier.padding(bottom = 4.dp),
            )
        }

        // Sort chips
        item {
            FlowSortChipRow(
                options = listOf(
                    "speed" to "Hiz \u2193",
                    "bytes" to "Boyut \u2193",
                    "protocol" to "Protokol",
                    "name" to "Hedef",
                ),
                selected = sortKey,
                onSelect = { sortKey = it },
            )
        }

        // Live flow cards or empty state
        if (sortedFlows.isEmpty()) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 24.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "Bu cihazin aktif baglantisi yok",
                        color = TextSecondary,
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center,
                    )
                }
            }
        } else {
            items(sortedFlows, key = { it.flowId }) { flow ->
                DeviceLiveFlowCard(flow = flow)
            }
        }

        // Top domains
        val topDomains = uiState.trafficSummary?.topDomains ?: emptyList()
        if (topDomains.isNotEmpty()) {
            item {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "En Cok Erisilen Domainler",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(bottom = 4.dp),
                )
            }
            items(topDomains) { domain ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = domain.domain,
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface,
                                maxLines = 1,
                            )
                            Text(
                                text = "${domain.flowCount} akis",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            )
                        }
                        Text(
                            text = formatBytes(domain.bytesTotal),
                            style = MaterialTheme.typography.bodyMedium,
                            color = colors.neonMagenta,
                        )
                    }
                }
            }
        }

        // Top ports
        val topPorts = uiState.trafficSummary?.topPorts ?: emptyList()
        if (topPorts.isNotEmpty()) {
            item {
                Text(
                    text = "En Cok Kullanilan Portlar",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonAmber,
                    modifier = Modifier.padding(bottom = 4.dp, top = 8.dp),
                )
            }
            items(topPorts) { port ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "${port.protocol}/${port.port}",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Text(
                                text = "${port.flowCount} akis",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            )
                        }
                        Text(
                            text = formatBytes(port.bytesTotal),
                            style = MaterialTheme.typography.bodyMedium,
                            color = colors.neonAmber,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun FlowSortChipRow(
    options: List<Pair<String, String>>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        options.forEach { (key, label) ->
            val isSelected = selected == key
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(16.dp))
                    .background(if (isSelected) NeonCyan.copy(alpha = 0.18f) else GlassBg)
                    .border(
                        0.5.dp,
                        if (isSelected) NeonCyan.copy(alpha = 0.6f) else GlassBorder,
                        RoundedCornerShape(16.dp),
                    )
                    .clickable { onSelect(key) }
                    .padding(horizontal = 10.dp, vertical = 5.dp),
            ) {
                Text(
                    text = label,
                    color = if (isSelected) NeonCyan else TextSecondary,
                    fontSize = 11.sp,
                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                )
            }
        }
    }
}

@Composable
private fun DeviceLiveFlowCard(flow: LiveFlowDto) {
    val isOutbound = flow.direction == "outbound"
    val directionColor = if (isOutbound) NeonCyan else NeonMagenta
    val stateCol = flowStateColor(flow.state ?: "")
    val totalBytes = flow.bytesIn + flow.bytesOut
    val isHuge = totalBytes > 10 * 1024 * 1024L // >10MB

    val infiniteTransition = rememberInfiniteTransition(label = "glow")
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "glowAlpha",
    )

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(if (isHuge) NeonMagenta.copy(alpha = 0.08f) else GlassBg)
            .border(
                width = if (isHuge) 1.dp else 0.5.dp,
                color = if (isHuge) NeonMagenta.copy(alpha = glowAlpha * 0.6f) else GlassBorder,
                shape = RoundedCornerShape(8.dp),
            )
            .padding(10.dp),
    ) {
        Column {
            // Top row: direction + protocol + app badge + state badge
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // Direction + protocol + app
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (isOutbound) Icons.Outlined.ArrowUpward else Icons.Outlined.ArrowDownward,
                        contentDescription = if (isOutbound) "Giden" else "Gelen",
                        tint = directionColor,
                        modifier = Modifier.size(14.dp),
                    )
                    Spacer(Modifier.width(4.dp))
                    Text(
                        text = flow.protocol.uppercase(),
                        color = directionColor,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.width(8.dp))
                    // App/service badge
                    val badgeText = flow.appName ?: flow.serviceName
                    if (badgeText != null) {
                        Box(
                            modifier = Modifier
                                .background(
                                    color = directionColor.copy(alpha = 0.15f),
                                    shape = RoundedCornerShape(4.dp),
                                )
                                .border(0.5.dp, directionColor.copy(alpha = 0.4f), RoundedCornerShape(4.dp))
                                .padding(horizontal = 6.dp, vertical = 1.dp),
                        ) {
                            Text(
                                text = badgeText,
                                color = directionColor,
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Medium,
                            )
                        }
                    }
                    // >10MB badge
                    if (isHuge) {
                        Spacer(Modifier.width(6.dp))
                        Box(
                            modifier = Modifier
                                .background(NeonMagenta.copy(alpha = 0.2f), RoundedCornerShape(4.dp))
                                .border(0.5.dp, NeonMagenta.copy(alpha = glowAlpha), RoundedCornerShape(4.dp))
                                .padding(horizontal = 6.dp, vertical = 1.dp),
                        ) {
                            Text(
                                text = ">10MB",
                                color = NeonMagenta,
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.alpha(glowAlpha),
                            )
                        }
                    }
                }
                // State badge
                Box(
                    modifier = Modifier
                        .background(stateCol.copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                        .padding(horizontal = 6.dp, vertical = 1.dp),
                ) {
                    Text(text = flow.state ?: "", color = stateCol, fontSize = 9.sp)
                }
            }

            Spacer(Modifier.height(4.dp))

            // Middle row: destination domain:port
            val dstLabel = flow.dstDomain ?: flow.dstIp
            Text(
                text = "$dstLabel:${flow.dstPort ?: "?"}",
                color = TextSecondary,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(Modifier.height(4.dp))

            // Bottom row: bytes left, speed right
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = "In: ${formatBytes(flow.bytesIn)}  Out: ${formatBytes(flow.bytesOut)}",
                    color = TextSecondary,
                    fontSize = 10.sp,
                )
                val speed = maxOf(flow.bpsIn, flow.bpsOut)
                if (speed > 0) {
                    Text(
                        text = formatSpeed(speed),
                        color = directionColor,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold,
                    )
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
private fun ManagementTab(
    uiState: DeviceDetailUiState,
    viewModel: DeviceDetailViewModel,
    colors: CyberpunkColors,
    onNavigateToServices: (deviceId: Int, deviceName: String) -> Unit,
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
            GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonCyan) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Outlined.Info,
                        contentDescription = null,
                        tint = colors.neonCyan,
                        modifier = Modifier.size(20.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Cihaz Bilgileri",
                        style = MaterialTheme.typography.titleMedium,
                        color = colors.neonCyan,
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("MAC Adresi", device.macAddress)
                InfoRow("IP Adresi", device.ipAddress ?: "-")
                if (!device.manufacturer.isNullOrBlank()) {
                    InfoRow("Uretici", device.manufacturer)
                }
                if (!device.deviceType.isNullOrBlank()) {
                    InfoRow("Cihaz Tipi", device.deviceType)
                }
                Spacer(modifier = Modifier.height(4.dp))
                // Risk score
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = "Risk Skoru",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        val riskColor = when (device.riskLevel) {
                            "critical" -> colors.neonRed
                            "high" -> colors.neonRed.copy(alpha = 0.8f)
                            "medium" -> colors.neonAmber
                            else -> colors.neonGreen
                        }
                        Icon(
                            imageVector = if (device.riskScore > 50) Icons.Outlined.Warning
                            else Icons.Outlined.CheckCircle,
                            contentDescription = null,
                            tint = riskColor,
                            modifier = Modifier.size(16.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = "${device.riskScore}/100 (${device.riskLevel})",
                            style = MaterialTheme.typography.bodySmall,
                            color = riskColor,
                        )
                    }
                }
            }
        }

        // Hostname editing
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Outlined.Edit,
                        contentDescription = null,
                        tint = colors.neonCyan,
                        modifier = Modifier.size(20.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Hostname",
                        style = MaterialTheme.typography.titleMedium,
                        color = colors.neonCyan,
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))

                var hostnameText by remember(device.hostname) {
                    mutableStateOf(device.hostname ?: "")
                }
                OutlinedTextField(
                    value = hostnameText,
                    onValueChange = { hostnameText = it },
                    label = { Text("Cihaz Adi") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonCyan,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedLabelColor = colors.neonCyan,
                        cursorColor = colors.neonCyan,
                    ),
                )
                Spacer(modifier = Modifier.height(8.dp))
                Button(
                    onClick = {
                        if (hostnameText.isNotBlank() && hostnameText != device.hostname) {
                            viewModel.updateHostname(hostnameText)
                        }
                    },
                    enabled = hostnameText.isNotBlank() && hostnameText != device.hostname,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = colors.neonCyan.copy(alpha = 0.2f),
                        contentColor = colors.neonCyan,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Kaydet")
                }
            }
        }

        // Bandwidth limit
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Outlined.Speed,
                        contentDescription = null,
                        tint = colors.neonAmber,
                        modifier = Modifier.size(20.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Bant Genisligi Limiti",
                        style = MaterialTheme.typography.titleMedium,
                        color = colors.neonAmber,
                    )
                }
                Spacer(modifier = Modifier.height(8.dp))

                var sliderValue by remember(device.bandwidthLimitMbps) {
                    mutableFloatStateOf(device.bandwidthLimitMbps ?: 0f)
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = if (sliderValue == 0f) "Limitsiz" else "${sliderValue.toInt()} Mbps",
                        style = MaterialTheme.typography.titleMedium,
                        color = if (sliderValue == 0f) colors.neonGreen else colors.neonAmber,
                    )
                    Text(
                        text = "0 = Limitsiz",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                    )
                }
                Slider(
                    value = sliderValue,
                    onValueChange = { sliderValue = it },
                    valueRange = 0f..100f,
                    steps = 19, // 0, 5, 10, ... 100
                    modifier = Modifier.fillMaxWidth(),
                    colors = SliderDefaults.colors(
                        thumbColor = colors.neonAmber,
                        activeTrackColor = colors.neonAmber,
                        inactiveTrackColor = colors.glassBorder,
                    ),
                )
                Spacer(modifier = Modifier.height(4.dp))
                Button(
                    onClick = {
                        viewModel.updateBandwidth(if (sliderValue == 0f) null else sliderValue)
                    },
                    enabled = sliderValue != (device.bandwidthLimitMbps ?: 0f),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = colors.neonAmber.copy(alpha = 0.2f),
                        contentColor = colors.neonAmber,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Uygula")
                }
            }
        }

        // IPTV toggle
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Outlined.LiveTv,
                            contentDescription = null,
                            tint = if (device.isIptv) colors.neonGreen else
                                MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            modifier = Modifier.size(20.dp),
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Column {
                            Text(
                                text = "IPTV Modu",
                                style = MaterialTheme.typography.titleMedium,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Text(
                                text = if (device.isIptv) "Aktif — DNS filtreleme bypass" else "Devre disi",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            )
                        }
                    }
                    Switch(
                        checked = device.isIptv,
                        onCheckedChange = { viewModel.toggleIptv() },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = colors.neonGreen,
                            checkedTrackColor = colors.neonGreen.copy(alpha = 0.3f),
                        ),
                    )
                }
            }
        }

        // Service blocking button
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = {
                        onNavigateToServices(
                            device.id,
                            device.hostname ?: "Bilinmeyen Cihaz",
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = colors.neonMagenta,
                    ),
                ) {
                    Icon(
                        imageVector = Icons.Outlined.Router,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Servis Engelleme Yonet")
                }
            }
        }

        // Block/Unblock button
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = { viewModel.toggleBlock() },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (device.isBlocked) colors.neonGreen.copy(alpha = 0.2f)
                        else colors.neonRed.copy(alpha = 0.2f),
                        contentColor = if (device.isBlocked) colors.neonGreen else colors.neonRed,
                    ),
                ) {
                    Icon(
                        imageVector = if (device.isBlocked) Icons.Outlined.LockOpen
                        else Icons.Outlined.Block,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (device.isBlocked) "Engeli Kaldir" else "Cihazi Engelle",
                    )
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

@Composable
private fun DeviceBandwidthChart(
    history: List<DeviceBandwidthPoint>,
    currentUpload: Long,
    currentDownload: Long,
    colors: CyberpunkColors,
) {
    val cyanColor = Color(0xFF00F0FF)
    val magentaColor = Color(0xFFFF00E5)

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = "Bant Genisligi",
            style = MaterialTheme.typography.titleMedium,
            color = colors.neonCyan,
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "${formatBps(currentDownload)} / ${formatBps(currentUpload)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Spacer(modifier = Modifier.height(8.dp))

        val downloadValues = remember(history) { history.map { it.downloadBps.toFloat() } }
        val uploadValues = remember(history) { history.map { it.uploadBps.toFloat() } }
        val maxVal = remember(history) {
            (downloadValues + uploadValues).maxOrNull()?.coerceAtLeast(1f) ?: 1f
        }

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp),
        ) {
            val w = size.width
            val h = size.height
            val padding = 4f
            val chartH = h - padding * 2
            val stepX = w / (downloadValues.size - 1).coerceAtLeast(1)

            fun drawLineSeries(values: List<Float>, color: Color) {
                if (values.size < 2) return
                val path = Path()
                values.forEachIndexed { i, v ->
                    val x = i * stepX
                    val y = padding + chartH * (1f - v / maxVal)
                    if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
                }
                drawPath(path, color, style = Stroke(width = 3f, cap = StrokeCap.Round))
            }

            // Grid lines
            for (i in 0..4) {
                val y = padding + chartH * i / 4f
                drawLine(
                    start = Offset(0f, y),
                    end = Offset(w, y),
                    color = Color.White.copy(alpha = 0.06f),
                    strokeWidth = 1f,
                )
            }

            drawLineSeries(uploadValues, cyanColor)      // RX = cyan (upload'a eşlenmiş)
            drawLineSeries(downloadValues, magentaColor) // TX = magenta (download'a eşlenmiş)
        }

        Spacer(modifier = Modifier.height(6.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(cyanColor),
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "Upload",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            )
            Spacer(modifier = Modifier.width(16.dp))
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(magentaColor),
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = "Download",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
            )
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

private fun formatBytes(bytes: Long): String {
    return when {
        bytes >= 1_073_741_824 -> String.format("%.1f GB", bytes / 1_073_741_824.0)
        bytes >= 1_048_576 -> String.format("%.1f MB", bytes / 1_048_576.0)
        bytes >= 1_024 -> String.format("%.1f KB", bytes / 1_024.0)
        else -> "$bytes B"
    }
}

private fun formatSpeed(bps: Double): String {
    if (bps < 1024) return "${bps.toLong()} B/s"
    val kbps = bps / 1024.0
    if (kbps < 1024) return "%.1f KB/s".format(kbps)
    val mbps = kbps / 1024.0
    return "%.1f MB/s".format(mbps)
}

private fun flowStateColor(state: String): Color = when (state.uppercase()) {
    "ESTABLISHED" -> NeonGreen
    "TIME_WAIT" -> TextSecondary
    "SYN_SENT" -> NeonAmber
    "CLOSE_WAIT" -> NeonRed
    else -> TextSecondary
}

private fun formatDuration(seconds: Int): String {
    return when {
        seconds >= 3600 -> "${seconds / 3600}s ${(seconds % 3600) / 60}dk"
        seconds >= 60 -> "${seconds / 60}dk ${seconds % 60}sn"
        else -> "${seconds}sn"
    }
}
