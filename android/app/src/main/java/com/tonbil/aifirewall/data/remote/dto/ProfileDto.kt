package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ProfileResponseDto(
    val id: Int = 0,
    val name: String = "",
    @SerialName("profile_type") val profileType: String? = null,
    @SerialName("allowed_hours") val allowedHours: Map<String, String>? = null,
    @SerialName("content_filters") val contentFilters: List<String> = emptyList(),
    @SerialName("bandwidth_limit_mbps") val bandwidthLimitMbps: Float? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)
