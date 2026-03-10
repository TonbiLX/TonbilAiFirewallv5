package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ============ WiFi Genisletilmis DTOlar ============

// Misafir WiFi konfigurasyonu
@Serializable
data class WifiGuestConfigDto(
    val enabled: Boolean = false,
    val ssid: String = "",
    val password: String = "",
    @SerialName("client_isolation") val clientIsolation: Boolean = true,
    @SerialName("bandwidth_limit_mbps") val bandwidthLimitMbps: Float? = null,
)

// WiFi zamanlama ayari
@Serializable
data class WifiScheduleDto(
    val enabled: Boolean = false,
    @SerialName("start_time") val startTime: String = "08:00",
    @SerialName("end_time") val endTime: String = "22:00",
    val days: List<String> = listOf("mon", "tue", "wed", "thu", "fri", "sat", "sun"),
)

// MAC adresi filtre listesi
@Serializable
data class WifiMacFilterDto(
    val mode: String = "disabled", // "disabled", "whitelist", "blacklist"
    val whitelist: List<String> = emptyList(),
    val blacklist: List<String> = emptyList(),
)

// Kullanilabilir WiFi kanallari
@Serializable
data class WifiChannelDto(
    val channel: Int = 0,
    val frequency: String = "",
    val band: String = "",
    @SerialName("in_use") val inUse: Boolean = false,
)

// ============ DHCP Havuz DTOlari ============

// DHCP IP havuzu (response)
@Serializable
data class DhcpPoolDto(
    val id: Int = 0,
    val name: String = "",
    @SerialName("start_ip") val startIp: String = "",
    @SerialName("end_ip") val endIp: String = "",
    val subnet: String = "",
    val gateway: String = "",
    @SerialName("lease_time") val leaseTime: String = "24h",
    val enabled: Boolean = true,
    @SerialName("dns_servers") val dnsServers: String? = null,
)

// DHCP IP havuzu olusturma (request)
@Serializable
data class DhcpPoolCreateDto(
    val name: String,
    @SerialName("start_ip") val startIp: String,
    @SerialName("end_ip") val endIp: String,
    val subnet: String = "255.255.255.0",
    val gateway: String,
    @SerialName("lease_time") val leaseTime: String = "24h",
    val enabled: Boolean = true,
    @SerialName("dns_servers") val dnsServers: String? = null,
)

// ============ Cihaz Kural DTOlari ============

// Cihaza ozel DNS kurali (response)
@Serializable
data class DeviceRuleDto(
    val id: Int = 0,
    @SerialName("device_id") val deviceId: Int = 0,
    val domain: String = "",
    val action: String = "", // "block" veya "allow"
    @SerialName("created_at") val createdAt: String? = null,
)

// Cihaza ozel DNS kurali olusturma (request)
@Serializable
data class DeviceRuleCreateDto(
    val domain: String,
    val action: String, // "block" veya "allow"
)

// ============ Trafik DTOlari ============

// Cihaz bazli trafik ozeti
@Serializable
data class TrafficPerDeviceDto(
    @SerialName("device_id") val deviceId: Int = 0,
    val hostname: String = "",
    @SerialName("ip_address") val ipAddress: String = "",
    @SerialName("upload_bytes") val totalUpload: Long = 0,
    @SerialName("download_bytes") val totalDownload: Long = 0,
    @SerialName("connection_count") val totalPackets: Long = 0,
    @SerialName("upload_bps") val uploadSpeed: Long = 0,
    @SerialName("download_bps") val downloadSpeed: Long = 0,
)

// Trafik gecmisi sayfalama response
@Serializable
data class TrafficHistoryDto(
    val items: List<TrafficHistoryItemDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    @SerialName("page_size") val pageSize: Int = 50,
)

