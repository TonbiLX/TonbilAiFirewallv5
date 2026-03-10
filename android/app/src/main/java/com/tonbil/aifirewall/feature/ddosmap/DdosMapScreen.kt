package com.tonbil.aifirewall.feature.ddosmap

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
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.DdosAttackPointDto
import com.tonbil.aifirewall.data.remote.dto.DdosProtectionStatusDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@Composable
fun DdosMapScreen(
    onBack: () -> Unit,
    viewModel: DdosMapViewModel = koinViewModel(),
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

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
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
                    text = "DDoS Saldiri Haritasi",
                    style = MaterialTheme.typography.titleLarge,
                    color = colors.neonCyan,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f),
                )
                if (uiState.isActionLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp), color = colors.neonRed, strokeWidth = 2.dp)
                } else {
                    IconButton(onClick = { viewModel.loadAll() }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = colors.neonAmber)
                    }
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

                    // Stats bar
                    item {
                        GlassCard(modifier = Modifier.fillMaxWidth()) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceEvenly,
                            ) {
                                StatsBarItem(
                                    label = "Engellenen Paket",
                                    value = formatLong(uiState.attackMap.totalBlocked),
                                    color = colors.neonRed,
                                )
                                StatsBarItem(
                                    label = "Aktif Saldiran",
                                    value = "${uiState.attackMap.activeAttackers}",
                                    color = colors.neonAmber,
                                )
                                StatsBarItem(
                                    label = "Koruma Sayisi",
                                    value = "${uiState.status.count { it.enabled }}/${uiState.status.size}",
                                    color = colors.neonGreen,
                                )
                            }
                        }
                    }

                    // Attack list header
                    item {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                "Saldiri Listesi",
                                color = colors.neonMagenta,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp,
                            )
                            Button(
                                onClick = { viewModel.flushAttackers() },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = colors.neonRed.copy(alpha = 0.18f),
                                ),
                                shape = RoundedCornerShape(8.dp),
                                contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                            ) {
                                Icon(Icons.Outlined.Delete, contentDescription = null, tint = colors.neonRed, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("Temizle", color = colors.neonRed, fontSize = 13.sp)
                            }
                        }
                    }

                    val sortedAttacks = uiState.attackMap.attacks.sortedByDescending { it.packetCount }

                    if (sortedAttacks.isEmpty()) {
                        item {
                            GlassCard(modifier = Modifier.fillMaxWidth()) {
                                Text("Aktif saldiri bulunamadi", color = TextSecondary, modifier = Modifier.padding(8.dp))
                            }
                        }
                    } else {
                        items(sortedAttacks, key = { it.ipAddress }) { attack ->
                            AttackPointCard(attack = attack, colors = colors)
                        }
                    }

                    // DDoS protection status cards
                    item {
                        Text(
                            "Koruma Durumu",
                            color = colors.neonGreen,
                            fontWeight = FontWeight.Bold,
                            fontSize = 14.sp,
                        )
                    }

                    items(uiState.status, key = { it.name }) { protection ->
                        ProtectionStatusCard(protection = protection, colors = colors)
                    }

                    item { Spacer(modifier = Modifier.height(16.dp)) }
                }
            }
        }

        SnackbarHost(
            hostState = snackbarHostState,
            modifier = Modifier.align(Alignment.BottomCenter).padding(16.dp),
        ) { data ->
            Snackbar(
                containerColor = colors.glassBg,
                contentColor = colors.neonCyan,
                snackbarData = data,
            )
        }
    }
}

@Composable
private fun StatsBarItem(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = color, fontWeight = FontWeight.Bold, fontSize = 20.sp)
        Text(label, color = TextSecondary, fontSize = 11.sp)
    }
}

@Composable
private fun AttackPointCard(
    attack: DdosAttackPointDto,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val attackTypeColor = when {
        attack.attackType.contains("syn", ignoreCase = true) -> colors.neonRed
        attack.attackType.contains("udp", ignoreCase = true) -> colors.neonAmber
        attack.attackType.contains("icmp", ignoreCase = true) -> colors.neonMagenta
        attack.attackType.contains("port", ignoreCase = true) -> colors.neonCyan
        else -> colors.neonGreen
    }

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Country flag + name
            Column(modifier = Modifier.width(80.dp)) {
                Text(
                    text = countryFlag(attack.countryCode),
                    fontSize = 22.sp,
                )
                Text(
                    text = attack.countryName ?: attack.countryCode ?: "?",
                    color = TextSecondary,
                    fontSize = 10.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(attack.ipAddress, color = TextPrimary, fontWeight = FontWeight.Medium, fontSize = 13.sp)
                attack.city?.let { Text(it, color = TextSecondary, fontSize = 11.sp) }
                Spacer(modifier = Modifier.height(4.dp))
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(attackTypeColor.copy(alpha = 0.15f))
                        .border(1.dp, attackTypeColor.copy(alpha = 0.4f), RoundedCornerShape(4.dp))
                        .padding(horizontal = 6.dp, vertical = 2.dp),
                ) {
                    Text(attack.attackType.uppercase(), color = attackTypeColor, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
            }

            Column(horizontalAlignment = Alignment.End) {
                Text(
                    formatLong(attack.packetCount),
                    color = colors.neonRed,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp,
                )
                Text("paket", color = TextSecondary, fontSize = 10.sp)
                attack.lastSeen?.let {
                    Text(it.take(16), color = TextSecondary, fontSize = 9.sp)
                }
            }
        }
    }
}

@Composable
private fun ProtectionStatusCard(
    protection: DdosProtectionStatusDto,
    colors: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val statusColor = if (protection.enabled) colors.neonGreen else TextSecondary

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Shield, contentDescription = null, tint = statusColor, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    protection.displayName.ifBlank { protection.name },
                    color = TextPrimary,
                    fontSize = 13.sp,
                )
            }
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(statusColor.copy(alpha = 0.15f))
                    .border(1.dp, statusColor.copy(alpha = 0.4f), RoundedCornerShape(4.dp))
                    .padding(horizontal = 8.dp, vertical = 3.dp),
            ) {
                Text(
                    if (protection.enabled) "AKTIF" else "PASIF",
                    color = statusColor,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

private fun formatLong(value: Long): String = when {
    value >= 1_000_000_000 -> "${"%.1f".format(value / 1_000_000_000.0)}G"
    value >= 1_000_000 -> "${"%.1f".format(value / 1_000_000.0)}M"
    value >= 1_000 -> "${"%.1f".format(value / 1_000.0)}K"
    else -> value.toString()
}

private fun countryFlag(countryCode: String?): String {
    if (countryCode.isNullOrBlank() || countryCode.length != 2) return "🌐"
    val offset = 0x1F1E6 - 'A'.code
    return countryCode.uppercase().map { char ->
        String(Character.toChars(char.code + offset))
    }.joinToString("")
}
