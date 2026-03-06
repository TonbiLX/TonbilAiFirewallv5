package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class RealtimeUpdateDto(
    val type: String,
    @SerialName("device_count") val deviceCount: Int,
    val devices: List<WsDeviceDto>,
    val dns: WsDnsDto,
    val bandwidth: WsBandwidthDto,
    val vpn: WsVpnDto,
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
    @SerialName("total_queries_24h") val totalQueries24h: Int,
    @SerialName("blocked_queries_24h") val blockedQueries24h: Int,
    @SerialName("block_percentage") val blockPercentage: Float,
    @SerialName("queries_per_min") val queriesPerMin: Int,
)

@Serializable
data class WsBandwidthDto(
    @SerialName("total_upload_bps") val totalUploadBps: Long,
    @SerialName("total_download_bps") val totalDownloadBps: Long,
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
    val enabled: Boolean,
    @SerialName("connected_peers") val connectedPeers: Int,
    @SerialName("total_peers") val totalPeers: Int,
)

@Serializable
data class WsVpnClientDto(
    val connected: Boolean,
    @SerialName("transfer_rx") val transferRx: Long,
    @SerialName("transfer_tx") val transferTx: Long,
)
