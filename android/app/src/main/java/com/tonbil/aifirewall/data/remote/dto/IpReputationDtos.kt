package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ============================================================
// IP Reputation DTOs
// Backend prefix: /ip-reputation
// ============================================================

// GET /ip-reputation/config
// PUT /ip-reputation/config
@Serializable
data class IpRepConfigDto(
    val enabled: Boolean = false,
    @SerialName("api_key") val apiKey: String = "",
    @SerialName("min_score") val minScore: Int = 80,
    @SerialName("check_interval_minutes") val checkIntervalMinutes: Int = 5,
    @SerialName("max_ips_per_cycle") val maxIpsPerCycle: Int = 10,
    @SerialName("auto_block") val autoBlock: Boolean = true,
    @SerialName("block_duration") val blockDuration: String? = null,
)

// GET /ip-reputation/summary
@Serializable
data class IpRepSummaryDto(
    @SerialName("total_checked") val totalChecked: Int = 0,
    @SerialName("total_clean") val totalClean: Int = 0,
    @SerialName("total_suspicious") val totalSuspicious: Int = 0,
    @SerialName("total_critical") val totalCritical: Int = 0,
    @SerialName("total_blocked") val totalBlocked: Int = 0,
    @SerialName("last_check") val lastCheck: String? = null,
    @SerialName("api_quota_remaining") val apiQuotaRemaining: Int? = null,
)

// GET /ip-reputation/ips  (items in list, supports ?min_score= filter)
@Serializable
data class IpRepCheckDto(
    val id: Int? = null,
    @SerialName("ip_address") val ipAddress: String = "",
    val score: Int = 0,
    @SerialName("country_code") val countryCode: String? = null,
    @SerialName("country_name") val countryName: String? = null,
    val isp: String? = null,
    val domain: String? = null,
    @SerialName("is_tor") val isTor: Boolean = false,
    @SerialName("total_reports") val totalReports: Int = 0,
    @SerialName("last_reported") val lastReported: String? = null,
    @SerialName("checked_at") val checkedAt: String? = null,
    val blocked: Boolean = false,
)

// GET /ip-reputation/blacklist  (items in list)
@Serializable
data class IpRepBlacklistDto(
    @SerialName("ip_address") val ipAddress: String = "",
    @SerialName("country_code") val countryCode: String? = null,
    val score: Int = 0,
    @SerialName("added_at") val addedAt: String? = null,
)

// GET /ip-reputation/blacklist/config
// PUT /ip-reputation/blacklist/config
@Serializable
data class IpRepBlacklistConfigDto(
    val enabled: Boolean = false,
    @SerialName("min_score") val minScore: Int = 100,
    @SerialName("fetch_interval_hours") val fetchIntervalHours: Int = 24,
    @SerialName("auto_block") val autoBlock: Boolean = true,
    @SerialName("last_fetch") val lastFetch: String? = null,
    @SerialName("total_entries") val totalEntries: Int = 0,
)

// POST /ip-reputation/test
@Serializable
data class IpRepTestDto(
    val success: Boolean = false,
    val message: String = "",
    @SerialName("quota_remaining") val quotaRemaining: Int? = null,
)

// ============================================================
// Request DTOs
// ============================================================

// PUT /ip-reputation/config  — request body
@Serializable
data class IpRepConfigUpdateDto(
    val enabled: Boolean? = null,
    @SerialName("api_key") val apiKey: String? = null,
    @SerialName("min_score") val minScore: Int? = null,
    @SerialName("check_interval_minutes") val checkIntervalMinutes: Int? = null,
    @SerialName("max_ips_per_cycle") val maxIpsPerCycle: Int? = null,
    @SerialName("auto_block") val autoBlock: Boolean? = null,
    @SerialName("block_duration") val blockDuration: String? = null,
)

// PUT /ip-reputation/blacklist/config  — request body
@Serializable
data class IpRepBlacklistConfigUpdateDto(
    val enabled: Boolean? = null,
    @SerialName("min_score") val minScore: Int? = null,
    @SerialName("fetch_interval_hours") val fetchIntervalHours: Int? = null,
    @SerialName("auto_block") val autoBlock: Boolean? = null,
)
