package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.DashboardSummaryDto
import com.tonbil.aifirewall.data.remote.dto.TrafficPerDeviceDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get

class DashboardRepository(private val client: HttpClient) {
    suspend fun getSummary(): Result<DashboardSummaryDto> {
        return try {
            val response: DashboardSummaryDto = client.get(ApiRoutes.DASHBOARD_SUMMARY).body()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getTrafficPerDevice(): Result<List<TrafficPerDeviceDto>> = runCatching {
        client.get(ApiRoutes.TRAFFIC_PER_DEVICE).body()
    }
}
