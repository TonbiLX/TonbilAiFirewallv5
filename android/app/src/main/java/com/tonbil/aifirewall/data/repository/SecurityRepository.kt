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
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get

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
}
