package com.tonbil.aifirewall.feature.securitysettings

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.RestartAlt
import androidx.compose.material.icons.outlined.Save
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.AlertSettingsConfigDto
import com.tonbil.aifirewall.data.remote.dto.DnsSecurityConfigDto
import com.tonbil.aifirewall.data.remote.dto.SecurityStatsDto
import com.tonbil.aifirewall.data.remote.dto.ThreatAnalysisConfigDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

@Composable
fun SecuritySettingsScreen(
    onBack: () -> Unit,
    viewModel: SecuritySettingsViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.actionMessage) {
        uiState.actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            // Top bar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Outlined.ArrowBack, contentDescription = "Geri", tint = colors.neonCyan)
                }
                Text(
                    text = "Guvenlik Ayarlari",
                    style = MaterialTheme.typography.titleLarge,
                    color = colors.neonCyan,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f),
                )
                if (uiState.isSaving) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = colors.neonCyan,
                        strokeWidth = 2.dp,
                    )
                } else {
                    IconButton(onClick = { viewModel.reloadConfig() }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = colors.neonAmber)
                    }
                }
            }

            // Tabs
            val tabs = listOf("Tehdit Analizi", "DNS Guvenlik", "Uyari Ayarlari")
            ScrollableTabRow(
                selectedTabIndex = uiState.selectedTab,
                containerColor = Color.Transparent,
                contentColor = colors.neonCyan,
                edgePadding = 0.dp,
                divider = {},
            ) {
                tabs.forEachIndexed { index, title ->
                    Tab(
                        selected = uiState.selectedTab == index,
                        onClick = { viewModel.selectTab(index) },
                        text = {
                            Text(
                                text = title,
                                color = if (uiState.selectedTab == index) colors.neonCyan else colors.glassBorder,
                                fontWeight = if (uiState.selectedTab == index) FontWeight.Bold else FontWeight.Normal,
                                fontSize = 13.sp,
                            )
                        },
                    )
                }
            }

            if (uiState.isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = colors.neonCyan)
                }
            } else if (uiState.error != null) {
                Box(modifier = Modifier.fillMaxSize().padding(16.dp), contentAlignment = Alignment.Center) {
                    GlassCard(modifier = Modifier.fillMaxWidth()) {
                        Text(uiState.error ?: "", color = colors.neonRed)
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(
                            onClick = { viewModel.loadAll() },
                            colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
                        ) { Text("Tekrar Dene", color = Color.Black) }
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item { Spacer(modifier = Modifier.height(4.dp)) }

                    when (uiState.selectedTab) {
                        0 -> item {
                            ThreatAnalysisTab(
                                config = uiState.config.threatAnalysis,
                                onUpdate = { viewModel.updateThreatAnalysis(it) },
                                colors = colors,
                            )
                        }
                        1 -> item {
                            DnsSecurityTab(
                                config = uiState.config.dnsSecurity,
                                onUpdate = { viewModel.updateDnsSecurity(it) },
                                colors = colors,
                            )
                        }
                        2 -> item {
                            AlertSettingsTab(
                                config = uiState.config.alertSettings,
                                onUpdate = { viewModel.updateAlertSettings(it) },
                                colors = colors,
                            )
                        }
                    }

                    // Live stats card
                    item {
                        SecurityStatsCard(stats = uiState.stats, colors = colors)
                    }

                    // Reset button
                    item {
                        Button(
                            onClick = { viewModel.resetToDefaults() },
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(containerColor = colors.neonRed.copy(alpha = 0.15f)),
                            shape = RoundedCornerShape(8.dp),
                        ) {
                            Icon(Icons.Outlined.RestartAlt, contentDescription = null, tint = colors.neonRed)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Varsayilana Don", color = colors.neonRed, fontWeight = FontWeight.Bold)
                        }
                    }

                    item { Spacer(modifier = Modifier.height(16.dp)) }
                }
            }
        }

        SnackbarHost(
            hostState = snackbarHostState,
            modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp),
        ) { data ->
            Snackbar(
                containerColor = colors.glassBg,
                contentColor = colors.neonCyan,
                snackbarData = data,
            )
        }
    }
}

