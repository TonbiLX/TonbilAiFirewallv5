package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DashboardSummaryDto(
    val devices: DevicesSummaryDto = DevicesSummaryDto(),
    val dns: DnsSummaryDto = DnsSummaryDto(),
    val vpn: VpnSummaryDto = VpnSummaryDto(),
    @SerialName("top_clients") val topClients: List<TopClientDto> = emptyList(),
    @SerialName("top_queried_domains") val topQueriedDomains: List<TopDomainDto> = emptyList(),
    @SerialName("top_blocked_domains") val topBlockedDomains: List<TopDomainDto> = emptyList(),
)

@Serializable
data class DevicesSummaryDto(
    val total: Int = 0,
    val online: Int = 0,
    val blocked: Int = 0,
)

@Serializable
data class DnsSummaryDto(
    @SerialName("total_queries_24h") val totalQueries24h: Int = 0,
    @SerialName("blocked_queries_24h") val blockedQueries24h: Int = 0,
    @SerialName("block_percentage") val blockPercentage: Float = 0f,
    @SerialName("active_blocklists") val activeBlocklists: Int = 0,
    @SerialName("total_blocked_domains") val totalBlockedDomains: Int = 0,
)

@Serializable
data class VpnSummaryDto(
    val enabled: Boolean = false,
    @SerialName("total_peers") val totalPeers: Int = 0,
    @SerialName("connected_peers") val connectedPeers: Int = 0,
    @SerialName("total_rx") val totalRx: Long = 0,
    @SerialName("total_tx") val totalTx: Long = 0,
)

@Serializable
data class TopClientDto(
    @SerialName("client_ip") val clientIp: String = "",
    @SerialName("query_count") val queryCount: Int = 0,
)

@Serializable
data class TopDomainDto(
    val domain: String = "",
    val count: Int = 0,
)
