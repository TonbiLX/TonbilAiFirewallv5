package com.tonbil.aifirewall.feature.traffic

import androidx.compose.animation.animateColorAsState
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
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowDownward
import androidx.compose.material.icons.outlined.ArrowUpward
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.data.remote.dto.LiveFlowDto
import com.tonbil.aifirewall.data.remote.dto.TrafficHistoryDto
import com.tonbil.aifirewall.data.remote.dto.TrafficHistoryItemDto
import com.tonbil.aifirewall.data.remote.dto.TrafficPerDeviceDto
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.GlassBg
import com.tonbil.aifirewall.ui.theme.GlassBorder
import com.tonbil.aifirewall.ui.theme.NeonAmber
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import kotlinx.coroutines.delay
import org.koin.androidx.compose.koinViewModel

private fun formatBytes(bytes: Long): String {
    if (bytes < 1024) return "$bytes B"
    val kb = bytes / 1024.0
    if (kb < 1024) return "%.1f KB".format(kb)
    val mb = kb / 1024.0
    if (mb < 1024) return "%.1f MB".format(mb)
    return "%.2f GB".format(mb / 1024.0)
}

private fun formatSpeed(bps: Double): String {
    if (bps < 1024) return "${bps.toLong()} B/s"
    val kbps = bps / 1024.0
    if (kbps < 1024) return "%.1f KB/s".format(kbps)
    val mbps = kbps / 1024.0
    return "%.1f MB/s".format(mbps)
}

private fun formatSpeed(bps: Long): String = formatSpeed(bps.toDouble())

private fun stateColor(state: String): Color = when (state.uppercase()) {
    "ESTABLISHED" -> NeonGreen
    "TIME_WAIT" -> TextSecondary
    "SYN_SENT" -> NeonAmber
    "CLOSE_WAIT" -> NeonRed
    else -> TextSecondary
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TrafficScreen(
    onBack: () -> Unit,
    viewModel: TrafficViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    val tabs = listOf("Canli", "Buyuk", "Gecmis", "Cihazlar")

    // Auto-refresh for live tab (5s) and large transfers tab (3s)
    LaunchedEffect(uiState.selectedTab) {
        while (true) {
            val delayMs = when (uiState.selectedTab) {
                0 -> 5000L
                1 -> 3000L
                else -> 30000L
            }
            delay(delayMs)
            when (uiState.selectedTab) {
                0 -> viewModel.loadLiveFlows()
                1 -> viewModel.loadLargeTransfers()
                2 -> viewModel.loadHistory(uiState.historyPage)
                3 -> viewModel.loadPerDevice()
            }
        }
    }

    Scaffold(
        containerColor = DarkBackground,
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Outlined.ShowChart,
                            contentDescription = null,
                            tint = NeonCyan,
                            modifier = Modifier.size(20.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            text = "Trafik Izleme",
                            color = TextPrimary,
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground),
                actions = {
                    IconButton(onClick = { viewModel.loadAll() }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = NeonCyan)
                    }
                },
            )
        },
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
        ) {
            // Stats bar
            uiState.flowStats?.let { stats ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(DarkSurface)
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceEvenly,
                ) {
                    StatChip(label = "Aktif", value = "${stats.totalActive}", color = NeonCyan)
                    StatChip(label = "Hedef", value = "${stats.uniqueDestinations}", color = NeonMagenta)
                    StatChip(label = "Cihaz", value = "${stats.trackedDevices}", color = NeonGreen)
                    StatChip(label = "In", value = formatBytes(stats.totalBytesIn), color = NeonAmber)
                    StatChip(label = "Out", value = formatBytes(stats.totalBytesOut), color = NeonCyan)
                }
            }

            // Tab row
            ScrollableTabRow(
                selectedTabIndex = uiState.selectedTab,
                containerColor = DarkSurface,
                contentColor = NeonCyan,
                edgePadding = 0.dp,
                indicator = { tabPositions ->
                    TabRowDefaults.SecondaryIndicator(
                        modifier = Modifier.tabIndicatorOffset(tabPositions[uiState.selectedTab]),
                        color = NeonCyan,
                    )
                },
            ) {
                tabs.forEachIndexed { idx, label ->
                    Tab(
                        selected = uiState.selectedTab == idx,
                        onClick = { viewModel.selectTab(idx) },
                        text = {
                            Text(
                                text = label,
                                color = if (uiState.selectedTab == idx) NeonCyan else TextSecondary,
                                fontSize = 13.sp,
                                fontWeight = if (uiState.selectedTab == idx) FontWeight.Bold else FontWeight.Normal,
                            )
                        },
                    )
                }
            }

            if (uiState.isLoading) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = NeonCyan)
                }
            } else if (uiState.error != null) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        text = "Hata: ${uiState.error}",
                        color = NeonRed,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(16.dp),
                    )
                }
            } else {
                when (uiState.selectedTab) {
                    0 -> LiveFlowsTab(flows = uiState.liveFlows)
                    1 -> LargeTransfersTab(flows = uiState.largeTransfers)
                    2 -> HistoryTab(
                        history = uiState.history,
                        currentPage = uiState.historyPage,
                        onPageChange = { viewModel.loadHistory(it) },
                    )
                    3 -> PerDeviceTab(devices = uiState.perDevice)
                }
            }
        }
    }
}

