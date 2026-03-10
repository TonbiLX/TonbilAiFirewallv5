package com.tonbil.aifirewall.feature.wifi

import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Save
import androidx.compose.material.icons.outlined.SignalWifi4Bar
import androidx.compose.material.icons.outlined.SignalWifiOff
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
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
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.WifiClientDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@Composable
fun WifiScreen(
    onBack: () -> Unit,
    viewModel: WifiViewModel = koinViewModel(),
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
                    Icons.Outlined.Wifi,
                    contentDescription = null,
                    tint = colors.neonCyan,
                    modifier = Modifier.size(24.dp),
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "WiFi Yonetimi",
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

                        // Status card
                        item {
                            WifiStatusCard(
                                status = uiState.status,
                                onToggle = { viewModel.toggleWifi() },
                                isActionLoading = uiState.isActionLoading,
                                colors = colors,
                            )
                        }

                        // Config edit card
                        item {
                            WifiConfigCard(
                                uiState = uiState,
                                onStartEdit = { viewModel.startEditing() },
                                onCancel = { viewModel.cancelEditing() },
                                onSave = { viewModel.saveConfig() },
                                onSsidChange = { viewModel.updateEditSsid(it) },
                                onPasswordChange = { viewModel.updateEditPassword(it) },
                                onChannelChange = { viewModel.updateEditChannel(it) },
                                colors = colors,
                            )
                        }

                        // Connected clients header
                        item {
                            Text(
                                text = "Bagli Istemciler (${uiState.clients.size})",
                                color = colors.neonCyan,
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                                modifier = Modifier.padding(vertical = 4.dp),
                            )
                        }

                        if (uiState.clients.isEmpty()) {
                            item {
                                GlassCard(modifier = Modifier.fillMaxWidth()) {
                                    Text(
                                        "Bagli istemci bulunamadi",
                                        color = TextSecondary,
                                        modifier = Modifier.padding(8.dp),
                                    )
                                }
                            }
                        } else {
                            items(uiState.clients, key = { it.macAddress }) { client ->
                                WifiClientItem(client = client, colors = colors)
                            }
                        }

                        item { Spacer(modifier = Modifier.height(16.dp)) }
                    }
                }
            }
        }
    }
}

// ========== Status Card ==========

