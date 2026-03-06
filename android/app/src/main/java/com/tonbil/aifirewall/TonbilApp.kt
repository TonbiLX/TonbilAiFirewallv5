package com.tonbil.aifirewall

import android.app.Application
import com.tonbil.aifirewall.di.appModule
import com.tonbil.aifirewall.di.featureModules
import org.koin.android.ext.koin.androidContext
import org.koin.core.context.startKoin

class TonbilApp : Application() {
    override fun onCreate() {
        super.onCreate()
        startKoin {
            androidContext(this@TonbilApp)
            modules(appModule, featureModules)
        }
    }
}
