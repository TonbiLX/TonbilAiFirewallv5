package com.tonbil.aifirewall.di

import com.tonbil.aifirewall.data.local.ServerConfig
import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.data.remote.NetworkMonitor
import com.tonbil.aifirewall.data.remote.ServerDiscovery
import com.tonbil.aifirewall.data.remote.createHttpClient
import com.tonbil.aifirewall.data.remote.WebSocketManager
import com.tonbil.aifirewall.data.remote.createTestHttpClient
import com.tonbil.aifirewall.data.repository.AuthRepository
import com.tonbil.aifirewall.data.repository.DashboardRepository
import com.tonbil.aifirewall.data.repository.DeviceRepository
import com.tonbil.aifirewall.data.repository.ProfileRepository
import com.tonbil.aifirewall.data.repository.SecurityRepository
import com.tonbil.aifirewall.feature.auth.LoginViewModel
import com.tonbil.aifirewall.feature.auth.ServerSettingsViewModel
import com.tonbil.aifirewall.feature.dashboard.DashboardViewModel
import com.tonbil.aifirewall.feature.devices.DeviceDetailViewModel
import com.tonbil.aifirewall.feature.devices.DevicesViewModel
import com.tonbil.aifirewall.feature.security.SecurityViewModel
import com.tonbil.aifirewall.feature.settings.SettingsViewModel
import io.ktor.client.HttpClient
import org.koin.core.module.dsl.viewModel
import org.koin.core.module.dsl.viewModelOf
import org.koin.android.ext.koin.androidContext
import org.koin.core.qualifier.named
import org.koin.dsl.module

val appModule = module {
    single { TokenManager(androidContext()) }
    single { ServerConfig(androidContext()) }
    single { NetworkMonitor(androidContext()) }
    single(named("test")) { createTestHttpClient() }
    single { ServerDiscovery(get<ServerConfig>(), get<HttpClient>(named("test"))) }
    single { createHttpClient(get<ServerDiscovery>(), get<TokenManager>()) }
    single { AuthRepository(get<HttpClient>(), get<TokenManager>()) }
    single { WebSocketManager(get<HttpClient>(), get<ServerDiscovery>(), get<TokenManager>(), get<NetworkMonitor>()) }
    single { DashboardRepository(get<HttpClient>()) }
    single { DeviceRepository(get<HttpClient>()) }
    single { ProfileRepository(get<HttpClient>()) }
    single { SecurityRepository(get<HttpClient>()) }
}

val featureModules = module {
    viewModelOf(::DashboardViewModel)
    viewModelOf(::DevicesViewModel)
    viewModel { params -> DeviceDetailViewModel(params.get(), get<DeviceRepository>(), get<ProfileRepository>(), get<WebSocketManager>()) }
    viewModelOf(::SecurityViewModel)
    viewModelOf(::SettingsViewModel)
    // Auth
    viewModelOf(::LoginViewModel)
    viewModelOf(::ServerSettingsViewModel)
}
