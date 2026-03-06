package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class RealtimeUpdateDto(
    val type: String = "",
    @SerialName("device_count") val deviceCount: Int = 0,
    val devices: List<WsDeviceDto> = emptyList(),
    val dns: WsDnsDto = WsDnsDto(),
    val bandwidth: WsBandwidthDto = WsBandwidthDto(),
    val vpn: WsVpnDto = WsVpnDto(),
    @SerialName("vpn_client") val vpnClient: WsVpnClientDto? = null,
)

@Serializable
data class WsDeviceDto(
    val id: Int,
    val mac: String,
    val ip: String,
    val hostname: String? = null,
    val manufacturer: String? = null,
    @SerialName("is_online") val isOnline: Boolean,
)

@Serializable
data class WsDnsDto(
    @SerialName("total_queries_24h") val totalQueries24h: Int = 0,
    @SerialName("blocked_queries_24h") val blockedQueries24h: Int = 0,
    @SerialName("block_percentage") val blockPercentage: Float = 0f,
    @SerialName("queries_per_min") val queriesPerMin: Int = 0,
)

@Serializable
data class WsBandwidthDto(
    @SerialName("total_upload_bps") val totalUploadBps: Long = 0,
    @SerialName("total_download_bps") val totalDownloadBps: Long = 0,
    val devices: Map<String, WsDeviceBandwidthDto> = emptyMap(),
)

@Serializable
data class WsDeviceBandwidthDto(
    @SerialName("upload_bps") val uploadBps: Long,
    @SerialName("download_bps") val downloadBps: Long,
    @SerialName("upload_total") val uploadTotal: Long,
    @SerialName("download_total") val downloadTotal: Long,
)

@Serializable
data class WsVpnDto(
    val enabled: Boolean = false,
    @SerialName("connected_peers") val connectedPeers: Int = 0,
    @SerialName("total_peers") val totalPeers: Int = 0,
)

@Serializable
data class WsVpnClientDto(
    val connected: Boolean,
    @SerialName("transfer_rx") val transferRx: Long,
    @SerialName("transfer_tx") val transferTx: Long,
)
