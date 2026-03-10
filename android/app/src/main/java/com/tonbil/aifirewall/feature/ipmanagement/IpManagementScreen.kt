package com.tonbil.aifirewall.feature.ipmanagement

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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Block
import androidx.compose.material.icons.outlined.CheckBox
import androidx.compose.material.icons.outlined.CheckBoxOutlineBlank
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.LockOpen
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.BlockedIpCreateDto
import com.tonbil.aifirewall.data.remote.dto.BlockedIpDto
import com.tonbil.aifirewall.data.remote.dto.IpMgmtStatsDto
import com.tonbil.aifirewall.data.remote.dto.TrustedIpCreateDto
import com.tonbil.aifirewall.data.remote.dto.TrustedIpDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IpManagementScreen(
    onBack: () -> Unit,
    viewModel: IpManagementViewModel = koinViewModel(),
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
                        text = "IP Yonetimi",
                        color = colors.neonCyan,
                        style = MaterialTheme.typography.titleLarge,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.Outlined.ArrowBack,
                            contentDescription = "Geri",
                            tint = colors.neonCyan,
                        )
                    }
                },
                actions = {
                    if (uiState.selectedBlockedIps.isNotEmpty()) {
                        TextButton(
                            onClick = { viewModel.bulkUnblock(uiState.selectedBlockedIps.toList()) },
                        ) {
                            Text("Engel Kaldir (${uiState.selectedBlockedIps.size})", color = colors.neonAmber)
                        }
                    }
                    IconButton(onClick = { viewModel.refresh() }) {
                        Icon(
                            imageVector = Icons.Outlined.Refresh,
                            contentDescription = "Yenile",
                            tint = colors.neonCyan,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                ),
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    if (uiState.selectedTab == 0) viewModel.showAddTrustedDialog()
                    else viewModel.showBlockIpDialog()
                },
                containerColor = colors.neonCyan,
                contentColor = MaterialTheme.colorScheme.background,
            ) {
                Icon(imageVector = Icons.Outlined.Add, contentDescription = "Ekle")
            }
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
                        GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonRed) {
                            Text(
                                text = uiState.error ?: "",
                                color = colors.neonRed,
                                style = MaterialTheme.typography.bodyLarge,
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Button(
                                onClick = { viewModel.refresh() },
                                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
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
                        // Stats summary card
                        uiState.stats?.let { stats ->
                            IpMgmtStatsCard(
                                stats = stats,
                                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                            )
                        }

                        // Tab row
                        TabRow(
                            selectedTabIndex = uiState.selectedTab,
                            containerColor = MaterialTheme.colorScheme.background,
                            contentColor = colors.neonCyan,
                            indicator = { tabPositions ->
                                TabRowDefaults.SecondaryIndicator(
                                    modifier = Modifier.tabIndicatorOffset(tabPositions[uiState.selectedTab]),
                                    color = colors.neonCyan,
                                )
                            },
                        ) {
                            Tab(
                                selected = uiState.selectedTab == 0,
                                onClick = { viewModel.selectTab(0) },
                                text = {
                                    Text(
                                        text = "Guvenilir (${uiState.trustedIps.size})",
                                        color = if (uiState.selectedTab == 0) colors.neonCyan
                                        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                    )
                                },
                            )
                            Tab(
                                selected = uiState.selectedTab == 1,
                                onClick = { viewModel.selectTab(1) },
                                text = {
                                    Text(
                                        text = "Engellenen (${uiState.blockedIps.size})",
                                        color = if (uiState.selectedTab == 1) colors.neonRed
                                        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                                    )
                                },
                            )
                        }

                        when (uiState.selectedTab) {
                            0 -> TrustedIpList(
                                items = uiState.trustedIps,
                                onDelete = { viewModel.deleteTrusted(it) },
                            )
                            1 -> BlockedIpList(
                                items = uiState.blockedIps,
                                selectedIps = uiState.selectedBlockedIps,
                                onUnblock = { viewModel.unblockIp(it) },
                                onToggleSelect = { viewModel.toggleBlockedSelection(it) },
                                onSelectAll = { viewModel.selectAllBlocked() },
                                onClearSelection = { viewModel.clearSelection() },
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

    // Add trusted IP dialog
    if (uiState.showAddTrustedDialog) {
        AddTrustedIpDialog(
            onDismiss = { viewModel.hideAddTrustedDialog() },
            onConfirm = { viewModel.addTrusted(it) },
        )
    }

    // Block IP dialog
    if (uiState.showBlockIpDialog) {
        BlockIpDialog(
            onDismiss = { viewModel.hideBlockIpDialog() },
            onConfirm = { viewModel.blockIp(it) },
        )
    }
}

// ============================================================
// Stats summary card
// ============================================================

@Composable
private fun IpMgmtStatsCard(
    stats: IpMgmtStatsDto,
    modifier: Modifier = Modifier,
) {
    val colors = CyberpunkTheme.colors

    GlassCard(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            StatItem(label = "Guvenilir", value = stats.totalTrusted.toString(), color = colors.neonGreen)
            StatItem(label = "Engellenen", value = stats.totalBlocked.toString(), color = colors.neonRed)
            StatItem(label = "Otomatik", value = stats.autoBlocked.toString(), color = colors.neonAmber)
            StatItem(label = "Manuel", value = stats.manualBlocked.toString(), color = colors.neonMagenta)
        }
    }
}

@Composable
private fun StatItem(
    label: String,
    value: String,
    color: androidx.compose.ui.graphics.Color,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            text = value,
            style = MaterialTheme.typography.headlineSmall,
            color = color,
        )
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
        )
    }
}

