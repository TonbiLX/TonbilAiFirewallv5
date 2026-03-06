package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.ConnectionCountDto
import com.tonbil.aifirewall.data.remote.dto.DdosCountersDto
import com.tonbil.aifirewall.data.remote.dto.DdosProtectionStatusDto
import com.tonbil.aifirewall.data.remote.dto.DhcpLeaseDto
import com.tonbil.aifirewall.data.remote.dto.DhcpStatsDto
import com.tonbil.aifirewall.data.remote.dto.DnsStatsDto
import com.tonbil.aifirewall.data.remote.dto.FirewallStatsDto
import com.tonbil.aifirewall.data.remote.dto.SecurityStatsDto
import com.tonbil.aifirewall.data.remote.dto.VpnPeerDto
import com.tonbil.aifirewall.data.remote.dto.VpnStatsDto
import com.tonbil.aifirewall.data.remote.dto.BlocklistDto
import com.tonbil.aifirewall.data.remote.dto.DnsRuleDto
import com.tonbil.aifirewall.data.remote.dto.FirewallRuleDto
import com.tonbil.aifirewall.data.remote.dto.LiveFlowDto
import com.tonbil.aifirewall.data.remote.dto.FlowStatsDto
import com.tonbil.aifirewall.data.remote.dto.AiInsightDto
import com.tonbil.aifirewall.data.remote.dto.WifiStatusDto
import com.tonbil.aifirewall.data.remote.dto.WifiClientDto
import com.tonbil.aifirewall.data.remote.dto.TelegramConfigDto
import com.tonbil.aifirewall.data.remote.dto.SystemOverviewDto
import com.tonbil.aifirewall.data.remote.dto.ServiceStatusDto
import com.tonbil.aifirewall.data.remote.dto.ProfileResponseDto
import com.tonbil.aifirewall.data.remote.dto.ChatSendDto
import com.tonbil.aifirewall.data.remote.dto.ChatResponseDto
import com.tonbil.aifirewall.data.remote.dto.ChatMessageDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class SecurityRepository(private val client: HttpClient) {

    suspend fun getDnsStats(): Result<DnsStatsDto> = runCatching {
        client.get(ApiRoutes.DNS_STATS).body()
    }

    suspend fun getFirewallStats(): Result<FirewallStatsDto> = runCatching {
        client.get(ApiRoutes.FIREWALL_STATS).body()
    }

    suspend fun getConnectionCount(): Result<ConnectionCountDto> = runCatching {
        client.get(ApiRoutes.FIREWALL_CONNECTIONS_COUNT).body()
    }

    suspend fun getVpnStats(): Result<VpnStatsDto> = runCatching {
        client.get(ApiRoutes.VPN_STATS).body()
    }

    suspend fun getVpnPeers(): Result<List<VpnPeerDto>> = runCatching {
        client.get(ApiRoutes.VPN_PEERS).body()
    }

    suspend fun getDdosStatus(): Result<List<DdosProtectionStatusDto>> = runCatching {
        client.get(ApiRoutes.DDOS_STATUS).body()
    }

    suspend fun getDdosCounters(): Result<DdosCountersDto> = runCatching {
        client.get(ApiRoutes.DDOS_COUNTERS).body()
    }

    suspend fun getSecurityStats(): Result<SecurityStatsDto> = runCatching {
        client.get(ApiRoutes.SECURITY_STATS).body()
    }

    suspend fun getDhcpStats(): Result<DhcpStatsDto> = runCatching {
        client.get(ApiRoutes.DHCP_STATS).body()
    }

    suspend fun getDhcpLeases(): Result<List<DhcpLeaseDto>> = runCatching {
        client.get(ApiRoutes.DHCP_LEASES_LIVE).body()
    }

    // DNS management
    suspend fun getBlocklists(): Result<List<BlocklistDto>> = runCatching {
        client.get(ApiRoutes.DNS_BLOCKLISTS).body()
    }

    suspend fun getDnsRules(): Result<List<DnsRuleDto>> = runCatching {
        client.get(ApiRoutes.DNS_RULES).body()
    }

    // Firewall rules
    suspend fun getFirewallRules(): Result<List<FirewallRuleDto>> = runCatching {
        client.get(ApiRoutes.FIREWALL_RULES).body()
    }

    // Traffic flows
    suspend fun getLiveFlows(): Result<List<LiveFlowDto>> = runCatching {
        client.get(ApiRoutes.TRAFFIC_FLOWS_LIVE).body()
    }

    suspend fun getFlowStats(): Result<FlowStatsDto> = runCatching {
        client.get(ApiRoutes.TRAFFIC_FLOWS_STATS).body()
    }

    // AI Insights
    suspend fun getInsights(): Result<List<AiInsightDto>> = runCatching {
        client.get(ApiRoutes.INSIGHTS).body()
    }

    // WiFi
    suspend fun getWifiStatus(): Result<WifiStatusDto> = runCatching {
        client.get(ApiRoutes.WIFI_STATUS).body()
    }

    suspend fun getWifiClients(): Result<List<WifiClientDto>> = runCatching {
        client.get(ApiRoutes.WIFI_CLIENTS).body()
    }

    // Telegram
    suspend fun getTelegramConfig(): Result<TelegramConfigDto> = runCatching {
        client.get(ApiRoutes.TELEGRAM_CONFIG).body()
    }

    // System
    suspend fun getSystemOverview(): Result<SystemOverviewDto> = runCatching {
        client.get(ApiRoutes.SYSTEM_OVERVIEW).body()
    }

    suspend fun getSystemServices(): Result<List<ServiceStatusDto>> = runCatching {
        client.get(ApiRoutes.SYSTEM_SERVICES).body()
    }

    // Profiles
    suspend fun getProfiles(): Result<List<ProfileResponseDto>> = runCatching {
        client.get(ApiRoutes.PROFILES).body()
    }

    // Chat
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
