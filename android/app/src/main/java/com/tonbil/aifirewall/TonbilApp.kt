package com.tonbil.aifirewall

import android.app.Application
import android.util.Log
import com.tonbil.aifirewall.data.remote.WebSocketManager
import com.tonbil.aifirewall.di.appModule
import com.tonbil.aifirewall.di.featureModules
import com.tonbil.aifirewall.util.NotificationHelper
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.koin.android.ext.koin.androidContext
import org.koin.core.context.startKoin
import org.koin.java.KoinJavaComponent.getKoin
import java.io.File

class TonbilApp : Application() {

    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    override fun onCreate() {
        super.onCreate()

        // Global crash handler — write stack trace to file for debugging
        val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            try {
                val sb = StringBuilder()
                sb.appendLine("=== CRASH on ${thread.name} ===")
                sb.appendLine("Time: ${System.currentTimeMillis()}")
                sb.appendLine()

                // Build full cause chain explicitly
                var current: Throwable? = throwable
                var depth = 0
                while (current != null && depth < 10) {
                    if (depth > 0) sb.appendLine("\n--- Caused by (depth $depth) ---")
                    sb.appendLine("${current.javaClass.name}: ${current.message}")
                    current.stackTrace.take(15).forEach { frame ->
                        sb.appendLine("  at $frame")
                    }
                    if ((current.stackTrace.size) > 15) {
                        sb.appendLine("  ... ${current.stackTrace.size - 15} more")
                    }
                    current = current.cause
                    depth++
                }

                val crashLog = sb.toString()
                Log.e("TonbilCrash", crashLog)
                val file = File(filesDir, "crash_log.txt")
                file.writeText(crashLog)
            } catch (_: Exception) { /* best effort */ }
            defaultHandler?.uncaughtException(thread, throwable)
        }

        startKoin {
            androidContext(this@TonbilApp)
            modules(appModule, featureModules)
        }

        // Bildirim kanalini olustur
        NotificationHelper.createNotificationChannel(this)

        // WebSocket security event'lerini dinle ve sistem bildirimi goster
        observeSecurityEvents()
    }

    private fun observeSecurityEvents() {
        appScope.launch {
            try {
                val wsManager = getKoin().get<WebSocketManager>()
                wsManager.securityEvents.collect { event ->
                    Log.d("TonbilApp", "Security event: ${event.eventType} - ${event.title}")
                    NotificationHelper.showSecurityNotification(this@TonbilApp, event)
                }
            } catch (e: Exception) {
                Log.e("TonbilApp", "Security event observer error: ${e.message}")
            }
        }
    }
}