@Composable
private fun StatChip(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text = value, color = color, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Text(text = label, color = TextSecondary, fontSize = 9.sp)
    }
}

@Composable
private fun SortChipRow(
    options: List<Pair<String, String>>,
    selected: String,
    onSelect: (String) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .padding(horizontal = 8.dp, vertical = 4.dp),
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
private fun LiveFlowsTab(flows: List<LiveFlowDto>) {
    if (flows.isEmpty()) {
        EmptyState("Aktif baglanti yok")
        return
    }
    var sortKey by remember { mutableStateOf("speed") }
    val sortedFlows = remember(flows, sortKey) {
        when (sortKey) {
            "speed" -> flows.sortedByDescending { maxOf(it.bpsIn, it.bpsOut) }
            "bytes" -> flows.sortedByDescending { it.bytesIn + it.bytesOut }
            "protocol" -> flows.sortedBy { it.protocol }
            "name" -> flows.sortedBy { (it.hostname ?: it.srcIp).lowercase() }
            else -> flows
        }
    }
    Column(modifier = Modifier.fillMaxSize()) {
        SortChipRow(
            options = listOf("speed" to "Hiz \u2193", "bytes" to "Boyut \u2193", "protocol" to "Protokol", "name" to "Isim"),
            selected = sortKey,
            onSelect = { sortKey = it },
        )
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(4.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(8.dp),
        ) {
            items(sortedFlows, key = { it.flowId }) { flow ->
                LiveFlowCard(flow = flow)
            }
        }
    }
}

@Composable
private fun LiveFlowCard(flow: LiveFlowDto) {
    val isOutbound = flow.direction == "outbound"
    val directionColor = if (isOutbound) NeonCyan else NeonMagenta
    val stateCol = stateColor(flow.state ?: "")

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(GlassBg)
            .border(0.5.dp, GlassBorder, RoundedCornerShape(8.dp))
            .padding(10.dp),
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // Direction + protocol
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (isOutbound) Icons.Outlined.ArrowUpward else Icons.Outlined.ArrowDownward,
                        contentDescription = if (isOutbound) "Outbound" else "Inbound",
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

            // src -> dst
            val srcLabel = flow.hostname ?: flow.srcIp
            val dstLabel = flow.dstDomain ?: flow.dstIp
            Text(
                text = "$srcLabel:${flow.srcPort ?: "?"}  →  $dstLabel:${flow.dstPort ?: "?"}",
                color = TextSecondary,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(Modifier.height(4.dp))

            // Bytes + speed
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = "In: ${formatBytes(flow.bytesIn)}  Out: ${formatBytes(flow.bytesOut)}",
                    color = TextSecondary,
                    fontSize = 10.sp,
                )
                val speed = if (isOutbound) flow.bpsOut else flow.bpsIn
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
private fun LargeTransfersTab(flows: List<LiveFlowDto>) {
    if (flows.isEmpty()) {
        EmptyState("Buyuk transfer yok (>1MB)")
        return
    }
    var sortKey by remember { mutableStateOf("bytes") }
    val sortedFlows = remember(flows, sortKey) {
        when (sortKey) {
            "bytes" -> flows.sortedByDescending { it.bytesIn + it.bytesOut }
            "speed" -> flows.sortedByDescending { maxOf(it.bpsIn, it.bpsOut) }
            "name" -> flows.sortedBy { (it.dstDomain ?: it.dstIp).lowercase() }
            else -> flows
        }
    }
    Column(modifier = Modifier.fillMaxSize()) {
        SortChipRow(
            options = listOf("bytes" to "Boyut \u2193", "speed" to "Hiz \u2193", "name" to "Hedef"),
            selected = sortKey,
            onSelect = { sortKey = it },
        )
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(4.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(8.dp),
        ) {
            items(sortedFlows, key = { it.flowId }) { flow ->
                LargeTransferCard(flow = flow)
            }
        }
    }
}

@Composable
private fun LargeTransferCard(flow: LiveFlowDto) {
    val totalBytes = flow.bytesIn + flow.bytesOut
    val isHuge = totalBytes > 10 * 1024 * 1024L // >10MB
    val isOutbound = flow.direction == "outbound"
    val directionColor = if (isOutbound) NeonCyan else NeonMagenta

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
                color = if (isHuge) NeonMagenta.copy(alpha = if (isHuge) glowAlpha * 0.6f else 0.2f) else GlassBorder,
                shape = RoundedCornerShape(8.dp),
            )
            .padding(10.dp),
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (isOutbound) Icons.Outlined.ArrowUpward else Icons.Outlined.ArrowDownward,
                        contentDescription = null,
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
                Text(
                    text = formatBytes(totalBytes),
                    color = if (isHuge) NeonMagenta else NeonAmber,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                )
            }

            Spacer(Modifier.height(4.dp))

            val srcLabel = flow.hostname ?: flow.srcIp
            val dstLabel = flow.dstDomain ?: flow.dstIp
            Text(
                text = "$srcLabel  →  $dstLabel",
                color = TextSecondary,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )

            val badge = flow.appName ?: flow.serviceName
            if (badge != null) {
                Spacer(Modifier.height(2.dp))
                Text(text = badge, color = TextSecondary, fontSize = 9.sp)
            }
        }
    }
}

