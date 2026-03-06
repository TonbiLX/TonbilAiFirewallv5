package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// DNS Stats
@Serializable
data class DnsStatsDto(
    @SerialName("total_queries_24h") val totalQueries24h: Int = 0,
    @SerialName("blocked_queries_24h") val blockedQueries24h: Int = 0,
    @SerialName("block_percentage") val blockPercentage: Float = 0f,
    @SerialName("total_blocklist_domains") val totalBlocklistDomains: Int = 0,
    @SerialName("active_blocklists") val activeBlocklists: Int = 0,
    @SerialName("top_blocked_domains") val topBlockedDomains: List<TopDomainDto> = emptyList(),
    @SerialName("top_queried_domains") val topQueriedDomains: List<TopDomainDto> = emptyList(),
)

// Firewall Stats
@Serializable
data class FirewallStatsDto(
    @SerialName("total_rules") val totalRules: Int = 0,
    @SerialName("active_rules") val activeRules: Int = 0,
    @SerialName("inbound_rules") val inboundRules: Int = 0,
    @SerialName("outbound_rules") val outboundRules: Int = 0,
    @SerialName("blocked_packets_24h") val blockedPackets24h: Int = 0,
    @SerialName("open_ports") val openPorts: List<String> = emptyList(),
    @SerialName("active_connections") val activeConnections: Int = 0,
    @SerialName("max_connections") val maxConnections: Int = 0,
)

@Serializable
data class ConnectionCountDto(
    val active: Int = 0,
    val max: Int = 0,
)

// VPN Stats
@Serializable
data class VpnStatsDto(
    @SerialName("server_enabled") val serverEnabled: Boolean = false,
    @SerialName("server_public_key") val serverPublicKey: String = "",
    @SerialName("listen_port") val listenPort: Int = 0,
    @SerialName("total_peers") val totalPeers: Int = 0,
    @SerialName("connected_peers") val connectedPeers: Int = 0,
    @SerialName("total_transfer_rx") val totalTransferRx: Long = 0,
    @SerialName("total_transfer_tx") val totalTransferTx: Long = 0,
)

@Serializable
data class VpnPeerDto(
    val name: String = "",
    @SerialName("public_key") val publicKey: String = "",
    @SerialName("allowed_ips") val allowedIps: String = "",
    @SerialName("latest_handshake") val latestHandshake: String? = null,
    @SerialName("transfer_rx") val transferRx: Long = 0,
    @SerialName("transfer_tx") val transferTx: Long = 0,
    val connected: Boolean = false,
)

// DDoS
@Serializable
data class DdosProtectionStatusDto(
    val name: String = "",
    val enabled: Boolean = false,
    @SerialName("display_name") val displayName: String = "",
)

@Serializable
data class DdosProtectionCounterDto(
    val packets: Long = 0,
    val bytes: Long = 0,
)

@Serializable
data class DdosCountersDto(
    @SerialName("total_dropped_packets") val totalDroppedPackets: Long = 0,
    @SerialName("total_dropped_bytes") val totalDroppedBytes: Long = 0,
    @SerialName("by_protection") val byProtection: Map<String, DdosProtectionCounterDto> = emptyMap(),
)

// Security Stats
@Serializable
data class SecurityStatsDto(
    @SerialName("blocked_ip_count") val blockedIpCount: Int = 0,
    @SerialName("total_auto_blocks") val totalAutoBlocks: Int = 0,
    @SerialName("total_external_blocked") val totalExternalBlocked: Int = 0,
    @SerialName("total_suspicious") val totalSuspicious: Int = 0,
    @SerialName("dga_detections") val dgaDetections: Int = 0,
    @SerialName("blocked_subnet_count") val blockedSubnetCount: Int = 0,
    @SerialName("last_threat_time") val lastThreatTime: String? = null,
)

