package com.tonbil.aifirewall.di

import com.tonbil.aifirewall.data.local.ServerConfig
import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.data.remote.ServerDiscovery
import com.tonbil.aifirewall.data.remote.createHttpClient
import com.tonbil.aifirewall.data.remote.WebSocketManager
import com.tonbil.aifirewall.data.remote.createTestHttpClient
import com.tonbil.aifirewall.data.repository.AuthRepository
import com.tonbil.aifirewall.data.repository.DashboardRepository
import com.tonbil.aifirewall.data.repository.DeviceRepository
import com.tonbil.aifirewall.data.repository.ProfileRepository
import com.tonbil.aifirewall.feature.auth.LoginViewModel
import com.tonbil.aifirewall.feature.auth.ServerSettingsViewModel
import com.tonbil.aifirewall.feature.dashboard.DashboardViewModel
import com.tonbil.aifirewall.feature.devices.DevicesViewModel
import com.tonbil.aifirewall.feature.security.SecurityViewModel
import com.tonbil.aifirewall.feature.settings.SettingsViewModel
import io.ktor.client.HttpClient
import org.koin.core.module.dsl.viewModel
import org.koin.android.ext.koin.androidContext
import org.koin.core.qualifier.named
import org.koin.dsl.module

val appModule = module {
    single { TokenManager(androidContext()) }
    single { ServerConfig(androidContext()) }
    single(named("test")) { createTestHttpClient() }
    single { ServerDiscovery(get<ServerConfig>(), get<HttpClient>(named("test"))) }
    single { createHttpClient(get<ServerDiscovery>(), get<TokenManager>()) }
    single { AuthRepository(get(), get<TokenManager>()) }
    single { WebSocketManager(get(), get<ServerDiscovery>(), get<TokenManager>()) }
    single { DashboardRepository(get()) }
    single { DeviceRepository(get()) }
    single { ProfileRepository(get()) }
}

val featureModules = module {
    viewModel { DashboardViewModel(get(), get()) }
    viewModel { DevicesViewModel() }
    viewModel { SecurityViewModel() }
    viewModel { SettingsViewModel() }
    // Auth
    viewModel { LoginViewModel(get(), get()) }
    viewModel { ServerSettingsViewModel(get(), get()) }
}
