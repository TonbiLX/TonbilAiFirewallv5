package com.tonbil.aifirewall.feature.settings

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
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Send
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Tab
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.ChatMessageDto
import com.tonbil.aifirewall.data.remote.dto.DhcpLeaseDto
import com.tonbil.aifirewall.data.remote.dto.DhcpStatsDto
import com.tonbil.aifirewall.data.remote.dto.ProfileResponseDto
import com.tonbil.aifirewall.data.remote.dto.ServiceStatusDto
import com.tonbil.aifirewall.data.remote.dto.SystemOverviewDto
import com.tonbil.aifirewall.data.remote.dto.TelegramConfigDto
import com.tonbil.aifirewall.data.remote.dto.TelegramConfigUpdateDto
import com.tonbil.aifirewall.data.remote.dto.WifiClientDto
import com.tonbil.aifirewall.data.remote.dto.WifiStatusDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

private val tabs = listOf("Profil", "DHCP", "WiFi", "Telegram", "Sistem", "Sohbet")

@Composable
fun SettingsScreen(viewModel: SettingsViewModel = koinViewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val snackbarHostState = remember { SnackbarHostState() }

    // Show action message as snackbar
    LaunchedEffect(uiState.actionMessage) {
        uiState.actionMessage?.let { message ->
            snackbarHostState.showSnackbar(message)
            viewModel.clearActionMessage()
        }
    }

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
        floatingActionButton = {
            if (!uiState.isLoading && uiState.error == null) {
                when (uiState.selectedTab) {
                    0 -> {
                        FloatingActionButton(
                            onClick = { viewModel.showAddProfileDialog() },
                            containerColor = colors.neonCyan,
                            contentColor = Color.Black,
                        ) {
                            Icon(Icons.Outlined.Add, contentDescription = "Profil Ekle")
                        }
                    }
                    1 -> {
                        FloatingActionButton(
                            onClick = { viewModel.showAddStaticLeaseDialog() },
                            containerColor = colors.neonMagenta,
                            contentColor = Color.White,
                        ) {
                            Icon(Icons.Outlined.Add, contentDescription = "Statik IP Ekle")
                        }
                    }
                }
            }
        },
        containerColor = Color.Transparent,
    ) { paddingValues ->
        Box(modifier = Modifier.padding(paddingValues)) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.background),
            ) {
                // Header
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        imageVector = Icons.Outlined.Settings,
                        contentDescription = null,
                        tint = colors.neonCyan,
                        modifier = Modifier.size(28.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Ayarlar",
                        style = MaterialTheme.typography.headlineMedium,
                        color = colors.neonCyan,
                        modifier = Modifier.weight(1f),
                    )
                    if (uiState.isActionLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = colors.neonMagenta,
                            strokeWidth = 2.dp,
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    if (uiState.isRefreshing) {
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

                // Tabs
                ScrollableTabRow(
                    selectedTabIndex = uiState.selectedTab,
                    containerColor = Color.Transparent,
                    contentColor = colors.neonCyan,
                    edgePadding = 8.dp,
                ) {
                    tabs.forEachIndexed { index, title ->
                        Tab(
                            selected = uiState.selectedTab == index,
                            onClick = { viewModel.selectTab(index) },
                            text = {
                                Text(
                                    text = title,
                                    color = if (uiState.selectedTab == index)
                                        colors.neonCyan else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                )
                            },
                        )
                    }
                }

                // Content
                when {
                    uiState.isLoading -> {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center,
                        ) {
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
                                Text(
                                    text = uiState.error ?: "",
                                    color = colors.neonRed,
                                )
                            }
                        }
                    }
                    else -> {
                        when (uiState.selectedTab) {
                            0 -> ProfileTab(uiState.profiles, viewModel)
                            1 -> DhcpTab(uiState.dhcpStats, uiState.dhcpLeases, viewModel)
                            2 -> WifiTab(uiState.wifiStatus, uiState.wifiClients, viewModel)
                            3 -> TelegramTab(uiState.telegramConfig, viewModel)
                            4 -> SystemTab(uiState.systemOverview, uiState.systemServices)
                            5 -> ChatTab(
                                chatHistory = uiState.chatHistory,
                                chatInput = uiState.chatInput,
                                chatLoading = uiState.chatLoading,
                                onInputChange = { viewModel.updateChatInput(it) },
                                onSend = { viewModel.sendChat() },
                            )
                        }
                    }
                }
            }
        }
    }

    // ---- Dialogs ----

    if (uiState.showAddProfileDialog) {
        AddProfileDialog(
            onDismiss = { viewModel.hideAddProfileDialog() },
            onCreate = { name, bandwidth, filters ->
                viewModel.createProfile(name, bandwidth, filters)
            },
        )
    }

    if (uiState.showAddStaticLeaseDialog) {
        AddStaticLeaseDialog(
            onDismiss = { viewModel.hideAddStaticLeaseDialog() },
            onCreate = { mac, ip, hostname ->
                viewModel.createStaticLease(mac, ip, hostname)
            },
        )
    }

    if (uiState.showEditWifiDialog) {
        EditWifiDialog(
            currentStatus = uiState.wifiStatus,
            onDismiss = { viewModel.hideEditWifiDialog() },
            onSave = { ssid, password, channel ->
                viewModel.updateWifiConfig(ssid, password, channel)
            },
        )
    }

    if (uiState.showEditTelegramDialog) {
        EditTelegramDialog(
            currentConfig = uiState.telegramConfig,
            onDismiss = { viewModel.hideEditTelegramDialog() },
            onSave = { dto -> viewModel.updateTelegramConfig(dto) },
        )
    }
}

