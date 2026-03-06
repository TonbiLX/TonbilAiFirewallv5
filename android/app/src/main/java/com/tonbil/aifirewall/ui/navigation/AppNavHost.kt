package com.tonbil.aifirewall.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.tonbil.aifirewall.feature.dashboard.DashboardScreen
import com.tonbil.aifirewall.feature.devices.DevicesScreen
import com.tonbil.aifirewall.feature.security.SecurityScreen
import com.tonbil.aifirewall.feature.settings.SettingsScreen

@Composable
fun AppNavHost(navController: NavHostController, modifier: Modifier = Modifier) {
    NavHost(
        navController = navController,
        startDestination = DashboardRoute,
        modifier = modifier,
    ) {
        composable<DashboardRoute> { DashboardScreen() }
        composable<DevicesRoute> { DevicesScreen() }
        composable<SecurityRoute> { SecurityScreen() }
        composable<SettingsRoute> { SettingsScreen() }
    }
}
