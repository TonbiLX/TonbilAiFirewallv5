package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// POST /push/register — FCM token kaydi
@Serializable
data class PushTokenDto(
    val token: String,
    val platform: String = "android",
    @SerialName("device_name") val deviceName: String = "",
)

// GET /push/channels — Bildirim kanal tercihleri
@Serializable
data class PushChannelDto(
    val id: String = "",
    val name: String = "",
    val description: String = "",
    val enabled: Boolean = true,
)

// POST /push/register response
@Serializable
data class PushRegistrationResponseDto(
    val success: Boolean = false,
    val message: String = "",
)
