package com.tonbil.aifirewall.feature.ddos

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.DeleteSweep
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.DdosProtectionCounterDto
import com.tonbil.aifirewall.data.remote.dto.DdosProtectionStatusDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@Composable
fun DdosScreen(
    onBack: () -> Unit,
    viewModel: DdosViewModel = koinViewModel(),
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

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = {
            SnackbarHost(hostState = snackbarHostState) { data ->
                Snackbar(
                    containerColor = colors.glassBg,
                    contentColor = colors.neonCyan,
                    snackbarData = data,
                )
            }
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
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
                Icon(
                    Icons.Outlined.Security,
                    contentDescription = null,
                    tint = colors.neonMagenta,
                    modifier = Modifier.size(24.dp),
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "DDoS Koruma",
                    style = MaterialTheme.typography.titleLarge,
                    color = colors.neonCyan,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f),
                )
                if (uiState.isActionLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = colors.neonCyan,
                        strokeWidth = 2.dp,
                    )
                } else {
                    IconButton(onClick = { viewModel.refresh() }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = colors.neonAmber)
                    }
                }
            }

            when {
                uiState.isLoading -> {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
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
                            Text(uiState.error ?: "", color = colors.neonRed)
                            Spacer(modifier = Modifier.height(8.dp))
                            Button(
                                onClick = { viewModel.loadAll() },
                                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
                            ) { Text("Tekrar Dene", color = Color.Black) }
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        item { Spacer(modifier = Modifier.height(4.dp)) }

                        // Counters summary
                        item {
                            CountersSummaryCard(
                                counters = uiState.counters,
                                colors = colors,
                            )
                        }

                        // Protection modules header
                        item {
                            Text(
                                text = "Koruma Modulleri",
                                color = colors.neonCyan,
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                                modifier = Modifier.padding(vertical = 4.dp),
                            )
                        }

                        // Protection items
                        items(uiState.protections, key = { it.name }) { protection ->
                            val counter = uiState.counters?.byProtection?.get(protection.name)
                            ProtectionItem(
                                protection = protection,
                                counter = counter,
                                onToggle = { viewModel.toggleProtection(protection.name) },
                                colors = colors,
                            )
                        }

                        // Action buttons
                        item {
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(12.dp),
                            ) {
                                Button(
                                    onClick = { viewModel.applyChanges() },
                                    modifier = Modifier.weight(1f),
                                    colors = ButtonDefaults.buttonColors(containerColor = colors.neonGreen.copy(alpha = 0.15f)),
                                    shape = RoundedCornerShape(8.dp),
                                    enabled = !uiState.isActionLoading,
                                ) {
                                    Icon(Icons.Outlined.Shield, contentDescription = null, tint = colors.neonGreen, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Uygula", color = colors.neonGreen, fontWeight = FontWeight.Bold)
                                }

                                Button(
                                    onClick = { viewModel.showFlushConfirm() },
                                    modifier = Modifier.weight(1f),
                                    colors = ButtonDefaults.buttonColors(containerColor = colors.neonRed.copy(alpha = 0.15f)),
                                    shape = RoundedCornerShape(8.dp),
                                    enabled = !uiState.isActionLoading,
                                ) {
                                    Icon(Icons.Outlined.DeleteSweep, contentDescription = null, tint = colors.neonRed, modifier = Modifier.size(18.dp))
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text("Temizle", color = colors.neonRed, fontWeight = FontWeight.Bold)
                                }
                            }
                        }

                        item { Spacer(modifier = Modifier.height(16.dp)) }
                    }
                }
            }
        }

        // Flush confirmation dialog
        if (uiState.showFlushConfirm) {
            AlertDialog(
                onDismissRequest = { viewModel.hideFlushConfirm() },
                containerColor = com.tonbil.aifirewall.ui.theme.DarkSurface,
                title = {
                    Text("Saldirgan Listesini Temizle", color = colors.neonRed, fontWeight = FontWeight.Bold)
                },
                text = {
                    Text(
                        "Tum engellenen saldirgan IP adresleri temizlenecek. Devam etmek istiyor musunuz?",
                        color = TextPrimary,
                    )
                },
                confirmButton = {
                    Button(
                        onClick = { viewModel.flushAttackers() },
                        colors = ButtonDefaults.buttonColors(containerColor = colors.neonRed),
                    ) {
                        Text("Temizle", color = Color.Black, fontWeight = FontWeight.Bold)
                    }
                },
                dismissButton = {
                    TextButton(onClick = { viewModel.hideFlushConfirm() }) {
                        Text("Iptal", color = TextSecondary)
                    }
                },
            )
        }
    }
}

