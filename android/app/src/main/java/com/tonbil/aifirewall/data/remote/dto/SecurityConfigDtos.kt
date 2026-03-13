package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// GET /security/config, PUT /security/config — Tam guvenlik konfigurasyonu
@Serializable
data class SecurityConfigDto(
    @SerialName("threat_analysis") val threatAnalysis: ThreatAnalysisConfigDto = ThreatAnalysisConfigDto(),
    @SerialName("dns_security") val dnsSecurity: DnsSecurityConfigDto = DnsSecurityConfigDto(),
    @SerialName("alert_settings") val alertSettings: AlertSettingsConfigDto = AlertSettingsConfigDto(),
    // DNS Guvenlik Katmanlari (flat alanlar — backend SecurityConfigResponse)
    @SerialName("dnssec_enabled") val dnssecEnabled: Boolean = true,
    @SerialName("dnssec_mode") val dnssecMode: String = "log_only",
    @SerialName("dns_tunneling_enabled") val dnsTunnelingEnabled: Boolean = true,
    @SerialName("dns_tunneling_max_subdomain_len") val dnsTunnelingMaxSubdomainLen: Int = 50,
    @SerialName("dns_tunneling_max_labels_per_min") val dnsTunnelingMaxLabelsPerMin: Int = 100,
    @SerialName("dns_tunneling_txt_ratio_threshold") val dnsTunnelingTxtRatioThreshold: Int = 30,
    @SerialName("doh_enabled") val dohEnabled: Boolean = true,
)

// Tehdit analizi ayarlari
@Serializable
data class ThreatAnalysisConfigDto(
    @SerialName("dga_detection_enabled") val dgaDetectionEnabled: Boolean = true,
    @SerialName("dga_entropy_threshold") val dgaEntropyThreshold: Float = 3.5f,
    @SerialName("subnet_flood_threshold") val subnetFloodThreshold: Int = 10,
    @SerialName("scan_pattern_threshold") val scanPatternThreshold: Int = 5,
    @SerialName("auto_block_enabled") val autoBlockEnabled: Boolean = true,
    @SerialName("auto_block_duration") val autoBlockDuration: String = "24h",
)

// DNS guvenlik ayarlari
@Serializable
data class DnsSecurityConfigDto(
    @SerialName("rate_limit_enabled") val rateLimitEnabled: Boolean = true,
    @SerialName("rate_limit_per_second") val rateLimitPerSecond: Int = 50,
    @SerialName("blocked_query_types") val blockedQueryTypes: List<String> = emptyList(),
    @SerialName("sinkhole_enabled") val sinkholeEnabled: Boolean = true,
    @SerialName("sinkhole_ip") val sinkholeIp: String = "0.0.0.0",
)

// Uyari ayarlari
@Serializable
data class AlertSettingsConfigDto(
    @SerialName("ddos_alert_threshold") val ddosAlertThreshold: Int = 100,
    @SerialName("cooldown_minutes") val cooldownMinutes: Int = 5,
    @SerialName("telegram_enabled") val telegramEnabled: Boolean = false,
    @SerialName("email_enabled") val emailEnabled: Boolean = false,
)

// PUT /security/config request — kismi guncelleme icin null-able alanlar
@Serializable
data class SecurityConfigUpdateDto(
    @SerialName("threat_analysis") val threatAnalysis: ThreatAnalysisConfigDto? = null,
    @SerialName("dns_security") val dnsSecurity: DnsSecurityConfigDto? = null,
    @SerialName("alert_settings") val alertSettings: AlertSettingsConfigDto? = null,
    // DNS Guvenlik Katmanlari (flat, null ise backend mevcut degeri korur)
    @SerialName("dnssec_enabled") val dnssecEnabled: Boolean? = null,
    @SerialName("dnssec_mode") val dnssecMode: String? = null,
    @SerialName("dns_tunneling_enabled") val dnsTunnelingEnabled: Boolean? = null,
    @SerialName("dns_tunneling_max_subdomain_len") val dnsTunnelingMaxSubdomainLen: Int? = null,
    @SerialName("dns_tunneling_max_labels_per_min") val dnsTunnelingMaxLabelsPerMin: Int? = null,
    @SerialName("dns_tunneling_txt_ratio_threshold") val dnsTunnelingTxtRatioThreshold: Int? = null,
    @SerialName("doh_enabled") val dohEnabled: Boolean? = null,
    @SerialName("dga_detection_enabled") val dgaDetectionEnabled: Boolean? = null,
)

// GET /security/defaults response
@Serializable
data class SecurityDefaultsDto(
    val config: SecurityConfigDto = SecurityConfigDto(),
)
