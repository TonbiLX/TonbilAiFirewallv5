package com.tonbil.aifirewall.feature.systemmonitor

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Memory
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Thermostat
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.FanConfigUpdateDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import kotlinx.coroutines.delay
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SystemMonitorScreen(
    onBack: () -> Unit,
    viewModel: SystemMonitorViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val snackbarHostState = remember { SnackbarHostState() }

    // Auto-refresh every 5 seconds
    LaunchedEffect(Unit) {
        while (true) {
            delay(5_000)
            viewModel.loadAll()
        }
    }

    LaunchedEffect(uiState.actionMessage) {
        uiState.actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }

    // Fan local state
    var fanMode by remember(uiState.fan.mode) { mutableStateOf(uiState.fan.mode) }
    var pwmValue by remember(uiState.fan.pwmValue) { mutableIntStateOf(uiState.fan.pwmValue) }
    var targetTemp by remember(uiState.fan.targetTemp) { mutableIntStateOf(uiState.fan.targetTemp) }

    Scaffold(
        snackbarHost = {
            SnackbarHost(hostState = snackbarHostState) { data ->
                Snackbar(
                    snackbarData = data,
                    containerColor = colors.neonCyan.copy(alpha = 0.9f),
                    contentColor = Color.Black,
                    shape = RoundedCornerShape(8.dp),
                )
            }
        },
        containerColor = Color.Transparent,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(padding),
        ) {
            // Header
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Outlined.ArrowBack, contentDescription = "Geri", tint = colors.neonCyan)
                }
                Icon(Icons.Outlined.Memory, contentDescription = null, tint = colors.neonCyan, modifier = Modifier.size(26.dp))
                Spacer(Modifier.width(8.dp))
                Text(
                    "Sistem Monitoru",
                    style = MaterialTheme.typography.headlineMedium,
                    color = colors.neonCyan,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = { viewModel.loadAll() }) {
                    Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = colors.neonCyan)
                }
            }

            if (uiState.isLoading) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = colors.neonCyan)
                }
                return@Column
            }

            uiState.error?.let { err ->
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(err, color = colors.neonRed, style = MaterialTheme.typography.bodyMedium)
                }
                return@Column
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                // Hardware Info Card
                item {
                    val info = uiState.info
                    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonCyan) {
                        Text("Donanim Bilgisi", style = MaterialTheme.typography.titleMedium, color = colors.neonCyan, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        HwInfoRow("Model", info.model)
                        HwInfoRow("CPU", info.cpuModel)
                        HwInfoRow("Cekirdek", "${info.cpuCores}")
                        HwInfoRow("RAM", "${info.totalRamMb} MB")
                        HwInfoRow("Disk", "${"%.1f".format(info.totalDiskGb)} GB")
                        HwInfoRow("Isletim Sistemi", info.osVersion)
                        HwInfoRow("Kernel", info.kernelVersion)
                        HwInfoRow("Hostname", info.hostname)
                        HwInfoRow("MAC", info.macAddress)
                    }
                }

                // Metrics Cards
                item {
                    val cpu = uiState.metrics.current.cpu
                    val mem = uiState.metrics.current.memory
                    val disk = uiState.metrics.current.disk
                    val cpuColor = when {
                        cpu.usagePercent >= 85f -> colors.neonRed
                        cpu.usagePercent >= 60f -> colors.neonAmber
                        else -> colors.neonGreen
                    }
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        // CPU + Temp row
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            MetricCard(
                                modifier = Modifier.weight(1f),
                                label = "CPU Kullanimi",
                                value = "${"%.1f".format(cpu.usagePercent)}%",
                                progress = cpu.usagePercent / 100f,
                                color = cpuColor,
                                sub = "${"%.0f".format(cpu.frequencyMhz)} MHz",
                            )
                            MetricCard(
                                modifier = Modifier.weight(1f),
                                label = "Sicaklik",
                                value = "${"%.1f".format(cpu.temperatureC)} C",
                                progress = (cpu.temperatureC / 90f).coerceIn(0f, 1f),
                                color = when {
                                    cpu.temperatureC >= 75f -> colors.neonRed
                                    cpu.temperatureC >= 60f -> colors.neonAmber
                                    else -> colors.neonGreen
                                },
                                sub = "Maks ~90C",
                            )
                        }
                        // Memory + Disk row
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            MetricCard(
                                modifier = Modifier.weight(1f),
                                label = "Bellek",
                                value = "${"%.0f".format(mem.usedMb)} / ${"%.0f".format(mem.totalMb)} MB",
                                progress = mem.usagePercent / 100f,
                                color = colors.neonMagenta,
                                sub = "${"%.1f".format(mem.usagePercent)}% dolu",
                            )
                            MetricCard(
                                modifier = Modifier.weight(1f),
                                label = "Disk",
                                value = "${"%.1f".format(disk.usedGb)} / ${"%.1f".format(disk.totalGb)} GB",
                                progress = disk.usagePercent / 100f,
                                color = colors.neonAmber,
                                sub = "${"%.1f".format(disk.usagePercent)}% dolu",
                            )
                        }
                    }
                }

                // Fan Control Card
                item {
                    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonMagenta) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Outlined.Thermostat, contentDescription = null, tint = colors.neonMagenta, modifier = Modifier.size(20.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Fan Kontrolu", style = MaterialTheme.typography.titleMedium, color = colors.neonMagenta, fontWeight = FontWeight.Bold)
                            Spacer(Modifier.weight(1f))
                            Text("${uiState.fan.currentRpm} RPM", style = MaterialTheme.typography.bodySmall, color = colors.neonGreen)
                        }
                        Spacer(Modifier.height(12.dp))

                        // Mode selector
                        Text("Mod", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.height(6.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("auto", "manual").forEach { mode ->
                                val selected = fanMode == mode
                                Button(
                                    onClick = { fanMode = mode },
                                    colors = ButtonDefaults.buttonColors(
                                        containerColor = if (selected) colors.neonMagenta else colors.glassBg,
                                        contentColor = if (selected) Color.Black else colors.neonMagenta,
                                    ),
                                    border = if (!selected) androidx.compose.foundation.BorderStroke(1.dp, colors.neonMagenta.copy(alpha = 0.4f)) else null,
                                    modifier = Modifier.height(36.dp),
                                ) {
                                    Text(if (mode == "auto") "Otomatik" else "Manuel", style = MaterialTheme.typography.labelMedium)
                                }
                            }
                        }
                        Spacer(Modifier.height(12.dp))

                        // PWM Slider (only in manual)
                        if (fanMode == "manual") {
                            Text("PWM: $pwmValue / 255", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Slider(
                                value = pwmValue.toFloat(),
                                onValueChange = { pwmValue = it.toInt() },
                                valueRange = 0f..255f,
                                steps = 0,
                                colors = SliderDefaults.colors(thumbColor = colors.neonMagenta, activeTrackColor = colors.neonMagenta),
                            )
                            Spacer(Modifier.height(8.dp))
                        }

                        // Target Temp Slider
                        Text("Hedef Sicaklik: ${targetTemp}C", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Slider(
                            value = targetTemp.toFloat(),
                            onValueChange = { targetTemp = it.toInt() },
                            valueRange = 40f..80f,
                            steps = 0,
                            colors = SliderDefaults.colors(thumbColor = colors.neonAmber, activeTrackColor = colors.neonAmber),
                        )
                        Spacer(Modifier.height(12.dp))

                        Button(
                            onClick = {
                                viewModel.updateFan(
                                    FanConfigUpdateDto(
                                        mode = fanMode,
                                        pwmValue = if (fanMode == "manual") pwmValue else null,
                                        targetTemp = targetTemp,
                                    )
                                )
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = colors.neonMagenta, contentColor = Color.Black),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("Fan Ayarlarini Kaydet", fontWeight = FontWeight.Bold)
                        }
                    }
                }

                item { Spacer(Modifier.height(16.dp)) }
            }
        }
    }
}

@Composable
private fun HwInfoRow(label: String, value: String) {
    val colors = CyberpunkTheme.colors
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 3.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(
            value.ifBlank { "-" },
            style = MaterialTheme.typography.bodySmall,
            color = colors.neonCyan,
            fontFamily = FontFamily.Monospace,
        )
    }
}

@Composable
private fun MetricCard(
    modifier: Modifier = Modifier,
    label: String,
    value: String,
    progress: Float,
    color: Color,
    sub: String,
) {
    GlassCard(modifier = modifier, glowColor = color) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(4.dp))
        Text(value, style = MaterialTheme.typography.bodyMedium, color = color, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        Spacer(Modifier.height(6.dp))
        LinearProgressIndicator(
            progress = { progress.coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth().height(4.dp),
            color = color,
            trackColor = color.copy(alpha = 0.15f),
        )
        Spacer(Modifier.height(4.dp))
        Text(sub, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
