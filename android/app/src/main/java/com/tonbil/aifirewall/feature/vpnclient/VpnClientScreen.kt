package com.tonbil.aifirewall.feature.vpnclient

import androidx.compose.foundation.background
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.LinkOff
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.VpnKey
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.FloatingActionButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SmallFloatingActionButton
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.VpnClientCreateDto
import com.tonbil.aifirewall.data.remote.dto.VpnClientImportDto
import com.tonbil.aifirewall.data.remote.dto.VpnClientServerDto
import com.tonbil.aifirewall.data.remote.dto.VpnClientStatusDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

// ---- Byte format helper ----
private fun formatBytes(bytes: Long): String {
    if (bytes < 1024) return "$bytes B"
    val kb = bytes / 1024.0
    if (kb < 1024) return "%.1f KB".format(kb)
    val mb = kb / 1024.0
    if (mb < 1024) return "%.1f MB".format(mb)
    return "%.2f GB".format(mb / 1024.0)
}

// ---- Screen entry ----

@Composable
fun VpnClientScreen(
    onBack: () -> Unit,
    viewModel: VpnClientViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val snackbarHostState = remember { SnackbarHostState() }

    // FAB expanded state
    var fabExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(state.actionMessage) {
        state.actionMessage?.let { msg ->
            snackbarHostState.showSnackbar(msg)
            viewModel.clearActionMessage()
        }
    }

    Scaffold(
        snackbarHost = {
            SnackbarHost(hostState = snackbarHostState) { data ->
                Snackbar(
                    snackbarData = data,
                    containerColor = colors.glassBg,
                    contentColor = colors.neonCyan,
                    shape = RoundedCornerShape(8.dp),
                )
            }
        },
        floatingActionButton = {
            Column(
                horizontalAlignment = Alignment.End,
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Secondary FABs — visible when expanded
                if (fabExpanded) {
                    // Import .conf
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Box(
                            modifier = Modifier
                                .background(
                                    color = colors.glassBg,
                                    shape = RoundedCornerShape(6.dp),
                                )
                                .padding(horizontal = 8.dp, vertical = 4.dp),
                        ) {
                            Text(
                                text = ".conf iceri aktar",
                                color = colors.neonMagenta,
                                fontSize = 12.sp,
                            )
                        }
                        SmallFloatingActionButton(
                            onClick = {
                                fabExpanded = false
                                viewModel.toggleImportDialog(true)
                            },
                            containerColor = colors.neonMagenta.copy(alpha = 0.15f),
                            contentColor = colors.neonMagenta,
                            elevation = FloatingActionButtonDefaults.elevation(0.dp),
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.Download,
                                contentDescription = "Konfigurasyon iceri aktar",
                            )
                        }
                    }

                    // Manual add
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Box(
                            modifier = Modifier
                                .background(
                                    color = colors.glassBg,
                                    shape = RoundedCornerShape(6.dp),
                                )
                                .padding(horizontal = 8.dp, vertical = 4.dp),
                        ) {
                            Text(
                                text = "Manuel ekle",
                                color = colors.neonCyan,
                                fontSize = 12.sp,
                            )
                        }
                        SmallFloatingActionButton(
                            onClick = {
                                fabExpanded = false
                                viewModel.toggleCreateDialog(true)
                            },
                            containerColor = colors.neonCyan.copy(alpha = 0.15f),
                            contentColor = colors.neonCyan,
                            elevation = FloatingActionButtonDefaults.elevation(0.dp),
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.Add,
                                contentDescription = "Manuel sunucu ekle",
                            )
                        }
                    }
                }

                // Primary FAB
                FloatingActionButton(
                    onClick = { fabExpanded = !fabExpanded },
                    containerColor = colors.neonCyan.copy(alpha = 0.2f),
                    contentColor = colors.neonCyan,
                    elevation = FloatingActionButtonDefaults.elevation(0.dp),
                ) {
                    Icon(
                        imageVector = if (fabExpanded) Icons.Outlined.LinkOff else Icons.Outlined.Add,
                        contentDescription = if (fabExpanded) "Kapat" else "Sunucu ekle",
                    )
                }
            }
        },
        containerColor = Color.Transparent,
    ) { paddingValues ->

        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background),
        ) {
            Column(modifier = Modifier.fillMaxSize()) {

                // ---- Top bar ----
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 4.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.Outlined.ArrowBack,
                            contentDescription = "Geri",
                            tint = colors.neonCyan,
                        )
                    }
                    Icon(
                        imageVector = Icons.Outlined.VpnKey,
                        contentDescription = null,
                        tint = colors.neonCyan,
                        modifier = Modifier.size(24.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "VPN Istemcisi",
                        style = MaterialTheme.typography.headlineMedium,
                        color = colors.neonCyan,
                        modifier = Modifier.weight(1f),
                    )
                    if (state.isRefreshing) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = colors.neonCyan,
                            strokeWidth = 2.dp,
                        )
                    } else {
                        IconButton(onClick = { viewModel.refresh() }) {
                            Icon(
                                imageVector = Icons.Outlined.Refresh,
                                contentDescription = "Yenile",
                                tint = colors.neonCyan,
                            )
                        }
                    }
                }

                when {
                    state.isLoading -> {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center,
                        ) {
                            CircularProgressIndicator(color = colors.neonCyan)
                        }
                    }

                    state.error != null -> {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(16.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            GlassCard(
                                modifier = Modifier.fillMaxWidth(),
                                glowColor = colors.neonRed,
                            ) {
                                Text(
                                    text = state.error ?: "",
                                    color = colors.neonRed,
                                )
                            }
                        }
                    }

                    else -> {
                        LazyColumn(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(horizontal = 16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                        ) {
                            item { Spacer(modifier = Modifier.height(4.dp)) }

                            // ---- Connection status card ----
                            item {
                                ConnectionStatusCard(
                                    status = state.status,
                                )
                            }

                            // ---- Stats summary ----
                            state.stats?.let { stats ->
                                item {
                                    GlassCard(modifier = Modifier.fillMaxWidth()) {
                                        Row(
                                            modifier = Modifier.fillMaxWidth(),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                        ) {
                                            StatItem(
                                                label = "Toplam Sunucu",
                                                value = "${stats.totalServers}",
                                                valueColor = colors.neonCyan,
                                            )
                                            StatItem(
                                                label = "Toplam Alindi",
                                                value = formatBytes(stats.totalTransferRx),
                                                valueColor = colors.neonGreen,
                                            )
                                            StatItem(
                                                label = "Toplam Gonderildi",
                                                value = formatBytes(stats.totalTransferTx),
                                                valueColor = colors.neonMagenta,
                                            )
                                        }
                                    }
                                }
                            }

                            // ---- Server list header ----
                            if (state.servers.isNotEmpty()) {
                                item {
                                    Text(
                                        text = "SUNUCULAR",
                                        color = CyberpunkTheme.colors.neonCyan,
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        letterSpacing = 2.sp,
                                        modifier = Modifier.padding(top = 4.dp, bottom = 2.dp),
                                    )
                                }
                            }

                            // ---- Server items ----
                            items(state.servers, key = { it.id }) { server ->
                                ServerItem(
                                    server = server,
                                    onActivate = { viewModel.activate(server.id) },
                                    onDeactivate = { viewModel.deactivate(server.id) },
                                    onDelete = { viewModel.deleteServer(server.id) },
                                    actionLoading = state.isActionLoading,
                                )
                            }

                            if (state.servers.isEmpty() && !state.isLoading) {
                                item {
                                    Box(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 32.dp),
                                        contentAlignment = Alignment.Center,
                                    ) {
                                        Text(
                                            text = "Henuz VPN sunucusu eklenmemis.\nSag alttaki + butonundan ekleyin.",
                                            color = CyberpunkTheme.colors.neonCyan.copy(alpha = 0.5f),
                                            style = MaterialTheme.typography.bodyMedium,
                                            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                                        )
                                    }
                                }
                            }

                            // Bottom spacing for FAB
                            item { Spacer(modifier = Modifier.height(80.dp)) }
                        }
                    }
                }
            }

        }
    }

    // ---- Create dialog ----
    if (state.showCreateDialog) {
        CreateServerDialog(
            onDismiss = { viewModel.toggleCreateDialog(false) },
            onConfirm = { dto -> viewModel.createServer(dto) },
        )
    }

    // ---- Import dialog ----
    if (state.showImportDialog) {
        ImportServerDialog(
            onDismiss = { viewModel.toggleImportDialog(false) },
            onConfirm = { dto -> viewModel.importServer(dto) },
        )
    }
}

