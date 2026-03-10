package com.tonbil.aifirewall.feature.dnsblocking

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuDefaults
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.BlocklistDto
import com.tonbil.aifirewall.data.remote.dto.DnsRuleDto
import com.tonbil.aifirewall.data.remote.dto.DnsStatsDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkColors
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@Composable
fun DnsBlockingScreen(
    onBack: () -> Unit,
    viewModel: DnsBlockingViewModel = koinViewModel(),
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

    if (uiState.showAddBlocklistDialog) {
        AddBlocklistDialog(
            onDismiss = { viewModel.hideAddBlocklistDialog() },
            onConfirm = { name, url -> viewModel.addBlocklist(name, url) },
            colors = colors,
        )
    }

    if (uiState.showAddRuleDialog) {
        AddRuleDialog(
            onDismiss = { viewModel.hideAddRuleDialog() },
            onConfirm = { domain, action -> viewModel.addRule(domain, action) },
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
                    text = "DNS Engelleme",
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

                    // Stats summary
                    item {
                        DnsStatsRow(stats = uiState.stats, colors = colors)
                    }

                    // Blocklists header + refresh all button
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "Engelleme Listeleri",
                                color = colors.neonMagenta,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                            )
                            Row {
                                IconButton(onClick = { viewModel.refreshAllBlocklists() }, modifier = Modifier.size(36.dp)) {
                                    Icon(Icons.Outlined.Refresh, contentDescription = "Tumu Guncelle", tint = colors.neonGreen, modifier = Modifier.size(18.dp))
                                }
                                IconButton(onClick = { viewModel.showAddBlocklistDialog() }, modifier = Modifier.size(36.dp)) {
                                    Icon(Icons.Outlined.Add, contentDescription = "Liste Ekle", tint = colors.neonCyan, modifier = Modifier.size(18.dp))
                                }
                            }
                        }
                    }

                    if (uiState.blocklists.isEmpty()) {
                        item {
                            GlassCard(modifier = Modifier.fillMaxWidth()) {
                                Text("Engelleme listesi bulunamadi", color = TextSecondary, modifier = Modifier.padding(8.dp))
                            }
                        }
                    } else {
                        items(uiState.blocklists, key = { "bl_${it.id}" }) { blocklist ->
                            BlocklistCard(
                                blocklist = blocklist,
                                onToggle = { viewModel.toggleBlocklist(blocklist.id) },
                                onDelete = { viewModel.deleteBlocklist(blocklist.id) },
                                colors = colors,
                            )
                        }
                    }

                    // DNS Rules header
                    item {
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "Ozel Kurallar",
                                color = colors.neonMagenta,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                            )
                            IconButton(onClick = { viewModel.showAddRuleDialog() }, modifier = Modifier.size(36.dp)) {
                                Icon(Icons.Outlined.Add, contentDescription = "Kural Ekle", tint = colors.neonCyan, modifier = Modifier.size(18.dp))
                            }
                        }
                    }

                    if (uiState.rules.isEmpty()) {
                        item {
                            GlassCard(modifier = Modifier.fillMaxWidth()) {
                                Text("Ozel kural bulunamadi", color = TextSecondary, modifier = Modifier.padding(8.dp))
                            }
                        }
                    } else {
                        items(uiState.rules, key = { "rule_${it.id}" }) { rule ->
                            RuleCard(
                                rule = rule,
                                onDelete = { viewModel.deleteRule(rule.id) },
                                colors = colors,
                            )
                        }
                    }

                    item { Spacer(modifier = Modifier.height(24.dp)) }
                }
            }
        }
    }
}

@Composable
private fun DnsStatsRow(
    stats: DnsStatsDto?,
    colors: CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Text("24 Saat DNS Ozeti", color = colors.neonCyan, fontWeight = FontWeight.Bold, fontSize = 14.sp)
        Spacer(modifier = Modifier.height(10.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            StatItem("Sorgu", formatNumber(stats?.totalQueries24h ?: 0), colors.neonCyan)
            StatItem("Engel", formatNumber(stats?.blockedQueries24h ?: 0), colors.neonRed)
            StatItem("Oran", "%.1f%%".format(stats?.blockPercentage ?: 0f), colors.neonAmber)
            StatItem("Liste", "${stats?.activeBlocklists ?: 0}", colors.neonGreen)
        }
    }
}

@Composable
private fun StatItem(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = color, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        Text(label, color = TextSecondary, fontSize = 10.sp)
    }
}