// ========== Counters Summary ==========

@Composable
private fun CountersSummaryCard(
    counters: com.tonbil.aifirewall.data.remote.dto.DdosCountersDto?,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonMagenta) {
        Text(
            text = "DDoS Sayaclari",
            color = colors.neonCyan,
            fontWeight = FontWeight.Bold,
            fontSize = 15.sp,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = formatNumber(counters?.totalDroppedPackets ?: 0),
                    color = colors.neonRed,
                    fontWeight = FontWeight.Bold,
                    fontSize = 22.sp,
                )
                Text("Dusurlen Paket", color = TextSecondary, fontSize = 12.sp)
            }
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = formatBytes(counters?.totalDroppedBytes ?: 0),
                    color = colors.neonAmber,
                    fontWeight = FontWeight.Bold,
                    fontSize = 22.sp,
                )
                Text("Dusurlen Veri", color = TextSecondary, fontSize = 12.sp)
            }
        }
    }
}

// ========== Protection Item ==========

@Composable
private fun ProtectionItem(
    protection: DdosProtectionStatusDto,
    counter: DdosProtectionCounterDto?,
    onToggle: () -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    GlassCard(
        modifier = Modifier.fillMaxWidth(),
        glowColor = if (protection.enabled) colors.neonGreen.copy(alpha = 0.2f) else null,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = protection.displayName.ifBlank { protection.name },
                    color = TextPrimary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp,
                )
                if (counter != null && (counter.packets > 0 || counter.bytes > 0)) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Text(
                            text = "${formatNumber(counter.packets)} paket",
                            color = colors.neonAmber,
                            fontSize = 12.sp,
                        )
                        Text(
                            text = formatBytes(counter.bytes),
                            color = TextSecondary,
                            fontSize = 12.sp,
                        )
                    }
                }
            }

            Text(
                text = if (protection.enabled) "Aktif" else "Pasif",
                color = if (protection.enabled) colors.neonGreen else colors.neonRed,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier
                    .background(
                        (if (protection.enabled) colors.neonGreen else colors.neonRed).copy(alpha = 0.15f),
                        RoundedCornerShape(4.dp),
                    )
                    .padding(horizontal = 6.dp, vertical = 2.dp),
            )

            Spacer(modifier = Modifier.width(8.dp))

            Switch(
                checked = protection.enabled,
                onCheckedChange = { onToggle() },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.Black,
                    checkedTrackColor = colors.neonGreen,
                    uncheckedThumbColor = TextSecondary,
                    uncheckedTrackColor = colors.glassBorder,
                ),
            )
        }
    }
}

// ========== Formatting Helpers ==========

private fun formatNumber(value: Long): String {
    return when {
        value >= 1_000_000_000 -> "${"%.1f".format(value / 1_000_000_000.0)}B"
        value >= 1_000_000 -> "${"%.1f".format(value / 1_000_000.0)}M"
        value >= 1_000 -> "${"%.1f".format(value / 1_000.0)}K"
        else -> "$value"
    }
}

private fun formatBytes(bytes: Long): String {
    return when {
        bytes >= 1_073_741_824 -> "${"%.1f".format(bytes / 1_073_741_824.0)} GB"
        bytes >= 1_048_576 -> "${"%.1f".format(bytes / 1_048_576.0)} MB"
        bytes >= 1_024 -> "${"%.1f".format(bytes / 1_024.0)} KB"
        else -> "$bytes B"
    }
}