@Composable
private fun WifiStatusCard(
    status: com.tonbil.aifirewall.data.remote.dto.WifiStatusDto?,
    onToggle: () -> Unit,
    isActionLoading: Boolean,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val isRunning = status?.running == true

    GlassCard(
        modifier = Modifier.fillMaxWidth(),
        glowColor = if (isRunning) colors.neonGreen else colors.neonRed,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                if (isRunning) Icons.Outlined.SignalWifi4Bar else Icons.Outlined.SignalWifiOff,
                contentDescription = null,
                tint = if (isRunning) colors.neonGreen else colors.neonRed,
                modifier = Modifier.size(32.dp),
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (isRunning) "WiFi Aktif" else "WiFi Kapali",
                    color = if (isRunning) colors.neonGreen else colors.neonRed,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                )
                if (status != null) {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "SSID: ${status.ssid}",
                        color = TextPrimary,
                        fontSize = 13.sp,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        Text("Kanal: ${status.channel}", color = TextSecondary, fontSize = 12.sp)
                        Text("Frekans: ${status.frequency}", color = TextSecondary, fontSize = 12.sp)
                        Text("${status.connectedClients} istemci", color = colors.neonCyan, fontSize = 12.sp)
                    }
                }
            }

            Switch(
                checked = isRunning,
                onCheckedChange = { onToggle() },
                enabled = !isActionLoading,
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

// ========== Config Card ==========

@Composable
private fun WifiConfigCard(
    uiState: WifiUiState,
    onStartEdit: () -> Unit,
    onCancel: () -> Unit,
    onSave: () -> Unit,
    onSsidChange: (String) -> Unit,
    onPasswordChange: (String) -> Unit,
    onChannelChange: (String) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val tfColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.neonCyan,
        unfocusedBorderColor = colors.glassBorder,
        focusedLabelColor = colors.neonCyan,
        cursorColor = colors.neonCyan,
        focusedTextColor = TextPrimary,
        unfocusedTextColor = TextPrimary,
        disabledTextColor = TextSecondary,
        disabledBorderColor = colors.glassBorder,
        disabledLabelColor = TextSecondary,
    )

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "Yapilandirma",
                color = colors.neonCyan,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp,
            )
            if (!uiState.isEditing) {
                IconButton(onClick = onStartEdit) {
                    Icon(Icons.Outlined.Edit, contentDescription = "Duzenle", tint = colors.neonCyan)
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        OutlinedTextField(
            value = uiState.editSsid,
            onValueChange = onSsidChange,
            label = { Text("SSID", color = TextSecondary) },
            singleLine = true,
            enabled = uiState.isEditing,
            modifier = Modifier.fillMaxWidth(),
            colors = tfColors,
        )

        Spacer(modifier = Modifier.height(8.dp))

        AnimatedVisibility(visible = uiState.isEditing) {
            Column {
                OutlinedTextField(
                    value = uiState.editPassword,
                    onValueChange = onPasswordChange,
                    label = { Text("Yeni Sifre (bos = degistirme)", color = TextSecondary) },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    colors = tfColors,
                )
                Spacer(modifier = Modifier.height(8.dp))
            }
        }

        OutlinedTextField(
            value = uiState.editChannel,
            onValueChange = onChannelChange,
            label = { Text("Kanal", color = TextSecondary) },
            singleLine = true,
            enabled = uiState.isEditing,
            modifier = Modifier.fillMaxWidth(),
            colors = tfColors,
        )

        AnimatedVisibility(visible = uiState.isEditing) {
            Column {
                Spacer(modifier = Modifier.height(12.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Button(
                        onClick = onSave,
                        modifier = Modifier.weight(1f),
                        enabled = !uiState.isActionLoading,
                        colors = ButtonDefaults.buttonColors(containerColor = colors.neonGreen),
                        shape = RoundedCornerShape(8.dp),
                    ) {
                        if (uiState.isActionLoading) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.Black, strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Outlined.Save, contentDescription = null, tint = Color.Black, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Kaydet", color = Color.Black, fontWeight = FontWeight.Bold)
                        }
                    }
                    TextButton(
                        onClick = onCancel,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("Iptal", color = TextSecondary, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

// ========== Client Item ==========

@Composable
private fun WifiClientItem(
    client: WifiClientDto,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val signalColor = when {
        client.signalStrength > -50 -> colors.neonGreen
        client.signalStrength > -70 -> colors.neonAmber
        else -> colors.neonRed
    }

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                Icons.Outlined.SignalWifi4Bar,
                contentDescription = null,
                tint = signalColor,
                modifier = Modifier.size(24.dp),
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = client.hostname ?: client.macAddress,
                    color = TextPrimary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp,
                )
                if (client.hostname != null) {
                    Text(
                        text = client.macAddress,
                        color = TextSecondary,
                        fontSize = 11.sp,
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(
                        text = "Sinyal: ${client.signalStrength} dBm",
                        color = signalColor,
                        fontSize = 12.sp,
                    )
                    Text(
                        text = "RX: ${formatBytes(client.rxBytes)}",
                        color = colors.neonCyan,
                        fontSize = 12.sp,
                    )
                    Text(
                        text = "TX: ${formatBytes(client.txBytes)}",
                        color = colors.neonMagenta,
                        fontSize = 12.sp,
                    )
                }
            }
        }
    }
}

// ========== Formatting ==========

private fun formatBytes(bytes: Long): String {
    return when {
        bytes >= 1_073_741_824 -> "${"%.1f".format(bytes / 1_073_741_824.0)} GB"
        bytes >= 1_048_576 -> "${"%.1f".format(bytes / 1_048_576.0)} MB"
        bytes >= 1_024 -> "${"%.1f".format(bytes / 1_024.0)} KB"
        else -> "$bytes B"
    }
}