// ---- Dialog: Add Profile ----

@Composable
private fun AddProfileDialog(
    onDismiss: () -> Unit,
    onCreate: (name: String, bandwidth: Float?, filters: List<String>) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var name by remember { mutableStateOf("") }
    var bandwidth by remember { mutableStateOf("") }
    var filtersText by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1A2E),
        titleContentColor = colors.neonCyan,
        title = { Text("Yeni Profil") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Profil Adi", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
                OutlinedTextField(
                    value = bandwidth,
                    onValueChange = { bandwidth = it },
                    label = { Text("Bant Limiti (Mbps)", color = colors.neonAmber.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    colors = dialogTextFieldColors(),
                )
                OutlinedTextField(
                    value = filtersText,
                    onValueChange = { filtersText = it },
                    label = { Text("Filtreler (virgul ile)", color = colors.neonMagenta.copy(alpha = 0.7f)) },
                    placeholder = { Text("adult, gambling, malware", color = Color.White.copy(alpha = 0.3f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val bw = bandwidth.toFloatOrNull()
                    val filters = filtersText
                        .split(",")
                        .map { it.trim() }
                        .filter { it.isNotBlank() }
                    onCreate(name.trim(), bw, filters)
                },
                enabled = name.isNotBlank(),
            ) {
                Text("Olustur", color = colors.neonCyan)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = colors.neonRed)
            }
        },
    )
}

// ---- Dialog: Add Static Lease ----

@Composable
private fun AddStaticLeaseDialog(
    onDismiss: () -> Unit,
    onCreate: (mac: String, ip: String, hostname: String?) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var mac by remember { mutableStateOf("") }
    var ip by remember { mutableStateOf("") }
    var hostname by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1A2E),
        titleContentColor = colors.neonMagenta,
        title = { Text("Statik IP Ata") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = mac,
                    onValueChange = { mac = it },
                    label = { Text("MAC Adresi", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    placeholder = { Text("AA:BB:CC:DD:EE:FF", color = Color.White.copy(alpha = 0.3f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
                OutlinedTextField(
                    value = ip,
                    onValueChange = { ip = it },
                    label = { Text("IP Adresi", color = colors.neonAmber.copy(alpha = 0.7f)) },
                    placeholder = { Text("192.168.1.100", color = Color.White.copy(alpha = 0.3f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
                OutlinedTextField(
                    value = hostname,
                    onValueChange = { hostname = it },
                    label = { Text("Hostname (opsiyonel)", color = colors.neonGreen.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val hn = hostname.trim().ifBlank { null }
                    onCreate(mac.trim(), ip.trim(), hn)
                },
                enabled = mac.isNotBlank() && ip.isNotBlank(),
            ) {
                Text("Ekle", color = colors.neonMagenta)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = colors.neonRed)
            }
        },
    )
}

// ---- Dialog: Edit WiFi ----

@Composable
private fun EditWifiDialog(
    currentStatus: WifiStatusDto?,
    onDismiss: () -> Unit,
    onSave: (ssid: String?, password: String?, channel: Int?) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var ssid by remember { mutableStateOf(currentStatus?.ssid ?: "") }
    var password by remember { mutableStateOf("") }
    var channel by remember { mutableStateOf(currentStatus?.channel?.toString() ?: "") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1A2E),
        titleContentColor = colors.neonAmber,
        title = { Text("WiFi Ayarlari") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = ssid,
                    onValueChange = { ssid = it },
                    label = { Text("SSID", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("Sifre (bos birakılırsa degismez)", color = colors.neonAmber.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
                OutlinedTextField(
                    value = channel,
                    onValueChange = { channel = it },
                    label = { Text("Kanal", color = colors.neonMagenta.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    colors = dialogTextFieldColors(),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val s = ssid.trim().ifBlank { null }
                    val p = password.trim().ifBlank { null }
                    val c = channel.trim().toIntOrNull()
                    onSave(s, p, c)
                },
            ) {
                Text("Kaydet", color = colors.neonAmber)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = colors.neonRed)
            }
        },
    )
}

// ---- Dialog: Edit Telegram ----

@Composable
private fun EditTelegramDialog(
    currentConfig: TelegramConfigDto?,
    onDismiss: () -> Unit,
    onSave: (TelegramConfigUpdateDto) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var botToken by remember { mutableStateOf("") }
    var chatId by remember { mutableStateOf(currentConfig?.chatId ?: "") }
    var enabled by remember { mutableStateOf(currentConfig?.enabled ?: false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF1A1A2E),
        titleContentColor = colors.neonGreen,
        title = { Text("Telegram Yapilandirmasi") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = "Bot Aktif",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.White,
                        modifier = Modifier.weight(1f),
                    )
                    Switch(
                        checked = enabled,
                        onCheckedChange = { enabled = it },
                        colors = cyberpunkSwitchColors(),
                    )
                }
                OutlinedTextField(
                    value = botToken,
                    onValueChange = { botToken = it },
                    label = { Text("Bot Token (bos = degismez)", color = colors.neonAmber.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
                OutlinedTextField(
                    value = chatId,
                    onValueChange = { chatId = it },
                    label = { Text("Chat ID", color = colors.neonCyan.copy(alpha = 0.7f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = dialogTextFieldColors(),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    val token = botToken.trim().ifBlank { null }
                    val cid = chatId.trim().ifBlank { null }
                    onSave(
                        TelegramConfigUpdateDto(
                            botToken = token,
                            chatId = cid,
                            enabled = enabled,
                        )
                    )
                },
            ) {
                Text("Kaydet", color = colors.neonGreen)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = colors.neonRed)
            }
        },
    )
}

// ---- Shared dialog text field colors ----

@Composable
private fun dialogTextFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = CyberpunkTheme.colors.neonCyan,
    unfocusedBorderColor = Color.White.copy(alpha = 0.2f),
    cursorColor = CyberpunkTheme.colors.neonCyan,
    focusedTextColor = Color.White,
    unfocusedTextColor = Color.White.copy(alpha = 0.8f),
    focusedLabelColor = CyberpunkTheme.colors.neonCyan,
    unfocusedLabelColor = Color.White.copy(alpha = 0.5f),
)

// ---- Shared cyberpunk switch colors ----

@Composable
private fun cyberpunkSwitchColors() = SwitchDefaults.colors(
    checkedThumbColor = Color.Black,
    checkedTrackColor = CyberpunkTheme.colors.neonGreen,
    checkedBorderColor = CyberpunkTheme.colors.neonGreen,
    uncheckedThumbColor = Color.Gray,
    uncheckedTrackColor = Color.White.copy(alpha = 0.1f),
    uncheckedBorderColor = Color.White.copy(alpha = 0.3f),
)

// ---- Tab 0: Profil ----

@Composable
private fun ProfileTab(profiles: List<ProfileResponseDto>, viewModel: SettingsViewModel) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (profiles.isEmpty()) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Henuz profil tanimlanmamis",
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }
        items(profiles) { profile ->
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = profile.name,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            color = colors.neonCyan,
                        )
                        if (profile.profileType != null) {
                            Text(
                                text = profile.profileType,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            )
                        }
                    }
                    if (profile.bandwidthLimitMbps != null) {
                        MiniStatCard(
                            modifier = Modifier.width(80.dp),
                            label = "Bant",
                            value = "${profile.bandwidthLimitMbps} Mbps",
                            color = colors.neonAmber,
                        )
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    IconButton(
                        onClick = { viewModel.deleteProfile(profile.id) },
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Delete,
                            contentDescription = "Profil Sil",
                            tint = colors.neonRed,
                        )
                    }
                }
                if (profile.contentFilters.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        val filterColors = listOf(
                            colors.neonMagenta, colors.neonCyan, colors.neonAmber,
                            colors.neonGreen, colors.neonRed,
                        )
                        profile.contentFilters.forEachIndexed { idx, filter ->
                            FilterBadge(
                                text = filter,
                                color = filterColors[idx % filterColors.size],
                            )
                        }
                    }
                }
            }
        }
        // Bottom spacer for FAB
        item { Spacer(modifier = Modifier.height(72.dp)) }
    }
}

@Composable
private fun FilterBadge(text: String, color: Color) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(color.copy(alpha = 0.15f))
            .padding(horizontal = 6.dp, vertical = 2.dp),
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelSmall,
            color = color,
        )
    }
}

