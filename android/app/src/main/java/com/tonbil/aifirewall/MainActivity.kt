package com.tonbil.aifirewall

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.ui.navigation.AppNavHost
import com.tonbil.aifirewall.ui.navigation.CyberpunkBottomNav
import com.tonbil.aifirewall.ui.navigation.DashboardRoute
import com.tonbil.aifirewall.ui.navigation.LoginRoute
import com.tonbil.aifirewall.ui.navigation.ServerSettingsRoute
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.android.ext.android.inject

class MainActivity : ComponentActivity() {

    private val tokenManager: TokenManager by inject()

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()

        // Dark status bar and navigation bar
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.parseColor("#12122A")),
        )

        super.onCreate(savedInstanceState)

        // Determine start destination based on token state
        val startDestination: Any = if (tokenManager.isLoggedIn()) {
            if (tokenManager.isBiometricEnabled()) {
                // Has token + biometric enabled → show login for biometric prompt
                LoginRoute
            } else {
                // Has token, no biometric → go directly to dashboard
                DashboardRoute
            }
        } else {
            // No token → must login
            LoginRoute
        }

        setContent {
            CyberpunkTheme {
                val navController = rememberNavController()
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = navBackStackEntry?.destination

                // Hide bottom nav on auth screens
                val isAuthScreen = currentDestination?.hasRoute(LoginRoute::class) == true ||
                    currentDestination?.hasRoute(ServerSettingsRoute::class) == true

                Scaffold(
                    bottomBar = {
                        if (!isAuthScreen) {
                            CyberpunkBottomNav(navController)
                        }
                    },
                ) { innerPadding ->
                    AppNavHost(
                        navController = navController,
                        modifier = Modifier.padding(innerPadding),
                        startDestination = startDestination,
                    )
                }
            }
        }
    }
}
