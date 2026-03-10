package com.tonbil.aifirewall.feature.insights

import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.ExpandLess
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material.icons.outlined.LockOpen
import androidx.compose.material.icons.outlined.Refresh
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.AiInsightDto
import com.tonbil.aifirewall.data.remote.dto.InsightBlockedIpDto
import com.tonbil.aifirewall.data.remote.dto.InsightThreatStatsDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@Composable
fun InsightsScreen(
    onBack: () -> Unit,
    viewModel: InsightsViewModel = koinViewModel(),
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

    if (uiState.showBlockIpDialog) {
        BlockIpDialog(
            onDismiss = { viewModel.hideBlockIpDialog() },
            onConfirm = { ip, reason -> viewModel.blockIp(ip, reason) },
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
                onClick = { viewModel.showBlockIpDialog() },
                containerColor = colors.neonRed.copy(alpha = 0.9f),
                contentColor = Color.Black,
            ) {
                Icon(Icons.Outlined.Add, contentDescription = "IP Engelle")
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
                    text = "AI Insights",
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

                    // Threat stats summary
                    item {
                        ThreatStatsRow(stats = uiState.threatStats, colors = colors)
                    }

                    // Insights feed header
                    item {
                        Text(
                            "Tehdit Akisi",
                            color = colors.neonMagenta,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                        )
                    }

                    if (uiState.insights.isEmpty()) {
                        item {
                            GlassCard(modifier = Modifier.fillMaxWidth()) {
                                Text(
                                    "Aktif insight bulunamadi",
                                    color = TextSecondary,
                                    modifier = Modifier.padding(8.dp),
                                )
                            }
                        }
                    } else {
                        items(uiState.insights.filter { !it.dismissed }, key = { it.id }) { insight ->
                            InsightCard(
                                insight = insight,
                                onDismiss = { viewModel.dismiss(insight.id) },
                                colors = colors,
                            )
                        }
                    }

                    // Blocked IPs panel
                    item {
                        BlockedIpsSection(
                            blockedIps = uiState.blockedIps,
                            expanded = uiState.blockedIpsExpanded,
                            onToggle = { viewModel.toggleBlockedIpsExpanded() },
                            onUnblock = { ip -> viewModel.unblockIp(ip) },
                            colors = colors,
                        )
                    }

                    item { Spacer(modifier = Modifier.height(80.dp)) }
                }
            }
        }
    }
}

@Composable
private fun ThreatStatsRow(
    stats: InsightThreatStatsDto?,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Text("24 Saat Ozeti", color = colors.neonCyan, fontWeight = FontWeight.Bold, fontSize = 14.sp)
        Spacer(modifier = Modifier.height(10.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            ThreatStatItem("Engelli IP", "${stats?.blockedIpCount ?: 0}", colors.neonCyan)
            ThreatStatItem("Harici", "${stats?.totalExternalBlocked ?: 0}", colors.neonRed)
            ThreatStatItem("Oto-Engel", "${stats?.totalAutoBlocks ?: 0}", colors.neonAmber)
            ThreatStatItem("Suphe", "${stats?.totalSuspicious ?: 0}", colors.neonMagenta)
        }
    }
}

@Composable
private fun ThreatStatItem(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = color, fontWeight = FontWeight.Bold, fontSize = 18.sp)
        Text(label, color = TextSecondary, fontSize = 10.sp)
    }
}

@Composable
private fun InsightCard(
    insight: AiInsightDto,
    onDismiss: () -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val (badgeColor, badgeLabel) = when (insight.severity.lowercase()) {
        "critical" -> colors.neonRed to "KRITIK"
        "warning" -> colors.neonAmber to "UYARI"
        else -> colors.neonCyan to "BILGI"
    }

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.Top) {
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
                        insight.category,
                        color = TextSecondary,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    insight.title,
                    color = TextPrimary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp,
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    insight.description,
                    color = TextSecondary,
                    fontSize = 12.sp,
                    lineHeight = 16.sp,
                )
                insight.createdAt?.let {
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(it, color = TextSecondary, fontSize = 10.sp)
                }
            }
            IconButton(onClick = onDismiss, modifier = Modifier.size(32.dp)) {
                Icon(Icons.Outlined.Close, contentDescription = "Kapat", tint = TextSecondary, modifier = Modifier.size(16.dp))
            }
        }
    }
}

@Composable
private fun BlockedIpsSection(
    blockedIps: List<InsightBlockedIpDto>,
    expanded: Boolean,
    onToggle: () -> Unit,
    onUnblock: (String) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { onToggle() },
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                "Engelli IP'ler (${blockedIps.size})",
                color = colors.neonRed,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
            )
            Icon(
                if (expanded) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore,
                contentDescription = null,
                tint = colors.neonRed,
            )
        }

        AnimatedVisibility(visible = expanded) {
            Column(modifier = Modifier.padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (blockedIps.isEmpty()) {
                    Text("Engelli IP bulunamadi", color = TextSecondary, fontSize = 13.sp)
                } else {
                    blockedIps.forEach { blocked ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(blocked.ipAddress, color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                                if (!blocked.reason.isNullOrBlank()) {
                                    Text(blocked.reason, color = TextSecondary, fontSize = 11.sp)
                                }
                                if (!blocked.blockedAt.isNullOrBlank()) {
                                    Text(blocked.blockedAt, color = TextSecondary, fontSize = 10.sp)
                                }
                            }
                            IconButton(
                                onClick = { onUnblock(blocked.ipAddress) },
                                modifier = Modifier.size(36.dp),
                            ) {
                                Icon(
                                    Icons.Outlined.LockOpen,
                                    contentDescription = "Engeli Kaldir",
                                    tint = colors.neonGreen,
                                    modifier = Modifier.size(18.dp),
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun BlockIpDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String?) -> Unit,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    var ip by remember { mutableStateOf("") }
    var reason by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = com.tonbil.aifirewall.ui.theme.DarkSurface,
        title = { Text("IP Engelle", color = colors.neonRed, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = ip,
                    onValueChange = { ip = it },
                    label = { Text("IP Adresi", color = TextSecondary) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonRed,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedLabelColor = colors.neonRed,
                        cursorColor = colors.neonRed,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                    ),
                )
                OutlinedTextField(
                    value = reason,
                    onValueChange = { reason = it },
                    label = { Text("Sebep (opsiyonel)", color = TextSecondary) },
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonRed,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedLabelColor = colors.neonRed,
                        cursorColor = colors.neonRed,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                    ),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { if (ip.isNotBlank()) onConfirm(ip.trim(), reason.ifBlank { null }) },
                enabled = ip.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonRed),
            ) { Text("Engelle", color = Color.Black) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Iptal", color = TextSecondary) }
        },
    )
}