// ---- Tab 1: DHCP ----

@Composable
private fun DhcpTab(stats: DhcpStatsDto?, leases: List<DhcpLeaseDto>, viewModel: SettingsViewModel) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // dnsmasq status
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    StatusDot(isActive = stats?.dnsmasqRunning == true)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (stats?.dnsmasqRunning == true) "dnsmasq Calisiyor" else "dnsmasq Kapali",
                        style = MaterialTheme.typography.titleMedium,
                        color = if (stats?.dnsmasqRunning == true) colors.neonGreen else colors.neonRed,
                    )
                }
            }
        }
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Havuz",
                    value = "${stats?.activePools ?: 0}/${stats?.totalPools ?: 0}",
                    color = colors.neonCyan,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Atanan IP",
                    value = "${stats?.assignedIps ?: 0}/${stats?.totalIps ?: 0}",
                    color = colors.neonMagenta,
                )
            }
        }
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Statik",
                    value = "${stats?.staticLeases ?: 0}",
                    color = colors.neonAmber,
                )
                MiniStatCard(
                    modifier = Modifier.weight(1f),
                    label = "Dinamik",
                    value = "${stats?.dynamicLeases ?: 0}",
                    color = colors.neonGreen,
                )
            }
        }
        if (leases.isNotEmpty()) {
            item {
                Text(
                    text = "Aktif Kiralamalar",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(leases) { lease ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = lease.hostname ?: lease.macAddress,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Text(
                                text = lease.macAddress,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            )
                        }
                        Text(
                            text = lease.ipAddress,
                            style = MaterialTheme.typography.bodyMedium,
                            color = colors.neonCyan,
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        IconButton(
                            onClick = { viewModel.deleteStaticLease(lease.macAddress) },
                        ) {
                            Icon(
                                imageVector = Icons.Outlined.Delete,
                                contentDescription = "Sil",
                                tint = colors.neonRed,
                                modifier = Modifier.size(20.dp),
                            )
                        }
                    }
                }
            }
        }
        // Bottom spacer for FAB
        item { Spacer(modifier = Modifier.height(72.dp)) }
    }
}

