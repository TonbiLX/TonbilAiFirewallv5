package com.tonbil.aifirewall.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.tonbil.aifirewall.feature.auth.LoginScreen
import com.tonbil.aifirewall.feature.auth.ServerSettingsScreen
import com.tonbil.aifirewall.feature.dashboard.DashboardScreen
import com.tonbil.aifirewall.feature.devices.DevicesScreen
import com.tonbil.aifirewall.feature.security.SecurityScreen
import com.tonbil.aifirewall.feature.settings.SettingsScreen

@Composable
fun AppNavHost(
    navController: NavHostController,
    modifier: Modifier = Modifier,
    startDestination: Any = DashboardRoute,
) {
    NavHost(
        navController = navController,
        startDestination = startDestination,
        modifier = modifier,
    ) {
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
        composable<DevicesRoute> { DevicesScreen() }
        composable<SecurityRoute> { SecurityScreen() }
        composable<SettingsRoute> { SettingsScreen() }
    }
}
