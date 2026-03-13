package com.tonbil.aifirewall

import android.app.Activity
import android.app.Application
import android.util.Log
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.tonbil.aifirewall.data.remote.WebSocketManager
import com.tonbil.aifirewall.di.appModule
import com.tonbil.aifirewall.di.featureModules
import com.tonbil.aifirewall.util.HapticHelper
import com.tonbil.aifirewall.util.NotificationHelper
import com.tonbil.aifirewall.widget.TonbilWidgetWorker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.koin.android.ext.koin.androidContext
import org.koin.core.context.startKoin
import org.koin.java.KoinJavaComponent.getKoin
import java.io.File
import java.util.concurrent.TimeUnit

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

        // 4 bildirim kanalini olustur (security_threats, device_events, traffic_alerts, system_notifications)
        NotificationHelper.createNotificationChannels(this)

        // WebSocket security event'lerini dinle ve sistem bildirimi goster
        observeSecurityEvents()

        // Aktif Activity takibi — HapticHelper icin WeakReference guncelleme
        registerActivityLifecycleCallbacks(object : ActivityLifecycleCallbacks {
            override fun onActivityResumed(activity: Activity) {
                HapticHelper.registerActivity(activity)
            }
            override fun onActivityPaused(activity: Activity) {
                HapticHelper.unregisterActivity()
            }
            override fun onActivityCreated(activity: Activity, savedInstanceState: android.os.Bundle?) {}
            override fun onActivityStarted(activity: Activity) {}
            override fun onActivityStopped(activity: Activity) {}
            override fun onActivitySaveInstanceState(activity: Activity, outState: android.os.Bundle) {}
            override fun onActivityDestroyed(activity: Activity) {}
        })

        // Widget'i 15 dakikada bir guncelleyen WorkManager periyodik is
        scheduleWidgetRefresh()
    }

    private fun scheduleWidgetRefresh() {
        try {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val request = PeriodicWorkRequestBuilder<TonbilWidgetWorker>(15, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .build()

            WorkManager.getInstance(this).enqueueUniquePeriodicWork(
                "tonbil_widget_refresh",
                ExistingPeriodicWorkPolicy.KEEP,
                request
            )
            Log.d("TonbilApp", "Widget guncelleme is planlandi (15 dk)")
        } catch (e: Exception) {
            Log.e("TonbilApp", "Widget is planlamasi basarisiz: ${e.message}")
        }
    }

    private fun observeSecurityEvents() {
        appScope.launch {
            try {
                val wsManager = getKoin().get<WebSocketManager>()
                wsManager.securityEvents.collect { event ->
                    Log.d("TonbilApp", "Security event: ${event.eventType} - ${event.title}")
                    // Uygulama on plandayken haptic tetikle (arka planda bildirim zaten vibrate icerir)
                    if (event.severity in listOf("critical", "warning")) {
                        HapticHelper.triggerHaptic(event.severity)
                    }
                    NotificationHelper.showSecurityNotification(this@TonbilApp, event)
                }
            } catch (e: Exception) {
                Log.e("TonbilApp", "Security event observer error: ${e.message}")
            }
        }
    }
}
