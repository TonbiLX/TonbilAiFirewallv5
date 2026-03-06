package com.tonbil.aifirewall.feature.dashboard

import androidx.compose.foundation.background
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.Smartphone
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.patrykandpatrick.vico.compose.cartesian.CartesianChartHost
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberLine
import com.patrykandpatrick.vico.compose.cartesian.layer.rememberLineCartesianLayer
import com.patrykandpatrick.vico.compose.cartesian.rememberCartesianChart
import com.patrykandpatrick.vico.compose.common.fill
import com.patrykandpatrick.vico.core.cartesian.data.CartesianChartModelProducer
import com.patrykandpatrick.vico.core.cartesian.data.lineSeries
import com.patrykandpatrick.vico.core.cartesian.layer.LineCartesianLayer
import com.tonbil.aifirewall.data.remote.WebSocketState
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.navigation.DevicesRoute
import com.tonbil.aifirewall.ui.navigation.SecurityRoute
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel

@Composable
fun DashboardScreen(
    onNavigate: (Any) -> Unit = {},
    viewModel: DashboardViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors

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
                        style = MaterialTheme.typography.bodyLarge,
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Button(
                        onClick = { viewModel.refresh() },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = colors.neonCyan,
                        ),
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Refresh,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Tekrar Dene")
                    }
                }
            }
        }
        else -> {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.background)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                // Connection status banner
                item {
                    ConnectionStatusBanner(state = uiState.connectionStatus)
                }

                // Stat cards (2x2 grid)
                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        StatCardItem(
                            modifier = Modifier.weight(1f),
                            title = "Aktif Cihaz",
                            value = "${uiState.onlineDevices}/${uiState.totalDevices}",
                            subtitle = "${uiState.blockedDevices} engelli",
                            icon = Icons.Outlined.Smartphone,
                            color = colors.neonCyan,
                            onClick = { onNavigate(DevicesRoute) },
                        )
                        StatCardItem(
                            modifier = Modifier.weight(1f),
                            title = "DNS Sorgulari",
                            value = formatCount(uiState.totalQueries24h),
                            subtitle = "%${String.format("%.1f", uiState.blockPercentage)} engellendi",
                            icon = Icons.Outlined.Shield,
                            color = colors.neonMagenta,
                            onClick = { onNavigate(SecurityRoute) },
                        )
                    }
                }

                item {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        StatCardItem(
                            modifier = Modifier.weight(1f),
                            title = "Engellenen",
                            value = formatCount(uiState.blockedQueries24h),
                            subtitle = "son 24 saat",
                            icon = Icons.Outlined.Shield,
                            color = colors.neonRed,
                            onClick = { onNavigate(SecurityRoute) },
                        )
                        StatCardItem(
                            modifier = Modifier.weight(1f),
                            title = "VPN",
                            value = if (uiState.vpnEnabled) "${uiState.vpnConnectedPeers}/${uiState.vpnTotalPeers}" else "Kapali",
                            subtitle = if (uiState.vpnEnabled) "bagli peer" else "devre disi",
                            icon = Icons.Outlined.Wifi,
                            color = if (uiState.vpnEnabled) colors.neonGreen else colors.neonAmber,
                            onClick = { onNavigate(SecurityRoute) },
                        )
                    }
                }

                // Bandwidth chart
                item {
                    BandwidthChart(
                        history = uiState.bandwidthHistory,
                        currentUpload = uiState.totalUploadBps,
                        currentDownload = uiState.totalDownloadBps,
                    )
                }

                // DNS per minute indicator
                item {
                    GlassCard(modifier = Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "DNS/dk",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "${uiState.queriesPerMin}",
                                style = MaterialTheme.typography.titleMedium,
                                color = colors.neonCyan,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ConnectionStatusBanner(state: WebSocketState) {
    val colors = CyberpunkTheme.colors
    val (color, text) = when (state) {
        WebSocketState.CONNECTED -> colors.neonGreen to "Bagli"
        WebSocketState.CONNECTING -> colors.neonAmber to "Baglaniyor..."
        WebSocketState.DISCONNECTED -> colors.neonRed to "Baglanti Kesildi"
    }

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(color),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = text,
                style = MaterialTheme.typography.bodyMedium,
                color = color,
            )
        }
    }
}

@Composable
private fun StatCardItem(
    modifier: Modifier = Modifier,
    title: String,
    value: String,
    subtitle: String,
    icon: ImageVector,
    color: Color,
    onClick: () -> Unit,
) {
    GlassCard(
        modifier = modifier.clickable(onClick = onClick),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = color,
                modifier = Modifier.size(24.dp),
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.headlineMedium,
            color = color,
        )
        Spacer(modifier = Modifier.height(2.dp))
        Text(
            text = subtitle,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
    }
}

@Composable
private fun BandwidthChart(
    history: List<BandwidthPoint>,
    currentUpload: Long,
    currentDownload: Long,
) {
    val colors = CyberpunkTheme.colors
    val modelProducer = remember { CartesianChartModelProducer() }

    LaunchedEffect(history) {
        if (history.isNotEmpty()) {
            modelProducer.runTransaction {
                lineSeries {
                    series(history.map { it.downloadBps.toFloat() / 1_000_000f })
                    series(history.map { it.uploadBps.toFloat() / 1_000_000f })
                }
            }
        }
    }

    GlassCard(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = "Bant Genisligi",
            style = MaterialTheme.typography.titleMedium,
            color = colors.neonCyan,
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "${formatBps(currentDownload)} / ${formatBps(currentUpload)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
        )
        Spacer(modifier = Modifier.height(8.dp))

        if (history.isNotEmpty()) {
            CartesianChartHost(
                chart = rememberCartesianChart(
                    rememberLineCartesianLayer(
                        lineProvider = LineCartesianLayer.LineProvider.series(
                            LineCartesianLayer.rememberLine(
                                fill = remember { LineCartesianLayer.LineFill.single(fill(Color(0xFF00F0FF))) },
                            ),
                            LineCartesianLayer.rememberLine(
                                fill = remember { LineCartesianLayer.LineFill.single(fill(Color(0xFFFF00E5))) },
                            ),
                        ),
                    ),
                ),
                modelProducer = modelProducer,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp),
            )
        } else {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(200.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "Veri bekleniyor...",
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

private fun formatBps(bps: Long): String {
    return when {
        bps >= 1_000_000_000 -> String.format("%.1f Gbps", bps / 1_000_000_000.0)
        bps >= 1_000_000 -> String.format("%.1f Mbps", bps / 1_000_000.0)
        bps >= 1_000 -> String.format("%.1f Kbps", bps / 1_000.0)
        else -> "$bps bps"
    }
}

private fun formatCount(count: Int): String {
    return when {
        count >= 1_000_000 -> String.format("%.1fM", count / 1_000_000.0)
        count >= 1_000 -> String.format("%.1fK", count / 1_000.0)
        else -> count.toString()
    }
}
