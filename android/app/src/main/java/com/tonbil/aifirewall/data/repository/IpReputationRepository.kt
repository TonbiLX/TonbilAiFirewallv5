package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class IpReputationRepository(private val client: HttpClient) {

    suspend fun getConfig(): Result<IpRepConfigDto> = runCatching {
        client.get(ApiRoutes.IP_REP_CONFIG).body()
    }

    suspend fun updateConfig(dto: IpRepConfigUpdateDto): Result<IpRepConfigDto> = runCatching {
        client.put(ApiRoutes.IP_REP_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun getSummary(): Result<IpRepSummaryDto> = runCatching {
        client.get(ApiRoutes.IP_REP_SUMMARY).body()
    }

    suspend fun getIps(minScore: Int? = null): Result<List<IpRepCheckDto>> = runCatching {
        client.get(ApiRoutes.IP_REP_IPS) {
            minScore?.let { parameter("min_score", it) }
        }.body()
    }

    suspend fun clearCache(): Result<MessageResponseDto> = runCatching {
        client.delete(ApiRoutes.IP_REP_CACHE).body()
    }

    suspend fun test(): Result<IpRepTestDto> = runCatching {
        client.post(ApiRoutes.IP_REP_TEST).body()
    }

    suspend fun getBlacklist(): Result<List<IpRepBlacklistDto>> = runCatching {
        client.get(ApiRoutes.IP_REP_BLACKLIST).body()
    }

    suspend fun fetchBlacklist(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.IP_REP_BLACKLIST_FETCH).body()
    }

    suspend fun getBlacklistConfig(): Result<IpRepBlacklistConfigDto> = runCatching {
        client.get(ApiRoutes.IP_REP_BLACKLIST_CONFIG).body()
    }

    suspend fun updateBlacklistConfig(dto: IpRepBlacklistConfigUpdateDto): Result<IpRepBlacklistConfigDto> = runCatching {
        client.put(ApiRoutes.IP_REP_BLACKLIST_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }
}
