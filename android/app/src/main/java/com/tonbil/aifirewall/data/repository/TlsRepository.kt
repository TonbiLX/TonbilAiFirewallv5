package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.patch
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType

class TlsRepository(private val client: HttpClient) {

    suspend fun getConfig(): Result<TlsConfigDto> = runCatching {
        client.get(ApiRoutes.TLS_CONFIG).body()
    }

    suspend fun updateConfig(dto: TlsConfigUpdateDto): Result<TlsConfigDto> = runCatching {
        client.patch(ApiRoutes.TLS_CONFIG) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun validate(dto: TlsValidateDto): Result<TlsValidateResponseDto> = runCatching {
        client.post(ApiRoutes.TLS_VALIDATE) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    // Multipart yerine JSON body kullaniliyor (basitlestirilmis)
    suspend fun uploadCert(cert: String, key: String): Result<TlsUploadResponseDto> = runCatching {
        client.post(ApiRoutes.TLS_UPLOAD) {
            contentType(ContentType.Application.Json)
            setBody(TlsValidateDto(cert = cert, key = key))
        }.body()
    }

    suspend fun letsEncrypt(dto: TlsLetsEncryptDto): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.TLS_LETSENCRYPT) {
            contentType(ContentType.Application.Json)
            setBody(dto)
        }.body()
    }

    suspend fun toggle(): Result<MessageResponseDto> = runCatching {
        client.post(ApiRoutes.TLS_TOGGLE).body()
    }
}
