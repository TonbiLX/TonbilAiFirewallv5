package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DashboardSummaryDto(
    val devices: DevicesSummaryDto,
    val dns: DnsSummaryDto,
    val vpn: VpnSummaryDto,
    @SerialName("top_clients") val topClients: List<TopClientDto>,
    @SerialName("top_queried_domains") val topQueriedDomains: List<TopDomainDto>,
    @SerialName("top_blocked_domains") val topBlockedDomains: List<TopDomainDto>,
)

@Serializable
data class DevicesSummaryDto(
    val total: Int,
    val online: Int,
    val blocked: Int,
)

@Serializable
data class DnsSummaryDto(
    @SerialName("total_queries_24h") val totalQueries24h: Int,
    @SerialName("blocked_queries_24h") val blockedQueries24h: Int,
    @SerialName("block_percentage") val blockPercentage: Float,
    @SerialName("active_blocklists") val activeBlocklists: Int,
    @SerialName("total_blocked_domains") val totalBlockedDomains: Int,
)

@Serializable
data class VpnSummaryDto(
    val enabled: Boolean,
    @SerialName("total_peers") val totalPeers: Int,
    @SerialName("connected_peers") val connectedPeers: Int,
    @SerialName("total_rx") val totalRx: Long,
    @SerialName("total_tx") val totalTx: Long,
)

@Serializable
data class TopClientDto(
    @SerialName("client_ip") val clientIp: String,
    @SerialName("query_count") val queryCount: Int,
)

@Serializable
data class TopDomainDto(
    val domain: String,
    val count: Int,
)