// Tek bir trafik gecmis kaydi
@Serializable
data class TrafficHistoryItemDto(
    @SerialName("flow_id") val flowId: String = "",
    val protocol: String = "",
    @SerialName("src_ip") val srcIp: String = "",
    @SerialName("dst_ip") val dstIp: String = "",
    @SerialName("dst_domain") val dstDomain: String? = null,
    @SerialName("bytes_total") val bytesTotal: Long = 0,
    @SerialName("service_name") val serviceName: String? = null,
    @SerialName("app_name") val appName: String? = null,
    @SerialName("started_at") val startedAt: String? = null,
    @SerialName("ended_at") val endedAt: String? = null,
)

// Cihazin en cok baglantigi hedefler
@Serializable
data class DeviceTopDestinationDto(
    val domain: String = "",
    @SerialName("ip_address") val ipAddress: String? = null,
    @SerialName("total_bytes") val totalBytes: Long = 0,
    @SerialName("connection_count") val connectionCount: Int = 0,
    @SerialName("last_seen") val lastSeen: String? = null,
)

// ============ Port Tarama DTOlari ============

// Tek port tarama sonucu
@Serializable
data class PortScanResultDto(
    val port: Int = 0,
    val protocol: String = "",
    val state: String = "", // "open", "closed", "filtered"
    val service: String = "",
)

// ============ Firewall Baglanti DTOlari ============

// Aktif firewall baglantisi (conntrack)
@Serializable
data class FirewallConnectionDto(
    val protocol: String = "",
    @SerialName("src_ip") val srcIp: String = "",
    @SerialName("src_port") val srcPort: Int = 0,
    @SerialName("dst_ip") val dstIp: String = "",
    @SerialName("dst_port") val dstPort: Int = 0,
    val state: String = "",
    val ttl: Int = 0,
)

// ============ DNS Sorgu DTOlari ============

// DNS sorgu gecmisi sayfalama response
@Serializable
data class DnsQueryPageDto(
    val items: List<DnsQueryItemDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    @SerialName("page_size") val pageSize: Int = 50,
)

// Tek bir DNS sorgu kaydi
@Serializable
data class DnsQueryItemDto(
    val id: Int = 0,
    val timestamp: String = "",
    @SerialName("client_ip") val clientIp: String = "",
    val domain: String = "",
    @SerialName("query_type") val queryType: String = "",
    val blocked: Boolean = false,
    @SerialName("block_reason") val blockReason: String? = null,
    @SerialName("response_time_ms") val responseTimeMs: Float? = null,
    val hostname: String? = null,
)

// Dis kaynaklardan gelen DNS sorgu ozeti
@Serializable
data class DnsExternalSummaryDto(
    @SerialName("total_external") val totalExternal: Int = 0,
    @SerialName("unique_sources") val uniqueSources: Int = 0,
    @SerialName("top_sources") val topSources: List<ExternalSourceDto> = emptyList(),
)

// Dis DNS sorgu kaynagi
@Serializable
data class ExternalSourceDto(
    @SerialName("source_ip") val sourceIp: String = "",
    val count: Int = 0,
    @SerialName("country_code") val countryCode: String? = null,
)

// DNS domain engelleme sorgu sonucu
@Serializable
data class DnsLookupDto(
    val domain: String = "",
    val blocked: Boolean = false,
    @SerialName("block_source") val blockSource: String? = null,
    @SerialName("blocklist_name") val blocklistName: String? = null,
)

// ============ Auth Genisletilmis DTOlari ============

// Profil guncelleme (display name)
@Serializable
data class AuthProfileUpdateDto(
    @SerialName("display_name") val displayName: String? = null,
)

// Sifre degistirme
@Serializable
data class AuthChangePasswordDto(
    @SerialName("current_password") val currentPassword: String,
    @SerialName("new_password") val newPassword: String,
)

// ============ Cihaz Ek DTOlari ============

// Cihaz bant genisligi limiti guncelleme
@Serializable
data class DeviceBandwidthDto(
    @SerialName("bandwidth_limit_mbps") val bandwidthLimitMbps: Float?,
)

// ARP tarama response
@Serializable
data class DeviceScanResponseDto(
    @SerialName("new_devices") val newDevices: Int = 0,
    @SerialName("total_devices") val totalDevices: Int = 0,
    val message: String = "",
)
