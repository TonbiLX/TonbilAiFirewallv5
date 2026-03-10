package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// GET /ip-management/stats
@Serializable
data class IpMgmtStatsDto(
    @SerialName("total_trusted") val totalTrusted: Int = 0,
    @SerialName("total_blocked") val totalBlocked: Int = 0,
    @SerialName("auto_blocked") val autoBlocked: Int = 0,
    @SerialName("manual_blocked") val manualBlocked: Int = 0,
)

// GET /ip-management/trusted → List<TrustedIpDto>
@Serializable
data class TrustedIpDto(
    val id: Int = 0,
    @SerialName("ip_address") val ipAddress: String = "",
    val description: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

// POST /ip-management/trusted — request body
@Serializable
data class TrustedIpCreateDto(
    @SerialName("ip_address") val ipAddress: String,
    val description: String? = null,
)

// GET /ip-management/blocked → List<BlockedIpDto>
@Serializable
data class BlockedIpDto(
    val id: Int? = null,
    @SerialName("ip_address") val ipAddress: String = "",
    val reason: String? = null,
    val source: String = "",
    val duration: String? = null,
    @SerialName("blocked_at") val blockedAt: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
    @SerialName("country_code") val countryCode: String? = null,
    @SerialName("country_name") val countryName: String? = null,
    @SerialName("abuse_score") val abuseScore: Int? = null,
)

// POST /ip-management/blocked — request body
@Serializable
data class BlockedIpCreateDto(
    @SerialName("ip_address") val ipAddress: String,
    val reason: String? = null,
    val duration: String? = null,
)

// POST /ip-management/unblock — request body
@Serializable
data class IpUnblockDto(
    @SerialName("ip_address") val ipAddress: String,
)

// PUT /ip-management/blocked/bulk-unblock — request body
@Serializable
data class IpBulkUnblockDto(
    @SerialName("ip_addresses") val ipAddresses: List<String>,
)

// PUT /ip-management/blocked/duration — request body
@Serializable
data class IpDurationDto(
    @SerialName("ip_address") val ipAddress: String,
    val duration: String,
)

// PUT /ip-management/blocked/bulk-duration — request body
@Serializable
data class IpBulkDurationDto(
    @SerialName("ip_addresses") val ipAddresses: List<String>,
    val duration: String,
)
