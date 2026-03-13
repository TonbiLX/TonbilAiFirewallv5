package com.tonbil.aifirewall.feature.dnsfiltering

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.TopDomainDto
import com.tonbil.aifirewall.feature.categories.ContentCategoriesScreen
import com.tonbil.aifirewall.feature.profiles.ProfilesScreen
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.DarkBackground
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
fun DnsFilteringScreen(
    onBack: () -> Unit,
    viewModel: DnsFilteringViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.actionMessage) {
        uiState.actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }

    Scaffold(
        containerColor = DarkBackground,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Outlined.Shield,
                            contentDescription = null,
                            tint = NeonCyan,
                            modifier = Modifier.size(20.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text("DNS Filtreleme", color = NeonCyan, fontWeight = FontWeight.Bold)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Geri", tint = TextSecondary)
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::loadAll) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = TextSecondary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground),
            )
        },
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
        ) {
            // Tab bar
            val tabTitles = listOf("Ozet", "Kategoriler", "Profiller", "Guvenlik")
            ScrollableTabRow(
                selectedTabIndex = uiState.selectedTab,
                containerColor = Color.Transparent,
                contentColor = NeonCyan,
                edgePadding = 0.dp,
                divider = {},
            ) {
                tabTitles.forEachIndexed { index, title ->
                    Tab(
                        selected = uiState.selectedTab == index,
                        onClick = { viewModel.selectTab(index) },
                        text = {
                            Text(
                                text = title,
                                color = if (uiState.selectedTab == index) NeonCyan else TextSecondary,
                                fontWeight = if (uiState.selectedTab == index) FontWeight.Bold else FontWeight.Normal,
                                fontSize = 13.sp,
                            )
                        },
                    )
                }
            }

            when (uiState.selectedTab) {
                0 -> DnsOverviewTab(uiState = uiState, viewModel = viewModel)
                1 -> ContentCategoriesScreen(onBack = {})
                2 -> ProfilesScreen(onBack = {})
                3 -> DnsSecurityTab(uiState = uiState, viewModel = viewModel)
            }
        }
    }
}

