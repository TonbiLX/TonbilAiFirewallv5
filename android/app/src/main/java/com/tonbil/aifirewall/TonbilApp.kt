package com.tonbil.aifirewall

import android.app.Application
import android.util.Log
import com.tonbil.aifirewall.di.appModule
import com.tonbil.aifirewall.di.featureModules
import org.koin.android.ext.koin.androidContext
import org.koin.core.context.startKoin
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter

class TonbilApp : Application() {
    override fun onCreate() {
        super.onCreate()

        // Global crash handler — write stack trace to file for debugging
        val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            try {
                val sw = StringWriter()
                throwable.printStackTrace(PrintWriter(sw))
                val crashLog = sw.toString()
                Log.e("TonbilCrash", "UNCAUGHT EXCEPTION on ${thread.name}:\n$crashLog")
                val file = File(filesDir, "crash_log.txt")
                file.writeText("${System.currentTimeMillis()}\n${thread.name}\n$crashLog")
            } catch (_: Exception) { /* best effort */ }
            defaultHandler?.uncaughtException(thread, throwable)
        }

        startKoin {
            androidContext(this@TonbilApp)
            modules(appModule, featureModules)
        }
    }
}
