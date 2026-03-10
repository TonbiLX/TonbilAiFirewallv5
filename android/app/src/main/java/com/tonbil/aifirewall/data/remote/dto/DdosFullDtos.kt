package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ============================================================
// DDoS Full DTOs
// Backend prefix: /ddos
//
// Note: The following already exist in SecurityDtos.kt and are
// reused as-is — do NOT redeclare them here:
//   - DdosProtectionStatusDto   (GET /ddos/status items)
//   - DdosCountersDto           (GET /ddos/counters)
//   - DdosProtectionCounterDto  (nested inside DdosCountersDto)
// ============================================================

// GET /ddos/config
@Serializable
data class DdosConfigDto(
    @SerialName("syn_flood_enabled") val synFloodEnabled: Boolean = true,
    @SerialName("syn_flood_rate") val synFloodRate: String = "25/second",
    @SerialName("syn_flood_burst") val synFloodBurst: Int = 50,
    @SerialName("udp_flood_enabled") val udpFloodEnabled: Boolean = true,
    @SerialName("udp_flood_rate") val udpFloodRate: String = "50/second",
    @SerialName("udp_flood_burst") val udpFloodBurst: Int = 100,
    @SerialName("icmp_flood_enabled") val icmpFloodEnabled: Boolean = true,
    @SerialName("icmp_flood_rate") val icmpFloodRate: String = "10/second",
    @SerialName("icmp_flood_burst") val icmpFloodBurst: Int = 20,
    @SerialName("port_scan_enabled") val portScanEnabled: Boolean = true,
    @SerialName("port_scan_rate") val portScanRate: String = "15/second",
    @SerialName("port_scan_burst") val portScanBurst: Int = 25,
    @SerialName("invalid_packet_enabled") val invalidPacketEnabled: Boolean = true,
    @SerialName("connection_limit_enabled") val connectionLimitEnabled: Boolean = true,
    @SerialName("connection_limit") val connectionLimit: Int = 100,
    @SerialName("dns_amplification_enabled") val dnsAmplificationEnabled: Boolean = true,
    @SerialName("dns_amplification_rate") val dnsAmplificationRate: String = "20/second",
    @SerialName("slowloris_enabled") val slowlorisEnabled: Boolean = false,
)

// PUT /ddos/config  — request body (all fields optional for partial update)
@Serializable
data class DdosConfigUpdateDto(
    @SerialName("syn_flood_enabled") val synFloodEnabled: Boolean? = null,
    @SerialName("syn_flood_rate") val synFloodRate: String? = null,
    @SerialName("syn_flood_burst") val synFloodBurst: Int? = null,
    @SerialName("udp_flood_enabled") val udpFloodEnabled: Boolean? = null,
    @SerialName("udp_flood_rate") val udpFloodRate: String? = null,
    @SerialName("udp_flood_burst") val udpFloodBurst: Int? = null,
    @SerialName("icmp_flood_enabled") val icmpFloodEnabled: Boolean? = null,
    @SerialName("icmp_flood_rate") val icmpFloodRate: String? = null,
    @SerialName("icmp_flood_burst") val icmpFloodBurst: Int? = null,
    @SerialName("port_scan_enabled") val portScanEnabled: Boolean? = null,
    @SerialName("port_scan_rate") val portScanRate: String? = null,
    @SerialName("port_scan_burst") val portScanBurst: Int? = null,
    @SerialName("invalid_packet_enabled") val invalidPacketEnabled: Boolean? = null,
    @SerialName("connection_limit_enabled") val connectionLimitEnabled: Boolean? = null,
    @SerialName("connection_limit") val connectionLimit: Int? = null,
    @SerialName("dns_amplification_enabled") val dnsAmplificationEnabled: Boolean? = null,
    @SerialName("dns_amplification_rate") val dnsAmplificationRate: String? = null,
    @SerialName("slowloris_enabled") val slowlorisEnabled: Boolean? = null,
)

// GET /ddos/attack-map — top-level response
@Serializable
data class DdosAttackMapDto(
    val attacks: List<DdosAttackPointDto> = emptyList(),
    @SerialName("total_blocked") val totalBlocked: Long = 0,
    @SerialName("active_attackers") val activeAttackers: Int = 0,
)

// GET /ddos/attack-map — individual attack point
@Serializable
data class DdosAttackPointDto(
    @SerialName("ip_address") val ipAddress: String = "",
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    @SerialName("country_code") val countryCode: String? = null,
    @SerialName("country_name") val countryName: String? = null,
    val city: String? = null,
    @SerialName("attack_type") val attackType: String = "",
    @SerialName("packet_count") val packetCount: Long = 0,
    @SerialName("last_seen") val lastSeen: String? = null,
)