// ========== Tab 1: Tehdit Analizi ==========

@Composable
private fun ThreatAnalysisTab(
    config: ThreatAnalysisConfigDto,
    onUpdate: (ThreatAnalysisConfigDto) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            SectionTitle("DGA Algilama", colors)
            Spacer(modifier = Modifier.height(8.dp))

            SettingToggleRow(
                label = "DGA Algilama Aktif",
                checked = config.dgaDetectionEnabled,
                onCheckedChange = { onUpdate(config.copy(dgaDetectionEnabled = it)) },
                colors = colors,
            )

            AnimatedVisibility(visible = config.dgaDetectionEnabled) {
                Column {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Entropi Esigi: ${"%.1f".format(config.dgaEntropyThreshold)}",
                        color = colors.neonCyan,
                        fontSize = 13.sp,
                    )
                    Slider(
                        value = config.dgaEntropyThreshold,
                        onValueChange = { onUpdate(config.copy(dgaEntropyThreshold = it)) },
                        valueRange = 1f..5f,
                        steps = 7,
                        colors = SliderDefaults.colors(
                            thumbColor = colors.neonCyan,
                            activeTrackColor = colors.neonCyan,
                            inactiveTrackColor = colors.glassBorder,
                        ),
                    )
                }
            }
        }

        GlassCard(modifier = Modifier.fillMaxWidth()) {
            SectionTitle("Flood / Tarama Esikleri", colors)
            Spacer(modifier = Modifier.height(8.dp))

            SliderSettingRow(
                label = "Subnet Flood Esigi",
                value = config.subnetFloodThreshold.toFloat(),
                range = 1f..50f,
                steps = 48,
                display = { "${it.toInt()}" },
                onValueChange = { onUpdate(config.copy(subnetFloodThreshold = it.toInt())) },
                colors = colors,
            )

            Spacer(modifier = Modifier.height(8.dp))

            SliderSettingRow(
                label = "Tarama Deseni Esigi",
                value = config.scanPatternThreshold.toFloat(),
                range = 1f..30f,
                steps = 28,
                display = { "${it.toInt()}" },
                onValueChange = { onUpdate(config.copy(scanPatternThreshold = it.toInt())) },
                colors = colors,
            )
        }

        GlassCard(modifier = Modifier.fillMaxWidth()) {
            SectionTitle("Otomatik Engelleme", colors)
            Spacer(modifier = Modifier.height(8.dp))

            SettingToggleRow(
                label = "Otomatik Engelleme Aktif",
                checked = config.autoBlockEnabled,
                onCheckedChange = { onUpdate(config.copy(autoBlockEnabled = it)) },
                colors = colors,
            )

            AnimatedVisibility(visible = config.autoBlockEnabled) {
                Column {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Engelleme Suresi",
                        color = com.tonbil.aifirewall.ui.theme.TextSecondary,
                        fontSize = 12.sp,
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    val durations = listOf("1h", "6h", "12h", "24h", "48h", "72h")
                    @OptIn(ExperimentalLayoutApi::class)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        durations.forEach { dur ->
                            FilterChip(
                                selected = config.autoBlockDuration == dur,
                                onClick = { onUpdate(config.copy(autoBlockDuration = dur)) },
                                label = { Text(dur, fontSize = 12.sp) },
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = colors.neonCyan.copy(alpha = 0.2f),
                                    selectedLabelColor = colors.neonCyan,
                                    containerColor = colors.glassBg,
                                    labelColor = com.tonbil.aifirewall.ui.theme.TextSecondary,
                                ),
                            )
                        }
                    }
                }
            }
        }
    }
}

