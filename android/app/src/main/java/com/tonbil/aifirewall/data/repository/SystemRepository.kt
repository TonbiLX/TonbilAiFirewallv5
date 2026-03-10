package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class SystemRepository(private val client: HttpClient) {

    // ========== SYSTEM MONITOR ==========

    suspend fun getSystemInfo(): Result<SystemInfoDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_INFO).body()
    }

    suspend fun getSystemMetrics(): Result<SystemMetricsResponseDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_METRICS).body()
    }

    suspend fun getFanConfig(): Result<FanConfigDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_FAN).body()
    }

    suspend fun updateFanConfig(dto: FanConfigUpdateDto): Result<FanConfigDto> = runCatching {
        client.put(ApiRoutes.SYSTEM_FAN) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    // ========== SYSTEM MANAGEMENT ==========

    suspend fun getOverview(): Result<SystemOverviewFullDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_OVERVIEW).body()
    }

    suspend fun getServices(): Result<List<ServiceStatusDto>> = runCatching {
        client.get(ApiRoutes.SYSTEM_SERVICES).body()
    }

    suspend fun restartService(name: String): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.systemServiceAction(name, "restart")).body()
    }

    suspend fun startService(name: String): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.systemServiceAction(name, "start")).body()
    }

    suspend fun stopService(name: String): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.systemServiceAction(name, "stop")).body()
    }

    suspend fun reboot(dto: SystemRebootDto): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.SYSTEM_REBOOT) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun shutdown(dto: SystemRebootDto): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.SYSTEM_SHUTDOWN) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun getBootInfo(): Result<BootInfoDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_BOOT_INFO).body()
    }

    suspend fun resetSafeMode(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.SYSTEM_SAFE_MODE).body()
    }

    suspend fun getJournal(lines: Int = 100): Result<JournalDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_JOURNAL) {
            parameter("lines", lines)
        }.body()
    }

    // ========== SYSTEM TIME ==========

    suspend fun getTimeStatus(): Result<TimeStatusDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_TIME_STATUS).body()
    }

    suspend fun getTimezones(): Result<List<TimezoneGroupDto>> = runCatching {
        client.get(ApiRoutes.SYSTEM_TIME_TIMEZONES).body()
    }

    suspend fun getNtpServers(): Result<List<NtpServerDto>> = runCatching {
        client.get(ApiRoutes.SYSTEM_TIME_NTP_SERVERS).body()
    }

    suspend fun setTimezone(dto: SetTimezoneDto): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.SYSTEM_TIME_SET_TZ) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun setNtpServer(dto: SetNtpServerDto): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.SYSTEM_TIME_SET_NTP) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun syncTime(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.SYSTEM_TIME_SYNC).body()
    }

    // ========== SYSTEM LOGS ==========

    suspend fun getLogs(
        page: Int = 1,
        pageSize: Int = 50,
        severity: String? = null,
        category: String? = null,
    ): Result<SystemLogPageDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_LOGS) {
            parameter("page", page)
            parameter("page_size", pageSize)
            if (severity != null) parameter("severity", severity)
            if (category != null) parameter("category", category)
        }.body()
    }

    suspend fun getLogsSummary(): Result<SystemLogSummaryDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_LOGS_SUMMARY).body()
    }
}
