package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ============================================================
// IP Reputation DTOs
// Backend prefix: /ip-reputation
// All fields match backend response format exactly.
// ============================================================

// GET /ip-reputation/config
@Serializable
data class IpRepConfigDto(
    val enabled: Boolean = false,
    @SerialName("abuseipdb_key") val abuseipdbKey: String = "",
    @SerialName("abuseipdb_key_set") val abuseipdbKeySet: Boolean = false,
    @SerialName("blocked_countries") val blockedCountries: List<String> = emptyList(),
    @SerialName("check_interval") val checkInterval: Int = 300,
    @SerialName("max_checks_per_cycle") val maxChecksPerCycle: Int = 10,
    @SerialName("daily_limit") val dailyLimit: Int = 900,
)

// PUT /ip-reputation/config — request body
@Serializable
data class IpRepConfigUpdateDto(
    val enabled: Boolean? = null,
    @SerialName("abuseipdb_key") val abuseipdbKey: String? = null,
    @SerialName("blocked_countries") val blockedCountries: List<String>? = null,
)

// GET /ip-reputation/summary
@Serializable
data class IpRepSummaryDto(
    @SerialName("total_checked") val totalChecked: Int = 0,
    @SerialName("flagged_critical") val flaggedCritical: Int = 0,
    @SerialName("flagged_warning") val flaggedWarning: Int = 0,
    @SerialName("daily_checks_used") val dailyChecksUsed: Int = 0,
    @SerialName("daily_limit") val dailyLimit: Int = 900,
    @SerialName("abuseipdb_remaining") val abuseipdbRemaining: Int? = null,
    @SerialName("abuseipdb_limit") val abuseipdbLimit: Int? = null,
)

// GET /ip-reputation/ips — wrapper response
@Serializable
data class IpRepIpsResponseDto(
    val ips: List<IpRepCheckDto> = emptyList(),
    val total: Int = 0,
)

// Each IP entry inside /ips response
@Serializable
data class IpRepCheckDto(
    val ip: String = "",
    @SerialName("abuse_score") val abuseScore: Int = 0,
    @SerialName("total_reports") val totalReports: Int = 0,
    val country: String = "",
    val city: String = "",
    val isp: String = "",
    val org: String = "",
    @SerialName("checked_at") val checkedAt: String = "",
)

// GET /ip-reputation/blacklist — wrapper response
@Serializable
data class IpRepBlacklistResponseDto(
    val ips: List<IpRepBlacklistDto> = emptyList(),
    val total: Int = 0,
    @SerialName("last_fetch") val lastFetch: String = "",
    @SerialName("total_count") val totalCount: Int = 0,
)

// Each blacklist entry
@Serializable
data class IpRepBlacklistDto(
    val ip: String = "",
    @SerialName("abuse_score") val abuseScore: Int = 0,
    val country: String = "",
    @SerialName("last_reported_at") val lastReportedAt: String = "",
)

// GET /ip-reputation/blacklist/config
@Serializable
data class IpRepBlacklistConfigDto(
    @SerialName("auto_block") val autoBlock: Boolean = true,
    @SerialName("min_score") val minScore: Int = 100,
    val limit: Int = 10000,
    @SerialName("daily_fetches") val dailyFetches: Int = 0,
    @SerialName("daily_limit") val dailyLimit: Int = 5,
    @SerialName("last_fetch") val lastFetch: String = "",
    @SerialName("total_count") val totalCount: Int = 0,
)

// PUT /ip-reputation/blacklist/config — request body
@Serializable
data class IpRepBlacklistConfigUpdateDto(
    @SerialName("auto_block") val autoBlock: Boolean? = null,
    @SerialName("min_score") val minScore: Int? = null,
    val limit: Int? = null,
)

// POST /ip-reputation/test
@Serializable
data class IpRepTestResponseDto(
    val status: String = "",
    val message: String = "",
    val data: IpRepTestDataDto? = null,
)

@Serializable
data class IpRepTestDataDto(
    @SerialName("tested_ip") val testedIp: String = "",
    @SerialName("abuse_score") val abuseScore: Int = 0,
    @SerialName("total_reports") val totalReports: Int = 0,
    val country: String = "",
    @SerialName("usage_type") val usageType: String = "",
    val isp: String = "",
)

// GET /ip-reputation/api-usage
@Serializable
data class IpRepApiUsageResponseDto(
    val status: String = "",
    val message: String = "",
    val data: IpRepApiUsageDataDto? = null,
)

@Serializable
data class IpRepApiUsageDataDto(
    val limit: Int? = null,
    val used: Int? = null,
    val remaining: Int? = null,
    @SerialName("usage_percent") val usagePercent: Double = 0.0,
    @SerialName("retry_after") val retryAfter: String? = null,
)

// DELETE /ip-reputation/cache
@Serializable
data class IpRepCacheClearResponseDto(
    val status: String = "",
    val deleted: Int = 0,
    @SerialName("sql_deleted") val sqlDeleted: Int = 0,
    val message: String = "",
)

// GET /ip-reputation/blacklist/api-usage
@Serializable
data class IpRepBlacklistApiUsageDto(
    val status: String = "",
    val data: IpRepBlacklistApiUsageDataDto? = null,
)

@Serializable
data class IpRepBlacklistApiUsageDataDto(
    val limit: Int = 0,
    val used: Int = 0,
    val remaining: Int = 0,
    @SerialName("usage_percent") val usagePercent: Double = 0.0,
    @SerialName("last_fetch") val lastFetch: String = "",
    @SerialName("total_ips") val totalIps: Int = 0,
)

// POST /ip-reputation/blacklist/fetch
@Serializable
data class IpRepBlacklistFetchResponseDto(
    val status: String = "",
    val message: String = "",
    @SerialName("new_ips") val newIps: Int = 0,
    val total: Int = 0,
)
