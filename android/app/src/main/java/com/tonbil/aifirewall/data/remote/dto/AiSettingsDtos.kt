package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * AI ayarları endpoint DTOs
 * Backend prefix: /ai-settings
 *
 * Endpoints:
 *   GET    /config             → AiConfigDto
 *   PUT    /config             → AiConfigUpdateDto (request) / AiConfigDto (response)
 *   POST   /test               → AiTestResponseDto
 *   GET    /providers          → List<AiProviderDto>
 *   GET    /stats              → AiStatsDto
 *   POST   /reset-counter      → (no body)
 */

@Serializable
data class AiConfigDto(
    val provider: String = "openai",
    @SerialName("api_key") val apiKey: String = "",
    val model: String = "",
    @SerialName("chat_enabled") val chatEnabled: Boolean = true,
    val temperature: Float = 0.7f,
    @SerialName("max_tokens") val maxTokens: Int = 1000,
    @SerialName("daily_limit") val dailyLimit: Int = 100,
    @SerialName("log_analysis_enabled") val logAnalysisEnabled: Boolean = true,
    @SerialName("log_analysis_interval") val logAnalysisInterval: Int = 60,
)

@Serializable
data class AiConfigUpdateDto(
    val provider: String? = null,
    @SerialName("api_key") val apiKey: String? = null,
    val model: String? = null,
    @SerialName("chat_enabled") val chatEnabled: Boolean? = null,
    val temperature: Float? = null,
    @SerialName("max_tokens") val maxTokens: Int? = null,
    @SerialName("daily_limit") val dailyLimit: Int? = null,
    @SerialName("log_analysis_enabled") val logAnalysisEnabled: Boolean? = null,
    @SerialName("log_analysis_interval") val logAnalysisInterval: Int? = null,
)

@Serializable
data class AiProviderDto(
    val id: String = "",
    val name: String = "",
    val models: List<String> = emptyList(),
    @SerialName("requires_api_key") val requiresApiKey: Boolean = true,
    @SerialName("base_url_configurable") val baseUrlConfigurable: Boolean = false,
)

@Serializable
data class AiStatsDto(
    @SerialName("requests_today") val requestsToday: Int = 0,
    @SerialName("daily_limit") val dailyLimit: Int = 100,
    @SerialName("total_requests") val totalRequests: Int = 0,
    @SerialName("total_tokens_used") val totalTokensUsed: Long = 0,
    @SerialName("avg_response_time_ms") val avgResponseTimeMs: Float = 0f,
    @SerialName("last_request") val lastRequest: String? = null,
)

@Serializable
data class AiTestResponseDto(
    val success: Boolean = false,
    val message: String = "",
    @SerialName("response_time_ms") val responseTimeMs: Long = 0,
    val model: String = "",
)