// ============================================================
// Trusted IP list
// ============================================================

@Composable
private fun TrustedIpList(
    items: List<TrustedIpDto>,
    onDelete: (Int) -> Unit,
) {
    if (items.isEmpty()) {
        EmptyState(message = "Guvenilir IP listesi bos", icon = Icons.Outlined.Security)
        return
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(items = items, key = { it.id }) { item ->
            TrustedIpCard(item = item, onDelete = { onDelete(item.id) })
        }
    }
}

@Composable
private fun TrustedIpCard(
    item: TrustedIpDto,
    onDelete: () -> Unit,
) {
    val colors = CyberpunkTheme.colors

    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonGreen.copy(alpha = 0.3f)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(colors.neonGreen),
            )
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = item.ipAddress,
                    style = MaterialTheme.typography.titleMedium,
                    color = colors.neonGreen,
                )
                if (!item.description.isNullOrBlank()) {
                    Text(
                        text = item.description,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                if (!item.createdAt.isNullOrBlank()) {
                    Text(
                        text = item.createdAt,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                    )
                }
            }
            IconButton(onClick = onDelete) {
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

// ============================================================
// Blocked IP list
// ============================================================

@Composable
private fun BlockedIpList(
    items: List<BlockedIpDto>,
    selectedIps: Set<String>,
    onUnblock: (String) -> Unit,
    onToggleSelect: (String) -> Unit,
    onSelectAll: () -> Unit,
    onClearSelection: () -> Unit,
) {
    val colors = CyberpunkTheme.colors

    if (items.isEmpty()) {
        EmptyState(message = "Engellenen IP yok", icon = Icons.Outlined.Block)
        return
    }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        // Bulk selection toolbar
        if (selectedIps.isNotEmpty()) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = "${selectedIps.size} secili",
                        style = MaterialTheme.typography.bodyMedium,
                        color = colors.neonAmber,
                        modifier = Modifier.weight(1f),
                    )
                    TextButton(onClick = onSelectAll) {
                        Text("Tumunu Sec", color = colors.neonCyan, style = MaterialTheme.typography.labelSmall)
                    }
                    TextButton(onClick = onClearSelection) {
                        Text("Iptal", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f), style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        }

        items(items = items, key = { it.ipAddress }) { item ->
            BlockedIpCard(
                item = item,
                isSelected = item.ipAddress in selectedIps,
                onUnblock = { onUnblock(item.ipAddress) },
                onToggleSelect = { onToggleSelect(item.ipAddress) },
            )
        }
    }
}

@Composable
private fun BlockedIpCard(
    item: BlockedIpDto,
    isSelected: Boolean,
    onUnblock: () -> Unit,
    onToggleSelect: () -> Unit,
) {
    val colors = CyberpunkTheme.colors
    val glowColor = if (isSelected) colors.neonAmber else colors.neonRed.copy(alpha = 0.3f)

    GlassCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onToggleSelect),
        glowColor = glowColor,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Selection checkbox
            Icon(
                imageVector = if (isSelected) Icons.Outlined.CheckBox else Icons.Outlined.CheckBoxOutlineBlank,
                contentDescription = null,
                tint = if (isSelected) colors.neonAmber else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                modifier = Modifier.size(20.dp),
            )

            Spacer(Modifier.width(10.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(
                        text = item.ipAddress,
                        style = MaterialTheme.typography.titleMedium,
                        color = colors.neonRed,
                    )
                    // Country flag emoji
                    item.countryCode?.let { code ->
                        val flag = countryCodeToFlag(code)
                        Text(text = flag, style = MaterialTheme.typography.bodyMedium)
                    }
                    // Abuse score badge
                    item.abuseScore?.let { score ->
                        val badgeColor = when {
                            score >= 80 -> colors.neonRed
                            score >= 50 -> colors.neonAmber
                            else -> colors.neonGreen
                        }
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(badgeColor.copy(alpha = 0.2f))
                                .border(1.dp, badgeColor.copy(alpha = 0.5f), RoundedCornerShape(4.dp))
                                .padding(horizontal = 6.dp, vertical = 2.dp),
                        ) {
                            Text(
                                text = "Abuse: $score",
                                style = MaterialTheme.typography.labelSmall,
                                color = badgeColor,
                            )
                        }
                    }
                }

                // Source badge
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    val sourceColor = if (item.source == "manual") colors.neonMagenta else colors.neonAmber
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(sourceColor.copy(alpha = 0.15f))
                            .padding(horizontal = 5.dp, vertical = 1.dp),
                    ) {
                        Text(
                            text = if (item.source == "manual") "Manuel" else "Otomatik",
                            style = MaterialTheme.typography.labelSmall,
                            color = sourceColor,
                        )
                    }
                    if (!item.reason.isNullOrBlank()) {
                        Text(
                            text = item.reason,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                }

                if (!item.expiresAt.isNullOrBlank()) {
                    Text(
                        text = "Bitis: ${item.expiresAt}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                    )
                }
            }

            // Unblock button
            IconButton(onClick = onUnblock) {
                Icon(
                    imageVector = Icons.Outlined.LockOpen,
                    contentDescription = "Engeli Kaldir",
                    tint = colors.neonGreen,
                    modifier = Modifier.size(20.dp),
                )
            }
        }
    }
}

