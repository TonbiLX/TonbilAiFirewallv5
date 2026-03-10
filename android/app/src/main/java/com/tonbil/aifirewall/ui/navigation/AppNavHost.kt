package com.tonbil.aifirewall.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.toRoute
import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.feature.auth.LoginScreen
import com.tonbil.aifirewall.feature.auth.ServerSettingsScreen
import com.tonbil.aifirewall.feature.dashboard.DashboardScreen
import com.tonbil.aifirewall.feature.devices.DeviceDetailScreen
import com.tonbil.aifirewall.feature.devices.DevicesScreen
import com.tonbil.aifirewall.feature.network.NetworkHubScreen
import com.tonbil.aifirewall.feature.security.SecurityHubScreen
import com.tonbil.aifirewall.feature.settings.SettingsHubScreen
import com.tonbil.aifirewall.feature.splash.SplashScreen
import com.tonbil.aifirewall.feature.vpnclient.VpnClientScreen
import com.tonbil.aifirewall.feature.categories.ContentCategoriesScreen
import com.tonbil.aifirewall.feature.deviceservices.DeviceServicesScreen
import com.tonbil.aifirewall.feature.ipmanagement.IpManagementScreen
import com.tonbil.aifirewall.feature.ipreputation.IpReputationScreen
import com.tonbil.aifirewall.feature.securitysettings.SecuritySettingsScreen
import com.tonbil.aifirewall.feature.insights.InsightsScreen
import com.tonbil.aifirewall.feature.ddosmap.DdosMapScreen
import com.tonbil.aifirewall.feature.systemmonitor.SystemMonitorScreen
import com.tonbil.aifirewall.feature.systemmanagement.SystemManagementScreen
import com.tonbil.aifirewall.feature.systemtime.SystemTimeScreen
import com.tonbil.aifirewall.feature.systemlogs.SystemLogsScreen
import com.tonbil.aifirewall.feature.tls.TlsScreen
import com.tonbil.aifirewall.feature.aisettings.AiSettingsScreen
import com.tonbil.aifirewall.feature.traffic.TrafficScreen
import com.tonbil.aifirewall.feature.notifications.PushNotificationsScreen
import com.tonbil.aifirewall.feature.usersettings.UserSettingsScreen
import com.tonbil.aifirewall.feature.dnsblocking.DnsBlockingScreen
import com.tonbil.aifirewall.feature.dhcp.DhcpScreen
import com.tonbil.aifirewall.feature.vpnserver.VpnServerScreen
import com.tonbil.aifirewall.feature.wifi.WifiScreen
import com.tonbil.aifirewall.feature.firewall.FirewallScreen
import com.tonbil.aifirewall.feature.ddos.DdosScreen
import com.tonbil.aifirewall.feature.telegram.TelegramScreen
import com.tonbil.aifirewall.feature.chat.ChatScreen
import com.tonbil.aifirewall.feature.profiles.ProfilesScreen

