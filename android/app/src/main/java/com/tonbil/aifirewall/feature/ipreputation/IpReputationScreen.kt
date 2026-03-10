package com.tonbil.aifirewall.feature.ipreputation

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.ArrowDownward
import androidx.compose.material.icons.outlined.ArrowUpward
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.Error
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Save
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.pullToRefresh
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistConfigDto
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.IpRepBlacklistDto
import com.tonbil.aifirewall.data.remote.dto.IpRepCheckDto
import com.tonbil.aifirewall.data.remote.dto.IpRepConfigDto
import com.tonbil.aifirewall.data.remote.dto.IpRepConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.IpRepSummaryDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

private val TAB_TITLES = listOf("Ozet", "IP'ler", "Kara Liste", "Ayarlar")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IpReputationScreen(
    onBack: () -> Unit,
    viewModel: IpReputationViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val snackbarHostState = remember { SnackbarHostState() }
    val pullToRefreshState = rememberPullToRefreshState()

    LaunchedEffect(uiState.actionMessage) {
        uiState.actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "IP Reputation",
                        color = colors.neonMagenta,
                        style = MaterialTheme.typography.titleLarge,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.Outlined.ArrowBack,
                            contentDescription = "Geri",
                            tint = colors.neonMagenta,
                        )
                    }
                },
                actions = {
                    if (uiState.isActionLoading) {
                        CircularProgressIndicator(
                            color = colors.neonMagenta,
                            modifier = Modifier.size(20.dp),
                        )
                        Spacer(Modifier.width(12.dp))
                    }
                    IconButton(onClick = { viewModel.refresh() }) {
                        Icon(
                            imageVector = Icons.Outlined.Refresh,
                            contentDescription = "Yenile",
                            tint = colors.neonMagenta,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                ),
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) },
        containerColor = MaterialTheme.colorScheme.background,
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
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
                        CircularProgressIndicator(color = colors.neonMagenta)
                    }
                }
                uiState.error != null -> {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        contentAlignment = Alignment.Center,
                    ) {
                        GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonRed) {
                            Text(
                                text = uiState.error ?: "",
                                color = colors.neonRed,
                                style = MaterialTheme.typography.bodyLarge,
                            )
                            Spacer(Modifier.height(12.dp))
                            Button(
                                onClick = { viewModel.refresh() },
                                colors = ButtonDefaults.buttonColors(containerColor = colors.neonMagenta),
                            ) {
                                Icon(Icons.Outlined.Refresh, null, modifier = Modifier.size(18.dp))
                                Spacer(Modifier.width(8.dp))
                                Text("Tekrar Dene")
                            }
                        }
                    }
                }
                else -> {
                    Column(modifier = Modifier.fillMaxSize()) {
                        // Tab row
                        TabRow(
                            selectedTabIndex = uiState.selectedTab,
                            containerColor = MaterialTheme.colorScheme.background,
                            contentColor = colors.neonMagenta,
                            indicator = { tabPositions ->
                                TabRowDefaults.SecondaryIndicator(
                                    modifier = Modifier.tabIndicatorOffset(tabPositions[uiState.selectedTab]),
                                    color = colors.neonMagenta,
                                )
                            },
                        ) {
                            TAB_TITLES.forEachIndexed { index, title ->
                                Tab(
                                    selected = uiState.selectedTab == index,
                                    onClick = { viewModel.selectTab(index) },
                                    text = {
                                        Text(
                                            text = title,
                                            style = MaterialTheme.typography.labelMedium,
                                            color = if (uiState.selectedTab == index) colors.neonMagenta
                                            else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                        )
                                    },
                                )
                            }
                        }

                        when (uiState.selectedTab) {
                            0 -> SummaryTab(summary = uiState.summary)
                            1 -> IpsTab(
                                ips = uiState.ips,
                                sortField = uiState.ipSortField,
                                sortAscending = uiState.ipSortAscending,
                                onSortBy = { viewModel.sortIpBy(it) },
                            )
                            2 -> BlacklistTab(
                                blacklist = uiState.blacklist,
                                blacklistConfig = uiState.blacklistConfig,
                                isFetching = uiState.isBlacklistFetching,
                                onFetch = { viewModel.fetchBlacklist() },
                                onUpdateConfig = { viewModel.updateBlacklistConfig(it) },
                            )
                            3 -> SettingsTab(
                                config = uiState.config,
                                onSave = { viewModel.updateConfig(it) },
                                onClearCache = { viewModel.clearCache() },
                                onTest = { viewModel.testApi() },
                            )
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
}

// ============================================================
// Tab 1: Summary
// ============================================================

@Composable
private fun SummaryTab(summary: IpRepSummaryDto?) {
    val colors = CyberpunkTheme.colors

    if (summary == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = colors.neonMagenta)
        }
        return
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Text(
                text = "Reputation Ozeti",
                style = MaterialTheme.typography.titleMedium,
                color = colors.neonMagenta,
            )
        }

        item {
            // Primary stats grid
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    SummaryStatCard(
                        label = "Toplam Kontrol",
                        value = summary.totalChecked.toString(),
                        color = colors.neonCyan,
                        modifier = Modifier.weight(1f),
                    )
                    SummaryStatCard(
                        label = "Temiz",
                        value = summary.totalClean.toString(),
                        color = colors.neonGreen,
                        icon = Icons.Outlined.CheckCircle,
                        modifier = Modifier.weight(1f),
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    SummaryStatCard(
                        label = "Supheli",
                        value = summary.totalSuspicious.toString(),
                        color = colors.neonAmber,
                        icon = Icons.Outlined.Warning,
                        modifier = Modifier.weight(1f),
                    )
                    SummaryStatCard(
                        label = "Kritik",
                        value = summary.totalCritical.toString(),
                        color = colors.neonRed,
                        icon = Icons.Outlined.Error,
                        modifier = Modifier.weight(1f),
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    SummaryStatCard(
                        label = "Engellenen",
                        value = summary.totalBlocked.toString(),
                        color = colors.neonRed,
                        icon = Icons.Outlined.Shield,
                        modifier = Modifier.weight(1f),
                    )
                    SummaryStatCard(
                        label = "API Kota",
                        value = summary.apiQuotaRemaining?.toString() ?: "—",
                        color = colors.neonMagenta,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }

        if (!summary.lastCheck.isNullOrBlank()) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Son Kontrol",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                    Text(
                        text = summary.lastCheck,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            }
        }

        // Score distribution bar
        if (summary.totalChecked > 0) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Skor Dagilimi",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                    Spacer(Modifier.height(8.dp))
                    ScoreDistributionBar(
                        clean = summary.totalClean,
                        suspicious = summary.totalSuspicious,
                        critical = summary.totalCritical,
                        total = summary.totalChecked,
                    )
                    Spacer(Modifier.height(6.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly,
                    ) {
                        LegendItem(color = colors.neonGreen, label = "Temiz (0-49)")
                        LegendItem(color = colors.neonAmber, label = "Supheli (50-79)")
                        LegendItem(color = colors.neonRed, label = "Kritik (80+)")
                    }
                }
            }
        }
    }
}

