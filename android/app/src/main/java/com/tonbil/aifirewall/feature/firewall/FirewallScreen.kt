package com.tonbil.aifirewall.feature.firewall

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
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Shield
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
import androidx.compose.material3.MenuAnchorType
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.FirewallRuleCreateDto
import com.tonbil.aifirewall.data.remote.dto.FirewallRuleDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@Composable
fun FirewallScreen(
    onBack: () -> Unit,
    viewModel: FirewallViewModel = koinViewModel(),
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
        floatingActionButton = {
            if (!uiState.isLoading && uiState.error == null) {
                FloatingActionButton(
                    onClick = { viewModel.showAddDialog() },
                    containerColor = colors.neonCyan,
                    contentColor = Color.Black,
                ) {
                    Icon(Icons.Outlined.Add, contentDescription = "Kural Ekle")
                }
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
                    Icons.Outlined.Shield,
                    contentDescription = null,
                    tint = colors.neonCyan,
                    modifier = Modifier.size(24.dp),
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Guvenlik Duvari",
                    style = MaterialTheme.typography.titleLarge,
                    color = colors.neonCyan,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = { viewModel.refresh() }) {
                    Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = colors.neonAmber)
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

                        // Stats card
                        item {
                            FirewallStatsCard(
                                stats = uiState.stats,
                                connectionCount = uiState.connectionCount,
                                colors = colors,
                            )
                        }

                        // Rules header
                        item {
                            Text(
                                text = "Kurallar (${uiState.rules.size})",
                                color = colors.neonCyan,
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                                modifier = Modifier.padding(vertical = 4.dp),
                            )
                        }

                        if (uiState.rules.isEmpty()) {
                            item {
                                GlassCard(modifier = Modifier.fillMaxWidth()) {
                                    Text(
                                        "Henuz kural tanimlanmamis",
                                        color = TextSecondary,
                                        modifier = Modifier.padding(8.dp),
                                    )
                                }
                            }
                        } else {
                            items(uiState.rules, key = { it.id }) { rule ->
                                FirewallRuleItem(
                                    rule = rule,
                                    onToggle = { viewModel.toggleRule(rule.id) },
                                    onDelete = { viewModel.deleteRule(rule.id) },
                                    colors = colors,
                                )
                            }
                        }

                        item { Spacer(modifier = Modifier.height(80.dp)) }
                    }
                }
            }
        }

        // Add rule dialog
        if (uiState.showAddDialog) {
            AddFirewallRuleDialog(
                isLoading = uiState.isActionLoading,
                onDismiss = { viewModel.hideAddDialog() },
                onConfirm = { viewModel.createRule(it) },
                colors = colors,
            )
        }
    }
}

// ========== Stats Card ==========

@Composable
private fun FirewallStatsCard(
    stats: com.tonbil.aifirewall.data.remote.dto.FirewallStatsDto?,
    connectionCount: com.tonbil.aifirewall.data.remote.dto.ConnectionCountDto?,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = "Genel Bakis",
            color = colors.neonCyan,
            fontWeight = FontWeight.Bold,
            fontSize = 15.sp,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            MiniStat("Toplam Kural", "${stats?.totalRules ?: 0}", colors.neonCyan)
            MiniStat("Aktif", "${stats?.activeRules ?: 0}", colors.neonGreen)
            MiniStat("Gelen", "${stats?.inboundRules ?: 0}", colors.neonAmber)
            MiniStat("Giden", "${stats?.outboundRules ?: 0}", colors.neonMagenta)
        }
        Spacer(modifier = Modifier.height(12.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            MiniStat(
                "Engellenen (24s)",
                "${stats?.blockedPackets24h ?: 0}",
                colors.neonRed,
            )
            MiniStat(
                "Baglantilar",
                "${connectionCount?.active ?: stats?.activeConnections ?: 0}/${connectionCount?.max ?: stats?.maxConnections ?: 0}",
                colors.neonCyan,
            )
        }
        if (!stats?.openPorts.isNullOrEmpty()) {
            Spacer(modifier = Modifier.height(8.dp))
            Text("Acik Portlar: ${stats?.openPorts?.joinToString(", ")}", color = TextSecondary, fontSize = 12.sp)
        }
    }
}

@Composable
private fun MiniStat(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = color, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        Text(label, color = TextSecondary, fontSize = 11.sp)
    }
}

// ========== Rule Item ==========

