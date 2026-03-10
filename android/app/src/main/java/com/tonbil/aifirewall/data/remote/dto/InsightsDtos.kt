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
    @SerialName("total_threats_24h") val totalThreats24h: Int = 0,
    @SerialName("critical_count") val criticalCount: Int = 0,
    @SerialName("warning_count") val warningCount: Int = 0,
    @SerialName("info_count") val infoCount: Int = 0,
    @SerialName("auto_blocked") val autoBlocked: Int = 0,
    @SerialName("top_categories") val topCategories: List<ThreatCategoryCountDto> = emptyList(),
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