// ========== Tab 0: Ozet ==========

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DnsOverviewTab(
    uiState: DnsFilteringUiState,
    viewModel: DnsFilteringViewModel,
) {
    PullToRefreshBox(
        isRefreshing = uiState.isLoading,
        onRefresh = viewModel::loadAll,
        modifier = Modifier.fillMaxSize(),
    ) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(DarkBackground)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 12.dp),
        ) {
            // 1. Global DNS Filtreleme Toggle
            item {
                GlassCard(glowColor = NeonCyan.copy(alpha = 0.25f)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "DNS Filtreleme",
                                color = TextPrimary,
                                fontWeight = FontWeight.SemiBold,
                                fontSize = 16.sp,
                            )
                            Spacer(Modifier.height(2.dp))
                            Text(
                                text = "Tum DNS guvenlik katmanlarini tek tusla ac/kapa",
                                color = TextSecondary,
                                fontSize = 12.sp,
                            )
                        }
                        Switch(
                            checked = viewModel.isGlobalFilterActive,
                            onCheckedChange = { viewModel.toggleGlobalFilter(!viewModel.isGlobalFilterActive) },
                            enabled = !uiState.isTogglingFilter,
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = NeonCyan,
                                checkedTrackColor = NeonCyan.copy(alpha = 0.3f),
                                uncheckedThumbColor = TextSecondary,
                            ),
                        )
                    }
                    if (uiState.isTogglingFilter) {
                        Spacer(Modifier.height(8.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(14.dp),
                                color = NeonCyan,
                                strokeWidth = 2.dp,
                            )
                            Spacer(Modifier.width(8.dp))
                            Text("Guncelleniyor...", color = TextSecondary, fontSize = 11.sp)
                        }
                    }
                }
            }

            // 2. DNS Istatistik Kartlari
            item {
                val stats = uiState.stats
                GlassCard(glowColor = NeonCyan.copy(alpha = 0.15f)) {
                    Text(
                        text = "DNS Istatistikleri (24s)",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(bottom = 12.dp),
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly,
                    ) {
                        DnsStatItem(
                            label = "Toplam Sorgu",
                            value = stats?.totalQueries24h?.toString() ?: "-",
                            color = NeonCyan,
                        )
                        DnsStatItem(
                            label = "Engellenen",
                            value = stats?.blockedQueries24h?.toString() ?: "-",
                            color = NeonRed,
                        )
                        DnsStatItem(
                            label = "Engelleme",
                            value = if (stats != null) "%.1f%%".format(stats.blockPercentage) else "-",
                            color = NeonAmber,
                        )
                        DnsStatItem(
                            label = "Blocklist",
                            value = stats?.activeBlocklists?.toString() ?: "-",
                            color = NeonGreen,
                        )
                    }
                }
            }

            // 3. Kaynak Tipi Dagilimi
            item {
                val stats = uiState.stats
                GlassCard(glowColor = NeonMagenta.copy(alpha = 0.1f)) {
                    Text(
                        text = "Kaynak Dagilimi (24s)",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(bottom = 10.dp),
                    )
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        SourceTypeChip(
                            label = "Internal",
                            count = stats?.internalQueries24h ?: 0,
                            color = NeonGreen,
                            modifier = Modifier.weight(1f),
                        )
                        SourceTypeChip(
                            label = "External",
                            count = stats?.externalQueries24h ?: 0,
                            color = NeonCyan,
                            modifier = Modifier.weight(1f),
                        )
                        SourceTypeChip(
                            label = "DoT",
                            count = stats?.dotQueries24h ?: 0,
                            color = NeonMagenta,
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }

            // 4. DNS Guvenlik Katmanlari
            item {
                val config = uiState.securityConfig
                GlassCard(glowColor = NeonAmber.copy(alpha = 0.15f)) {
                    Text(
                        text = "Guvenlik Katmanlari",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(bottom = 12.dp),
                    )
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        SecurityLayerRow(
                            indicator = NeonCyan,
                            label = "DNSSEC Dogrulama",
                            detail = config?.dnssecMode ?: "log_only",
                            enabled = config?.dnssecEnabled ?: false,
                            onToggle = { viewModel.toggleDnssec(it) },
                            isLoading = uiState.isTogglingFilter,
                        )
                        SecurityLayerRow(
                            indicator = NeonAmber,
                            label = "DNS Tunneling Tespiti",
                            detail = null,
                            enabled = config?.dnsTunnelingEnabled ?: false,
                            onToggle = { viewModel.toggleDnsTunneling(it) },
                            isLoading = uiState.isTogglingFilter,
                        )
                        SecurityLayerRow(
                            indicator = NeonMagenta,
                            label = "DoH Endpoint",
                            detail = "guard.tonbilx.com",
                            enabled = config?.dohEnabled ?: false,
                            onToggle = { viewModel.toggleDoh(it) },
                            isLoading = uiState.isTogglingFilter,
                        )
                        SecurityLayerRow(
                            indicator = NeonRed,
                            label = "DGA Tespiti",
                            detail = null,
                            enabled = config?.threatAnalysis?.dgaDetectionEnabled ?: false,
                            onToggle = { viewModel.toggleDga(it) },
                            isLoading = uiState.isTogglingFilter,
                        )
                        SecurityLayerRow(
                            indicator = NeonGreen,
                            label = "Sinkhole",
                            detail = config?.dnsSecurity?.sinkholeIp,
                            enabled = config?.dnsSecurity?.sinkholeEnabled ?: false,
                            onToggle = { viewModel.toggleSinkhole(it) },
                            isLoading = uiState.isTogglingFilter,
                        )
                        val rateLimitEnabled = config?.dnsSecurity?.rateLimitEnabled ?: false
                        val rateLimitPerSec = config?.dnsSecurity?.rateLimitPerSecond ?: 50
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .size(8.dp)
                                        .clip(CircleShape)
                                        .background(if (rateLimitEnabled) NeonCyan else TextSecondary.copy(alpha = 0.4f)),
                                )
                                Spacer(Modifier.width(10.dp))
                                Column {
                                    Text("Rate Limiting", color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                                    Text("${rateLimitPerSec}/sn", color = TextSecondary, fontSize = 11.sp)
                                }
                            }
                        }
                    }
                }
            }

            // 5. En Cok Sorgulanan Domainler
            val topQueried = uiState.stats?.topQueriedDomains ?: emptyList()
            if (topQueried.isNotEmpty()) {
                item {
                    GlassCard(glowColor = NeonCyan.copy(alpha = 0.1f)) {
                        Text(
                            text = "En Cok Sorgulanan",
                            color = TextSecondary,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(bottom = 8.dp),
                        )
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            topQueried.take(10).forEach { domain ->
                                DomainRow(domain = domain, accentColor = NeonCyan)
                            }
                        }
                    }
                }
            } else {
                item {
                    GlassCard(glowColor = NeonCyan.copy(alpha = 0.1f)) {
                        Text("En Cok Sorgulanan", color = TextSecondary, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.height(8.dp))
                        Text("Henuz veri yok", color = TextSecondary.copy(alpha = 0.5f), fontSize = 13.sp)
                    }
                }
            }

            // 6. En Cok Engellenen Domainler
            val topBlocked = uiState.stats?.topBlockedDomains ?: emptyList()
            if (topBlocked.isNotEmpty()) {
                item {
                    GlassCard(glowColor = NeonRed.copy(alpha = 0.1f)) {
                        Text(
                            text = "En Cok Engellenen",
                            color = NeonRed,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(bottom = 8.dp),
                        )
                        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            topBlocked.take(10).forEach { domain ->
                                DomainRow(domain = domain, accentColor = NeonRed)
                            }
                        }
                    }
                }
            } else {
                item {
                    GlassCard(glowColor = NeonRed.copy(alpha = 0.1f)) {
                        Text("En Cok Engellenen", color = NeonRed, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.height(8.dp))
                        Text("Henuz veri yok", color = TextSecondary.copy(alpha = 0.5f), fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

// ========== Tab 3: Guvenlik ==========

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun DnsSecurityTab(
    uiState: DnsFilteringUiState,
    viewModel: DnsFilteringViewModel,
) {
    val config = uiState.securityConfig

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 12.dp),
    ) {
        // DNSSEC Modu Segmented Button
        item {
            GlassCard(glowColor = NeonCyan.copy(alpha = 0.2f)) {
                Text(
                    text = "DNSSEC Modu",
                    color = TextSecondary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(bottom = 12.dp),
                )
                val dnssecModes = listOf("enforce", "log_only", "disabled")
                val currentMode = config?.dnssecMode ?: "log_only"
                SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
                    dnssecModes.forEachIndexed { index, mode ->
                        SegmentedButton(
                            selected = currentMode == mode,
                            onClick = { viewModel.updateDnssecMode(mode) },
                            shape = SegmentedButtonDefaults.itemShape(index = index, count = dnssecModes.size),
                            colors = SegmentedButtonDefaults.colors(
                                activeContainerColor = NeonCyan.copy(alpha = 0.2f),
                                activeContentColor = NeonCyan,
                                inactiveContainerColor = Color.Transparent,
                                inactiveContentColor = TextSecondary,
                            ),
                        ) {
                            Text(
                                text = when (mode) {
                                    "enforce" -> "Enforce"
                                    "log_only" -> "Log Only"
                                    else -> "Devre Disi"
                                },
                                fontSize = 12.sp,
                            )
                        }
                    }
                }
                Spacer(Modifier.height(8.dp))
                Text(
                    text = when (config?.dnssecMode) {
                        "enforce" -> "Gecersiz DNSSEC imzali alan adlari engelleniyor"
                        "log_only" -> "Gecersiz imzalar sadece loglanir, engellenmez"
                        "disabled" -> "DNSSEC dogrulamasi kapali"
                        else -> ""
                    },
                    color = TextSecondary.copy(alpha = 0.7f),
                    fontSize = 11.sp,
                )
            }
        }

        // Rate Limiting
        item {
            GlassCard(glowColor = NeonGreen.copy(alpha = 0.15f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column {
                        Text("Rate Limiting", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                        Text(
                            text = "Sorgu hiz limiti: ${config?.dnsSecurity?.rateLimitPerSecond ?: 50}/sn",
                            color = TextSecondary,
                            fontSize = 12.sp,
                        )
                    }
                    Switch(
                        checked = config?.dnsSecurity?.rateLimitEnabled ?: false,
                        onCheckedChange = { viewModel.toggleRateLimit(it) },
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = NeonGreen,
                            checkedTrackColor = NeonGreen.copy(alpha = 0.3f),
                        ),
                    )
                }
            }
        }

        // Engelli Sorgu Tipleri
        val blockedTypes = config?.dnsSecurity?.blockedQueryTypes ?: emptyList()
        if (blockedTypes.isNotEmpty()) {
            item {
                GlassCard(glowColor = NeonRed.copy(alpha = 0.1f)) {
                    Text(
                        text = "Engelli Sorgu Tipleri",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.padding(bottom = 10.dp),
                    )
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        blockedTypes.forEach { queryType ->
                            Box(
                                modifier = Modifier
                                    .background(NeonRed.copy(alpha = 0.12f), RoundedCornerShape(6.dp))
                                    .padding(horizontal = 10.dp, vertical = 4.dp),
                            ) {
                                Text(queryType, color = NeonRed, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                            }
                        }
                    }
                }
            }
        }

        // Sinkhole
        item {
            GlassCard(glowColor = NeonGreen.copy(alpha = 0.1f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column {
                        Text("Sinkhole", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                        Text(
                            text = "IPv4: ${config?.dnsSecurity?.sinkholeIp ?: "0.0.0.0"}",
                            color = TextSecondary,
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                    Switch(
                        checked = config?.dnsSecurity?.sinkholeEnabled ?: false,
                        onCheckedChange = { viewModel.toggleSinkhole(it) },
                        enabled = !uiState.isTogglingFilter,
                        colors = SwitchDefaults.colors(
                            checkedThumbColor = NeonGreen,
                            checkedTrackColor = NeonGreen.copy(alpha = 0.3f),
                        ),
                    )
                }
            }
        }

        // DNS Tunneling Parametreleri
        item {
            GlassCard(glowColor = NeonAmber.copy(alpha = 0.1f)) {
                Text(
                    text = "DNS Tunneling Parametreleri",
                    color = TextSecondary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(bottom = 10.dp),
                )
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    TunnelingParamRow(
                        label = "Max Subdomain Uzunlugu",
                        value = config?.dnsTunnelingMaxSubdomainLen?.toString() ?: "50",
                        color = NeonAmber,
                    )
                    TunnelingParamRow(
                        label = "Max Etiket/Dakika",
                        value = config?.dnsTunnelingMaxLabelsPerMin?.toString() ?: "100",
                        color = NeonAmber,
                    )
                    TunnelingParamRow(
                        label = "TXT Oran Esigi (%)",
                        value = config?.dnsTunnelingTxtRatioThreshold?.toString() ?: "30",
                        color = NeonAmber,
                    )
                }
            }
        }

        // Yükleniyor gosterim
        if (uiState.isLoading) {
            item {
                Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = NeonCyan, modifier = Modifier.size(32.dp))
                }
            }
        }
    }
}

// ========== Yardimci Composable'lar ==========

@Composable
private fun SecurityLayerRow(
    indicator: Color,
    label: String,
    detail: String?,
    enabled: Boolean,
    onToggle: (Boolean) -> Unit,
    isLoading: Boolean,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(if (enabled) indicator else TextSecondary.copy(alpha = 0.4f)),
            )
            Spacer(Modifier.width(10.dp))
            Column {
                Text(label, color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                detail?.let {
                    Text(it, color = TextSecondary, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                }
            }
        }
        Switch(
            checked = enabled,
            onCheckedChange = onToggle,
            enabled = !isLoading,
            colors = SwitchDefaults.colors(
                checkedThumbColor = indicator,
                checkedTrackColor = indicator.copy(alpha = 0.3f),
                uncheckedThumbColor = TextSecondary,
            ),
        )
    }
}