// ========== Tab 2: DNS Guvenlik ==========

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DnsSecurityTab(
    config: DnsSecurityConfigDto,
    onUpdate: (DnsSecurityConfigDto) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val queryTypes = listOf("ANY", "AXFR", "IXFR", "TXT", "HINFO", "CHAOS")

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            SectionTitle("DNS Rate Limiting", colors)
            Spacer(modifier = Modifier.height(8.dp))

            SettingToggleRow(
                label = "Rate Limit Aktif",
                checked = config.rateLimitEnabled,
                onCheckedChange = { onUpdate(config.copy(rateLimitEnabled = it)) },
                colors = colors,
            )

            AnimatedVisibility(visible = config.rateLimitEnabled) {
                Column {
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = config.rateLimitPerSecond.toString(),
                        onValueChange = { v ->
                            v.toIntOrNull()?.let { onUpdate(config.copy(rateLimitPerSecond = it)) }
                        },
                        label = { Text("Saniyede Max Sorgu", color = com.tonbil.aifirewall.ui.theme.TextSecondary) },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        colors = neonTextFieldColors(colors),
                    )
                }
            }
        }

        GlassCard(modifier = Modifier.fillMaxWidth()) {
            SectionTitle("Engellenen Sorgu Tipleri", colors)
            Spacer(modifier = Modifier.height(8.dp))
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                queryTypes.forEach { qType ->
                    val selected = config.blockedQueryTypes.contains(qType)
                    FilterChip(
                        selected = selected,
                        onClick = {
                            val newList = if (selected) {
                                config.blockedQueryTypes - qType
                            } else {
                                config.blockedQueryTypes + qType
                            }
                            onUpdate(config.copy(blockedQueryTypes = newList))
                        },
                        label = { Text(qType, fontSize = 12.sp) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = colors.neonRed.copy(alpha = 0.2f),
                            selectedLabelColor = colors.neonRed,
                            containerColor = colors.glassBg,
                            labelColor = com.tonbil.aifirewall.ui.theme.TextSecondary,
                        ),
                    )
                }
            }
        }

        GlassCard(modifier = Modifier.fillMaxWidth()) {
            SectionTitle("DNS Sinkhole", colors)
            Spacer(modifier = Modifier.height(8.dp))

            SettingToggleRow(
                label = "Sinkhole Aktif",
                checked = config.sinkholeEnabled,
                onCheckedChange = { onUpdate(config.copy(sinkholeEnabled = it)) },
                colors = colors,
            )

            AnimatedVisibility(visible = config.sinkholeEnabled) {
                Column {
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = config.sinkholeIp,
                        onValueChange = { onUpdate(config.copy(sinkholeIp = it)) },
                        label = { Text("Sinkhole IP Adresi", color = com.tonbil.aifirewall.ui.theme.TextSecondary) },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii),
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        colors = neonTextFieldColors(colors),
                    )
                }
            }
        }
    }
}

// ========== Tab 3: Uyari Ayarlari ==========

@Composable
private fun AlertSettingsTab(
    config: AlertSettingsConfigDto,
    onUpdate: (AlertSettingsConfigDto) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        GlassCard(modifier = Modifier.fillMaxWidth()) {
            SectionTitle("DDoS Uyari Esikleri", colors)
            Spacer(modifier = Modifier.height(8.dp))

            SliderSettingRow(
                label = "Uyari Esigi (paket)",
                value = config.ddosAlertThreshold.toFloat(),
                range = 10f..1000f,
                steps = 98,
                display = { "${it.toInt()}" },
                onValueChange = { onUpdate(config.copy(ddosAlertThreshold = it.toInt())) },
                colors = colors,
            )

            Spacer(modifier = Modifier.height(12.dp))

            SliderSettingRow(
                label = "Bekleme Suresi (dakika)",
                value = config.cooldownMinutes.toFloat(),
                range = 1f..60f,
                steps = 58,
                display = { "${it.toInt()} dk" },
                onValueChange = { onUpdate(config.copy(cooldownMinutes = it.toInt())) },
                colors = colors,
            )
        }

        GlassCard(modifier = Modifier.fillMaxWidth()) {
            SectionTitle("Bildirim Kanallari", colors)
            Spacer(modifier = Modifier.height(8.dp))

            SettingToggleRow(
                label = "Telegram Bildirimleri",
                checked = config.telegramEnabled,
                onCheckedChange = { onUpdate(config.copy(telegramEnabled = it)) },
                colors = colors,
                activeColor = colors.neonGreen,
            )

            Spacer(modifier = Modifier.height(8.dp))

            SettingToggleRow(
                label = "E-posta Bildirimleri",
                checked = config.emailEnabled,
                onCheckedChange = { onUpdate(config.copy(emailEnabled = it)) },
                colors = colors,
                activeColor = colors.neonGreen,
            )
        }
    }
}