@Composable
private fun BlocklistCard(
    blocklist: BlocklistDto,
    onToggle: () -> Unit,
    onDelete: () -> Unit,
    colors: CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    blocklist.name,
                    color = TextPrimary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    blocklist.url,
                    color = TextSecondary,
                    fontSize = 11.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(colors.neonCyan.copy(alpha = 0.12f))
                            .padding(horizontal = 6.dp, vertical = 2.dp),
                    ) {
                        Text(
                            "${formatNumber(blocklist.domainCount)} domain",
                            color = colors.neonCyan,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Medium,
                        )
                    }
                    blocklist.lastUpdated?.let {
                        Text(it, color = TextSecondary, fontSize = 10.sp)
                    }
                }
            }
            Switch(
                checked = blocklist.enabled,
                onCheckedChange = { onToggle() },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.Black,
                    checkedTrackColor = colors.neonGreen,
                    uncheckedThumbColor = TextSecondary,
                    uncheckedTrackColor = colors.glassBg,
                ),
            )
            IconButton(onClick = onDelete, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Outlined.Delete, contentDescription = "Sil", tint = colors.neonRed, modifier = Modifier.size(18.dp))
            }
        }
    }
}

@Composable
private fun RuleCard(
    rule: DnsRuleDto,
    onDelete: () -> Unit,
    colors: CyberpunkColors,
) {
    val (badgeColor, badgeLabel) = when (rule.action.lowercase()) {
        "block" -> colors.neonRed to "ENGELLE"
        "allow" -> colors.neonGreen to "IZIN VER"
        else -> colors.neonAmber to rule.action.uppercase()
    }

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(badgeColor.copy(alpha = 0.18f))
                            .border(1.dp, badgeColor.copy(alpha = 0.5f), RoundedCornerShape(4.dp))
                            .padding(horizontal = 8.dp, vertical = 2.dp),
                    ) {
                        Text(badgeLabel, color = badgeColor, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        rule.domain,
                        color = TextPrimary,
                        fontWeight = FontWeight.Medium,
                        fontSize = 14.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                rule.createdAt?.let {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(it, color = TextSecondary, fontSize = 10.sp)
                }
            }
            IconButton(onClick = onDelete, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Outlined.Delete, contentDescription = "Sil", tint = colors.neonRed, modifier = Modifier.size(18.dp))
            }
        }
    }
}

@Composable
private fun AddBlocklistDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String) -> Unit,
    colors: CyberpunkColors,
) {
    var name by remember { mutableStateOf("") }
    var url by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("Engelleme Listesi Ekle", color = colors.neonCyan, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Liste Adi", color = TextSecondary) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonCyan,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedLabelColor = colors.neonCyan,
                        cursorColor = colors.neonCyan,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                    ),
                )
                OutlinedTextField(
                    value = url,
                    onValueChange = { url = it },
                    label = { Text("URL", color = TextSecondary) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonCyan,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedLabelColor = colors.neonCyan,
                        cursorColor = colors.neonCyan,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                    ),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { if (name.isNotBlank() && url.isNotBlank()) onConfirm(name.trim(), url.trim()) },
                enabled = name.isNotBlank() && url.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
            ) { Text("Ekle", color = Color.Black) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Iptal", color = TextSecondary) }
        },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddRuleDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String) -> Unit,
    colors: CyberpunkColors,
) {
    var domain by remember { mutableStateOf("") }
    var action by remember { mutableStateOf("block") }
    var dropdownExpanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("DNS Kurali Ekle", color = colors.neonCyan, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = domain,
                    onValueChange = { domain = it },
                    label = { Text("Domain", color = TextSecondary) },
                    singleLine = true,
                    placeholder = { Text("ornek.com", color = TextSecondary.copy(alpha = 0.5f)) },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonCyan,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedLabelColor = colors.neonCyan,
                        cursorColor = colors.neonCyan,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                    ),
                )
                ExposedDropdownMenuBox(
                    expanded = dropdownExpanded,
                    onExpandedChange = { dropdownExpanded = !dropdownExpanded },
                ) {
                    OutlinedTextField(
                        value = if (action == "block") "Engelle" else "Izin Ver",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Islem", color = TextSecondary) },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = dropdownExpanded) },
                        modifier = Modifier
                            .menuAnchor()
                            .fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = colors.neonCyan,
                            unfocusedBorderColor = colors.glassBorder,
                            focusedLabelColor = colors.neonCyan,
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary,
                        ),
                    )
                    ExposedDropdownMenu(
                        expanded = dropdownExpanded,
                        onDismissRequest = { dropdownExpanded = false },
                        containerColor = DarkSurface,
                    ) {
                        DropdownMenuItem(
                            text = { Text("Engelle") },
                            onClick = { action = "block"; dropdownExpanded = false },
                            colors = MenuDefaults.itemColors(textColor = colors.neonRed),
                        )
                        DropdownMenuItem(
                            text = { Text("Izin Ver") },
                            onClick = { action = "allow"; dropdownExpanded = false },
                            colors = MenuDefaults.itemColors(textColor = colors.neonGreen),
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { if (domain.isNotBlank()) onConfirm(domain.trim(), action) },
                enabled = domain.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
            ) { Text("Ekle", color = Color.Black) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Iptal", color = TextSecondary) }
        },
    )
}

private fun formatNumber(n: Int): String {
    return when {
        n >= 1_000_000 -> "%.1fM".format(n / 1_000_000f)
        n >= 1_000 -> "%.1fK".format(n / 1_000f)
        else -> "$n"
    }
}
