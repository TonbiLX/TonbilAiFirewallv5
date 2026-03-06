package com.tonbil.aifirewall.feature.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonRed
import com.tonbil.aifirewall.ui.theme.TextSecondary
import kotlinx.coroutines.delay
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ServerSettingsScreen(
    onBack: () -> Unit,
    viewModel: ServerSettingsViewModel = koinViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val cyberpunk = CyberpunkTheme.colors

    // Auto-navigate back on success after 1.5s
    LaunchedEffect(state.connectionResult) {
        if (state.connectionResult is ConnectionResult.Success) {
            delay(1500L)
            onBack()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        "Sunucu Ayarlari",
                        color = NeonCyan,
                        fontWeight = FontWeight.Bold,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Geri",
                            tint = NeonCyan,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = DarkBackground,
                ),
            )
        },
        containerColor = DarkBackground,
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // Auto-discover section
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    "Otomatik Kesif",
                    style = MaterialTheme.typography.titleSmall,
                    color = NeonCyan,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.height(12.dp))
                FilledTonalButton(
                    onClick = { viewModel.autoDiscover() },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !state.isAutoDiscovering && !state.isTestingConnection,
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = NeonCyan.copy(alpha = 0.15f),
                        contentColor = NeonCyan,
                    ),
                ) {
                    if (state.isAutoDiscovering) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            color = NeonCyan,
                            strokeWidth = 2.dp,
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    } else {
                        Icon(
                            Icons.Default.Search,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text("Otomatik Bul")
                }
            }

            // Quick selection section
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    "Hizli Secim",
                    style = MaterialTheme.typography.titleSmall,
                    color = NeonCyan,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.height(12.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    OutlinedButton(
                        onClick = { viewModel.useLocalNetwork() },
                        modifier = Modifier.weight(1f),
                        enabled = !state.isTestingConnection && !state.isAutoDiscovering,
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = NeonCyan,
                        ),
                    ) {
                        Icon(
                            Icons.Default.Wifi,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Yerel Ag", style = MaterialTheme.typography.bodySmall)
                    }
                    OutlinedButton(
                        onClick = { viewModel.useRemoteServer() },
                        modifier = Modifier.weight(1f),
                        enabled = !state.isTestingConnection && !state.isAutoDiscovering,
                        colors = ButtonDefaults.outlinedButtonColors(
                            contentColor = NeonCyan,
                        ),
                    ) {
                        Icon(
                            Icons.Default.Cloud,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Uzak Sunucu", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            // Manual URL section
            GlassCard(modifier = Modifier.fillMaxWidth()) {
                Text(
                    "Manuel URL",
                    style = MaterialTheme.typography.titleSmall,
                    color = NeonCyan,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = state.serverUrl,
                    onValueChange = viewModel::onUrlChange,
                    label = { Text("Sunucu URL") },
                    placeholder = { Text("https://sunucu-adresi/api/v1/") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = NeonCyan,
                        unfocusedBorderColor = cyberpunk.glassBorder,
                        focusedLabelColor = NeonCyan,
                        unfocusedLabelColor = cyberpunk.glassBorder,
                        cursorColor = NeonCyan,
                    ),
                    enabled = !state.isTestingConnection && !state.isAutoDiscovering,
                )
                Spacer(modifier = Modifier.height(12.dp))
                FilledTonalButton(
                    onClick = { viewModel.testConnection() },
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !state.isTestingConnection && !state.isAutoDiscovering,
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = NeonCyan.copy(alpha = 0.15f),
                        contentColor = NeonCyan,
                    ),
                ) {
                    if (state.isTestingConnection) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            color = NeonCyan,
                            strokeWidth = 2.dp,
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text("Baglanti Testi")
                }
            }

            // Connection result
            when (val result = state.connectionResult) {
                is ConnectionResult.Success -> {
                    GlassCard(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                Icons.Default.CheckCircle,
                                contentDescription = null,
                                tint = NeonGreen,
                                modifier = Modifier.size(24.dp),
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    "Baglanti basarili",
                                    color = NeonGreen,
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(
                                    result.url,
                                    color = TextSecondary,
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                        }
                    }
                }
                is ConnectionResult.Failure -> {
                    GlassCard(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Icon(
                                Icons.Default.Error,
                                contentDescription = null,
                                tint = NeonRed,
                                modifier = Modifier.size(24.dp),
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                result.message,
                                color = NeonRed,
                                style = MaterialTheme.typography.bodyMedium,
                            )
                        }
                    }
                }
                null -> { /* No result yet */ }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }
    }
}
