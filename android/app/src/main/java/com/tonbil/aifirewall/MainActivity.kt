package com.tonbil.aifirewall

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Modifier
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.navigation.compose.rememberNavController
import com.tonbil.aifirewall.ui.navigation.AppNavHost
import com.tonbil.aifirewall.ui.navigation.CyberpunkBottomNav
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()

        // Dark status bar and navigation bar
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.parseColor("#12122A")),
        )

        super.onCreate(savedInstanceState)

        setContent {
            CyberpunkTheme {
                val navController = rememberNavController()
                Scaffold(
                    bottomBar = {
                        CyberpunkBottomNav(navController)
                    },
                ) { innerPadding ->
                    AppNavHost(
                        navController = navController,
                        modifier = Modifier.padding(innerPadding),
                    )
                }
            }
        }
    }
}