@Composable
private fun HistoryTab(
    history: TrafficHistoryDto?,
    currentPage: Int,
    onPageChange: (Int) -> Unit,
) {
    if (history == null || history.items.isEmpty()) {
        EmptyState("Trafik gecmisi yok")
        return
    }

    val totalPages = if (history.pageSize > 0) {
        (history.total + history.pageSize - 1) / history.pageSize
    } else 1

    var sortKey by remember { mutableStateOf("time") }
    val sortedItems = remember(history.items, sortKey) {
        when (sortKey) {
            "time" -> history.items // backend default: yeni önce
            "time_asc" -> history.items.reversed()
            "bytes" -> history.items.sortedByDescending { it.bytesTotal }
            "domain" -> history.items.sortedBy { (it.dstDomain ?: it.dstIp).lowercase() }
            else -> history.items
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        SortChipRow(
            options = listOf("time" to "Yeni Once", "time_asc" to "Eski Once", "bytes" to "Boyut \u2193", "domain" to "Hedef"),
            selected = sortKey,
            onSelect = { sortKey = it },
        )
        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(4.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(8.dp),
        ) {
            items(sortedItems) { item ->
                HistoryItemCard(item = item)
            }
        }

        // Pagination
        if (totalPages > 1) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(DarkSurface)
                    .padding(8.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TextButton(
                    onClick = { if (currentPage > 1) onPageChange(currentPage - 1) },
                    enabled = currentPage > 1,
                ) {
                    Text("<", color = if (currentPage > 1) NeonCyan else TextSecondary)
                }
                Text(
                    text = "$currentPage / $totalPages",
                    color = TextPrimary,
                    fontSize = 13.sp,
                    modifier = Modifier.padding(horizontal = 12.dp),
                )
                TextButton(
                    onClick = { if (currentPage < totalPages) onPageChange(currentPage + 1) },
                    enabled = currentPage < totalPages,
                ) {
                    Text(">", color = if (currentPage < totalPages) NeonCyan else TextSecondary)
                }
            }
        }
    }
}

