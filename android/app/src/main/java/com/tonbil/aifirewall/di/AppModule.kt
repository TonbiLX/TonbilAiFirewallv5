package com.tonbil.aifirewall.di

import com.tonbil.aifirewall.data.local.ServerConfig
import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.data.remote.NetworkMonitor
import com.tonbil.aifirewall.data.remote.ServerDiscovery
import com.tonbil.aifirewall.data.remote.createHttpClient
import com.tonbil.aifirewall.data.remote.WebSocketManager
import com.tonbil.aifirewall.data.remote.createTestHttpClient
import com.tonbil.aifirewall.data.repository.AiSettingsRepository
import com.tonbil.aifirewall.data.repository.AuthRepository
import com.tonbil.aifirewall.data.repository.ContentCategoryRepository
import com.tonbil.aifirewall.data.repository.DashboardRepository
import com.tonbil.aifirewall.data.repository.DeviceRepository
import com.tonbil.aifirewall.data.repository.DeviceServiceRepository
import com.tonbil.aifirewall.data.repository.InsightsRepository
import com.tonbil.aifirewall.data.repository.IpManagementRepository
import com.tonbil.aifirewall.data.repository.IpReputationRepository
import com.tonbil.aifirewall.data.repository.ProfileRepository
import com.tonbil.aifirewall.data.repository.SecurityRepository
import com.tonbil.aifirewall.data.repository.SystemRepository
import com.tonbil.aifirewall.data.repository.TlsRepository
import com.tonbil.aifirewall.data.repository.VpnClientRepository
import com.tonbil.aifirewall.feature.aisettings.AiSettingsViewModel
import com.tonbil.aifirewall.feature.auth.LoginViewModel
import com.tonbil.aifirewall.feature.auth.ServerSettingsViewModel
import com.tonbil.aifirewall.feature.categories.ContentCategoriesViewModel
import com.tonbil.aifirewall.feature.dashboard.DashboardViewModel
import com.tonbil.aifirewall.feature.ddosmap.DdosMapViewModel
import com.tonbil.aifirewall.feature.devices.DeviceDetailViewModel
import com.tonbil.aifirewall.feature.devices.DevicesViewModel
import com.tonbil.aifirewall.feature.deviceservices.DeviceServicesViewModel
import com.tonbil.aifirewall.feature.insights.InsightsViewModel
import com.tonbil.aifirewall.feature.ipmanagement.IpManagementViewModel
import com.tonbil.aifirewall.feature.ipreputation.IpReputationViewModel
import com.tonbil.aifirewall.feature.notifications.PushNotificationsViewModel
import com.tonbil.aifirewall.feature.security.SecurityViewModel
import com.tonbil.aifirewall.feature.securitysettings.SecuritySettingsViewModel
import com.tonbil.aifirewall.feature.settings.SettingsViewModel
import com.tonbil.aifirewall.feature.systemlogs.SystemLogsViewModel
import com.tonbil.aifirewall.feature.systemmanagement.SystemManagementViewModel
import com.tonbil.aifirewall.feature.systemmonitor.SystemMonitorViewModel
import com.tonbil.aifirewall.feature.systemtime.SystemTimeViewModel
import com.tonbil.aifirewall.feature.tls.TlsViewModel
import com.tonbil.aifirewall.feature.traffic.TrafficViewModel
import com.tonbil.aifirewall.feature.usersettings.UserSettingsViewModel
import com.tonbil.aifirewall.feature.vpnclient.VpnClientViewModel
import com.tonbil.aifirewall.feature.dnsblocking.DnsBlockingViewModel
import com.tonbil.aifirewall.feature.dhcp.DhcpViewModel
import com.tonbil.aifirewall.feature.vpnserver.VpnServerViewModel
import com.tonbil.aifirewall.feature.firewall.FirewallViewModel
import com.tonbil.aifirewall.feature.ddos.DdosViewModel
import com.tonbil.aifirewall.feature.wifi.WifiViewModel
import com.tonbil.aifirewall.feature.telegram.TelegramViewModel
import com.tonbil.aifirewall.feature.chat.ChatViewModel
import com.tonbil.aifirewall.feature.profiles.ProfilesViewModel
import io.ktor.client.HttpClient
import org.koin.core.module.dsl.viewModel
import org.koin.core.module.dsl.viewModelOf
import org.koin.android.ext.koin.androidContext
import org.koin.core.qualifier.named
import org.koin.dsl.module

