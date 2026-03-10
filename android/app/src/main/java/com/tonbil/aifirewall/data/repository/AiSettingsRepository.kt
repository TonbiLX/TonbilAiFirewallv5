package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class AiSettingsRepository(private val client: HttpClient) {

    suspend fun getConfig(): Result<AiConfigDto> = runCatching {
        client.get(ApiRoutes.AI_CONFIG).body()
    }

    suspend fun updateConfig(dto: AiConfigUpdateDto): Result<AiConfigDto> = runCatching {
        client.put(ApiRoutes.AI_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun test(): Result<AiTestResponseDto> = runCatching {
        client.post(ApiRoutes.AI_TEST).body()
    }

    suspend fun getProviders(): Result<List<AiProviderDto>> = runCatching {
        client.get(ApiRoutes.AI_PROVIDERS).body()
    }

    suspend fun getStats(): Result<AiStatsDto> = runCatching {
        client.get(ApiRoutes.AI_STATS).body()
    }

    suspend fun resetCounter(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.AI_RESET_COUNTER).body()
    }
}