// ---- Tab 2: WiFi ----

@Composable
private fun WifiTab(wifiStatus: WifiStatusDto?, wifiClients: List<WifiClientDto>, viewModel: SettingsViewModel) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // AP status with toggle and edit
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    StatusDot(isActive = wifiStatus?.running == true)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (wifiStatus?.running == true) "AP Aktif" else "AP Kapali",
                        style = MaterialTheme.typography.titleMedium,
                        color = if (wifiStatus?.running == true) colors.neonGreen else colors.neonRed,
                        modifier = Modifier.weight(1f),
                    )
                    Switch(
                        checked = wifiStatus?.running == true,
                        onCheckedChange = { viewModel.toggleWifi() },
                        colors = cyberpunkSwitchColors(),
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    IconButton(onClick = { viewModel.showEditWifiDialog() }) {
                        Icon(
                            imageVector = Icons.Outlined.Edit,
                            contentDescription = "WiFi Duzenle",
                            tint = colors.neonAmber,
                        )
                    }
                }
                if (wifiStatus != null) {
                    Spacer(modifier = Modifier.height(12.dp))
                    InfoRow("SSID", wifiStatus.ssid, colors.neonCyan)
                    Spacer(modifier = Modifier.height(6.dp))
                    InfoRow("Kanal", "${wifiStatus.channel}", colors.neonAmber)
                    Spacer(modifier = Modifier.height(6.dp))
                    InfoRow("Frekans", wifiStatus.frequency, colors.neonMagenta)
                    Spacer(modifier = Modifier.height(6.dp))
                    InfoRow("Bagli Istemci", "${wifiStatus.connectedClients}", colors.neonGreen)
                }
            }
        }
        if (wifiClients.isNotEmpty()) {
            item {
                Text(
                    text = "Bagli Istemciler",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(wifiClients) { client ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = client.hostname ?: client.macAddress,
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                            Text(
                                text = client.macAddress,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            )
                        }
                        Column(horizontalAlignment = Alignment.End) {
                            SignalBadge(signal = client.signalStrength)
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "${formatBytes(client.rxBytes)} / ${formatBytes(client.txBytes)}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SignalBadge(signal: Int) {
    val colors = CyberpunkTheme.colors
    val (color, label) = when {
        signal >= -50 -> colors.neonGreen to "Mukemmel"
        signal >= -60 -> colors.neonGreen to "Iyi"
        signal >= -70 -> colors.neonAmber to "Orta"
        else -> colors.neonRed to "Zayif"
    }
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(color.copy(alpha = 0.15f))
            .padding(horizontal = 6.dp, vertical = 2.dp),
    ) {
        Text(
            text = "$signal dBm ($label)",
            style = MaterialTheme.typography.labelSmall,
            color = color,
        )
    }
}

// ---- Tab 3: Telegram ----

@Composable
private fun TelegramTab(config: TelegramConfigDto?, viewModel: SettingsViewModel) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (config == null) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Telegram yapilandirmasi alinamadi",
                        color = colors.neonRed,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
            return@LazyColumn
        }
        // Bot config with edit and test buttons
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    StatusDot(isActive = config.enabled)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (config.enabled) "Bot Aktif" else "Bot Devre Disi",
                        style = MaterialTheme.typography.titleMedium,
                        color = if (config.enabled) colors.neonGreen else colors.neonRed,
                        modifier = Modifier.weight(1f),
                    )
                    Switch(
                        checked = config.enabled,
                        onCheckedChange = { newValue ->
                            viewModel.updateTelegramConfig(TelegramConfigUpdateDto(enabled = newValue))
                        },
                        colors = cyberpunkSwitchColors(),
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
                val maskedToken = if (config.botToken.length > 5)
                    config.botToken.take(5) + "***" else "***"
                InfoRow("Token", maskedToken, colors.neonAmber)
                Spacer(modifier = Modifier.height(6.dp))
                InfoRow("Chat ID", config.chatId, colors.neonCyan)
                Spacer(modifier = Modifier.height(12.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                ) {
                    TextButton(onClick = { viewModel.showEditTelegramDialog() }) {
                        Icon(
                            imageVector = Icons.Outlined.Edit,
                            contentDescription = null,
                            tint = colors.neonAmber,
                            modifier = Modifier.size(16.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Duzenle", color = colors.neonAmber)
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    TextButton(onClick = { viewModel.testTelegram() }) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Outlined.Send,
                            contentDescription = null,
                            tint = colors.neonGreen,
                            modifier = Modifier.size(16.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Test", color = colors.neonGreen)
                    }
                }
            }
        }
        // Notification settings with real switches
        item {
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "Bildirim Ayarlari",
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonCyan,
                )
                Spacer(modifier = Modifier.height(12.dp))
                NotificationToggleRow(
                    label = "Tehditler",
                    enabled = config.notifyThreats,
                    onToggle = { newValue ->
                        viewModel.updateTelegramConfig(TelegramConfigUpdateDto(notifyThreats = newValue))
                    },
                )
                Spacer(modifier = Modifier.height(8.dp))
                NotificationToggleRow(
                    label = "Cihazlar",
                    enabled = config.notifyDevices,
                    onToggle = { newValue ->
                        viewModel.updateTelegramConfig(TelegramConfigUpdateDto(notifyDevices = newValue))
                    },
                )
                Spacer(modifier = Modifier.height(8.dp))
                NotificationToggleRow(
                    label = "DDoS",
                    enabled = config.notifyDdos,
                    onToggle = { newValue ->
                        viewModel.updateTelegramConfig(TelegramConfigUpdateDto(notifyDdos = newValue))
                    },
                )
            }
        }
    }
}