@Composable
private fun SummaryStatCard(
    label: String,
    value: String,
    color: Color,
    icon: androidx.compose.ui.graphics.vector.ImageVector? = null,
    modifier: Modifier = Modifier,
) {
    GlassCard(modifier = modifier, glowColor = color.copy(alpha = 0.2f)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            icon?.let {
                Icon(imageVector = it, contentDescription = null, tint = color, modifier = Modifier.size(18.dp))
            }
            Column {
                Text(text = value, style = MaterialTheme.typography.headlineSmall, color = color)
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                )
            }
        }
    }
}

@Composable
private fun ScoreDistributionBar(
    clean: Int,
    suspicious: Int,
    critical: Int,
    total: Int,
) {
    val colors = CyberpunkTheme.colors
    val cleanRatio = if (total > 0) clean.toFloat() / total else 0f
    val suspiciousRatio = if (total > 0) suspicious.toFloat() / total else 0f
    val criticalRatio = if (total > 0) critical.toFloat() / total else 0f

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(12.dp)
            .clip(RoundedCornerShape(6.dp)),
    ) {
        if (cleanRatio > 0f) {
            Box(
                modifier = Modifier
                    .weight(cleanRatio)
                    .fillMaxSize()
                    .background(colors.neonGreen),
            )
        }
        if (suspiciousRatio > 0f) {
            Box(
                modifier = Modifier
                    .weight(suspiciousRatio)
                    .fillMaxSize()
                    .background(colors.neonAmber),
            )
        }
        if (criticalRatio > 0f) {
            Box(
                modifier = Modifier
                    .weight(criticalRatio)
                    .fillMaxSize()
                    .background(colors.neonRed),
            )
        }
        // Fill remainder if totals don't add up
        val remainder = 1f - cleanRatio - suspiciousRatio - criticalRatio
        if (remainder > 0f) {
            Box(
                modifier = Modifier
                    .weight(remainder)
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.1f)),
            )
        }
    }
}

