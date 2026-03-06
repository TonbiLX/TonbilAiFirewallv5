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