// ---- Connection Status Card ----

@Composable
private fun ConnectionStatusCard(status: VpnClientStatusDto?) {
    val colors = CyberpunkTheme.colors
    val connected = status?.connected == true
    val accentColor = if (connected) colors.neonGreen else colors.neonRed

    GlassCard(
        modifier = Modifier.fillMaxWidth(),
        glowColor = accentColor,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Status dot
            Box(
                modifier = Modifier
                    .size(12.dp)
                    .clip(CircleShape)
                    .background(accentColor),
            )
            Spacer(modifier = Modifier.width(10.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (connected) "BAGLI" else "BAGLI DEGIL",
                    color = accentColor,
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp,
                    letterSpacing = 1.sp,
                    fontFamily = FontFamily.Monospace,
                )
                if (connected && status?.serverName != null) {
                    Text(
                        text = status.serverName,
                        color = colors.neonCyan,
                        style = MaterialTheme.typography.bodyMedium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    if (status.endpoint != null) {
                        Text(
                            text = status.endpoint,
                            color = colors.neonCyan.copy(alpha = 0.6f),
                            fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                } else if (!connected) {
                    Text(
                        text = "Hicbir sunucuya baglanilmadi",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }

            // Transfer stats (only when connected)
            if (connected && status != null) {
                Column(horizontalAlignment = Alignment.End) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "RX ",
                            color = colors.neonGreen.copy(alpha = 0.7f),
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                        )
                        Text(
                            text = formatBytes(status.transferRx),
                            color = colors.neonGreen,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "TX ",
                            color = colors.neonMagenta.copy(alpha = 0.7f),
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                        )
                        Text(
                            text = formatBytes(status.transferTx),
                            color = colors.neonMagenta,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.SemiBold,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                    if (status.connectedSince != null) {
                        Text(
                            text = status.connectedSince.take(16).replace("T", " "),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 9.sp,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                }
            }
        }
    }
}

// ---- Server Item ----

@Composable
private fun ServerItem(
    server: VpnClientServerDto,
    onActivate: () -> Unit,
    onDeactivate: () -> Unit,
    onDelete: () -> Unit,
    actionLoading: Boolean,
) {
    val colors = CyberpunkTheme.colors
    val isConnected = server.connected
    val isActive = server.active
    val cardGlow = when {
        isConnected -> colors.neonGreen
        isActive -> colors.neonCyan
        else -> null
    }

    GlassCard(
        modifier = Modifier.fillMaxWidth(),
        glowColor = cardGlow,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Status indicator
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(
                        when {
                            isConnected -> colors.neonGreen
                            isActive -> colors.neonCyan
                            else -> MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f)
                        }
                    ),
            )
            Spacer(modifier = Modifier.width(10.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(
                        text = server.name,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.bodyLarge,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f, fill = false),
                    )
                    // Connected badge
                    if (isConnected) {
                        Box(
                            modifier = Modifier
                                .background(
                                    color = colors.neonGreen.copy(alpha = 0.15f),
                                    shape = RoundedCornerShape(4.dp),
                                )
                                .padding(horizontal = 6.dp, vertical = 2.dp),
                        ) {
                            Text(
                                text = "BAGLI",
                                color = colors.neonGreen,
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 1.sp,
                                fontFamily = FontFamily.Monospace,
                            )
                        }
                    } else if (isActive) {
                        Box(
                            modifier = Modifier
                                .background(
                                    color = colors.neonCyan.copy(alpha = 0.12f),
                                    shape = RoundedCornerShape(4.dp),
                                )
                                .padding(horizontal = 6.dp, vertical = 2.dp),
                        ) {
                            Text(
                                text = "AKTIF",
                                color = colors.neonCyan,
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 1.sp,
                                fontFamily = FontFamily.Monospace,
                            )
                        }
                    }
                }
                Text(
                    text = "${server.endpoint}:${server.port}",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                if (server.dns != null) {
                    Text(
                        text = "DNS: ${server.dns}",
                        color = colors.neonAmber.copy(alpha = 0.7f),
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace,
                    )
                }
            }

            Spacer(modifier = Modifier.width(4.dp))

            // Action buttons
            Row(
                verticalAlignment = Alignment.CenterVertically,
            ) {
                if (actionLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        color = colors.neonCyan,
                        strokeWidth = 2.dp,
                    )
                } else {
                    if (isConnected) {
                        // Deactivate button
                        IconButton(
                            onClick = onDeactivate,
                            modifier = Modifier.size(36.dp),
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.LinkOff,
                                contentDescription = "Baglantıyi kes",
                                tint = colors.neonRed,
                                modifier = Modifier.size(18.dp),
                            )
                        }
                    } else {
                        // Activate button
                        IconButton(
                            onClick = onActivate,
                            modifier = Modifier.size(36.dp),
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.PlayArrow,
                                contentDescription = "Baglan",
                                tint = colors.neonGreen,
                                modifier = Modifier.size(18.dp),
                            )
                        }
                    }

                    // Delete button
                    IconButton(
                        onClick = onDelete,
                        modifier = Modifier.size(36.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Delete,
                            contentDescription = "Sil",
                            tint = colors.neonRed.copy(alpha = 0.7f),
                            modifier = Modifier.size(18.dp),
                        )
                    }
                }
            }
        }
    }
}

