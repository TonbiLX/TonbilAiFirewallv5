package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.put
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class SecurityRepository(private val client: HttpClient) {

    // ========== DNS ==========

    suspend fun getDnsStats(): Result<DnsStatsDto> = runCatching {
        client.get(ApiRoutes.DNS_STATS).body()
    }

    suspend fun getBlocklists(): Result<List<BlocklistDto>> = runCatching {
        client.get(ApiRoutes.DNS_BLOCKLISTS).body()
    }

    suspend fun createBlocklist(dto: BlocklistCreateDto): Result<BlocklistDto> = runCatching {
        client.post(ApiRoutes.DNS_BLOCKLISTS) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun toggleBlocklist(id: Int): Result<BlocklistDto> = runCatching {
        client.post(ApiRoutes.blocklistToggle(id)).body()
    }

    suspend fun deleteBlocklist(id: Int): Result<Unit> = runCatching {
        client.delete(ApiRoutes.blocklistDetail(id))
    }

    suspend fun getDnsRules(): Result<List<DnsRuleDto>> = runCatching {
        client.get(ApiRoutes.DNS_RULES).body()
    }

    suspend fun createDnsRule(dto: DnsRuleCreateDto): Result<DnsRuleDto> = runCatching {
        client.post(ApiRoutes.DNS_RULES) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteDnsRule(id: Int): Result<Unit> = runCatching {
        client.delete(ApiRoutes.dnsRuleDetail(id))
    }

    // ========== FIREWALL ==========

    suspend fun getFirewallStats(): Result<FirewallStatsDto> = runCatching {
        client.get(ApiRoutes.FIREWALL_STATS).body()
    }

    suspend fun getConnectionCount(): Result<ConnectionCountDto> = runCatching {
        client.get(ApiRoutes.FIREWALL_CONNECTIONS_COUNT).body()
    }

    suspend fun getFirewallRules(): Result<List<FirewallRuleDto>> = runCatching {
        client.get(ApiRoutes.FIREWALL_RULES).body()
    }

    suspend fun createFirewallRule(dto: FirewallRuleCreateDto): Result<FirewallRuleDto> = runCatching {
        client.post(ApiRoutes.FIREWALL_RULES) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun updateFirewallRule(id: Int, dto: FirewallRuleCreateDto): Result<FirewallRuleDto> = runCatching {
        client.patch(ApiRoutes.firewallRuleDetail(id)) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteFirewallRule(id: Int): Result<Unit> = runCatching {
        client.delete(ApiRoutes.firewallRuleDetail(id))
    }

    suspend fun toggleFirewallRule(id: Int): Result<FirewallRuleDto> = runCatching {
        client.post(ApiRoutes.firewallRuleToggle(id)).body()
    }

    // ========== VPN ==========

    suspend fun getVpnStats(): Result<VpnStatsDto> = runCatching {
        client.get(ApiRoutes.VPN_STATS).body()
    }

    suspend fun getVpnPeers(): Result<List<VpnPeerDto>> = runCatching {
        client.get(ApiRoutes.VPN_PEERS).body()
    }

    suspend fun startVpn(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.VPN_START).body()
    }

    suspend fun stopVpn(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.VPN_STOP).body()
    }

    suspend fun addVpnPeer(dto: VpnPeerCreateDto): Result<VpnPeerDto> = runCatching {
        client.post(ApiRoutes.VPN_PEERS) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteVpnPeer(name: String): Result<Unit> = runCatching {
        client.delete(ApiRoutes.vpnPeerDelete(name))
    }

    suspend fun getVpnPeerConfig(name: String): Result<VpnPeerConfigDto> = runCatching {
        client.get(ApiRoutes.vpnPeerConfig(name)).body()
    }

    // ========== DDoS ==========

    suspend fun getDdosStatus(): Result<List<DdosProtectionStatusDto>> = runCatching {
        client.get(ApiRoutes.DDOS_STATUS).body()
    }

    suspend fun getDdosCounters(): Result<DdosCountersDto> = runCatching {
        client.get(ApiRoutes.DDOS_COUNTERS).body()
    }

    // ========== SECURITY CONFIG ==========

    suspend fun getSecurityStats(): Result<SecurityStatsDto> = runCatching {
        client.get(ApiRoutes.SECURITY_STATS).body()
    }

    // ========== DHCP ==========

    suspend fun getDhcpStats(): Result<DhcpStatsDto> = runCatching {
        client.get(ApiRoutes.DHCP_STATS).body()
    }

    suspend fun getDhcpLeases(): Result<List<DhcpLeaseDto>> = runCatching {
        client.get(ApiRoutes.DHCP_LEASES_LIVE).body()
    }

    suspend fun createStaticLease(dto: DhcpStaticLeaseCreateDto): Result<DhcpLeaseDto> = runCatching {
        client.post(ApiRoutes.DHCP_LEASES_STATIC) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteStaticLease(mac: String): Result<Unit> = runCatching {
        client.delete(ApiRoutes.dhcpStaticLeaseDelete(mac))
    }

    // ========== TRAFFIC ==========

    suspend fun getLiveFlows(): Result<List<LiveFlowDto>> = runCatching {
        client.get(ApiRoutes.TRAFFIC_FLOWS_LIVE).body()
    }

    suspend fun getFlowStats(): Result<FlowStatsDto> = runCatching {
        client.get(ApiRoutes.TRAFFIC_FLOWS_STATS).body()
    }

    // ========== AI INSIGHTS ==========

    suspend fun getInsights(): Result<List<AiInsightDto>> = runCatching {
        client.get(ApiRoutes.INSIGHTS).body()
    }

    // ========== WIFI ==========

    suspend fun getWifiStatus(): Result<WifiStatusDto> = runCatching {
        client.get(ApiRoutes.WIFI_STATUS).body()
    }

    suspend fun getWifiClients(): Result<List<WifiClientDto>> = runCatching {
        client.get(ApiRoutes.WIFI_CLIENTS).body()
    }

    suspend fun enableWifi(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.WIFI_ENABLE).body()
    }

    suspend fun disableWifi(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.WIFI_DISABLE).body()
    }

    suspend fun updateWifiConfig(dto: WifiConfigUpdateDto): Result<WifiStatusDto> = runCatching {
        client.put(ApiRoutes.WIFI_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    // ========== TELEGRAM ==========

    suspend fun getTelegramConfig(): Result<TelegramConfigDto> = runCatching {
        client.get(ApiRoutes.TELEGRAM_CONFIG).body()
    }

    suspend fun updateTelegramConfig(dto: TelegramConfigUpdateDto): Result<TelegramConfigDto> = runCatching {
        client.put(ApiRoutes.TELEGRAM_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun testTelegram(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.TELEGRAM_TEST).body()
    }

    // ========== SYSTEM ==========

    suspend fun getSystemOverview(): Result<SystemOverviewDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_OVERVIEW).body()
    }

    suspend fun getSystemServices(): Result<List<ServiceStatusDto>> = runCatching {
        client.get(ApiRoutes.SYSTEM_SERVICES).body()
    }

    // ========== PROFILES ==========

    suspend fun getProfiles(): Result<List<ProfileResponseDto>> = runCatching {
        client.get(ApiRoutes.PROFILES).body()
    }

    suspend fun createProfile(dto: ProfileCreateDto): Result<ProfileResponseDto> = runCatching {
        client.post(ApiRoutes.PROFILES) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun updateProfile(id: Int, dto: ProfileCreateDto): Result<ProfileResponseDto> = runCatching {
        client.patch(ApiRoutes.profileDetail(id)) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteProfile(id: Int): Result<Unit> = runCatching {
        client.delete(ApiRoutes.profileDetail(id))
    }

    // ========== CHAT ==========

    suspend fun sendChat(message: String): Result<ChatResponseDto> = runCatching {
        client.post(ApiRoutes.CHAT_SEND) {
            contentType(ContentType.Application.Json)
            setBody(ChatSendDto(message))
        }.body()
    }

    suspend fun getChatHistory(): Result<List<ChatMessageDto>> = runCatching {
        client.get(ApiRoutes.CHAT_HISTORY).body()
    }
}
