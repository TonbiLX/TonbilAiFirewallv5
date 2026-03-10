package com.tonbil.aifirewall.feature.security

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Fireplace
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.Lightbulb
import androidx.compose.material.icons.outlined.Map
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.VerifiedUser
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.feature.network.HubCard
import com.tonbil.aifirewall.feature.network.HubItem
import com.tonbil.aifirewall.ui.navigation.DdosMapRoute
import com.tonbil.aifirewall.ui.navigation.DdosRoute
import com.tonbil.aifirewall.ui.navigation.FirewallRoute
import com.tonbil.aifirewall.ui.navigation.InsightsRoute
import com.tonbil.aifirewall.ui.navigation.IpManagementRoute
import com.tonbil.aifirewall.ui.navigation.IpReputationRoute
import com.tonbil.aifirewall.ui.navigation.SecuritySettingsRoute
import com.tonbil.aifirewall.ui.theme.*

@Composable
fun SecurityHubScreen(onNavigate: (Any) -> Unit) {
    val items = listOf(
        HubItem("Guvenlik Duvari", Icons.Outlined.Security, NeonCyan, FirewallRoute),
        HubItem("DDoS Koruma", Icons.Outlined.Shield, NeonRed, DdosRoute),
        HubItem("DDoS Haritasi", Icons.Outlined.Map, NeonMagenta, DdosMapRoute),
        HubItem("IP Yonetimi", Icons.Outlined.Language, NeonAmber, IpManagementRoute),
        HubItem("IP Itibar", Icons.Outlined.VerifiedUser, NeonGreen, IpReputationRoute),
        HubItem("Guvenlik Ayarlari", Icons.Outlined.Settings, NeonCyan, SecuritySettingsRoute),
        HubItem("AI Icgoruler", Icons.Outlined.Lightbulb, NeonMagenta, InsightsRoute),
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(16.dp),
    ) {
        Text(
            text = "Guvenlik",
            color = NeonRed,
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