@Composable
private fun LegendItem(color: Color, label: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(color),
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
        )
    }
}

// ============================================================
// Tab 2: IP list
// ============================================================

@Composable
private fun IpsTab(
    ips: List<IpRepCheckDto>,
    sortField: IpSortField,
    sortAscending: Boolean,
    onSortBy: (IpSortField) -> Unit,
) {
    val colors = CyberpunkTheme.colors

    if (ips.isEmpty()) {
        Box(modifier = Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Icon(
                    imageVector = Icons.Outlined.Shield,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f),
                    modifier = Modifier.size(48.dp),
                )
                Text(
                    text = "Henuz kontrol edilen IP yok",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                )
            }
        }
        return
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // Sort header row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "Sirala:",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
            )
            listOf(
                IpSortField.SCORE to "Skor",
                IpSortField.IP to "IP",
                IpSortField.COUNTRY to "Ulke",
                IpSortField.LAST_CHECKED to "Tarih",
            ).forEach { (field, label) ->
                SortChip(
                    label = label,
                    isActive = sortField == field,
                    ascending = sortAscending,
                    onClick = { onSortBy(field) },
                )
            }
        }

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(items = ips, key = { it.ipAddress }) { ip ->
                IpRepCheckCard(ip = ip)
            }
        }
    }
}

@Composable
private fun SortChip(
    label: String,
    isActive: Boolean,
    ascending: Boolean,
    onClick: () -> Unit,
) {
    val colors = CyberpunkTheme.colors
    val chipColor = if (isActive) colors.neonMagenta else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .background(if (isActive) colors.neonMagenta.copy(alpha = 0.15f) else Color.Transparent)
            .border(1.dp, chipColor.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
            .padding(horizontal = 10.dp, vertical = 4.dp),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Text(text = label, style = MaterialTheme.typography.labelSmall, color = chipColor)
            if (isActive) {
                Icon(
                    imageVector = if (ascending) Icons.Outlined.ArrowUpward else Icons.Outlined.ArrowDownward,
                    contentDescription = null,
                    tint = chipColor,
                    modifier = Modifier.size(10.dp),
                )
            }
        }
    }
}

