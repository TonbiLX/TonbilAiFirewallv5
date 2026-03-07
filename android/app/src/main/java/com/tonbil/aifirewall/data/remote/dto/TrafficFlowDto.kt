package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DeviceTrafficSummaryDto(
    @SerialName("device_id") val deviceId: Int = 0,
    @SerialName("device_hostname") val deviceHostname: String? = null,
    @SerialName("active_flows") val activeFlows: Int = 0,
    @SerialName("total_flows_period") val totalFlowsPeriod: Int = 0,
    @SerialName("total_bytes_sent") val totalBytesSent: Long = 0,
    @SerialName("total_bytes_received") val totalBytesReceived: Long = 0,
    @SerialName("top_domains") val topDomains: List<TopDomainFlowDto> = emptyList(),
    @SerialName("top_ports") val topPorts: List<TopPortFlowDto> = emptyList(),
)

@Serializable
data class TopDomainFlowDto(
    val domain: String = "",
    @SerialName("bytes_total") val bytesTotal: Long = 0,
    @SerialName("flow_count") val flowCount: Int = 0,
)

@Serializable
data class TopPortFlowDto(
    val port: Int = 0,
    val protocol: String = "",
    @SerialName("bytes_total") val bytesTotal: Long = 0,
    @SerialName("flow_count") val flowCount: Int = 0,
)