val appModule = module {
    // Core
    single { TokenManager(androidContext()) }
    single { ServerConfig(androidContext()) }
    single { NetworkMonitor(androidContext()) }
    single(named("test")) { createTestHttpClient() }
    single { ServerDiscovery(get<ServerConfig>(), get<HttpClient>(named("test"))) }
    single { createHttpClient(get<ServerDiscovery>(), get<TokenManager>()) }
    single { WebSocketManager(get<HttpClient>(), get<ServerDiscovery>(), get<TokenManager>(), get<NetworkMonitor>()) }

    // Repositories
    single { AuthRepository(get<HttpClient>(), get<TokenManager>()) }
    single { DashboardRepository(get<HttpClient>()) }
    single { DeviceRepository(get<HttpClient>()) }
    single { ProfileRepository(get<HttpClient>()) }
    single { SecurityRepository(get<HttpClient>()) }
    single { VpnClientRepository(get<HttpClient>()) }
    single { ContentCategoryRepository(get<HttpClient>()) }
    single { DeviceServiceRepository(get<HttpClient>()) }
    single { IpManagementRepository(get<HttpClient>()) }
    single { IpReputationRepository(get<HttpClient>()) }
    single { SystemRepository(get<HttpClient>()) }
    single { TlsRepository(get<HttpClient>()) }
    single { AiSettingsRepository(get<HttpClient>()) }
    single { InsightsRepository(get<HttpClient>()) }
}

val featureModules = module {
    // Existing ViewModels
    viewModelOf(::DashboardViewModel)
    viewModelOf(::DevicesViewModel)
    viewModel { params -> DeviceDetailViewModel(params.get(), get<DeviceRepository>(), get<ProfileRepository>(), get<WebSocketManager>()) }
    viewModelOf(::SecurityViewModel)
    viewModelOf(::SettingsViewModel)
    viewModelOf(::LoginViewModel)
    viewModelOf(::ServerSettingsViewModel)

    // New ViewModels
    viewModelOf(::VpnClientViewModel)
    viewModel { ContentCategoriesViewModel(get<ContentCategoryRepository>(), get<SecurityRepository>()) }
    viewModel { params -> DeviceServicesViewModel(params.get(), get<DeviceServiceRepository>()) }
    viewModelOf(::IpManagementViewModel)
    viewModelOf(::IpReputationViewModel)
    viewModelOf(::SecuritySettingsViewModel)
    viewModelOf(::InsightsViewModel)
    viewModelOf(::DdosMapViewModel)
    viewModelOf(::SystemMonitorViewModel)
    viewModelOf(::SystemManagementViewModel)
    viewModelOf(::SystemTimeViewModel)
    viewModelOf(::SystemLogsViewModel)
    viewModelOf(::TlsViewModel)
    viewModelOf(::AiSettingsViewModel)
    viewModelOf(::TrafficViewModel)
    viewModelOf(::PushNotificationsViewModel)
    viewModelOf(::UserSettingsViewModel)

    // Placeholder → Real Screen ViewModels
    viewModelOf(::DnsBlockingViewModel)
    viewModelOf(::DhcpViewModel)
    viewModelOf(::VpnServerViewModel)
    viewModelOf(::FirewallViewModel)
    viewModelOf(::DdosViewModel)
    viewModelOf(::WifiViewModel)
    viewModelOf(::TelegramViewModel)
    viewModelOf(::ChatViewModel)
    viewModelOf(::ProfilesViewModel)
}
