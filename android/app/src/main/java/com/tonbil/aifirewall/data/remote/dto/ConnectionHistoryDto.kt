package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ConnectionHistoryDto(
    @SerialName("device_id") val deviceId: Int,
    @SerialName("connected_at") val connectedAt: String? = null,
    @SerialName("disconnected_at") val disconnectedAt: String? = null,
    val timestamp: String? = null,
    @SerialName("duration_seconds") val durationSeconds: Int? = null,
)