@Composable
private fun NotificationToggleRow(label: String, enabled: Boolean, onToggle: (Boolean) -> Unit) {
    val colors = CyberpunkTheme.colors
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = if (enabled) "Acik" else "Kapali",
            style = MaterialTheme.typography.bodySmall,
            color = if (enabled) colors.neonGreen else colors.neonRed,
        )
        Spacer(modifier = Modifier.width(8.dp))
        Switch(
            checked = enabled,
            onCheckedChange = onToggle,
            colors = cyberpunkSwitchColors(),
        )
    }
}

// ---- Tab 4: Sistem ----

@Composable
private fun SystemTab(overview: SystemOverviewDto?, services: List<ServiceStatusDto>) {
    val colors = CyberpunkTheme.colors
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (overview != null) {
            item {
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "Sistem Durumu",
                        style = MaterialTheme.typography.titleMedium,
                        color = colors.neonCyan,
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    InfoRow("Uptime", overview.uptime, colors.neonGreen)
                    Spacer(modifier = Modifier.height(6.dp))
                    InfoRow("CPU Sicaklik", String.format("%.1f C", overview.cpuTemp), colors.neonAmber)
                    Spacer(modifier = Modifier.height(12.dp))

                    // CPU
                    UsageBar(
                        label = "CPU",
                        percent = overview.cpuPercent,
                        detail = "%${String.format("%.0f", overview.cpuPercent)}",
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    // RAM
                    UsageBar(
                        label = "RAM",
                        percent = overview.memoryPercent,
                        detail = "${overview.memoryUsedMb} / ${overview.memoryTotalMb} MB",
                    )
                    Spacer(modifier = Modifier.height(10.dp))

                    // Disk
                    UsageBar(
                        label = "Disk",
                        percent = overview.diskPercent,
                        detail = "${String.format("%.1f", overview.diskUsedGb)} / ${String.format("%.1f", overview.diskTotalGb)} GB",
                    )
                }
            }
        }
        if (services.isNotEmpty()) {
            item {
                Text(
                    text = "Servisler",
                    style = MaterialTheme.typography.titleSmall,
                    color = colors.neonCyan,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
            items(services) { svc ->
                GlassCard(modifier = Modifier.fillMaxWidth()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        StatusDot(isActive = svc.status == "running")
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = svc.displayName.ifBlank { svc.serviceName },
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.weight(1f),
                        )
                        val statusColor = when (svc.status) {
                            "running" -> colors.neonGreen
                            "stopped" -> colors.neonRed
                            "failed" -> colors.neonRed
                            else -> colors.neonAmber
                        }
                        Text(
                            text = svc.status,
                            style = MaterialTheme.typography.labelSmall,
                            color = statusColor,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun UsageBar(label: String, percent: Float, detail: String) {
    val colors = CyberpunkTheme.colors
    val barColor = when {
        percent < 60f -> colors.neonGreen
        percent < 80f -> colors.neonAmber
        else -> colors.neonRed
    }
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                modifier = Modifier.width(50.dp),
            )
            LinearProgressIndicator(
                progress = { (percent / 100f).coerceIn(0f, 1f) },
                modifier = Modifier
                    .weight(1f)
                    .height(8.dp)
                    .clip(RoundedCornerShape(4.dp)),
                color = barColor,
                trackColor = barColor.copy(alpha = 0.15f),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = detail,
                style = MaterialTheme.typography.labelSmall,
                color = barColor,
                modifier = Modifier.width(90.dp),
                textAlign = TextAlign.End,
            )
        }
    }
}

// ---- Tab 5: Sohbet (AI Chat) ----

@Composable
private fun ChatTab(
    chatHistory: List<ChatMessageDto>,
    chatInput: String,
    chatLoading: Boolean,
    onInputChange: (String) -> Unit,
    onSend: () -> Unit,
) {
    val colors = CyberpunkTheme.colors
    val listState = rememberLazyListState()

    LaunchedEffect(chatHistory.size) {
        if (chatHistory.isNotEmpty()) {
            listState.animateScrollToItem(chatHistory.size - 1)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
    ) {
        // Messages
        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(top = 8.dp),
            state = listState,
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            if (chatHistory.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier.fillMaxWidth(),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = "AI asistana bir soru sorun",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                        )
                    }
                }
            }
            items(chatHistory) { msg ->
                val isUser = msg.role == "user"
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
                ) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(
                                if (isUser) colors.neonCyan.copy(alpha = 0.15f)
                                else Color.White.copy(alpha = 0.05f)
                            )
                            .padding(horizontal = 12.dp, vertical = 8.dp)
                            .fillMaxWidth(0.8f),
                    ) {
                        Text(
                            text = msg.content,
                            style = MaterialTheme.typography.bodyMedium,
                            color = if (isUser) colors.neonCyan else MaterialTheme.colorScheme.onSurface,
                        )
                    }
                }
            }
            if (chatLoading) {
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Start,
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = colors.neonMagenta,
                            strokeWidth = 2.dp,
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Dusunuyor...",
                            style = MaterialTheme.typography.bodySmall,
                            color = colors.neonMagenta,
                        )
                    }
                }
            }
        }

        // Input row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = chatInput,
                onValueChange = onInputChange,
                modifier = Modifier.weight(1f),
                placeholder = {
                    Text(
                        text = "Mesajinizi yazin...",
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                    )
                },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = colors.neonCyan,
                    cursorColor = colors.neonCyan,
                    focusedTextColor = MaterialTheme.colorScheme.onSurface,
                    unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
                ),
                singleLine = true,
                shape = RoundedCornerShape(12.dp),
            )
            Spacer(modifier = Modifier.width(8.dp))
            IconButton(
                onClick = onSend,
                enabled = chatInput.isNotBlank() && !chatLoading,
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Outlined.Send,
                    contentDescription = "Gonder",
                    tint = if (chatInput.isNotBlank() && !chatLoading)
                        colors.neonCyan else colors.neonCyan.copy(alpha = 0.3f),
                )
            }
        }
    }
}

