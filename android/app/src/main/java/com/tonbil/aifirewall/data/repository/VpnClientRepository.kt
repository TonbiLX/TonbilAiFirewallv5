package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.request.url
import io.ktor.http.ContentType
import io.ktor.http.contentType

class VpnClientRepository(private val client: HttpClient) {

    suspend fun getServers(): Result<List<VpnClientServerDto>> = runCatching {
        client.get(ApiRoutes.VPN_CLIENT_SERVERS).body()
    }

    suspend fun createServer(dto: VpnClientCreateDto): Result<VpnClientServerDto> = runCatching {
        client.post(ApiRoutes.VPN_CLIENT_SERVERS) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun importServer(dto: VpnClientImportDto): Result<VpnClientServerDto> = runCatching {
        client.post(ApiRoutes.VPN_CLIENT_IMPORT) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun updateServer(id: Int, dto: VpnClientUpdateDto): Result<VpnClientServerDto> = runCatching {
        client.patch(ApiRoutes.vpnClientServerDetail(id)) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun deleteServer(id: Int): Result<Unit> = runCatching {
        client.delete(ApiRoutes.vpnClientServerDetail(id))
    }

    suspend fun activate(id: Int): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.vpnClientActivate(id)).body()
    }

    suspend fun deactivate(id: Int): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.vpnClientDeactivate(id)).body()
    }

    suspend fun getStatus(): Result<VpnClientStatusDto> = runCatching {
        client.get(ApiRoutes.VPN_CLIENT_STATUS).body()
    }

    suspend fun getStats(): Result<VpnClientStatsDto> = runCatching {
        client.get(ApiRoutes.VPN_CLIENT_STATS).body()
    }
}
