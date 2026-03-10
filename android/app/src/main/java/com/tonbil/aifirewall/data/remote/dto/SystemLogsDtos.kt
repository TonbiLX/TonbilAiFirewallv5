package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Sistem logları endpoint DTOs
 * Backend prefix: /system-logs
 *
 * Endpoints:
 *   GET /          → SystemLogPageDto  (filtreli + sayfalı)
 *   GET /summary   → SystemLogSummaryDto  (30 günlük özet)
 */

@Serializable
data class SystemLogDto(
    val id: Int = 0,
    val timestamp: String = "",
    @SerialName("log_type") val logType: String = "",
    val severity: String = "",
    val category: String = "",
    @SerialName("source_ip") val sourceIp: String? = null,
    val domain: String? = null,
    val action: String? = null,
    val message: String = "",
    @SerialName("device_id") val deviceId: Int? = null,
    val hostname: String? = null,
)

@Serializable
data class SystemLogSummaryDto(
    @SerialName("total_logs") val totalLogs: Int = 0,
    @SerialName("total_dns") val totalDns: Int = 0,
    @SerialName("total_traffic") val totalTraffic: Int = 0,
    @SerialName("total_insights") val totalInsights: Int = 0,
    @SerialName("total_blocked") val totalBlocked: Int = 0,
    @SerialName("by_severity") val bySeverity: Map<String, Int> = emptyMap(),
    @SerialName("by_category") val byCategory: Map<String, Int> = emptyMap(),
)

@Serializable
data class SystemLogPageDto(
    val items: List<SystemLogDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    @SerialName("page_size") val pageSize: Int = 50,
    @SerialName("total_pages") val totalPages: Int = 0,
)
