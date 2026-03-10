package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.client.request.url
import io.ktor.http.ContentType
import io.ktor.http.contentType

class DeviceServiceRepository(private val client: HttpClient) {

    suspend fun getServices(group: String? = null): Result<List<ServiceDto>> = runCatching {
        client.get(ApiRoutes.SERVICES) {
            if (group != null) {
                url {
                    parameters.append("group", group)
                }
            }
        }.body()
    }

    suspend fun getGroups(): Result<List<ServiceGroupDto>> = runCatching {
        client.get(ApiRoutes.SERVICES_GROUPS).body()
    }

    suspend fun getDeviceServices(deviceId: Int): Result<List<DeviceServiceDto>> = runCatching {
        client.get(ApiRoutes.deviceServices(deviceId)).body()
    }

    suspend fun toggleService(deviceId: Int, dto: ServiceToggleDto): Result<MessageResponseDto> = runCatching {
        client.put(ApiRoutes.deviceServiceToggle(deviceId)) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun bulkUpdate(deviceId: Int, dto: ServiceBulkDto): Result<MessageResponseDto> = runCatching {
        client.put(ApiRoutes.deviceServiceBulk(deviceId)) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }
}
