package com.tonbil.aifirewall.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Lan
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Smartphone
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.compose.currentBackStackEntryAsState
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.TextSecondary

data class BottomNavItem(
    val label: String,
    val icon: ImageVector,
    val route: Any,
    val childRoutes: List<kotlin.reflect.KClass<*>> = emptyList(),
)

val bottomNavItems = listOf(
    BottomNavItem("Panel", Icons.Default.Home, DashboardRoute),
    BottomNavItem("Cihaz", Icons.Default.Smartphone, DevicesRoute, listOf(
        DeviceDetailRoute::class, DeviceServicesRoute::class,
    )),
    BottomNavItem("Ag", Icons.Default.Lan, NetworkRoute, listOf(
        DnsBlockingRoute::class, DhcpRoute::class, VpnServerRoute::class,
        VpnClientRoute::class, TrafficRoute::class, ContentCategoriesRoute::class,
        WifiRoute::class,
    )),
    BottomNavItem("Guvenlik", Icons.Default.Shield, SecurityRoute, listOf(
        FirewallRoute::class, DdosRoute::class, DdosMapRoute::class,
        IpManagementRoute::class, IpReputationRoute::class,
        SecuritySettingsRoute::class, InsightsRoute::class,
    )),
    BottomNavItem("Ayar", Icons.Default.Settings, SettingsRoute, listOf(
        SystemMonitorRoute::class, SystemManagementRoute::class, SystemTimeRoute::class,
        SystemLogsRoute::class, TlsRoute::class, AiSettingsRoute::class,
        TelegramRoute::class, ChatRoute::class, PushNotificationsRoute::class,
        UserSettingsRoute::class, ProfilesRoute::class,
    )),
)

@Composable
fun CyberpunkBottomNav(navController: NavController) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    Box(
        modifier = Modifier.drawBehind {
            // Top glow line
            drawRoundRect(
                brush = Brush.horizontalGradient(
                    listOf(
                        Color.Transparent,
                        NeonCyan.copy(alpha = 0.3f),
                        NeonMagenta.copy(alpha = 0.2f),
                        NeonCyan.copy(alpha = 0.3f),
                        Color.Transparent,
                    )
                ),
                size = size.copy(height = 2.dp.toPx()),
                cornerRadius = CornerRadius(1.dp.toPx()),
            )
        },
    ) {
        NavigationBar(
            containerColor = DarkSurface,
            contentColor = NeonCyan,
        ) {
            bottomNavItems.forEach { item ->
                val selected = currentDestination?.hasRoute(item.route::class) == true ||
                    item.childRoutes.any { currentDestination?.hasRoute(it) == true }

                NavigationBarItem(
                    selected = selected,
                    onClick = {
                        navController.navigate(item.route) {
                            // Always pop back to Dashboard (the real root after auth)
                            // so that any sub-screen is cleared when switching tabs
                            popUpTo<DashboardRoute> {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    icon = {
                        Icon(
                            imageVector = item.icon,
                            contentDescription = item.label,
                        )
                    },
                    label = { Text(item.label) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = NeonCyan,
                        selectedTextColor = NeonCyan,
                        unselectedIconColor = TextSecondary,
                        unselectedTextColor = TextSecondary,
                        indicatorColor = NeonCyan.copy(alpha = 0.1f),
                    ),
                )
            }
        }
    }
}
