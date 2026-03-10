package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// GET /system-time/status
@Serializable
data class TimeStatusDto(
    @SerialName("current_time") val currentTime: String = "",
    @SerialName("timezone") val timezone: String = "",
    @SerialName("ntp_enabled") val ntpEnabled: Boolean = false,
    @SerialName("ntp_synchronized") val ntpSynchronized: Boolean = false,
    @SerialName("ntp_server") val ntpServer: String = "",
)

// GET /system-time/timezones — grouped by region
@Serializable
data class TimezoneGroupDto(
    val region: String = "",
    val timezones: List<String> = emptyList(),
)

// GET /system-time/ntp-servers
@Serializable
data class NtpServerDto(
    val name: String = "",
    val address: String = "",
    val description: String = "",
)

// POST /system-time/set-timezone
@Serializable
data class SetTimezoneDto(
    val timezone: String,
)

// POST /system-time/set-ntp-server
@Serializable
data class SetNtpServerDto(
    val server: String,
)
