package com.tonbil.aifirewall.feature.vpnserver

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Stop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
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
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.VpnPeerConfigDto
import com.tonbil.aifirewall.data.remote.dto.VpnPeerDto
import com.tonbil.aifirewall.data.remote.dto.VpnStatsDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkColors
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@Composable
fun VpnServerScreen(
    onBack: () -> Unit,
    viewModel: VpnServerViewModel = koinViewModel(),
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

    if (uiState.showAddPeerDialog) {
        AddPeerDialog(
            onDismiss = { viewModel.hideAddPeerDialog() },
            onConfirm = { name -> viewModel.addPeer(name) },
            colors = colors,
        )
    }

    if (uiState.showConfigDialog && uiState.peerConfig != null) {
        PeerConfigDialog(
            peerName = uiState.configPeerName,
            config = uiState.peerConfig!!,
            onDismiss = { viewModel.hideConfigDialog() },
            colors = colors,
        )
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = {
            SnackbarHost(snackbarHostState) { data ->
                Snackbar(
                    containerColor = colors.glassBg,
                    contentColor = colors.neonCyan,
                    snackbarData = data,
                )
            }
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { viewModel.showAddPeerDialog() },
                containerColor = colors.neonCyan.copy(alpha = 0.9f),
                contentColor = Color.Black,
            ) {
                Icon(Icons.Outlined.Add, contentDescription = "Peer Ekle")
            }
        },
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
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
                Text(
                    text = "VPN Sunucusu",
                    style = MaterialTheme.typography.titleLarge,
                    color = colors.neonCyan,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = { viewModel.loadAll() }) {
                    Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = colors.neonAmber)
                }
            }

            if (uiState.isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = colors.neonCyan)
                }
            } else if (uiState.error != null) {
                Box(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
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
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    item { Spacer(modifier = Modifier.height(4.dp)) }

                    // Server status card
                    item {
                        ServerStatusCard(
                            stats = uiState.stats,
                            isActionLoading = uiState.isActionLoading,
                            onStart = { viewModel.startVpn() },
                            onStop = { viewModel.stopVpn() },
                            colors = colors,
                        )
                    }

                    // Peers header
                    item {
                        Text(
                            "Peer'lar (${uiState.peers.size})",
                            color = colors.neonMagenta,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                        )
                    }

                    if (uiState.peers.isEmpty()) {
                        item {
                            GlassCard(modifier = Modifier.fillMaxWidth()) {
                                Text("Peer bulunamadi", color = TextSecondary, modifier = Modifier.padding(8.dp))
                            }
                        }
                    } else {
                        items(uiState.peers, key = { it.name }) { peer ->
                            PeerCard(
                                peer = peer,
                                onShowConfig = { viewModel.showPeerConfig(peer.name) },
                                onDelete = { viewModel.deletePeer(peer.name) },
                                colors = colors,
                            )
                        }
                    }

                    item { Spacer(modifier = Modifier.height(80.dp)) }
                }
            }
        }
    }
}

