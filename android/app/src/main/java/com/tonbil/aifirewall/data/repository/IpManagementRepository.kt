package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class IpManagementRepository(private val client: HttpClient) {

    suspend fun getStats(): Result<IpMgmtStatsDto> = runCatching {
        client.get(ApiRoutes.IP_MGMT_STATS).body()
    }

    suspend fun getTrustedIps(): Result<List<TrustedIpDto>> = runCatching {
        client.get(ApiRoutes.IP_MGMT_TRUSTED).body()
    }

    suspend fun addTrustedIp(dto: TrustedIpCreateDto): Result<TrustedIpDto> = runCatching {
        client.post(ApiRoutes.IP_MGMT_TRUSTED) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteTrustedIp(id: Int): Result<Unit> = runCatching {
        client.delete(ApiRoutes.ipMgmtTrustedDelete(id))
    }

    suspend fun getBlockedIps(): Result<List<BlockedIpDto>> = runCatching {
        client.get(ApiRoutes.IP_MGMT_BLOCKED).body()
    }

    suspend fun blockIp(dto: BlockedIpCreateDto): Result<BlockedIpDto> = runCatching {
        client.post(ApiRoutes.IP_MGMT_BLOCKED) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun unblockIp(dto: IpUnblockDto): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.IP_MGMT_UNBLOCK) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun bulkUnblock(dto: IpBulkUnblockDto): Result<MessageResponseDto> = runCatching {
        client.put(ApiRoutes.IP_MGMT_BULK_UNBLOCK) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun updateDuration(dto: IpDurationDto): Result<MessageResponseDto> = runCatching {
        client.put(ApiRoutes.IP_MGMT_DURATION) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun bulkUpdateDuration(dto: IpBulkDurationDto): Result<MessageResponseDto> = runCatching {
        client.put(ApiRoutes.IP_MGMT_BULK_DURATION) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }
}
