package com.tonbil.aifirewall.feature.network

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.FilterList
import androidx.compose.material.icons.outlined.Router
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material.icons.outlined.VpnKey
import androidx.compose.material.icons.outlined.VpnLock
import androidx.compose.material.icons.outlined.Wifi
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.ui.navigation.ContentCategoriesRoute
import com.tonbil.aifirewall.ui.navigation.DhcpRoute
import com.tonbil.aifirewall.ui.navigation.DnsBlockingRoute
import com.tonbil.aifirewall.ui.navigation.TrafficRoute
import com.tonbil.aifirewall.ui.navigation.VpnClientRoute
import com.tonbil.aifirewall.ui.navigation.VpnServerRoute
import com.tonbil.aifirewall.ui.navigation.WifiRoute
import com.tonbil.aifirewall.ui.theme.*

// Shared data class — imported by Security and Settings hub screens
data class HubItem(
    val label: String,
    val icon: ImageVector,
    val color: Color,
    val route: Any,
)

@Composable
fun NetworkHubScreen(onNavigate: (Any) -> Unit) {
    val items = listOf(
        HubItem("DNS Engelleme", Icons.Outlined.Shield, NeonCyan, DnsBlockingRoute),
        HubItem("DHCP Sunucu", Icons.Outlined.Router, NeonGreen, DhcpRoute),
        HubItem("VPN Sunucu", Icons.Outlined.VpnKey, NeonMagenta, VpnServerRoute),
        HubItem("VPN Istemci", Icons.Outlined.VpnLock, NeonAmber, VpnClientRoute),
        HubItem("Trafik Izleme", Icons.Outlined.ShowChart, NeonCyan, TrafficRoute),
        HubItem("Icerik Filtreleri", Icons.Outlined.FilterList, NeonRed, ContentCategoriesRoute),
        HubItem("WiFi AP", Icons.Outlined.Wifi, NeonGreen, WifiRoute),
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkBackground)
            .padding(16.dp),
    ) {
        Text(
            text = "Ag Yonetimi",
            color = NeonCyan,
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

@Composable
fun HubCard(item: HubItem, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .aspectRatio(1.1f)
            .drawBehind {
                drawRoundRect(
                    color = item.color.copy(alpha = 0.10f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(16.dp.toPx()),
                    style = Stroke(width = 5.dp.toPx()),
                )
            }
            .clip(RoundedCornerShape(16.dp))
            .background(GlassBg)
            .clickable(onClick = onClick)
            .padding(16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Box(
                modifier = Modifier
                    .size(52.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(item.color.copy(alpha = 0.12f)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = item.icon,
                    contentDescription = item.label,
                    tint = item.color,
                    modifier = Modifier.size(28.dp),
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            Text(
                text = item.label,
                color = TextPrimary,
                fontSize = 13.sp,
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center,
                lineHeight = 17.sp,
            )
        }
    }
}