// ========== Live Stats Card ==========

@Composable
private fun SecurityStatsCard(
    stats: SecurityStatsDto?,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        SectionTitle("Canli Istatistikler", colors)
        Spacer(modifier = Modifier.height(8.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            MiniStatItem(
                label = "Engelli IP",
                value = "${stats?.blockedIpCount ?: 0}",
                color = colors.neonRed,
            )
            MiniStatItem(
                label = "Oto-Engel",
                value = "${stats?.totalAutoBlocks ?: 0}",
                color = colors.neonAmber,
            )
            MiniStatItem(
                label = "DGA Tespiti",
                value = "${stats?.dgaDetections ?: 0}",
                color = colors.neonMagenta,
            )
            MiniStatItem(
                label = "Supheliler",
                value = "${stats?.totalSuspicious ?: 0}",
                color = colors.neonCyan,
            )
        }
    }
}

// ========== Shared Composables ==========

@Composable
private fun SectionTitle(text: String, colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors) {
    Text(
        text = text,
        color = colors.neonCyan,
        fontWeight = FontWeight.Bold,
        fontSize = 15.sp,
    )
}

@Composable
private fun SettingToggleRow(
    label: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
    activeColor: Color = colors.neonCyan,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            color = com.tonbil.aifirewall.ui.theme.TextPrimary,
            fontSize = 14.sp,
            modifier = Modifier.weight(1f),
        )
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Color.Black,
                checkedTrackColor = activeColor,
                uncheckedThumbColor = com.tonbil.aifirewall.ui.theme.TextSecondary,
                uncheckedTrackColor = colors.glassBorder,
            ),
        )
    }
}

@Composable
private fun SliderSettingRow(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    steps: Int,
    display: (Float) -> String,
    onValueChange: (Float) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(label, color = com.tonbil.aifirewall.ui.theme.TextPrimary, fontSize = 14.sp)
            Text(display(value), color = colors.neonCyan, fontSize = 14.sp, fontWeight = FontWeight.Bold)
        }
        Slider(
            value = value,
            onValueChange = onValueChange,
            valueRange = range,
            steps = steps,
            colors = SliderDefaults.colors(
                thumbColor = colors.neonCyan,
                activeTrackColor = colors.neonCyan,
                inactiveTrackColor = colors.glassBorder,
            ),
        )
    }
}

@Composable
private fun MiniStatItem(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = color, fontWeight = FontWeight.Bold, fontSize = 20.sp)
        Text(label, color = com.tonbil.aifirewall.ui.theme.TextSecondary, fontSize = 11.sp)
    }
}

@Composable
private fun neonTextFieldColors(colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors) =
    OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.neonCyan,
        unfocusedBorderColor = colors.glassBorder,
        focusedLabelColor = colors.neonCyan,
        cursorColor = colors.neonCyan,
        focusedTextColor = com.tonbil.aifirewall.ui.theme.TextPrimary,
        unfocusedTextColor = com.tonbil.aifirewall.ui.theme.TextPrimary,
    )