@Composable
private fun IpRepCheckCard(ip: IpRepCheckDto) {
    val colors = CyberpunkTheme.colors

    val scoreColor = when {
        ip.score >= 80 -> colors.neonRed
        ip.score >= 50 -> colors.neonAmber
        else -> colors.neonGreen
    }

    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = scoreColor.copy(alpha = 0.15f)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Score badge
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(scoreColor.copy(alpha = 0.15f))
                    .border(1.dp, scoreColor.copy(alpha = 0.5f), RoundedCornerShape(8.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = ip.score.toString(),
                    style = MaterialTheme.typography.titleMedium,
                    color = scoreColor,
                )
            }

            Spacer(Modifier.width(12.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(
                        text = ip.ipAddress,
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    // Country flag
                    ip.countryCode?.let { code ->
                        Text(text = countryCodeToFlag(code), style = MaterialTheme.typography.bodyMedium)
                    }
                    // TOR badge
                    if (ip.isTor) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(colors.neonMagenta.copy(alpha = 0.2f))
                                .border(1.dp, colors.neonMagenta.copy(alpha = 0.5f), RoundedCornerShape(4.dp))
                                .padding(horizontal = 5.dp, vertical = 1.dp),
                        ) {
                            Text("TOR", style = MaterialTheme.typography.labelSmall, color = colors.neonMagenta)
                        }
                    }
                    // Blocked badge
                    if (ip.blocked) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(colors.neonRed.copy(alpha = 0.2f))
                                .border(1.dp, colors.neonRed.copy(alpha = 0.5f), RoundedCornerShape(4.dp))
                                .padding(horizontal = 5.dp, vertical = 1.dp),
                        ) {
                            Text("Engelli", style = MaterialTheme.typography.labelSmall, color = colors.neonRed)
                        }
                    }
                }

                // Country + ISP
                val infoText = listOfNotNull(ip.countryName, ip.isp).joinToString(" • ")
                if (infoText.isNotBlank()) {
                    Text(
                        text = infoText,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.55f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }

                // Reports + last reported
                if (ip.totalReports > 0) {
                    Text(
                        text = "${ip.totalReports} rapor" + (ip.lastReported?.let { " • $it" } ?: ""),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                    )
                }
            }
        }
    }
}

// ============================================================
// Tab 3: Blacklist
// ============================================================

@Composable
private fun BlacklistTab(
    blacklist: List<IpRepBlacklistDto>,
    blacklistConfig: IpRepBlacklistConfigDto?,
    isFetching: Boolean,
    onFetch: () -> Unit,
    onUpdateConfig: (IpRepBlacklistConfigUpdateDto) -> Unit,
) {
    val colors = CyberpunkTheme.colors

    Column(modifier = Modifier.fillMaxSize()) {
        // Blacklist info + fetch button
        blacklistConfig?.let { cfg ->
            GlassCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "AbuseIPDB Kara Listesi",
                            style = MaterialTheme.typography.titleSmall,
                            color = colors.neonMagenta,
                        )
                        Text(
                            text = "${cfg.totalEntries} kayit",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                        )
                        if (!cfg.lastFetch.isNullOrBlank()) {
                            Text(
                                text = "Son guncelleme: ${cfg.lastFetch}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                            )
                        }
                    }
                    // Enabled toggle
                    Column(horizontalAlignment = Alignment.End) {
                        Switch(
                            checked = cfg.enabled,
                            onCheckedChange = { enabled ->
                                onUpdateConfig(IpRepBlacklistConfigUpdateDto(enabled = enabled))
                            },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = colors.neonMagenta,
                                checkedTrackColor = colors.neonMagenta.copy(alpha = 0.3f),
                            ),
                        )
                        Text(
                            text = if (cfg.enabled) "Aktif" else "Pasif",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (cfg.enabled) colors.neonGreen else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                        )
                    }
                }

                Spacer(Modifier.height(8.dp))

                Button(
                    onClick = onFetch,
                    enabled = !isFetching,
                    colors = ButtonDefaults.buttonColors(containerColor = colors.neonMagenta),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (isFetching) {
                        CircularProgressIndicator(
                            color = MaterialTheme.colorScheme.background,
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp,
                        )
                    } else {
                        Icon(Icons.Outlined.Download, null, modifier = Modifier.size(16.dp))
                    }
                    Spacer(Modifier.width(8.dp))
                    Text(if (isFetching) "Guncelleniyor..." else "Listeyi Guncelle")
                }
            }
        }

        // Blacklist entries
        if (blacklist.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize().padding(32.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "Kara listede giris yok",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                item {
                    Text(
                        text = "${blacklist.size} giris",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        modifier = Modifier.padding(vertical = 4.dp),
                    )
                }
                items(items = blacklist, key = { it.ipAddress }) { entry ->
                    BlacklistEntryCard(entry = entry)
                }
            }
        }
    }
}