// ---- Shared Components ----

@Composable
private fun StatusDot(isActive: Boolean) {
    val colors = CyberpunkTheme.colors
    Box(
        modifier = Modifier
            .size(10.dp)
            .clip(CircleShape)
            .background(if (isActive) colors.neonGreen else colors.neonRed),
    )
}

@Composable
private fun MiniStatCard(
    modifier: Modifier = Modifier,
    label: String,
    value: String,
    color: Color,
) {
    GlassCard(modifier = modifier) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.titleLarge,
            color = color,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
private fun InfoRow(label: String, value: String, color: Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
            modifier = Modifier.width(120.dp),
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            color = color,
        )
    }
}

private fun formatBytes(bytes: Long): String {
    return when {
        bytes >= 1_073_741_824 -> String.format("%.1f GB", bytes / 1_073_741_824.0)
        bytes >= 1_048_576 -> String.format("%.1f MB", bytes / 1_048_576.0)
        bytes >= 1_024 -> String.format("%.1f KB", bytes / 1_024.0)
        else -> "$bytes B"
    }
}

@Suppress("unused")
private fun formatCount(count: Int): String {
    return when {
        count >= 1_000_000 -> String.format("%.1fM", count / 1_000_000.0)
        count >= 1_000 -> String.format("%.1fK", count / 1_000.0)
        else -> count.toString()
    }
}
