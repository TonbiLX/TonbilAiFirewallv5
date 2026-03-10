package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// GET /tls/config
@Serializable
data class TlsConfigDto(
    val enabled: Boolean = false,
    @SerialName("cert_valid") val certValid: Boolean = false,
    @SerialName("cert_expiry") val certExpiry: String? = null,
    @SerialName("cert_issuer") val certIssuer: String? = null,
    @SerialName("cert_subject") val certSubject: String? = null,
    @SerialName("dot_port") val dotPort: Int = 853,
    @SerialName("upstream_dot") val upstreamDot: Boolean = false,
    @SerialName("upstream_server") val upstreamServer: String? = null,
)

// PATCH /tls/config
@Serializable
data class TlsConfigUpdateDto(
    @SerialName("upstream_dot") val upstreamDot: Boolean? = null,
    @SerialName("upstream_server") val upstreamServer: String? = null,
)

// POST /tls/validate
@Serializable
data class TlsValidateDto(
    val cert: String,
    val key: String,
)

@Serializable
data class TlsValidateResponseDto(
    val valid: Boolean = false,
    val message: String = "",
    val issuer: String? = null,
    val expiry: String? = null,
)

// POST /tls/upload-cert
@Serializable
data class TlsUploadResponseDto(
    val success: Boolean = false,
    val message: String = "",
)

// POST /tls/letsencrypt
@Serializable
data class TlsLetsEncryptDto(
    val domain: String,
    val email: String,
)
