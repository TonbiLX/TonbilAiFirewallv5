package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// GET /services → List<ServiceDto>
@Serializable
data class ServiceDto(
    val id: Int = 0,
    @SerialName("service_id") val serviceId: String = "",
    val name: String = "",
    @SerialName("group_name") val groupName: String = "",
    @SerialName("icon_svg") val iconSvg: String? = null,
    val rules: List<String> = emptyList(),
    @SerialName("domain_count") val domainCount: Int = 0,
    val enabled: Boolean = true,
)

// GET /services/groups → List<ServiceGroupDto>
// Backend returns: { "group": "social_network", "count": 42 }
@Serializable
data class ServiceGroupDto(
    val group: String = "",
    val count: Int = 0,
) {
    // UI display name: "social_network" → "Social Network"
    val name: String get() = group
    val displayName: String get() = group.replace("_", " ")
        .replaceFirstChar { it.uppercaseChar() }
}

// GET /services/devices/{device_id} → List<DeviceServiceDto>
// Backend returns: { "service_id": "youtube", "name": "YouTube", "group_name": "video", ... }
@Serializable
data class DeviceServiceDto(
    @SerialName("service_id") val serviceId: String = "",
    val name: String = "",
    @SerialName("group_name") val groupName: String = "",
    @SerialName("icon_svg") val iconSvg: String? = null,
    val blocked: Boolean = false,
) {
    val displayName: String get() = name
    val group: String get() = groupName
}

// PUT /services/devices/{device_id}/toggle — request body
// Backend expects: { "service_id": "youtube", "blocked": true }
@Serializable
data class ServiceToggleDto(
    @SerialName("service_id") val serviceId: String,
    val blocked: Boolean,
)

// PUT /services/devices/{device_id}/bulk — request body
@Serializable
data class ServiceBulkDto(
    @SerialName("blocked_service_ids") val blockedServiceIds: List<String>,
)