@Composable
private fun BlacklistEntryCard(entry: IpRepBlacklistDto) {
    val colors = CyberpunkTheme.colors
    val scoreColor = when {
        entry.score >= 80 -> colors.neonRed
        entry.score >= 50 -> colors.neonAmber
        else -> colors.neonGreen
    }

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            // Score dot
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(scoreColor),
            )
            Text(
                text = entry.ipAddress,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.weight(1f),
            )
            entry.countryCode?.let { code ->
                Text(text = countryCodeToFlag(code), style = MaterialTheme.typography.bodySmall)
            }
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(scoreColor.copy(alpha = 0.15f))
                    .padding(horizontal = 6.dp, vertical = 2.dp),
            ) {
                Text(
                    text = entry.score.toString(),
                    style = MaterialTheme.typography.labelSmall,
                    color = scoreColor,
                )
            }
        }
    }
}

// ============================================================
// Tab 4: Settings
// ============================================================

@Composable
private fun SettingsTab(
    config: IpRepConfigDto?,
    onSave: (IpRepConfigUpdateDto) -> Unit,
    onClearCache: () -> Unit,
    onTest: () -> Unit,
) {
    val colors = CyberpunkTheme.colors

    if (config == null) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator(color = colors.neonMagenta)
        }
        return
    }

    var enabled by rememberSaveable { mutableStateOf(config.enabled) }
    var apiKey by rememberSaveable { mutableStateOf(config.apiKey) }
    var apiKeyVisible by remember { mutableStateOf(false) }
    var minScore by rememberSaveable { mutableFloatStateOf(config.minScore.toFloat()) }
    var checkInterval by rememberSaveable { mutableStateOf(config.checkIntervalMinutes.toString()) }
    var maxPerCycle by rememberSaveable { mutableStateOf(config.maxIpsPerCycle.toString()) }
    var autoBlock by rememberSaveable { mutableStateOf(config.autoBlock) }
    var blockDuration by rememberSaveable { mutableStateOf(config.blockDuration ?: "24h") }

    val textFieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.neonMagenta,
        unfocusedBorderColor = colors.glassBorder,
        focusedLabelColor = colors.neonMagenta,
        unfocusedLabelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
        cursorColor = colors.neonMagenta,
        focusedTextColor = MaterialTheme.colorScheme.onSurface,
        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        // Enable / Disable toggle
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "IP Reputation Aktif",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    Text(
                        text = "Gelen baglantilarin IP reputation skorlarini kontrol eder",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                }
                Switch(
                    checked = enabled,
                    onCheckedChange = { enabled = it },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = colors.neonMagenta,
                        checkedTrackColor = colors.neonMagenta.copy(alpha = 0.3f),
                    ),
                )
            }
        }

        // API Key field
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = "AbuseIPDB API Anahtari",
                style = MaterialTheme.typography.labelMedium,
                color = colors.neonMagenta,
            )
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = apiKey,
                onValueChange = { apiKey = it },
                label = { Text("API Key") },
                singleLine = true,
                visualTransformation = if (apiKeyVisible) VisualTransformation.None else PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                trailingIcon = {
                    TextButton(onClick = { apiKeyVisible = !apiKeyVisible }) {
                        Text(
                            text = if (apiKeyVisible) "Gizle" else "Goster",
                            style = MaterialTheme.typography.labelSmall,
                            color = colors.neonMagenta,
                        )
                    }
                },
                colors = textFieldColors,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        // Min score slider
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = "Minimum Engelleme Skoru: ${minScore.toInt()}",
                style = MaterialTheme.typography.labelMedium,
                color = colors.neonMagenta,
            )
            Text(
                text = "Bu skorun uzerindeki IP'ler otomatik engellenir (0-100)",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
            )
            Spacer(Modifier.height(4.dp))
            Slider(
                value = minScore,
                onValueChange = { minScore = it },
                valueRange = 0f..100f,
                steps = 9,
                colors = SliderDefaults.colors(
                    thumbColor = when {
                        minScore >= 80 -> colors.neonRed
                        minScore >= 50 -> colors.neonAmber
                        else -> colors.neonGreen
                    },
                    activeTrackColor = when {
                        minScore >= 80 -> colors.neonRed
                        minScore >= 50 -> colors.neonAmber
                        else -> colors.neonGreen
                    },
                ),
            )
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("0", style = MaterialTheme.typography.labelSmall, color = colors.neonGreen)
                Text("50", style = MaterialTheme.typography.labelSmall, color = colors.neonAmber)
                Text("100", style = MaterialTheme.typography.labelSmall, color = colors.neonRed)
            }
        }

        // Interval + max per cycle
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Text(
                text = "Kontrol Parametreleri",
                style = MaterialTheme.typography.labelMedium,
                color = colors.neonMagenta,
            )
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = checkInterval,
                onValueChange = { checkInterval = it },
                label = { Text("Kontrol Araligi (dakika)") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                colors = textFieldColors,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = maxPerCycle,
                onValueChange = { maxPerCycle = it },
                label = { Text("Dongu Basi Max IP Sayisi") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                colors = textFieldColors,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        // Auto block + block duration
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Otomatik Engelleme",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    Text(
                        text = "Kritik IP'leri otomatik engelle",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                }
                Switch(
                    checked = autoBlock,
                    onCheckedChange = { autoBlock = it },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = colors.neonRed,
                        checkedTrackColor = colors.neonRed.copy(alpha = 0.3f),
                    ),
                )
            }
            if (autoBlock) {
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = blockDuration,
                    onValueChange = { blockDuration = it },
                    label = { Text("Engelleme Suresi (ornek: 24h, 7d, permanent)") },
                    singleLine = true,
                    colors = textFieldColors,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }

        // Action buttons
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Button(
                onClick = {
                    onSave(
                        IpRepConfigUpdateDto(
                            enabled = enabled,
                            apiKey = apiKey.takeIf { it.isNotBlank() },
                            minScore = minScore.toInt(),
                            checkIntervalMinutes = checkInterval.toIntOrNull(),
                            maxIpsPerCycle = maxPerCycle.toIntOrNull(),
                            autoBlock = autoBlock,
                            blockDuration = blockDuration.takeIf { it.isNotBlank() },
                        )
                    )
                },
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonMagenta),
                modifier = Modifier.weight(1f),
            ) {
                Icon(Icons.Outlined.Save, null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(6.dp))
                Text("Kaydet")
            }

            Button(
                onClick = onTest,
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
                modifier = Modifier.weight(1f),
            ) {
                Icon(Icons.Outlined.CheckCircle, null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(6.dp))
                Text("Test Et")
            }
        }

        // Cache clear
        GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonRed.copy(alpha = 0.2f)) {
            Text(
                text = "Tehlikeli Islemler",
                style = MaterialTheme.typography.labelMedium,
                color = colors.neonRed,
            )
            Spacer(Modifier.height(8.dp))
            Button(
                onClick = onClearCache,
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonRed.copy(alpha = 0.2f)),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Outlined.Delete, null, modifier = Modifier.size(16.dp), tint = colors.neonRed)
                Spacer(Modifier.width(8.dp))
                Text("Cache Temizle", color = colors.neonRed)
            }
        }

        Spacer(Modifier.height(80.dp))
    }
}

// ============================================================
// Country code → flag emoji helper
// ============================================================

private fun countryCodeToFlag(countryCode: String): String {
    if (countryCode.length != 2) return ""
    val base = 0x1F1E6 - 'A'.code
    return String(
        intArrayOf(
            base + countryCode[0].uppercaseChar().code,
            base + countryCode[1].uppercaseChar().code,
        ),
        0,
        2,
    )
}
