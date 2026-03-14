package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DnsQueryLogDto(
    val id: Int = 0,
    val domain: String = "",
    @SerialName("query_type") val queryType: String = "",
    val blocked: Boolean = false,
    val timestamp: String = "",
    @SerialName("client_ip") val clientIp: String = "",
    @SerialName("response_ip") val responseIp: String? = null,
    @SerialName("source_type") val sourceType: String = "INTERNAL",
    @SerialName("device_id") val deviceId: Int? = null,
    @SerialName("block_reason") val blockReason: String? = null,
)