// ============================================================
// Dialogs
// ============================================================

@Composable
private fun AddTrustedIpDialog(
    onDismiss: () -> Unit,
    onConfirm: (TrustedIpCreateDto) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var ipAddress by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }

    val textFieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.neonCyan,
        unfocusedBorderColor = colors.glassBorder,
        focusedLabelColor = colors.neonCyan,
        unfocusedLabelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
        cursorColor = colors.neonCyan,
        focusedTextColor = MaterialTheme.colorScheme.onSurface,
        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = MaterialTheme.colorScheme.surface,
        title = {
            Text(
                text = "Guvenilir IP Ekle",
                color = colors.neonCyan,
                style = MaterialTheme.typography.titleLarge,
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = ipAddress,
                    onValueChange = { ipAddress = it },
                    label = { Text("IP Adresi") },
                    placeholder = { Text("192.168.1.100", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                    colors = textFieldColors,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("Aciklama (opsiyonel)") },
                    singleLine = true,
                    colors = textFieldColors,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (ipAddress.isNotBlank()) {
                        onConfirm(
                            TrustedIpCreateDto(
                                ipAddress = ipAddress.trim(),
                                description = description.takeIf { it.isNotBlank() },
                            )
                        )
                    }
                },
                enabled = ipAddress.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
            ) {
                Text("Ekle", color = MaterialTheme.colorScheme.background)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
            }
        },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BlockIpDialog(
    onDismiss: () -> Unit,
    onConfirm: (BlockedIpCreateDto) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var ipAddress by remember { mutableStateOf("") }
    var reason by remember { mutableStateOf("") }
    var selectedDuration by remember { mutableStateOf("1h") }
    var durationMenuExpanded by remember { mutableStateOf(false) }

    val durations = listOf(
        "1h" to "1 Saat",
        "6h" to "6 Saat",
        "24h" to "24 Saat",
        "7d" to "7 Gun",
        "30d" to "30 Gun",
        "permanent" to "Kalici",
    )

    val textFieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.neonRed,
        unfocusedBorderColor = colors.glassBorder,
        focusedLabelColor = colors.neonRed,
        unfocusedLabelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
        cursorColor = colors.neonRed,
        focusedTextColor = MaterialTheme.colorScheme.onSurface,
        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = MaterialTheme.colorScheme.surface,
        title = {
            Text(
                text = "IP Engelle",
                color = colors.neonRed,
                style = MaterialTheme.typography.titleLarge,
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = ipAddress,
                    onValueChange = { ipAddress = it },
                    label = { Text("IP Adresi") },
                    placeholder = { Text("1.2.3.4", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                    colors = textFieldColors,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = reason,
                    onValueChange = { reason = it },
                    label = { Text("Neden (opsiyonel)") },
                    singleLine = true,
                    colors = textFieldColors,
                    modifier = Modifier.fillMaxWidth(),
                )
                ExposedDropdownMenuBox(
                    expanded = durationMenuExpanded,
                    onExpandedChange = { durationMenuExpanded = it },
                ) {
                    OutlinedTextField(
                        value = durations.find { it.first == selectedDuration }?.second ?: selectedDuration,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Sure") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = durationMenuExpanded) },
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = colors.neonRed,
                            unfocusedBorderColor = colors.glassBorder,
                            focusedLabelColor = colors.neonRed,
                        ),
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor(),
                    )
                    ExposedDropdownMenu(
                        expanded = durationMenuExpanded,
                        onDismissRequest = { durationMenuExpanded = false },
                    ) {
                        durations.forEach { (value, label) ->
                            DropdownMenuItem(
                                text = { Text(label) },
                                onClick = {
                                    selectedDuration = value
                                    durationMenuExpanded = false
                                },
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    if (ipAddress.isNotBlank()) {
                        onConfirm(
                            BlockedIpCreateDto(
                                ipAddress = ipAddress.trim(),
                                reason = reason.takeIf { it.isNotBlank() },
                                duration = selectedDuration,
                            )
                        )
                    }
                },
                enabled = ipAddress.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonRed),
            ) {
                Text("Engelle", color = MaterialTheme.colorScheme.background)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
            }
        },
    )
}

// ============================================================
// Empty state
// ============================================================

@Composable
private fun EmptyState(
    message: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f),
                modifier = Modifier.size(48.dp),
            )
            Text(
                text = message,
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
            )
        }
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
