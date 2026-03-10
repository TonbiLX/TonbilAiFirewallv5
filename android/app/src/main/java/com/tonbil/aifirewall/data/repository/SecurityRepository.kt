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
        val resp: SystemMetricsResponseDto = client.get(ApiRoutes.SYSTEM_METRICS).body()
        val c = resp.current
        val uptimeSec = c.uptimeSeconds.toLong()
        val hours = uptimeSec / 3600
        val minutes = (uptimeSec % 3600) / 60
        val uptimeStr = if (hours > 24) {
            val days = hours / 24
            val remHours = hours % 24
            "${days}g ${remHours}s ${minutes}dk"
        } else {
            "${hours}s ${minutes}dk"
        }
        SystemOverviewDto(
            uptime = uptimeStr,
            cpuPercent = c.cpu.usagePercent,
            memoryPercent = c.memory.usagePercent,
            memoryUsedMb = c.memory.usedMb.toInt(),
            memoryTotalMb = c.memory.totalMb.toInt(),
            diskPercent = c.disk.usagePercent,
            diskUsedGb = c.disk.usedGb,
            diskTotalGb = c.disk.totalGb,
            cpuTemp = c.cpu.temperatureC,
        )
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

    // ========== DDoS CONFIG ==========

    suspend fun getDdosConfig(): Result<DdosConfigDto> = runCatching {
        client.get(ApiRoutes.DDOS_CONFIG).body()
    }

    suspend fun updateDdosConfig(dto: DdosConfigUpdateDto): Result<DdosConfigDto> = runCatching {
        client.put(ApiRoutes.DDOS_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun applyDdos(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.DDOS_APPLY).body()
    }

    suspend fun toggleDdosProtection(name: String): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.ddosToggle(name)).body()
    }

    suspend fun flushAttackers(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.DDOS_FLUSH_ATTACKERS).body()
    }

    suspend fun getDdosAttackMap(): Result<DdosAttackMapDto> = runCatching {
        client.get(ApiRoutes.DDOS_ATTACK_MAP).body()
    }

    // ========== SECURITY CONFIG (full) ==========

    suspend fun getSecurityConfig(): Result<SecurityConfigDto> = runCatching {
        client.get(ApiRoutes.SECURITY_CONFIG).body()
    }

    suspend fun updateSecurityConfig(dto: SecurityConfigUpdateDto): Result<SecurityConfigDto> = runCatching {
        client.put(ApiRoutes.SECURITY_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun reloadSecurity(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.SECURITY_RELOAD).body()
    }

    suspend fun getSecurityDefaults(): Result<SecurityDefaultsDto> = runCatching {
        client.get(ApiRoutes.SECURITY_DEFAULTS).body()
    }

    suspend fun resetSecurity(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.SECURITY_RESET).body()
    }

    // ========== FIREWALL EXTENDED ==========

    suspend fun getFirewallScan(): Result<List<PortScanResultDto>> = runCatching {
        client.get(ApiRoutes.FIREWALL_SCAN).body()
    }

    suspend fun getFirewallConnections(): Result<List<FirewallConnectionDto>> = runCatching {
        client.get(ApiRoutes.FIREWALL_CONNECTIONS).body()
    }

    // ========== DNS EXTENDED ==========

    suspend fun getDnsQueries(page: Int = 1, pageSize: Int = 50, blocked: Boolean? = null): Result<DnsQueryPageDto> = runCatching {
        client.get(ApiRoutes.DNS_QUERIES) {
            url {
                parameters.append("page", page.toString())
                parameters.append("page_size", pageSize.toString())
                if (blocked != null) parameters.append("blocked", blocked.toString())
            }
        }.body()
    }

    suspend fun getDnsExternalSummary(): Result<DnsExternalSummaryDto> = runCatching {
        client.get(ApiRoutes.DNS_QUERIES_EXTERNAL_SUMMARY).body()
    }

    suspend fun dnsLookup(domain: String): Result<DnsLookupDto> = runCatching {
        client.get(ApiRoutes.dnsLookup(domain)).body()
    }

    suspend fun refreshBlocklist(id: Int): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.blocklistRefresh(id)).body()
    }

    suspend fun refreshAllBlocklists(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.DNS_BLOCKLISTS_REFRESH_ALL).body()
    }

    suspend fun updateBlocklist(id: Int, dto: BlocklistCreateDto): Result<BlocklistDto> = runCatching {
        client.patch(ApiRoutes.blocklistDetail(id)) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    // ========== DHCP EXTENDED ==========

    suspend fun getDhcpPools(): Result<List<DhcpPoolDto>> = runCatching {
        client.get(ApiRoutes.DHCP_POOLS).body()
    }

    suspend fun createDhcpPool(dto: DhcpPoolCreateDto): Result<DhcpPoolDto> = runCatching {
        client.post(ApiRoutes.DHCP_POOLS) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun updateDhcpPool(id: Int, dto: DhcpPoolCreateDto): Result<DhcpPoolDto> = runCatching {
        client.patch(ApiRoutes.dhcpPoolDetail(id)) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteDhcpPool(id: Int): Result<Unit> = runCatching {
        client.delete(ApiRoutes.dhcpPoolDetail(id))
    }

    suspend fun toggleDhcpPool(id: Int): Result<DhcpPoolDto> = runCatching {
        client.post(ApiRoutes.dhcpPoolToggle(id)).body()
    }

    suspend fun deleteDhcpLease(mac: String): Result<Unit> = runCatching {
        client.delete(ApiRoutes.dhcpLeaseDelete(mac))
    }

    // ========== WIFI EXTENDED ==========

    suspend fun getWifiChannels(): Result<List<WifiChannelDto>> = runCatching {
        client.get(ApiRoutes.WIFI_CHANNELS).body()
    }

    suspend fun getWifiGuest(): Result<WifiGuestConfigDto> = runCatching {
        client.get(ApiRoutes.WIFI_GUEST).body()
    }

    suspend fun updateWifiGuest(dto: WifiGuestConfigDto): Result<WifiGuestConfigDto> = runCatching {
        client.put(ApiRoutes.WIFI_GUEST) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun getWifiSchedule(): Result<WifiScheduleDto> = runCatching {
        client.get(ApiRoutes.WIFI_SCHEDULE).body()
    }

    suspend fun updateWifiSchedule(dto: WifiScheduleDto): Result<WifiScheduleDto> = runCatching {
        client.put(ApiRoutes.WIFI_SCHEDULE) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun getWifiMacFilter(): Result<WifiMacFilterDto> = runCatching {
        client.get(ApiRoutes.WIFI_MAC_FILTER).body()
    }

    suspend fun updateWifiMacFilter(dto: WifiMacFilterDto): Result<WifiMacFilterDto> = runCatching {
        client.put(ApiRoutes.WIFI_MAC_FILTER) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    // ========== TRAFFIC EXTENDED ==========

    suspend fun getTrafficPerDevice(): Result<List<TrafficPerDeviceDto>> = runCatching {
        client.get(ApiRoutes.TRAFFIC_PER_DEVICE).body()
    }

    suspend fun getLargeTransfers(): Result<List<LiveFlowDto>> = runCatching {
        client.get(ApiRoutes.TRAFFIC_LARGE_TRANSFERS).body()
    }

    suspend fun getTrafficHistory(page: Int = 1, pageSize: Int = 50): Result<TrafficHistoryDto> = runCatching {
        client.get(ApiRoutes.TRAFFIC_HISTORY) {
            url {
                parameters.append("page", page.toString())
                parameters.append("page_size", pageSize.toString())
            }
        }.body()
    }

    suspend fun getDeviceTrafficHistory(deviceId: Int): Result<List<Map<String, Any>>> = runCatching {
        client.get(ApiRoutes.deviceTrafficHistory(deviceId)).body()
    }

    suspend fun getDeviceConnections(deviceId: Int): Result<List<LiveFlowDto>> = runCatching {
        client.get(ApiRoutes.deviceTrafficConnections(deviceId)).body()
    }

    suspend fun getDeviceTopDestinations(deviceId: Int): Result<List<DeviceTopDestinationDto>> = runCatching {
        client.get(ApiRoutes.deviceTopDestinations(deviceId)).body()
    }

    // ========== CHAT EXTENDED ==========

    suspend fun clearChatHistory(): Result<MessageResponseDto> = runCatching {
        client.delete(ApiRoutes.CHAT_HISTORY_DELETE).body()
    }
}
