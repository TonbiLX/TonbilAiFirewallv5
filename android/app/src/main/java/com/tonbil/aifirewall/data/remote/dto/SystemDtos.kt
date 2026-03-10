package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// GET /system-monitor/info
@Serializable
data class SystemInfoDto(
    val model: String = "",
    @SerialName("cpu_model") val cpuModel: String = "",
    @SerialName("cpu_cores") val cpuCores: Int = 0,
    @SerialName("total_ram_mb") val totalRamMb: Int = 0,
    @SerialName("total_disk_gb") val totalDiskGb: Float = 0f,
    @SerialName("os_version") val osVersion: String = "",
    @SerialName("kernel_version") val kernelVersion: String = "",
    val hostname: String = "",
    @SerialName("mac_address") val macAddress: String = "",
)

// GET /system-monitor/fan, PUT /system-monitor/fan
@Serializable
data class FanConfigDto(
    val mode: String = "auto",
    @SerialName("pwm_value") val pwmValue: Int = 128,
    @SerialName("target_temp") val targetTemp: Int = 55,
    @SerialName("current_rpm") val currentRpm: Int = 0,
    @SerialName("current_pwm") val currentPwm: Int = 0,
)

@Serializable
data class FanConfigUpdateDto(
    val mode: String? = null,
    @SerialName("pwm_value") val pwmValue: Int? = null,
    @SerialName("target_temp") val targetTemp: Int? = null,
)

// GET /system-management/overview
@Serializable
data class SystemOverviewFullDto(
    @SerialName("uptime_seconds") val uptimeSeconds: Long = 0,
    @SerialName("uptime_human") val uptimeHuman: String = "",
    @SerialName("boot_count") val bootCount: Int = 0,
    @SerialName("safe_mode") val safeMode: Boolean = false,
    @SerialName("watchdog_enabled") val watchdogEnabled: Boolean = false,
    @SerialName("last_boot") val lastBoot: String? = null,
)

// GET /system-management/boot-info
@Serializable
data class BootInfoDto(
    @SerialName("boot_count") val bootCount: Int = 0,
    @SerialName("safe_mode") val safeMode: Boolean = false,
    @SerialName("watchdog_enabled") val watchdogEnabled: Boolean = false,
    @SerialName("watchdog_timeout") val watchdogTimeout: Int = 0,
    @SerialName("last_boot") val lastBoot: String? = null,
    @SerialName("last_shutdown_reason") val lastShutdownReason: String? = null,
)

// GET /system-management/journal
@Serializable
data class JournalDto(
    val lines: List<String> = emptyList(),
    val total: Int = 0,
)

// POST /system-management/reboot
@Serializable
data class SystemRebootDto(
    val confirm: Boolean = true,
)
