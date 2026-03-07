package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DeviceTrafficSummaryDto(
    @SerialName("device_id") val deviceId: Int = 0,
    @SerialName("total_flows") val totalFlows: Int = 0,
    @SerialName("active_flows") val activeFlows: Int = 0,
    @SerialName("total_bytes_in") val totalBytesIn: Long = 0,
    @SerialName("total_bytes_out") val totalBytesOut: Long = 0,
    @SerialName("top_services") val topServices: List<TopServiceDto> = emptyList(),
)

@Serializable
data class TopServiceDto(
    val service: String = "",
    val bytes: Long = 0,
)
