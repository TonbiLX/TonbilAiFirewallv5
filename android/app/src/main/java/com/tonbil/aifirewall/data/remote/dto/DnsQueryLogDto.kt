package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DnsQueryLogDto(
    val domain: String,
    @SerialName("query_type") val queryType: String,
    val blocked: Boolean,
    val timestamp: String,
    @SerialName("client_ip") val clientIp: String,
    @SerialName("response_ip") val responseIp: String? = null,
)
