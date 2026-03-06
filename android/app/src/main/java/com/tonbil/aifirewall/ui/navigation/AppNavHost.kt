package com.tonbil.aifirewall.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.tonbil.aifirewall.feature.auth.LoginScreen
import com.tonbil.aifirewall.feature.auth.ServerSettingsScreen
import com.tonbil.aifirewall.feature.dashboard.DashboardScreen
import com.tonbil.aifirewall.feature.devices.DeviceDetailScreen
import com.tonbil.aifirewall.feature.devices.DevicesScreen
import androidx.navigation.toRoute
import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.feature.security.SecurityScreen
import com.tonbil.aifirewall.feature.settings.SettingsScreen
import com.tonbil.aifirewall.feature.splash.SplashScreen

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
            ServerSettingsScreen(
                onBack = { navController.popBackStack() },
            )
        }
        composable<DashboardRoute> { DashboardScreen(onNavigate = { navController.navigate(it) }) }
        composable<DevicesRoute> {
            DevicesScreen(onNavigateToDetail = { deviceId ->
                navController.navigate(DeviceDetailRoute(deviceId))
            })
        }
        composable<DeviceDetailRoute> { backStackEntry ->
            val route = backStackEntry.toRoute<DeviceDetailRoute>()
            DeviceDetailScreen(
                deviceId = route.deviceId,
                onBack = { navController.popBackStack() },
            )
        }
        composable<SecurityRoute> { SecurityScreen() }
        composable<SettingsRoute> { SettingsScreen() }
    }
}
