package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DeviceTrafficSummaryDto(
    @SerialName("device_id") val deviceId: Int,
    @SerialName("total_flows") val totalFlows: Int,
    @SerialName("active_flows") val activeFlows: Int,
    @SerialName("total_bytes_in") val totalBytesIn: Long,
    @SerialName("total_bytes_out") val totalBytesOut: Long,
    @SerialName("top_services") val topServices: List<TopServiceDto> = emptyList(),
)

@Serializable
data class TopServiceDto(
    val service: String,
    val bytes: Long,
)
