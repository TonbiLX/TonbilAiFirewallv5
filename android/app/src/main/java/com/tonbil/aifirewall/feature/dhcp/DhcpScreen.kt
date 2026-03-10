package com.tonbil.aifirewall.feature.dhcp

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
import androidx.compose.foundation.shape.CircleShape
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
import com.tonbil.aifirewall.data.remote.dto.DhcpLeaseDto
import com.tonbil.aifirewall.data.remote.dto.DhcpPoolDto
import com.tonbil.aifirewall.data.remote.dto.DhcpStatsDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkColors
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@Composable
fun DhcpScreen(
    onBack: () -> Unit,
    viewModel: DhcpViewModel = koinViewModel(),
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

    if (uiState.showAddLeaseDialog) {
        AddStaticLeaseDialog(
            onDismiss = { viewModel.hideAddLeaseDialog() },
            onConfirm = { mac, ip, hostname -> viewModel.addStaticLease(mac, ip, hostname) },
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
                    text = "DHCP Yonetimi",
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
                        DhcpStatsRow(stats = uiState.stats, colors = colors)
                    }

                    // IP Pools header
                    item {
                        Text(
                            "IP Havuzlari",
                            color = colors.neonMagenta,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                        )
                    }

                    if (uiState.pools.isEmpty()) {
                        item {
                            GlassCard(modifier = Modifier.fillMaxWidth()) {
                                Text("IP havuzu bulunamadi", color = TextSecondary, modifier = Modifier.padding(8.dp))
                            }
                        }
                    } else {
                        items(uiState.pools, key = { it.id }) { pool ->
                            PoolCard(
                                pool = pool,
                                onToggle = { viewModel.togglePool(pool.id) },
                                colors = colors,
                            )
                        }
                    }

                    // Leases header
                    item {
                        Spacer(modifier = Modifier.height(4.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "Aktif Kiralar (${uiState.leases.size})",
                                color = colors.neonMagenta,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                            )
                            IconButton(onClick = { viewModel.showAddLeaseDialog() }, modifier = Modifier.size(36.dp)) {
                                Icon(Icons.Outlined.Add, contentDescription = "Statik Kira Ekle", tint = colors.neonCyan, modifier = Modifier.size(18.dp))
                            }
                        }
                    }

                    if (uiState.leases.isEmpty()) {
                        item {
                            GlassCard(modifier = Modifier.fillMaxWidth()) {
                                Text("Aktif kira bulunamadi", color = TextSecondary, modifier = Modifier.padding(8.dp))
                            }
                        }
                    } else {
                        items(uiState.leases, key = { it.macAddress }) { lease ->
                            LeaseCard(
                                lease = lease,
                                onDelete = { viewModel.deleteLease(lease.macAddress) },
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
private fun DhcpStatsRow(
    stats: DhcpStatsDto?,
    colors: CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("DHCP Durumu", color = colors.neonCyan, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            // dnsmasq status indicator
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(if (stats?.dnsmasqRunning == true) colors.neonGreen else colors.neonRed),
                )
                Spacer(modifier = Modifier.width(6.dp))
                Text(
                    if (stats?.dnsmasqRunning == true) "dnsmasq aktif" else "dnsmasq kapali",
                    color = if (stats?.dnsmasqRunning == true) colors.neonGreen else colors.neonRed,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
        }
        Spacer(modifier = Modifier.height(10.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            StatItem("Havuz", "${stats?.totalPools ?: 0}/${stats?.activePools ?: 0}", colors.neonCyan)
            StatItem("Atanmis", "${stats?.assignedIps ?: 0}", colors.neonAmber)
            StatItem("Musait", "${stats?.availableIps ?: 0}", colors.neonGreen)
            StatItem("Statik", "${stats?.staticLeases ?: 0}", colors.neonMagenta)
            StatItem("Dinamik", "${stats?.dynamicLeases ?: 0}", colors.neonCyan)
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
private fun PoolCard(
    pool: DhcpPoolDto,
    onToggle: () -> Unit,
    colors: CyberpunkColors,
) {
    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    pool.name,
                    color = TextPrimary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp,
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    "${pool.startIp} - ${pool.endIp}",
                    color = colors.neonCyan,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Medium,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("Ag gecidi: ${pool.gateway}", color = TextSecondary, fontSize = 11.sp)
                    Text("Maske: ${pool.subnet}", color = TextSecondary, fontSize = 11.sp)
                }
                Spacer(modifier = Modifier.height(2.dp))
                Text("Kira suresi: ${pool.leaseTime}", color = TextSecondary, fontSize = 11.sp)
            }
            Switch(
                checked = pool.enabled,
                onCheckedChange = { onToggle() },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color.Black,
                    checkedTrackColor = colors.neonGreen,
                    uncheckedThumbColor = TextSecondary,
                    uncheckedTrackColor = colors.glassBg,
                ),
            )
        }
    }
}

@Composable
private fun LeaseCard(
    lease: DhcpLeaseDto,
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
                    lease.hostname ?: "Bilinmeyen",
                    color = TextPrimary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 14.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(colors.neonCyan.copy(alpha = 0.12f))
                            .padding(horizontal = 6.dp, vertical = 2.dp),
                    ) {
                        Text(lease.ipAddress, color = colors.neonCyan, fontSize = 11.sp, fontWeight = FontWeight.Medium)
                    }
                    Text(
                        lease.macAddress,
                        color = TextSecondary,
                        fontSize = 11.sp,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                lease.expiry?.let {
                    Spacer(modifier = Modifier.height(2.dp))
                    Text("Bitis: $it", color = TextSecondary, fontSize = 10.sp)
                }
            }
            IconButton(onClick = onDelete, modifier = Modifier.size(36.dp)) {
                Icon(Icons.Outlined.Delete, contentDescription = "Sil", tint = colors.neonRed, modifier = Modifier.size(18.dp))
            }
        }
    }
}

@Composable
private fun AddStaticLeaseDialog(
    onDismiss: () -> Unit,
    onConfirm: (String, String, String?) -> Unit,
    colors: CyberpunkColors,
) {
    var mac by remember { mutableStateOf("") }
    var ip by remember { mutableStateOf("") }
    var hostname by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = { Text("Statik Kira Ekle", color = colors.neonCyan, fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = mac,
                    onValueChange = { mac = it },
                    label = { Text("MAC Adresi", color = TextSecondary) },
                    singleLine = true,
                    placeholder = { Text("AA:BB:CC:DD:EE:FF", color = TextSecondary.copy(alpha = 0.5f)) },
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
                    value = ip,
                    onValueChange = { ip = it },
                    label = { Text("IP Adresi", color = TextSecondary) },
                    singleLine = true,
                    placeholder = { Text("192.168.1.100", color = TextSecondary.copy(alpha = 0.5f)) },
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
                    value = hostname,
                    onValueChange = { hostname = it },
                    label = { Text("Hostname (opsiyonel)", color = TextSecondary) },
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
                onClick = {
                    if (mac.isNotBlank() && ip.isNotBlank()) {
                        onConfirm(mac.trim(), ip.trim(), hostname.ifBlank { null })
                    }
                },
                enabled = mac.isNotBlank() && ip.isNotBlank(),
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
            ) { Text("Ekle", color = Color.Black) }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Iptal", color = TextSecondary) }
        },
    )
}
