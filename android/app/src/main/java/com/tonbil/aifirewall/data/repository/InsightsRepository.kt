package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class InsightsRepository(private val client: HttpClient) {

    suspend fun getInsights(): Result<List<AiInsightDto>> = runCatching {
        client.get(ApiRoutes.INSIGHTS).body()
    }

    suspend fun getCriticalCount(): Result<Int> = runCatching {
        // Returns {"count": N}
        val resp: Map<String, Int> = client.get(ApiRoutes.INSIGHTS_CRITICAL_COUNT).body()
        resp["count"] ?: 0
    }

    suspend fun dismiss(id: Int): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.insightDismiss(id)).body()
    }

    suspend fun getThreatStats(): Result<InsightThreatStatsDto> = runCatching {
        client.get(ApiRoutes.INSIGHTS_THREAT_STATS).body()
    }

    suspend fun getBlockedIps(): Result<List<InsightBlockedIpDto>> = runCatching {
        client.get(ApiRoutes.INSIGHTS_BLOCKED_IPS).body()
    }

    suspend fun blockIp(dto: InsightBlockIpDto): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.INSIGHTS_BLOCK_IP) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun unblockIp(dto: InsightUnblockIpDto): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.INSIGHTS_UNBLOCK_IP) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }
}
