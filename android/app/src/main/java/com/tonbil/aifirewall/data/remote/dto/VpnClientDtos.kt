package com.tonbil.aifirewall.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// VPN Client Server (response)
@Serializable
data class VpnClientServerDto(
    val id: Int = 0,
    val name: String = "",
    val endpoint: String = "",
    val port: Int = 51820,
    @SerialName("public_key") val publicKey: String = "",
    @SerialName("private_key") val privateKey: String = "",
    @SerialName("allowed_ips") val allowedIps: String = "0.0.0.0/0",
    val dns: String? = null,
    val active: Boolean = false,
    val connected: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
)

// VPN Client Connection Status
@Serializable
data class VpnClientStatusDto(
    val connected: Boolean = false,
    @SerialName("server_name") val serverName: String? = null,
    @SerialName("server_id") val serverId: Int? = null,
    val endpoint: String? = null,
    @SerialName("transfer_rx") val transferRx: Long = 0,
    @SerialName("transfer_tx") val transferTx: Long = 0,
    @SerialName("latest_handshake") val latestHandshake: String? = null,
    @SerialName("connected_since") val connectedSince: String? = null,
)

// VPN Client Aggregate Stats
@Serializable
data class VpnClientStatsDto(
    @SerialName("total_servers") val totalServers: Int = 0,
    @SerialName("active_server") val activeServer: String? = null,
    val connected: Boolean = false,
    @SerialName("total_transfer_rx") val totalTransferRx: Long = 0,
    @SerialName("total_transfer_tx") val totalTransferTx: Long = 0,
)

// ============ REQUEST DTOs ============

// POST /vpn-client/servers — manual server creation
@Serializable
data class VpnClientCreateDto(
    val name: String,
    val endpoint: String,
    val port: Int = 51820,
    @SerialName("public_key") val publicKey: String,
    @SerialName("private_key") val privateKey: String,
    @SerialName("allowed_ips") val allowedIps: String = "0.0.0.0/0",
    val dns: String? = null,
)

// POST /vpn-client/servers/import — import from .conf text
@Serializable
data class VpnClientImportDto(
    val name: String,
    @SerialName("config_text") val configText: String,
)

// PATCH /vpn-client/servers/{id} — partial update
@Serializable
data class VpnClientUpdateDto(
    val name: String? = null,
    val endpoint: String? = null,
    val port: Int? = null,
    @SerialName("public_key") val publicKey: String? = null,
    @SerialName("private_key") val privateKey: String? = null,
    @SerialName("allowed_ips") val allowedIps: String? = null,
    val dns: String? = null,
)
