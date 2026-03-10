package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// GET /services → List<ServiceDto>
@Serializable
data class ServiceDto(
    val id: Int = 0,
    val name: String = "",
    @SerialName("display_name") val displayName: String = "",
    val group: String = "",
    val icon: String = "",
    val domains: List<String> = emptyList(),
)

// GET /services/groups → List<ServiceGroupDto>
@Serializable
data class ServiceGroupDto(
    val name: String = "",
    @SerialName("display_name") val displayName: String = "",
    val icon: String = "",
    val count: Int = 0,
)

// GET /services/devices/{device_id} → List<DeviceServiceDto>
@Serializable
data class DeviceServiceDto(
    @SerialName("service_id") val serviceId: Int = 0,
    @SerialName("service_name") val serviceName: String = "",
    @SerialName("display_name") val displayName: String = "",
    val group: String = "",
    val icon: String = "",
    val blocked: Boolean = false,
)

// PUT /services/devices/{device_id}/toggle — request body
@Serializable
data class ServiceToggleDto(
    @SerialName("service_id") val serviceId: Int,
    val blocked: Boolean,
)

// PUT /services/devices/{device_id}/bulk — request body
@Serializable
data class ServiceBulkDto(
    val services: List<ServiceToggleDto>,
)
