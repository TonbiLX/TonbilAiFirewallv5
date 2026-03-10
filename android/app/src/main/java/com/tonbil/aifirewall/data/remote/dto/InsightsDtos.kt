package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * AI Insights ek endpoint DTOs
 * Not: Temel AiInsightDto SecurityDtos.kt içinde tanımlıdır.
 *
 * Endpoints:
 *   POST /{id}/dismiss   → (no body, no response DTO)
 *   GET  /threat-stats   → InsightThreatStatsDto
 *   GET  /blocked-ips    → List<InsightBlockedIpDto>
 *   POST /block-ip       → InsightBlockIpDto (request)
 *   POST /unblock-ip     → InsightUnblockIpDto (request)
 */

@Serializable
data class InsightThreatStatsDto(
    @SerialName("blocked_ip_count") val blockedIpCount: Int = 0,
    @SerialName("total_external_blocked") val totalExternalBlocked: Int = 0,
    @SerialName("total_auto_blocks") val totalAutoBlocks: Int = 0,
    @SerialName("total_suspicious") val totalSuspicious: Int = 0,
    @SerialName("last_threat_time") val lastThreatTime: String? = null,
)

@Serializable
data class ThreatCategoryCountDto(
    val category: String = "",
    val count: Int = 0,
)

@Serializable
data class InsightBlockedIpDto(
    @SerialName("ip_address") val ipAddress: String = "",
    val reason: String? = null,
    @SerialName("blocked_at") val blockedAt: String? = null,
    @SerialName("country_code") val countryCode: String? = null,
)

@Serializable
data class InsightBlockIpDto(
    @SerialName("ip_address") val ipAddress: String,
    val reason: String? = null,
)

@Serializable
data class InsightUnblockIpDto(
    @SerialName("ip_address") val ipAddress: String,
)
