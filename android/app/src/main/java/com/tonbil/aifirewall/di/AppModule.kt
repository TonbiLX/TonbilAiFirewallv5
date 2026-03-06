package com.tonbil.aifirewall.di

import com.tonbil.aifirewall.data.remote.createHttpClient
import com.tonbil.aifirewall.feature.dashboard.DashboardViewModel
import com.tonbil.aifirewall.feature.devices.DevicesViewModel
import com.tonbil.aifirewall.feature.security.SecurityViewModel
import com.tonbil.aifirewall.feature.settings.SettingsViewModel
import org.koin.core.module.dsl.viewModel
import org.koin.dsl.module

val appModule = module {
    single { createHttpClient() }
}

val featureModules = module {
    viewModel { DashboardViewModel(get()) }
    viewModel { DevicesViewModel() }
    viewModel { SecurityViewModel() }
    viewModel { SettingsViewModel() }
}