@Composable
private fun ServerStatusCard(
    stats: VpnStatsDto?,
    isActionLoading: Boolean,
    onStart: () -> Unit,
    onStop: () -> Unit,
    colors: CyberpunkColors,
) {
    val serverEnabled = stats?.serverEnabled == true
    GlassCard(
        modifier = Modifier.fillMaxWidth(),
        glowColor = if (serverEnabled) colors.neonGreen else colors.neonRed,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("WireGuard Sunucu", color = colors.neonCyan, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(if (serverEnabled) colors.neonGreen else colors.neonRed),
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    if (serverEnabled) "Aktif" else "Kapali",
                    color = if (serverEnabled) colors.neonGreen else colors.neonRed,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            StatItem("Port", "${stats?.listenPort ?: "-"}", colors.neonCyan)
            StatItem("Peer", "${stats?.totalPeers ?: 0}", colors.neonAmber)
            StatItem("Bagli", "${stats?.connectedPeers ?: 0}", colors.neonGreen)
            StatItem("RX", formatBytes(stats?.totalTransferRx ?: 0), colors.neonMagenta)
            StatItem("TX", formatBytes(stats?.totalTransferTx ?: 0), colors.neonCyan)
        }

        if (stats?.serverPublicKey?.isNotBlank() == true) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                "Public Key: ${stats.serverPublicKey.take(20)}...",
                color = TextSecondary,
                fontSize = 10.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        Button(
            onClick = { if (serverEnabled) onStop() else onStart() },
            enabled = !isActionLoading,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = if (serverEnabled) colors.neonRed.copy(alpha = 0.8f) else colors.neonGreen.copy(alpha = 0.8f),
            ),
        ) {
            if (isActionLoading) {
                CircularProgressIndicator(color = Color.Black, modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
            } else {
                Icon(
                    if (serverEnabled) Icons.Outlined.Stop else Icons.Outlined.PlayArrow,
                    contentDescription = null,
                    tint = Color.Black,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    if (serverEnabled) "Sunucuyu Durdur" else "Sunucuyu Baslat",
                    color = Color.Black,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

@Composable
private fun StatItem(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = color, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Text(label, color = TextSecondary, fontSize = 10.sp)
    }
}

@Composable
private fun PeerCard(
    peer: VpnPeerDto,
    onShowConfig: () -> Unit,
    onDelete: () -> Unit,
    colors: CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.Top,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(if (peer.connected) colors.neonGreen else colors.neonRed),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        peer.name,
                        color = TextPrimary,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp,
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(
                                (if (peer.connected) colors.neonGreen else colors.neonRed).copy(alpha = 0.18f)
                            )
                            .border(
                                1.dp,
                                (if (peer.connected) colors.neonGreen else colors.neonRed).copy(alpha = 0.5f),
                                RoundedCornerShape(4.dp),
                            )
                            .padding(horizontal = 6.dp, vertical = 1.dp),
                    ) {
                        Text(
                            if (peer.connected) "BAGLI" else "BAGLI DEGIL",
                            color = if (peer.connected) colors.neonGreen else colors.neonRed,
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }

                Spacer(modifier = Modifier.height(6.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    Column {
                        Text("RX", color = TextSecondary, fontSize = 10.sp)
                        Text(formatBytes(peer.transferRx), color = colors.neonCyan, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                    }
                    Column {
                        Text("TX", color = TextSecondary, fontSize = 10.sp)
                        Text(formatBytes(peer.transferTx), color = colors.neonMagenta, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    "IP: ${peer.allowedIps}",
                    color = TextSecondary,
                    fontSize = 11.sp,
                )
                peer.latestHandshake?.let {
                    Text("Son el sikisma: $it", color = TextSecondary, fontSize = 10.sp)
                }
            }

            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                IconButton(onClick = onShowConfig, modifier = Modifier.size(36.dp)) {
                    Icon(Icons.Outlined.Settings, contentDescription = "Konfigurasyon", tint = colors.neonCyan, modifier = Modifier.size(18.dp))
                }
                IconButton(onClick = onDelete, modifier = Modifier.size(36.dp)) {
                    Icon(Icons.Outlined.Delete, contentDescription = "Sil", tint = colors.neonRed, modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

@Composable
private fun AddPeerDialog(
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
    colors: CyberpunkColors,
) {
    var name by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("Yeni Peer Ekle", color = colors.neonCyan, fontWeight = FontWeight.Bold) },
        text = {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("Peer Adi", color = TextSecondary) },
                singleLine = true,
                placeholder = { Text("telefon, laptop, vb.", color = TextSecondary.copy(alpha = 0.5f)) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = colors.neonCyan,
                    unfocusedBorderColor = colors.glassBorder,
                    focusedLabelColor = colors.neonCyan,
                    cursorColor = colors.neonCyan,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary,
                ),
            )
        },
        confirmButton = {
            Button(
                onClick = { if (name.isNotBlank()) onConfirm(name.trim()) },
                enabled = name.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
            ) { Text("Ekle", color = Color.Black) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Iptal", color = TextSecondary) }
        },
    )
}

@Composable
private fun PeerConfigDialog(
    peerName: String,
    config: VpnPeerConfigDto,
    onDismiss: () -> Unit,
    colors: CyberpunkColors,
) {
    val clipboardManager = LocalClipboardManager.current

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Text("$peerName Konfigurasyonu", color = colors.neonCyan, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Config text in a monospace box
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFF0A0A14))
                        .border(1.dp, colors.glassBorder, RoundedCornerShape(8.dp))
                        .padding(12.dp),
                ) {
                    Text(
                        config.configText,
                        color = colors.neonGreen,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        lineHeight = 16.sp,
                    )
                }

                // Copy button
                Button(
                    onClick = {
                        clipboardManager.setText(AnnotatedString(config.configText))
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan.copy(alpha = 0.8f)),
                ) {
                    Icon(Icons.Outlined.ContentCopy, contentDescription = null, tint = Color.Black, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Konfigurasyonu Kopyala", color = Color.Black, fontWeight = FontWeight.Medium)
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

private fun formatBytes(bytes: Long): String {
    return when {
        bytes >= 1_073_741_824 -> "%.1f GB".format(bytes / 1_073_741_824.0)
        bytes >= 1_048_576 -> "%.1f MB".format(bytes / 1_048_576.0)
        bytes >= 1_024 -> "%.1f KB".format(bytes / 1_024.0)
        else -> "$bytes B"
    }
}
