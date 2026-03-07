package com.tonbil.aifirewall

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.ui.unit.dp
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
import com.tonbil.aifirewall.ui.navigation.SplashRoute
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.android.ext.android.inject
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import android.widget.Toast
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.mutableStateOf

class MainActivity : ComponentActivity() {

    private val tokenManager: TokenManager by inject()
    private val crashText = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()

        // Dark status bar and navigation bar
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.parseColor("#12122A")),
        )

        super.onCreate(savedInstanceState)

        // Check for previous crash log
        val crashFile = File(filesDir, "crash_log.txt")
        if (crashFile.exists()) {
            crashText.value = crashFile.readText()
            crashFile.delete()
        }

        // Splash intro: only once per day, at app launch (before login)
        val showSplash = tokenManager.shouldShowSplashToday()
        if (showSplash) {
            tokenManager.markSplashShownToday()
        }

        val startDestination: Any = if (showSplash) {
            SplashRoute
        } else if (tokenManager.isLoggedIn() && !tokenManager.isBiometricEnabled()) {
            DashboardRoute
        } else {
            LoginRoute
        }

        setContent {
            CyberpunkTheme {
                val crash = crashText.value
                if (crash != null) {
                    // Show crash log on screen so user can screenshot it
                    androidx.compose.foundation.layout.Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp)
                            .verticalScroll(rememberScrollState()),
                    ) {
                        Text(
                            text = "HATA",
                            color = androidx.compose.ui.graphics.Color.Red,
                            style = androidx.compose.material3.MaterialTheme.typography.headlineLarge,
                        )
                        // Extract first exception line for easy reading
                        val lines = crash.lines()
                        val exceptionLine = lines.firstOrNull { it.contains("Exception") || it.contains("Error") } ?: ""
                        if (exceptionLine.isNotBlank()) {
                            androidx.compose.foundation.layout.Spacer(modifier = Modifier.padding(8.dp))
                            Text(
                                text = exceptionLine.trim(),
                                color = androidx.compose.ui.graphics.Color.Yellow,
                                style = androidx.compose.material3.MaterialTheme.typography.titleMedium,
                                fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                            )
                        }
                        androidx.compose.foundation.layout.Spacer(modifier = Modifier.padding(8.dp))
                        Text(
                            text = crash,
                            color = androidx.compose.ui.graphics.Color.White,
                            style = androidx.compose.material3.MaterialTheme.typography.bodySmall,
                            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                        )
                        androidx.compose.foundation.layout.Spacer(modifier = Modifier.padding(16.dp))
                        androidx.compose.material3.Button(onClick = { crashText.value = null }) {
                            Text("Devam Et")
                        }
                    }
                } else {
                    val navController = rememberNavController()
                    val navBackStackEntry by navController.currentBackStackEntryAsState()
                    val currentDestination = navBackStackEntry?.destination

                    // Hide bottom nav on auth/splash screens
                    val isAuthScreen = currentDestination?.hasRoute(LoginRoute::class) == true ||
                        currentDestination?.hasRoute(ServerSettingsRoute::class) == true ||
                        currentDestination?.hasRoute(SplashRoute::class) == true

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
                            tokenManager = tokenManager,
                        )
                    }
                }
            }
        }
    }
}
