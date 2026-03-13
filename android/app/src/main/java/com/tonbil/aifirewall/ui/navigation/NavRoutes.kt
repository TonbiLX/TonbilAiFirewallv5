package com.tonbil.aifirewall.ui.navigation

import kotlinx.serialization.Serializable

// ========== Bottom Nav Top-Level ==========
@Serializable object DashboardRoute
@Serializable object DevicesRoute
@Serializable object NetworkRoute       // Ag bolumu (yeni)
@Serializable object SecurityRoute
@Serializable object SettingsRoute

// ========== Splash & Auth ==========
@Serializable object SplashRoute
@Serializable object LoginRoute
@Serializable object ServerSettingsRoute

// ========== Device Sub-Screens ==========
@Serializable data class DeviceDetailRoute(val deviceId: String)
@Serializable data class DeviceServicesRoute(val deviceId: String, val deviceName: String = "")

// ========== Network Section ==========
@Serializable object DnsFilteringRoute
@Serializable object DnsBlockingRoute
@Serializable object DhcpRoute
@Serializable object VpnServerRoute
@Serializable object VpnClientRoute
@Serializable object TrafficRoute
@Serializable object ContentCategoriesRoute
@Serializable object WifiRoute

// ========== Security Section ==========
@Serializable object FirewallRoute
@Serializable object DdosRoute
@Serializable object DdosMapRoute
@Serializable object IpManagementRoute
@Serializable object IpReputationRoute
@Serializable object SecuritySettingsRoute
@Serializable object InsightsRoute

// ========== Settings Section ==========
@Serializable object SystemMonitorRoute
@Serializable object SystemManagementRoute
@Serializable object SystemTimeRoute
@Serializable object SystemLogsRoute
@Serializable object TlsRoute
@Serializable object AiSettingsRoute
@Serializable object TelegramRoute
@Serializable object ChatRoute
@Serializable object PushNotificationsRoute
@Serializable object UserSettingsRoute
@Serializable object ProfilesRoute