@Composable
private fun DnsStatItem(
    label: String,
    value: String,
    color: Color,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            color = color,
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
        )
        Text(
            text = label,
            color = TextSecondary,
            fontSize = 10.sp,
        )
    }
}

@Composable
private fun SourceTypeChip(
    label: String,
    count: Int,
    color: Color,
    modifier: Modifier = Modifier,
) {
    val chipColor = if (count > 0) color else TextSecondary.copy(alpha = 0.4f)
    Box(
        modifier = modifier
            .background(chipColor.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
            .padding(horizontal = 8.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = count.toString(),
                color = chipColor,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
            )
            Text(
                text = label,
                color = chipColor.copy(alpha = 0.8f),
                fontSize = 10.sp,
            )
        }
    }
}

@Composable
private fun DomainRow(domain: TopDomainDto, accentColor: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = domain.domain,
            color = TextPrimary,
            fontSize = 12.sp,
            fontFamily = FontFamily.Monospace,
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.width(8.dp))
        Text(
            text = domain.count.toString(),
            color = accentColor,
            fontSize = 12.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
        )
    }
}

@Composable
private fun TunnelingParamRow(label: String, value: String, color: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = TextSecondary, fontSize = 12.sp)
        Text(value, color = color, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, fontFamily = FontFamily.Monospace)
    }
}
