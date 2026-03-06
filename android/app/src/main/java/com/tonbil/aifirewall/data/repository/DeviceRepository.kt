package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.BlockResponseDto
import com.tonbil.aifirewall.data.remote.dto.ConnectionHistoryDto
import com.tonbil.aifirewall.data.remote.dto.DeviceResponseDto
import com.tonbil.aifirewall.data.remote.dto.DeviceTrafficSummaryDto
import com.tonbil.aifirewall.data.remote.dto.DeviceUpdateDto
import com.tonbil.aifirewall.data.remote.dto.DnsQueryLogDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class DeviceRepository(private val client: HttpClient) {

    suspend fun getDevices(
        sortBy: String = "hostname",
        sortOrder: String = "asc",
    ): Result<List<DeviceResponseDto>> {
        return try {
            val response: List<DeviceResponseDto> = client.get(ApiRoutes.DEVICES) {
                url {
                    parameters.append("sort_by", sortBy)
                    parameters.append("sort_order", sortOrder)
                }
            }.body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getDevice(id: Int): Result<DeviceResponseDto> {
        return try {
            val response: DeviceResponseDto = client.get(ApiRoutes.deviceDetail(id)).body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun updateDevice(id: Int, update: DeviceUpdateDto): Result<DeviceResponseDto> {
        return try {
            val response: DeviceResponseDto = client.patch(ApiRoutes.deviceDetail(id)) {
                contentType(ContentType.Application.Json)
                setBody(update)
            }.body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun blockDevice(id: Int): Result<BlockResponseDto> {
        return try {
            val response: BlockResponseDto = client.post(ApiRoutes.deviceBlock(id)).body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun unblockDevice(id: Int): Result<BlockResponseDto> {
        return try {
            val response: BlockResponseDto = client.post(ApiRoutes.deviceUnblock(id)).body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getConnectionHistory(
        id: Int,
        limit: Int = 20,
    ): Result<List<ConnectionHistoryDto>> {
        return try {
            val response: List<ConnectionHistoryDto> =
                client.get(ApiRoutes.deviceConnectionHistory(id)) {
                    url {
                        parameters.append("limit", limit.toString())
                    }
                }.body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getDnsLogs(
        clientIp: String,
        limit: Int = 50,
    ): Result<List<DnsQueryLogDto>> {
        return try {
            val response: List<DnsQueryLogDto> = client.get(ApiRoutes.DNS_QUERY_LOGS) {
                url {
                    parameters.append("client_ip", clientIp)
                    parameters.append("limit", limit.toString())
                }
            }.body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getTrafficSummary(id: Int): Result<DeviceTrafficSummaryDto> {
        return try {
            val response: DeviceTrafficSummaryDto =
                client.get(ApiRoutes.deviceTrafficSummary(id)).body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