@Composable
fun AppNavHost(
    navController: NavHostController,
    modifier: Modifier = Modifier,
    startDestination: Any = DashboardRoute,
    tokenManager: TokenManager,
) {
    NavHost(
        navController = navController,
        startDestination = startDestination,
        modifier = modifier,
    ) {
        // ========== Splash & Auth ==========
        composable<SplashRoute> {
            SplashScreen(
                onSplashFinished = {
                    val nextRoute: Any = if (tokenManager.isLoggedIn()) DashboardRoute else LoginRoute
                    navController.navigate(nextRoute) {
                        popUpTo(SplashRoute) { inclusive = true }
                    }
                },
            )
        }
        composable<LoginRoute> {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(DashboardRoute) {
                        popUpTo(LoginRoute) { inclusive = true }
                    }
                },
                onNavigateToServerSettings = {
                    navController.navigate(ServerSettingsRoute)
                },
            )
        }
        composable<ServerSettingsRoute> {
            ServerSettingsScreen(onBack = { navController.popBackStack() })
        }

        // ========== Bottom Nav Main Screens ==========
        composable<DashboardRoute> {
            DashboardScreen(onNavigate = { navController.navigate(it) })
        }
        composable<DevicesRoute> {
            DevicesScreen(onNavigateToDetail = { deviceId ->
                navController.navigate(DeviceDetailRoute(deviceId))
            })
        }
        composable<NetworkRoute> {
            NetworkHubScreen(onNavigate = { navController.navigate(it) })
        }
        composable<SecurityRoute> {
            SecurityHubScreen(onNavigate = { navController.navigate(it) })
        }
        composable<SettingsRoute> {
            SettingsHubScreen(onNavigate = { navController.navigate(it) })
        }

        // ========== Device Sub-Screens ==========
        composable<DeviceDetailRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<DeviceDetailRoute>()
            DeviceDetailScreen(
                deviceId = route.deviceId,
                onBack = { navController.popBackStack() },
            )
        }
        composable<DeviceServicesRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<DeviceServicesRoute>()
            DeviceServicesScreen(
                deviceId = route.deviceId.toIntOrNull() ?: 0,
                deviceName = route.deviceName,
                onBack = { navController.popBackStack() },
            )
        }

        // ========== Network Sub-Screens ==========
        composable<DnsBlockingRoute> { DnsBlockingScreen(onBack = { navController.popBackStack() }) }
        composable<DhcpRoute> { DhcpScreen(onBack = { navController.popBackStack() }) }
        composable<VpnServerRoute> { VpnServerScreen(onBack = { navController.popBackStack() }) }
        composable<VpnClientRoute> { VpnClientScreen(onBack = { navController.popBackStack() }) }
        composable<TrafficRoute> { TrafficScreen(onBack = { navController.popBackStack() }) }
        composable<ContentCategoriesRoute> { ContentCategoriesScreen(onBack = { navController.popBackStack() }) }
        composable<WifiRoute> { WifiScreen(onBack = { navController.popBackStack() }) }

        // ========== Security Sub-Screens ==========
        composable<FirewallRoute> { FirewallScreen(onBack = { navController.popBackStack() }) }
        composable<DdosRoute> { DdosScreen(onBack = { navController.popBackStack() }) }
        composable<DdosMapRoute> { DdosMapScreen(onBack = { navController.popBackStack() }) }
        composable<IpManagementRoute> { IpManagementScreen(onBack = { navController.popBackStack() }) }
        composable<IpReputationRoute> { IpReputationScreen(onBack = { navController.popBackStack() }) }
        composable<SecuritySettingsRoute> { SecuritySettingsScreen(onBack = { navController.popBackStack() }) }
        composable<InsightsRoute> { InsightsScreen(onBack = { navController.popBackStack() }) }

        // ========== Settings Sub-Screens ==========
        composable<SystemMonitorRoute> { SystemMonitorScreen(onBack = { navController.popBackStack() }) }
        composable<SystemManagementRoute> { SystemManagementScreen(onBack = { navController.popBackStack() }) }
        composable<SystemTimeRoute> { SystemTimeScreen(onBack = { navController.popBackStack() }) }
        composable<SystemLogsRoute> { SystemLogsScreen(onBack = { navController.popBackStack() }) }
        composable<TlsRoute> { TlsScreen(onBack = { navController.popBackStack() }) }
        composable<AiSettingsRoute> { AiSettingsScreen(onBack = { navController.popBackStack() }) }
        composable<TelegramRoute> { TelegramScreen(onBack = { navController.popBackStack() }) }
        composable<ChatRoute> { ChatScreen(onBack = { navController.popBackStack() }) }
        composable<PushNotificationsRoute> { PushNotificationsScreen(onBack = { navController.popBackStack() }) }
        composable<ProfilesRoute> { ProfilesScreen(onBack = { navController.popBackStack() }) }
        composable<UserSettingsRoute> {
            UserSettingsScreen(
                onBack = { navController.popBackStack() },
                onLogout = {
                    tokenManager.clearTokens()
                    navController.navigate(LoginRoute) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }
    }
}
