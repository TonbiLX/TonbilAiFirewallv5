package com.tonbil.aifirewall.feature.systemtime

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SystemTimeScreen(
    onBack: () -> Unit,
    viewModel: SystemTimeViewModel = koinViewModel(),
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
        containerColor = Color.Transparent,
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .padding(padding),
        ) {
            // Header
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Outlined.ArrowBack, contentDescription = "Geri", tint = colors.neonCyan)
                }
                Icon(Icons.Outlined.Schedule, contentDescription = null, tint = colors.neonCyan, modifier = Modifier.size(26.dp))
                Spacer(Modifier.width(8.dp))
                Text(
                    "Sistem Saati",
                    style = MaterialTheme.typography.headlineMedium,
                    color = colors.neonCyan,
                    modifier = Modifier.weight(1f),
                )
                if (uiState.isActionLoading) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), color = colors.neonMagenta, strokeWidth = 2.dp)
                    Spacer(Modifier.width(8.dp))
                }
                IconButton(onClick = { viewModel.loadAll() }) {
                    Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = colors.neonCyan)
                }
            }

            if (uiState.isLoading) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = colors.neonCyan)
                }
                return@Column
            }

            uiState.error?.let { err ->
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(err, color = colors.neonRed, style = MaterialTheme.typography.bodyMedium)
                }
                return@Column
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                // Current time card
                item {
                    val st = uiState.status
                    val ntpSynced = st.ntpSynchronized
                    val ntpColor = if (ntpSynced) colors.neonGreen else colors.neonAmber

                    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonCyan) {
                        // NTP badge
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text("Guncel Saat", style = MaterialTheme.typography.titleMedium, color = colors.neonCyan, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                            Surface(
                                color = ntpColor.copy(alpha = 0.2f),
                                shape = RoundedCornerShape(6.dp),
                                border = androidx.compose.foundation.BorderStroke(1.dp, ntpColor.copy(alpha = 0.5f)),
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                                ) {
                                    Icon(
                                        if (ntpSynced) Icons.Outlined.CheckCircle else Icons.Outlined.Warning,
                                        contentDescription = null,
                                        tint = ntpColor,
                                        modifier = Modifier.size(12.dp),
                                    )
                                    Text(
                                        if (ntpSynced) "NTP SENKRON" else "SENKRON DEGIL",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = ntpColor,
                                        fontWeight = FontWeight.Bold,
                                    )
                                }
                            }
                        }
                        Spacer(Modifier.height(16.dp))
                        // Large digital clock
                        Text(
                            text = st.currentTime,
                            style = MaterialTheme.typography.displayMedium.copy(
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold,
                                fontSize = 32.sp,
                            ),
                            color = colors.neonCyan,
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            text = st.timezone,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        if (st.ntpServer.isNotBlank()) {
                            Spacer(Modifier.height(4.dp))
                            Text(
                                text = "NTP: ${st.ntpServer}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontFamily = FontFamily.Monospace,
                            )
                        }
                    }
                }

                // Timezone selector
                item {
                    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonMagenta) {
                        Text("Saat Dilimi", style = MaterialTheme.typography.titleMedium, color = colors.neonMagenta, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        Text("Mevcut", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.height(4.dp))
                        Text(uiState.status.timezone.ifBlank { "Ayarlanmamis" }, style = MaterialTheme.typography.bodyMedium, color = colors.neonMagenta, fontFamily = FontFamily.Monospace)
                        Spacer(Modifier.height(12.dp))
                        Button(
                            onClick = { viewModel.showTimezoneDialog() },
                            colors = ButtonDefaults.buttonColors(containerColor = colors.neonMagenta, contentColor = Color.Black),
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Icon(Icons.Outlined.Public, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(6.dp))
                            Text("Saat Dilimi Sec", fontWeight = FontWeight.Bold)
                        }
                    }
                }

                // NTP server selector
                item {
                    GlassCard(modifier = Modifier.fillMaxWidth(), glowColor = colors.neonAmber) {
                        Text("NTP Sunucusu", style = MaterialTheme.typography.titleMedium, color = colors.neonAmber, fontWeight = FontWeight.Bold)
                        Spacer(Modifier.height(10.dp))
                        if (uiState.ntpServers.isEmpty()) {
                            Text("Sunucu listesi yuklenemedi", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        } else {
                            uiState.ntpServers.forEach { server ->
                                val isSelected = uiState.status.ntpServer == server.address
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .clickable { viewModel.setNtpServer(server.address) }
                                        .background(
                                            if (isSelected) colors.neonAmber.copy(alpha = 0.1f) else Color.Transparent,
                                            RoundedCornerShape(8.dp),
                                        )
                                        .padding(horizontal = 8.dp, vertical = 8.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                                ) {
                                    RadioButton(
                                        selected = isSelected,
                                        onClick = { viewModel.setNtpServer(server.address) },
                                        colors = RadioButtonDefaults.colors(
                                            selectedColor = colors.neonAmber,
                                            unselectedColor = MaterialTheme.colorScheme.onSurfaceVariant,
                                        ),
                                    )
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(server.name, style = MaterialTheme.typography.bodyMedium, color = if (isSelected) colors.neonAmber else MaterialTheme.colorScheme.onSurface, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal)
                                        Text(server.address, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, fontFamily = FontFamily.Monospace)
                                        if (server.description.isNotBlank()) {
                                            Text(server.description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                        }
                                    }
                                }
                                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.3f), thickness = 0.5.dp)
                            }
                        }
                    }
                }

                // Sync Now button
                item {
                    Button(
                        onClick = { viewModel.syncNow() },
                        colors = ButtonDefaults.buttonColors(containerColor = colors.neonGreen, contentColor = Color.Black),
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                        enabled = !uiState.isActionLoading,
                    ) {
                        if (uiState.isActionLoading) {
                            CircularProgressIndicator(modifier = Modifier.size(18.dp), color = Color.Black, strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Outlined.Sync, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(8.dp))
                            Text("Simdi Senkronize Et", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        }
                    }
                }

                item { Spacer(Modifier.height(16.dp)) }
            }
        }
    }

    // Timezone dialog
    if (uiState.showTimezoneDialog) {
        TimezonePickerDialog(
            groups = uiState.timezones,
            currentTimezone = uiState.status.timezone,
            onSelect = { viewModel.setTimezone(it) },
            onDismiss = { viewModel.hideTimezoneDialog() },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TimezonePickerDialog(
    groups: List<com.tonbil.aifirewall.data.remote.dto.TimezoneGroupDto>,
    currentTimezone: String,
    onSelect: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val colors = CyberpunkTheme.colors
    var searchQuery by remember { mutableStateOf("") }

    // Filtered flat list
    val filtered = remember(searchQuery, groups) {
        if (searchQuery.isBlank()) {
            groups
        } else {
            groups.map { g ->
                g.copy(timezones = g.timezones.filter { it.contains(searchQuery, ignoreCase = true) })
            }.filter { it.timezones.isNotEmpty() }
        }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Column {
                Text("Saat Dilimi Sec", color = colors.neonMagenta, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("Ara...") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonMagenta,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                        cursorColor = colors.neonMagenta,
                    ),
                    leadingIcon = { Icon(Icons.Outlined.Search, contentDescription = null, tint = colors.neonMagenta) },
                )
            }
        },
        text = {
            LazyColumn(modifier = Modifier.heightIn(max = 380.dp)) {
                filtered.forEach { group ->
                    item {
                        Text(
                            group.region,
                            style = MaterialTheme.typography.labelMedium,
                            color = colors.neonMagenta,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(vertical = 6.dp),
                        )
                    }
                    items(group.timezones) { tz ->
                        val isSelected = tz == currentTimezone
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onSelect(tz) }
                                .background(
                                    if (isSelected) colors.neonMagenta.copy(alpha = 0.1f) else Color.Transparent,
                                    RoundedCornerShape(6.dp),
                                )
                                .padding(horizontal = 8.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            if (isSelected) {
                                Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = colors.neonMagenta, modifier = Modifier.size(16.dp))
                            } else {
                                Spacer(Modifier.size(16.dp))
                            }
                            Text(
                                tz,
                                style = MaterialTheme.typography.bodyMedium,
                                color = if (isSelected) colors.neonMagenta else MaterialTheme.colorScheme.onSurface,
                                fontFamily = FontFamily.Monospace,
                            )
                        }
                        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.2f), thickness = 0.5.dp)
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Kapat") }
        },
        containerColor = MaterialTheme.colorScheme.surface,
    )
}
