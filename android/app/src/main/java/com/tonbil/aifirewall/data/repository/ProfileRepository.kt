package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.ProfileResponseDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get

class ProfileRepository(private val client: HttpClient) {

    suspend fun getProfiles(): Result<List<ProfileResponseDto>> {
        return try {
            val response: List<ProfileResponseDto> = client.get(ApiRoutes.PROFILES).body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