@Composable
private fun FirewallRuleItem(
    rule: FirewallRuleDto,
    onToggle: () -> Unit,
    onDelete: () -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val actionColor = when (rule.action.lowercase()) {
        "accept" -> colors.neonGreen
        "drop" -> colors.neonRed
        "reject" -> colors.neonAmber
        else -> TextSecondary
    }

    GlassCard(
        modifier = Modifier.fillMaxWidth(),
        glowColor = if (rule.enabled) actionColor.copy(alpha = 0.3f) else null,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = rule.name.ifBlank { "Kural #${rule.id}" },
                        color = TextPrimary,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 14.sp,
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = rule.action.uppercase(),
                        color = actionColor,
                        fontWeight = FontWeight.Bold,
                        fontSize = 11.sp,
                        modifier = Modifier
                            .background(actionColor.copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                            .padding(horizontal = 6.dp, vertical = 2.dp),
                    )
                }
                Spacer(modifier = Modifier.height(4.dp))

                val dirLabel = if (rule.direction == "inbound") "Gelen" else "Giden"
                val detail = buildString {
                    append("$dirLabel | ${rule.protocol.uppercase()}")
                    if (!rule.port.isNullOrBlank()) append(" :${rule.port}")
                    if (!rule.sourceIp.isNullOrBlank()) append(" | Kaynak: ${rule.sourceIp}")
                    if (!rule.destIp.isNullOrBlank()) append(" | Hedef: ${rule.destIp}")
                }
                Text(detail, color = TextSecondary, fontSize = 12.sp)
            }

            Switch(
                checked = rule.enabled,
                onCheckedChange = { onToggle() },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.Black,
                    checkedTrackColor = colors.neonGreen,
                    uncheckedThumbColor = TextSecondary,
                    uncheckedTrackColor = colors.glassBorder,
                ),
            )

            IconButton(onClick = onDelete) {
                Icon(Icons.Outlined.Delete, contentDescription = "Sil", tint = colors.neonRed, modifier = Modifier.size(20.dp))
            }
        }
    }
}

// ========== Add Rule Dialog ==========

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddFirewallRuleDialog(
    isLoading: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (FirewallRuleCreateDto) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    var name by remember { mutableStateOf("") }
    var direction by remember { mutableStateOf("inbound") }
    var protocol by remember { mutableStateOf("tcp") }
    var port by remember { mutableStateOf("") }
    var sourceIp by remember { mutableStateOf("") }
    var destIp by remember { mutableStateOf("") }
    var action by remember { mutableStateOf("drop") }

    val tfColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = colors.neonCyan,
        unfocusedBorderColor = colors.glassBorder,
        focusedLabelColor = colors.neonCyan,
        cursorColor = colors.neonCyan,
        focusedTextColor = TextPrimary,
        unfocusedTextColor = TextPrimary,
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = com.tonbil.aifirewall.ui.theme.DarkSurface,
        title = {
            Text("Yeni Kural", color = colors.neonCyan, fontWeight = FontWeight.Bold)
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Kural Adi", color = TextSecondary) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = tfColors,
                )

                // Direction dropdown
                DropdownField(
                    label = "Yon",
                    selected = direction,
                    options = listOf("inbound" to "Gelen", "outbound" to "Giden"),
                    onSelect = { direction = it },
                    colors = colors,
                    tfColors = tfColors,
                )

                // Protocol dropdown
                DropdownField(
                    label = "Protokol",
                    selected = protocol,
                    options = listOf("tcp" to "TCP", "udp" to "UDP", "icmp" to "ICMP"),
                    onSelect = { protocol = it },
                    colors = colors,
                    tfColors = tfColors,
                )

                OutlinedTextField(
                    value = port,
                    onValueChange = { port = it },
                    label = { Text("Port", color = TextSecondary) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = tfColors,
                )

                OutlinedTextField(
                    value = sourceIp,
                    onValueChange = { sourceIp = it },
                    label = { Text("Kaynak IP (opsiyonel)", color = TextSecondary) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = tfColors,
                )

                OutlinedTextField(
                    value = destIp,
                    onValueChange = { destIp = it },
                    label = { Text("Hedef IP (opsiyonel)", color = TextSecondary) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = tfColors,
                )

                // Action dropdown
                DropdownField(
                    label = "Aksiyon",
                    selected = action,
                    options = listOf("accept" to "Kabul Et", "drop" to "Dusur", "reject" to "Reddet"),
                    onSelect = { action = it },
                    colors = colors,
                    tfColors = tfColors,
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    onConfirm(
                        FirewallRuleCreateDto(
                            name = name.ifBlank { "Kural" },
                            direction = direction,
                            protocol = protocol,
                            port = port.ifBlank { null },
                            sourceIp = sourceIp.ifBlank { null },
                            destIp = destIp.ifBlank { null },
                            action = action,
                        )
                    )
                },
                enabled = !isLoading,
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
            ) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), color = Color.Black, strokeWidth = 2.dp)
                } else {
                    Text("Olustur", color = Color.Black, fontWeight = FontWeight.Bold)
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = TextSecondary)
            }
        },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DropdownField(
    label: String,
    selected: String,
    options: List<Pair<String, String>>,
    onSelect: (String) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
    tfColors: androidx.compose.material3.TextFieldColors,
) {
    var expanded by remember { mutableStateOf(false) }
    val displayText = options.find { it.first == selected }?.second ?: selected

    ExposedDropdownMenuBox(
        expanded = expanded,
        onExpandedChange = { expanded = it },
    ) {
        OutlinedTextField(
            value = displayText,
            onValueChange = {},
            readOnly = true,
            label = { Text(label, color = TextSecondary) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .fillMaxWidth()
                .menuAnchor(MenuAnchorType.PrimaryNotEditable),
            colors = tfColors,
        )
        ExposedDropdownMenu(
            expanded = expanded,
            onDismissRequest = { expanded = false },
            containerColor = com.tonbil.aifirewall.ui.theme.DarkSurface,
        ) {
            options.forEach { (value, display) ->
                DropdownMenuItem(
                    text = { Text(display, color = if (value == selected) colors.neonCyan else TextPrimary) },
                    onClick = {
                        onSelect(value)
                        expanded = false
                    },
                )
            }
        }
    }
}
