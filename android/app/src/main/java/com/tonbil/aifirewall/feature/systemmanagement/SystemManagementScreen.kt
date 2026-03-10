package com.tonbil.aifirewall.feature.systemmanagement

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
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
import com.tonbil.aifirewall.data.remote.dto.ServiceStatusDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import kotlinx.coroutines.delay
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SystemManagementScreen(
    onBack: () -> Unit,
    viewModel: SystemManagementViewModel = koinViewModel(),
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

    // Journal line count
    var journalLines by remember { mutableIntStateOf(100) }

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
                Icon(Icons.Outlined.Settings, contentDescription = null, tint = colors.neonCyan, modifier = Modifier.size(26.dp))
                Spacer(Modifier.width(8.dp))
                Text(
                    "Sistem Yonetimi",
                    style = MaterialTheme.typography.headlineMedium,
                    color = colors.neonCyan,
                    modifier = Modifier.weight(1f),
                )
                if (uiState.isActionLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), color = colors.neonMagenta, strokeWidth = 2.dp)
                    Spacer(Modifier.width(8.dp))
                }
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
                // Overview card
                item {
                    val ov = uiState.overview
                    val boot = uiState.bootInfo
                    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonCyan) {
                        Text("Sistem Durumu", style = MaterialTheme.typography.titleMedium, color = colors.neonCyan, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                            InfoChip("Calisma Suresi", ov.uptimeHuman, colors.neonGreen)
                            InfoChip("Yeniden Baslatma", "${ov.bootCount}", colors.neonAmber)
                        }
                        Spacer(Modifier.height(8.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            if (ov.safeMode) {
                                Surface(
                                    color = colors.neonAmber.copy(alpha = 0.2f),
                                    shape = RoundedCornerShape(6.dp),
                                    border = androidx.compose.foundation.BorderStroke(1.dp, colors.neonAmber.copy(alpha = 0.5f)),
                                ) {
                                    Text("GUVENLI MOD", modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp), style = MaterialTheme.typography.labelSmall, color = colors.neonAmber, fontWeight = FontWeight.Bold)
                                }
                            }
                            val wdColor = if (ov.watchdogEnabled) colors.neonGreen else MaterialTheme.colorScheme.onSurfaceVariant
                            Surface(
                                color = wdColor.copy(alpha = 0.15f),
                                shape = RoundedCornerShape(6.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, wdColor.copy(alpha = 0.4f)),
                            ) {
                                Text(
                                    if (ov.watchdogEnabled) "WATCHDOG AKTIF" else "WATCHDOG PASIF",
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = wdColor,
                                    fontWeight = FontWeight.Bold,
                                )
                            }
                        }
                        ov.lastBoot?.let { lb ->
                            Spacer(Modifier.height(6.dp))
                            Text("Son baslama: $lb", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        boot.lastShutdownReason?.let { reason ->
                            Text("Kapanma nedeni: $reason", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }

                // Services header
                item {
                    Text("Servisler", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(vertical = 4.dp))
                }

                // Services list
                items(uiState.services) { svc ->
                    ServiceItem(
                        service = svc,
                        onRestart = { viewModel.restartService(svc.name) },
                        onStart = { viewModel.startService(svc.name) },
                        onStop = { viewModel.stopService(svc.name) },
                    )
                }

                // Journal + Actions
                item {
                    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonMagenta) {
                        Text("Sistem Gunlugu", style = MaterialTheme.typography.titleMedium, color = colors.neonMagenta, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf(50, 100, 200).forEach { count ->
                                val selected = journalLines == count
                                FilterChip(
                                    selected = selected,
                                    onClick = { journalLines = count },
                                    label = { Text("$count satir") },
                                    colors = FilterChipDefaults.filterChipColors(
                                        selectedContainerColor = colors.neonMagenta.copy(alpha = 0.3f),
                                        selectedLabelColor = colors.neonMagenta,
                                    ),
                                )
                            }
                        }
                        Spacer(Modifier.height(8.dp))
                        Button(
                            onClick = { viewModel.loadJournal(journalLines) },
                            colors = ButtonDefaults.buttonColors(containerColor = colors.neonMagenta, contentColor = Color.Black),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Icon(Icons.Outlined.List, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Gunlugu Goster", fontWeight = FontWeight.Bold)
                        }
                    }
                }

                // Bottom action buttons
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(
                            onClick = { viewModel.showRebootConfirm() },
                            colors = ButtonDefaults.buttonColors(containerColor = colors.neonAmber, contentColor = Color.Black),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Icon(Icons.Outlined.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Yeniden Baslat", fontWeight = FontWeight.Bold)
                        }
                        Button(
                            onClick = { viewModel.showShutdownConfirm() },
                            colors = ButtonDefaults.buttonColors(containerColor = colors.neonRed, contentColor = Color.White),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Icon(Icons.Outlined.PowerSettingsNew, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Kapat", fontWeight = FontWeight.Bold)
                        }
                        if (uiState.bootInfo.safeMode) {
                            OutlinedButton(
                                onClick = { viewModel.resetSafeMode() },
                                border = androidx.compose.foundation.BorderStroke(1.dp, colors.neonAmber),
                                colors = ButtonDefaults.outlinedButtonColors(contentColor = colors.neonAmber),
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text("Guvenli Modu Sifirla", fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }

                item { Spacer(Modifier.height(16.dp)) }
            }
        }
    }

    // Reboot confirm dialog
    if (uiState.showRebootConfirm) {
        CountdownConfirmDialog(
            title = "Yeniden Baslat",
            message = "Sistem yeniden baslatilacak. Tum baglantiler kesilecek.",
            confirmLabel = "Yeniden Baslat",
            confirmColor = colors.neonAmber,
            onConfirm = { viewModel.reboot() },
            onDismiss = { viewModel.hideRebootConfirm() },
        )
    }

    // Shutdown confirm dialog
    if (uiState.showShutdownConfirm) {
        CountdownConfirmDialog(
            title = "Sistemi Kapat",
            message = "Sistem kapatilacak. Uzaktan erisim kaybolacak.",
            confirmLabel = "Kapat",
            confirmColor = colors.neonRed,
            onConfirm = { viewModel.shutdown() },
            onDismiss = { viewModel.hideShutdownConfirm() },
        )
    }

    // Journal modal bottom sheet
    if (uiState.showJournal) {
        ModalBottomSheet(
            onDismissRequest = { viewModel.hideJournal() },
            containerColor = MaterialTheme.colorScheme.surface,
            scrimColor = Color.Black.copy(alpha = 0.6f),
        ) {
            Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Sistem Gunlugu", style = MaterialTheme.typography.titleMedium, color = colors.neonMagenta, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                    Text("${uiState.journal.total} satir", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Spacer(Modifier.height(12.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(max = 400.dp)
                        .background(Color.Black.copy(alpha = 0.6f), RoundedCornerShape(8.dp))
                        .padding(12.dp)
                        .verticalScroll(rememberScrollState()),
                ) {
                    Text(
                        text = uiState.journal.lines.joinToString("\n"),
                        style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace, fontSize = 11.sp),
                        color = colors.neonGreen,
                    )
                }
                Spacer(Modifier.height(16.dp))
            }
        }
    }
}

@Composable
private fun ServiceItem(
    service: ServiceStatusDto,
    onRestart: () -> Unit,
    onStart: () -> Unit,
    onStop: () -> Unit,
) {
    val colors = CyberpunkTheme.colors
    val isActive = service.activeState == "active"
    val isFailed = service.activeState == "failed"
    val statusColor = when {
        isFailed -> colors.neonRed
        isActive -> colors.neonGreen
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    val statusText = when {
        isFailed -> "HATA"
        isActive -> service.subState.uppercase()
        else -> "PASIF"
    }

    GlassCard(
        modifier = Modifier.fillMaxWidth(),
        glowColor = if (isFailed) colors.neonRed else null,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(service.label.ifBlank { service.name }, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.SemiBold)
                    if (service.critical) {
                        Surface(
                            color = colors.neonAmber.copy(alpha = 0.2f),
                            shape = RoundedCornerShape(4.dp),
                        ) {
                            Text("KRITIK", modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp), style = MaterialTheme.typography.labelSmall, color = colors.neonAmber, fontSize = 9.sp)
                        }
                    }
                }
                Spacer(Modifier.height(2.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Surface(
                        color = statusColor.copy(alpha = 0.2f),
                        shape = RoundedCornerShape(4.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, statusColor.copy(alpha = 0.4f)),
                    ) {
                        Text(statusText, modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp), style = MaterialTheme.typography.labelSmall, color = statusColor, fontWeight = FontWeight.Bold)
                    }
                    service.memoryMb?.let { mem ->
                        Text("${"%.1f".format(mem)} MB", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    service.uptimeSeconds?.let { uptime ->
                        val h = uptime / 3600; val m = (uptime % 3600) / 60
                        Text(if (h > 0) "${h}s ${m}d" else "${m}d", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            // Action buttons
            Row {
                if (!isActive) {
                    IconButton(onClick = onStart, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Outlined.PlayArrow, contentDescription = "Baslat", tint = colors.neonGreen, modifier = Modifier.size(18.dp))
                    }
                }
                if (isActive) {
                    IconButton(onClick = onStop, modifier = Modifier.size(36.dp)) {
                        Icon(Icons.Outlined.Stop, contentDescription = "Durdur", tint = colors.neonAmber, modifier = Modifier.size(18.dp))
                    }
                }
                IconButton(onClick = onRestart, modifier = Modifier.size(36.dp)) {
                    Icon(Icons.Outlined.Refresh, contentDescription = "Yeniden Baslat", tint = colors.neonCyan, modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

@Composable
private fun InfoChip(label: String, value: String, color: Color) {
    Surface(
        color = color.copy(alpha = 0.1f),
        shape = RoundedCornerShape(8.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = 0.3f)),
    ) {
        Column(modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)) {
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.bodySmall, color = color, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun CountdownConfirmDialog(
    title: String,
    message: String,
    confirmLabel: String,
    confirmColor: Color,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    var countdown by remember { mutableIntStateOf(3) }
    LaunchedEffect(Unit) {
        while (countdown > 0) {
            delay(1_000)
            countdown--
        }
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title, color = confirmColor, fontWeight = FontWeight.Bold) },
        text = {
            Column {
                Text(message, style = MaterialTheme.typography.bodyMedium)
                if (countdown > 0) {
                    Spacer(Modifier.height(8.dp))
                    Text("$countdown saniye bekleyin...", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        },
        confirmButton = {
            Button(
                onClick = onConfirm,
                enabled = countdown == 0,
                colors = ButtonDefaults.buttonColors(containerColor = confirmColor, contentColor = Color.Black),
            ) {
                Text(confirmLabel, fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Iptal") }
        },
        containerColor = MaterialTheme.colorScheme.surface,
    )
}
