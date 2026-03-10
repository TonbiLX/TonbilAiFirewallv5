package com.tonbil.aifirewall.feature.notifications

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
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.NotificationsActive
import androidx.compose.material.icons.outlined.NotificationsOff
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.data.remote.dto.PushChannelDto
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.GlassBg
import com.tonbil.aifirewall.ui.theme.GlassBorder
import com.tonbil.aifirewall.ui.theme.NeonAmber
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

// Kanal kategorileri: her kanal id prefix'ine gore renk atar
private fun channelColor(channelId: String) = when {
    channelId.startsWith("security") || channelId.startsWith("ddos") || channelId.startsWith("threat") -> NeonRed
    channelId.startsWith("device") -> NeonCyan
    channelId.startsWith("traffic") || channelId.startsWith("bandwidth") -> NeonAmber
    channelId.startsWith("system") || channelId.startsWith("service") -> NeonMagenta
    else -> NeonGreen
}

private fun channelCategory(channelId: String) = when {
    channelId.startsWith("security") || channelId.startsWith("ddos") || channelId.startsWith("threat") -> "Guvenlik"
    channelId.startsWith("device") -> "Cihaz"
    channelId.startsWith("traffic") || channelId.startsWith("bandwidth") -> "Trafik"
    else -> "Sistem"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PushNotificationsScreen(
    onBack: () -> Unit,
    viewModel: PushNotificationsViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        containerColor = DarkBackground,
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Outlined.Notifications, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(8.dp))
                        Text("Push Bildirimler", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground),
                actions = {
                    IconButton(onClick = { viewModel.loadChannels() }) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = NeonCyan)
                    }
                },
            )
        },
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
        ) {
            // Hata / basari mesaji
            uiState.error?.let {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(NeonRed.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
                        .border(0.5.dp, NeonRed.copy(alpha = 0.4f), RoundedCornerShape(8.dp))
                        .padding(12.dp),
                ) {
                    Text(text = it, color = NeonRed, fontSize = 12.sp)
                }
                Spacer(Modifier.height(12.dp))
            }
            uiState.successMessage?.let {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(NeonGreen.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
                        .border(0.5.dp, NeonGreen.copy(alpha = 0.4f), RoundedCornerShape(8.dp))
                        .padding(12.dp),
                ) {
                    Text(text = it, color = NeonGreen, fontSize = 12.sp)
                }
                Spacer(Modifier.height(12.dp))
            }

            // Kayit durumu karti
            RegistrationCard(
                isRegistered = uiState.isRegistered,
                isLoading = uiState.isLoading,
                onRegister = { viewModel.registerToken("fcm-placeholder-token") },
            )

            Spacer(Modifier.height(16.dp))

            // Kanal baslik
            Text(
                text = "Bildirim Kanallari",
                color = TextPrimary,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(8.dp))

            if (uiState.isLoading && uiState.channels.isEmpty()) {
                Box(Modifier.fillMaxWidth().height(120.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = NeonCyan, modifier = Modifier.size(32.dp))
                }
            } else if (uiState.channels.isEmpty()) {
                Box(Modifier.fillMaxWidth().height(80.dp), contentAlignment = Alignment.Center) {
                    Text("Kanal bulunamadi", color = TextSecondary, textAlign = TextAlign.Center)
                }
            } else {
                // Kanallari kategoriye gore grupla
                val grouped = uiState.channels.groupBy { channelCategory(it.id) }
                val categoryOrder = listOf("Guvenlik", "Cihaz", "Trafik", "Sistem")

                LazyColumn(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    categoryOrder.forEach { category ->
                        val chList = grouped[category] ?: return@forEach
                        item {
                            Text(
                                text = category,
                                color = TextSecondary,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Medium,
                                modifier = Modifier.padding(vertical = 4.dp),
                            )
                        }
                        items(chList) { channel ->
                            ChannelCard(
                                channel = channel,
                                onToggle = { viewModel.toggleChannel(channel.id) },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun RegistrationCard(
    isRegistered: Boolean,
    isLoading: Boolean,
    onRegister: () -> Unit,
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(GlassBg)
            .border(1.dp, if (isRegistered) NeonGreen.copy(alpha = 0.4f) else GlassBorder, RoundedCornerShape(12.dp))
            .padding(16.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = if (isRegistered) Icons.Outlined.NotificationsActive else Icons.Outlined.NotificationsOff,
                    contentDescription = null,
                    tint = if (isRegistered) NeonGreen else TextSecondary,
                    modifier = Modifier.size(28.dp),
                )
                Spacer(Modifier.width(12.dp))
                Column {
                    Text(
                        text = if (isRegistered) "Bildirimler Aktif" else "Bildirimler Pasif",
                        color = if (isRegistered) NeonGreen else TextSecondary,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text = if (isRegistered) "Bu cihaz bildirimlere kayitli" else "Bildirimleri etkinlestirin",
                        color = TextSecondary,
                        fontSize = 11.sp,
                    )
                }
            }
            if (!isRegistered) {
                Button(
                    onClick = onRegister,
                    enabled = !isLoading,
                    colors = ButtonDefaults.buttonColors(containerColor = NeonCyan.copy(alpha = 0.2f)),
                    shape = RoundedCornerShape(8.dp),
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(color = NeonCyan, modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    } else {
                        Text("Kaydet", color = NeonCyan, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun ChannelCard(
    channel: PushChannelDto,
    onToggle: () -> Unit,
) {
    val accentColor = channelColor(channel.id)
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(GlassBg)
            .border(0.5.dp, if (channel.enabled) accentColor.copy(alpha = 0.3f) else GlassBorder, RoundedCornerShape(8.dp))
            .padding(horizontal = 14.dp, vertical = 10.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = channel.name,
                    color = if (channel.enabled) TextPrimary else TextSecondary,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium,
                )
                if (channel.description.isNotBlank()) {
                    Text(
                        text = channel.description,
                        color = TextSecondary,
                        fontSize = 10.sp,
                    )
                }
            }
            Switch(
                checked = channel.enabled,
                onCheckedChange = { onToggle() },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = accentColor,
                    checkedTrackColor = accentColor.copy(alpha = 0.3f),
                    uncheckedThumbColor = TextSecondary,
                    uncheckedTrackColor = DarkSurface,
                ),
            )
        }
    }
}
