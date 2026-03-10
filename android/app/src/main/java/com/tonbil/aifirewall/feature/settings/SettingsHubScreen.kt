package com.tonbil.aifirewall.feature.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Send
import androidx.compose.material.icons.outlined.Article
import androidx.compose.material.icons.outlined.Build
import androidx.compose.material.icons.outlined.Chat
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Monitor
import androidx.compose.material.icons.outlined.Notifications
import androidx.compose.material.icons.outlined.People
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Psychology
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.feature.network.HubCard
import com.tonbil.aifirewall.feature.network.HubItem
import com.tonbil.aifirewall.ui.navigation.AiSettingsRoute
import com.tonbil.aifirewall.ui.navigation.ChatRoute
import com.tonbil.aifirewall.ui.navigation.ProfilesRoute
import com.tonbil.aifirewall.ui.navigation.PushNotificationsRoute
import com.tonbil.aifirewall.ui.navigation.SystemLogsRoute
import com.tonbil.aifirewall.ui.navigation.SystemManagementRoute
import com.tonbil.aifirewall.ui.navigation.SystemMonitorRoute
import com.tonbil.aifirewall.ui.navigation.SystemTimeRoute
import com.tonbil.aifirewall.ui.navigation.TelegramRoute
import com.tonbil.aifirewall.ui.navigation.TlsRoute
import com.tonbil.aifirewall.ui.navigation.UserSettingsRoute
import com.tonbil.aifirewall.ui.theme.*

@Composable
fun SettingsHubScreen(onNavigate: (Any) -> Unit) {
    val items = listOf(
        HubItem("Sistem Izleme", Icons.Outlined.Monitor, NeonCyan, SystemMonitorRoute),
        HubItem("Sistem Yonetimi", Icons.Outlined.Build, NeonAmber, SystemManagementRoute),
        HubItem("Saat/Tarih", Icons.Outlined.Schedule, NeonGreen, SystemTimeRoute),
        HubItem("Sistem Loglari", Icons.Outlined.Article, NeonMagenta, SystemLogsRoute),
        HubItem("TLS Sifreleme", Icons.Outlined.Lock, NeonRed, TlsRoute),
        HubItem("AI Ayarlari", Icons.Outlined.Psychology, NeonCyan, AiSettingsRoute),
        HubItem("Telegram", Icons.AutoMirrored.Outlined.Send, NeonGreen, TelegramRoute),
        HubItem("AI Sohbet", Icons.Outlined.Chat, NeonMagenta, ChatRoute),
        HubItem("Bildirimler", Icons.Outlined.Notifications, NeonAmber, PushNotificationsRoute),
        HubItem("Profiller", Icons.Outlined.People, NeonCyan, ProfilesRoute),
        HubItem("Hesap", Icons.Outlined.Person, NeonRed, UserSettingsRoute),
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(16.dp),
    ) {
        Text(
            text = "Ayarlar",
            color = NeonAmber,
            fontSize = 24.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 16.dp),
        )

        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxSize(),
        ) {
            items(items) { item ->
                HubCard(item = item, onClick = { onNavigate(item.route) })
            }
        }
    }
}