@Composable
private fun HistoryItemCard(item: TrafficHistoryItemDto) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(GlassBg)
            .border(0.5.dp, GlassBorder, RoundedCornerShape(8.dp))
            .padding(10.dp),
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    text = item.protocol.uppercase(),
                    color = NeonCyan,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
                Text(
                    text = formatBytes(item.bytesTotal),
                    color = NeonAmber,
                    fontSize = 10.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
            Spacer(Modifier.height(3.dp))
            val dstLabel = item.dstDomain ?: item.dstIp
            Text(
                text = "${item.srcIp}  →  $dstLabel",
                color = TextSecondary,
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            val badge = item.appName ?: item.serviceName
            if (badge != null) {
                Spacer(Modifier.height(2.dp))
                Text(text = badge, color = TextSecondary, fontSize = 9.sp)
            }
            if (item.startedAt != null || item.endedAt != null) {
                Spacer(Modifier.height(3.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (item.startedAt != null) {
                        Text(text = "Baslangic: ${item.startedAt.take(19)}", color = TextSecondary, fontSize = 9.sp)
                    }
                    if (item.endedAt != null) {
                        Text(text = "Bitis: ${item.endedAt.take(19)}", color = TextSecondary, fontSize = 9.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun PerDeviceTab(devices: List<TrafficPerDeviceDto>) {
    if (devices.isEmpty()) {
        EmptyState("Cihaz trafik verisi yok")
        return
    }
    var sortKey by remember { mutableStateOf("speed") }
    val sortedDevices = remember(devices, sortKey) {
        when (sortKey) {
            "speed" -> devices.sortedByDescending { it.uploadSpeed + it.downloadSpeed }
            "upload" -> devices.sortedByDescending { it.totalUpload }
            "download" -> devices.sortedByDescending { it.totalDownload }
            "name" -> devices.sortedBy { it.hostname.ifBlank { it.ipAddress }.lowercase() }
            else -> devices
        }
    }
    Column(modifier = Modifier.fillMaxSize()) {
        SortChipRow(
            options = listOf("speed" to "Hiz \u2193", "upload" to "Upload \u2193", "download" to "Download \u2193", "name" to "Isim"),
            selected = sortKey,
            onSelect = { sortKey = it },
        )
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(8.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            // Header
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(DarkSurface)
                        .padding(horizontal = 12.dp, vertical = 6.dp),
                ) {
                    Text("Cihaz", color = TextSecondary, fontSize = 10.sp, modifier = Modifier.weight(2.5f))
                    Text("Upload", color = NeonCyan, fontSize = 10.sp, modifier = Modifier.weight(1.5f), textAlign = TextAlign.End)
                    Text("Download", color = NeonMagenta, fontSize = 10.sp, modifier = Modifier.weight(1.5f), textAlign = TextAlign.End)
                    Text("Hiz", color = NeonAmber, fontSize = 10.sp, modifier = Modifier.weight(1.5f), textAlign = TextAlign.End)
                }
            }
            items(sortedDevices) { dev ->
                PerDeviceRow(dev = dev)
            }
        }
    }
}

@Composable
private fun PerDeviceRow(dev: TrafficPerDeviceDto) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(6.dp))
            .background(GlassBg)
            .border(0.5.dp, GlassBorder, RoundedCornerShape(6.dp))
            .padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Column(modifier = Modifier.weight(2.5f)) {
                Text(
                    text = dev.hostname.ifBlank { "Cihaz #${dev.deviceId}" },
                    color = TextPrimary,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(text = dev.ipAddress, color = TextSecondary, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
            }
            Column(modifier = Modifier.weight(1.5f), horizontalAlignment = Alignment.End) {
                Text(text = formatBytes(dev.totalUpload), color = NeonCyan, fontSize = 10.sp)
                if (dev.uploadSpeed > 0) {
                    Text(text = formatSpeed(dev.uploadSpeed), color = NeonCyan.copy(alpha = 0.6f), fontSize = 9.sp)
                }
            }
            Column(modifier = Modifier.weight(1.5f), horizontalAlignment = Alignment.End) {
                Text(text = formatBytes(dev.totalDownload), color = NeonMagenta, fontSize = 10.sp)
                if (dev.downloadSpeed > 0) {
                    Text(text = formatSpeed(dev.downloadSpeed), color = NeonMagenta.copy(alpha = 0.6f), fontSize = 9.sp)
                }
            }
            Column(modifier = Modifier.weight(1.5f), horizontalAlignment = Alignment.End) {
                val totalSpeed = dev.uploadSpeed + dev.downloadSpeed
                Text(
                    text = if (totalSpeed > 0) formatSpeed(totalSpeed) else "-",
                    color = NeonAmber,
                    fontSize = 10.sp,
                )
            }
        }
    }
}

@Composable
private fun EmptyState(message: String) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = message,
            color = TextSecondary,
            fontSize = 14.sp,
            textAlign = TextAlign.Center,
        )
    }
}
