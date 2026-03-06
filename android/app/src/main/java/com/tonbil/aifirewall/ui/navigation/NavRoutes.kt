package com.tonbil.aifirewall.ui.navigation

import kotlinx.serialization.Serializable

@Serializable object DashboardRoute
@Serializable object DevicesRoute
@Serializable object SecurityRoute
@Serializable object SettingsRoute

// Sub-screens (prepared for future phases)
@Serializable data class DeviceDetailRoute(val deviceId: String)