// ---- Stat Item ----

@Composable
private fun StatItem(
    label: String,
    value: String,
    valueColor: Color,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            color = valueColor,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            fontSize = 15.sp,
        )
        Text(
            text = label,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontSize = 10.sp,
        )
    }
}

// ---- Create Server Dialog ----

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CreateServerDialog(
    onDismiss: () -> Unit,
    onConfirm: (VpnClientCreateDto) -> Unit,
) {
    val colors = CyberpunkTheme.colors

    var name by remember { mutableStateOf("") }
    var endpoint by remember { mutableStateOf("") }
    var port by remember { mutableStateOf("51820") }
    var publicKey by remember { mutableStateOf("") }
    var privateKey by remember { mutableStateOf("") }
    var allowedIps by remember { mutableStateOf("0.0.0.0/0") }
    var dns by remember { mutableStateOf("") }

    val isValid = name.isNotBlank() && endpoint.isNotBlank() &&
        publicKey.isNotBlank() && privateKey.isNotBlank()

    val fieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.neonCyan,
        unfocusedBorderColor = colors.glassBorder,
        cursorColor = colors.neonCyan,
        focusedLabelColor = colors.neonCyan,
        unfocusedLabelColor = MaterialTheme.colorScheme.onSurfaceVariant,
        focusedTextColor = MaterialTheme.colorScheme.onSurface,
        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = MaterialTheme.colorScheme.surface,
        titleContentColor = colors.neonCyan,
        title = {
            Text(
                text = "Sunucu Ekle",
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                        OutlinedTextField(
                            value = name,
                            onValueChange = { name = it },
                            label = { Text("Sunucu Adi") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            colors = fieldColors,
                        )
                        OutlinedTextField(
                            value = endpoint,
                            onValueChange = { endpoint = it },
                            label = { Text("Endpoint (IP/hostname)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            colors = fieldColors,
                            placeholder = { Text("vpn.example.com", color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)) },
                        )
                        OutlinedTextField(
                            value = port,
                            onValueChange = { port = it },
                            label = { Text("Port") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            colors = fieldColors,
                        )
                        OutlinedTextField(
                            value = publicKey,
                            onValueChange = { publicKey = it },
                            label = { Text("Acik Anahtar (Public Key)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            colors = fieldColors,
                            placeholder = { Text("base64...", color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)) },
                        )
                        OutlinedTextField(
                            value = privateKey,
                            onValueChange = { privateKey = it },
                            label = { Text("Gizli Anahtar (Private Key)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            colors = fieldColors,
                            placeholder = { Text("base64...", color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)) },
                        )
                        OutlinedTextField(
                            value = allowedIps,
                            onValueChange = { allowedIps = it },
                            label = { Text("Izin Verilen IP'ler") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            colors = fieldColors,
                        )
                        OutlinedTextField(
                            value = dns,
                            onValueChange = { dns = it },
                            label = { Text("DNS (opsiyonel)") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                            colors = fieldColors,
                            placeholder = { Text("1.1.1.1", color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)) },
                        )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onConfirm(
                        VpnClientCreateDto(
                            name = name.trim(),
                            endpoint = endpoint.trim(),
                            port = port.toIntOrNull() ?: 51820,
                            publicKey = publicKey.trim(),
                            privateKey = privateKey.trim(),
                            allowedIps = allowedIps.trim(),
                            dns = dns.trim().takeIf { it.isNotBlank() },
                        )
                    )
                },
                enabled = isValid,
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.neonCyan.copy(alpha = 0.2f),
                    contentColor = colors.neonCyan,
                    disabledContainerColor = colors.glassBg,
                    disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
                ),
            ) {
                Text("Ekle")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.onSurfaceVariant),
            ) {
                Text("Iptal")
            }
        },
    )
}

// ---- Import Server Dialog ----

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ImportServerDialog(
    onDismiss: () -> Unit,
    onConfirm: (VpnClientImportDto) -> Unit,
) {
    val colors = CyberpunkTheme.colors

    var name by remember { mutableStateOf("") }
    var configText by remember { mutableStateOf("") }

    val isValid = name.isNotBlank() && configText.isNotBlank()

    val fieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.neonMagenta,
        unfocusedBorderColor = colors.glassBorder,
        cursorColor = colors.neonMagenta,
        focusedLabelColor = colors.neonMagenta,
        unfocusedLabelColor = MaterialTheme.colorScheme.onSurfaceVariant,
        focusedTextColor = MaterialTheme.colorScheme.onSurface,
        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = MaterialTheme.colorScheme.surface,
        titleContentColor = colors.neonMagenta,
        title = {
            Text(
                text = ".conf Iceri Aktar",
                fontWeight = FontWeight.Bold,
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Sunucu Adi") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = fieldColors,
                    placeholder = { Text("Sunucum", color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)) },
                )
                OutlinedTextField(
                    value = configText,
                    onValueChange = { configText = it },
                    label = { Text("WireGuard .conf icerik") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(200.dp),
                    colors = fieldColors,
                    placeholder = {
                        Text(
                            text = "[Interface]\nPrivateKey = ...\nAddress = ...\n\n[Peer]\nPublicKey = ...\nEndpoint = ...",
                            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                            fontFamily = FontFamily.Monospace,
                            fontSize = 11.sp,
                        )
                    },
                    textStyle = MaterialTheme.typography.bodySmall.copy(
                        fontFamily = FontFamily.Monospace,
                        color = MaterialTheme.colorScheme.onSurface,
                    ),
                    maxLines = Int.MAX_VALUE,
                )
                Text(
                    text = "WireGuard konfigurasyon dosyanizin tum icerigi yapistirin.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onConfirm(
                        VpnClientImportDto(
                            name = name.trim(),
                            configText = configText.trim(),
                        )
                    )
                },
                enabled = isValid,
                colors = ButtonDefaults.buttonColors(
                    containerColor = colors.neonMagenta.copy(alpha = 0.2f),
                    contentColor = colors.neonMagenta,
                    disabledContainerColor = colors.glassBg,
                    disabledContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
                ),
            ) {
                Text("Iceri Aktar")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.onSurfaceVariant),
            ) {
                Text("Iptal")
            }
        },
    )
}