// DHCP Stats
@Serializable
data class DhcpStatsDto(
    @SerialName("total_pools") val totalPools: Int = 0,
    @SerialName("active_pools") val activePools: Int = 0,
    @SerialName("total_ips") val totalIps: Int = 0,
    @SerialName("assigned_ips") val assignedIps: Int = 0,
    @SerialName("available_ips") val availableIps: Int = 0,
    @SerialName("static_leases") val staticLeases: Int = 0,
    @SerialName("dynamic_leases") val dynamicLeases: Int = 0,
    @SerialName("dnsmasq_running") val dnsmasqRunning: Boolean = false,
)

@Serializable
data class DhcpLeaseDto(
    @SerialName("mac_address") val macAddress: String = "",
    @SerialName("ip_address") val ipAddress: String = "",
    val hostname: String? = null,
    val expiry: String? = null,
)

// DNS Blocklist
@Serializable
data class BlocklistDto(
    val id: Int = 0,
    val name: String = "",
    val url: String = "",
    val enabled: Boolean = true,
    @SerialName("domain_count") val domainCount: Int = 0,
    @SerialName("last_updated") val lastUpdated: String? = null,
)

// DNS Rule (custom allow/block)
@Serializable
data class DnsRuleDto(
    val id: Int = 0,
    val domain: String = "",
    val action: String = "", // "block" or "allow"
    @SerialName("created_at") val createdAt: String? = null,
)

// Firewall Rule
@Serializable
data class FirewallRuleDto(
    val id: Int = 0,
    val name: String = "",
    val direction: String = "", // "inbound" or "outbound"
    val protocol: String = "",
    val port: String? = null,
    @SerialName("source_ip") val sourceIp: String? = null,
    @SerialName("dest_ip") val destIp: String? = null,
    val action: String = "", // "accept", "drop", "reject"
    val enabled: Boolean = true,
)

// AI Insight
@Serializable
data class AiInsightDto(
    val id: Int = 0,
    val severity: String = "", // "info", "warning", "critical"
    val category: String = "",
    val title: String = "",
    val description: String = "",
    val dismissed: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
)

// Live Flow
@Serializable
data class LiveFlowDto(
    @SerialName("flow_id") val flowId: String = "",
    val protocol: String = "",
    @SerialName("src_ip") val srcIp: String = "",
    @SerialName("src_port") val srcPort: Int = 0,
    @SerialName("dst_ip") val dstIp: String = "",
    @SerialName("dst_port") val dstPort: Int = 0,
    @SerialName("dst_domain") val dstDomain: String? = null,
    @SerialName("bytes_in") val bytesIn: Long = 0,
    @SerialName("bytes_out") val bytesOut: Long = 0,
    @SerialName("bps_in") val bpsIn: Long = 0,
    @SerialName("bps_out") val bpsOut: Long = 0,
    val state: String = "",
    @SerialName("service_name") val serviceName: String? = null,
    @SerialName("app_name") val appName: String? = null,
    val direction: String = "", // "outbound" or "inbound"
    @SerialName("device_id") val deviceId: Int? = null,
    val hostname: String? = null,
)

// Flow Stats
@Serializable
data class FlowStatsDto(
    @SerialName("total_active") val totalActive: Int = 0,
    @SerialName("total_bytes_in") val totalBytesIn: Long = 0,
    @SerialName("total_bytes_out") val totalBytesOut: Long = 0,
    @SerialName("unique_destinations") val uniqueDestinations: Int = 0,
    @SerialName("tracked_devices") val trackedDevices: Int = 0,
)

// WiFi AP
@Serializable
data class WifiStatusDto(
    val running: Boolean = false,
    val ssid: String = "",
    val channel: Int = 0,
    @SerialName("connected_clients") val connectedClients: Int = 0,
    val frequency: String = "",
)

@Serializable
data class WifiClientDto(
    @SerialName("mac_address") val macAddress: String = "",
    @SerialName("signal_strength") val signalStrength: Int = 0,
    @SerialName("rx_bytes") val rxBytes: Long = 0,
    @SerialName("tx_bytes") val txBytes: Long = 0,
    val hostname: String? = null,
)

