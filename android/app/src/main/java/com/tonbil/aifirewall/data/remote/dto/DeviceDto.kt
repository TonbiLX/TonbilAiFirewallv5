package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class DeviceResponseDto(
    val id: Int = 0,
    @SerialName("mac_address") val macAddress: String = "",
    @SerialName("ip_address") val ipAddress: String? = null,
    val hostname: String? = null,
    val manufacturer: String? = null,
    @SerialName("profile_id") val profileId: Int? = null,
    @SerialName("is_blocked") val isBlocked: Boolean = false,
    @SerialName("is_online") val isOnline: Boolean = false,
    @SerialName("first_seen") val firstSeen: String? = null,
    @SerialName("last_seen") val lastSeen: String? = null,
    @SerialName("total_online_seconds") val totalOnlineSeconds: Int = 0,
    @SerialName("last_online_start") val lastOnlineStart: String? = null,
    @SerialName("bandwidth_limit_mbps") val bandwidthLimitMbps: Float? = null,
)

@Serializable
data class DeviceUpdateDto(
    val hostname: String? = null,
    @SerialName("ip_address") val ipAddress: String? = null,
    val manufacturer: String? = null,
    @SerialName("profile_id") val profileId: Int? = null,
)

@Serializable
data class BlockResponseDto(
    val status: String = "",
    val mac: String = "",
)
