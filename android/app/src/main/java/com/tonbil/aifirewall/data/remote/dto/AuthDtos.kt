package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class LoginRequest(
    val username: String,
    val password: String,
    @SerialName("remember_me") val rememberMe: Boolean = true,
    val platform: String = "android",
)

@Serializable
data class LoginResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    val username: String,
    @SerialName("display_name") val displayName: String? = null
)

@Serializable
data class UserInfo(
    val id: Int,
    val username: String,
    @SerialName("display_name") val displayName: String? = null,
    @SerialName("is_admin") val isAdmin: Boolean = false
)