// Telegram
@Serializable
data class TelegramConfigDto(
    @SerialName("bot_token") val botToken: String = "",
    @SerialName("chat_id") val chatId: String = "",
    val enabled: Boolean = false,
    @SerialName("notify_threats") val notifyThreats: Boolean = true,
    @SerialName("notify_devices") val notifyDevices: Boolean = true,
    @SerialName("notify_ddos") val notifyDdos: Boolean = true,
)

// System Monitor
@Serializable
data class SystemOverviewDto(
    val uptime: String = "",
    @SerialName("cpu_percent") val cpuPercent: Float = 0f,
    @SerialName("memory_percent") val memoryPercent: Float = 0f,
    @SerialName("memory_used_mb") val memoryUsedMb: Int = 0,
    @SerialName("memory_total_mb") val memoryTotalMb: Int = 0,
    @SerialName("disk_percent") val diskPercent: Float = 0f,
    @SerialName("disk_used_gb") val diskUsedGb: Float = 0f,
    @SerialName("disk_total_gb") val diskTotalGb: Float = 0f,
    @SerialName("cpu_temp") val cpuTemp: Float = 0f,
)

@Serializable
data class ServiceStatusDto(
    @SerialName("service_name") val serviceName: String = "",
    val status: String = "", // "running", "stopped", "failed"
    @SerialName("display_name") val displayName: String = "",
)

// Chat
@Serializable
data class ChatSendDto(
    val message: String,
)

@Serializable
data class ChatResponseDto(
    val reply: String = "",
    val intent: String? = null,
    val data: kotlinx.serialization.json.JsonElement? = null,
)

@Serializable
data class ChatMessageDto(
    val role: String = "",
    val content: String = "",
    val timestamp: String? = null,
)

// ============ REQUEST DTOs ============

// DNS Rule Create
@Serializable
data class DnsRuleCreateDto(
    val domain: String,
    val action: String, // "block" or "allow"
)

// Blocklist Create
@Serializable
data class BlocklistCreateDto(
    val name: String,
    val url: String,
)

// Firewall Rule Create/Update
@Serializable
data class FirewallRuleCreateDto(
    val name: String,
    val direction: String, // "inbound" or "outbound"
    val protocol: String,
    val port: String? = null,
    @SerialName("source_ip") val sourceIp: String? = null,
    @SerialName("dest_ip") val destIp: String? = null,
    val action: String, // "accept", "drop", "reject"
    val enabled: Boolean = true,
)

// VPN Peer Create
@Serializable
data class VpnPeerCreateDto(
    val name: String,
    val dns: String? = null,
)

// VPN Peer Config (for QR code display)
@Serializable
data class VpnPeerConfigDto(
    @SerialName("config_text") val configText: String = "",
    @SerialName("qr_code_base64") val qrCodeBase64: String? = null,
)

// DHCP Static Lease Create
@Serializable
data class DhcpStaticLeaseCreateDto(
    @SerialName("mac_address") val macAddress: String,
    @SerialName("ip_address") val ipAddress: String,
    val hostname: String? = null,
)

// Profile Create/Update
@Serializable
data class ProfileCreateDto(
    val name: String,
    @SerialName("profile_type") val profileType: String? = null,
    @SerialName("content_filters") val contentFilters: List<String> = emptyList(),
    @SerialName("bandwidth_limit_mbps") val bandwidthLimitMbps: Float? = null,
)

// WiFi Config Update
@Serializable
data class WifiConfigUpdateDto(
    val ssid: String? = null,
    val password: String? = null,
    val channel: Int? = null,
)

// Telegram Config Update
@Serializable
data class TelegramConfigUpdateDto(
    @SerialName("bot_token") val botToken: String? = null,
    @SerialName("chat_id") val chatId: String? = null,
    val enabled: Boolean? = null,
    @SerialName("notify_threats") val notifyThreats: Boolean? = null,
    @SerialName("notify_devices") val notifyDevices: Boolean? = null,
    @SerialName("notify_ddos") val notifyDdos: Boolean? = null,
)

// Generic message response
@Serializable
data class MessageResponseDto(
    val message: String = "",
    val status: String = "",
)
