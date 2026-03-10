package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Content Category (response)
@Serializable
data class ContentCategoryDto(
    val id: Int = 0,
    val key: String = "",
    val name: String = "",
    val icon: String = "",
    val color: String = "",
    val enabled: Boolean = true,
    @SerialName("custom_domains") val customDomains: String? = null,
    @SerialName("domain_count") val domainCount: Int = 0,
    @SerialName("blocklist_ids") val blocklistIds: List<Int> = emptyList(),
    @SerialName("created_at") val createdAt: String? = null,
)

// ============ REQUEST DTOs ============

// POST /content-categories — create new category
@Serializable
data class ContentCategoryCreateDto(
    val key: String,
    val name: String,
    val icon: String = "shield",
    val color: String = "#00F0FF",
    val enabled: Boolean = true,
    @SerialName("custom_domains") val customDomains: String? = null,
    @SerialName("blocklist_ids") val blocklistIds: List<Int> = emptyList(),
)

// PATCH /content-categories/{id} — partial update (blocklist binding + domain rebuild)
@Serializable
data class ContentCategoryUpdateDto(
    val name: String? = null,
    val icon: String? = null,
    val color: String? = null,
    val enabled: Boolean? = null,
    @SerialName("custom_domains") val customDomains: String? = null,
    @SerialName("blocklist_ids") val blocklistIds: List<Int>? = null,
)
