package com.tonbil.aifirewall.data.remote

import com.tonbil.aifirewall.data.local.TokenManager
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.HttpRequestRetry
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.api.createClientPlugin
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.http.ContentType
import io.ktor.http.Url
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

fun createHttpClient(
    serverDiscovery: ServerDiscovery,
    tokenManager: TokenManager
): HttpClient {
    return HttpClient(OkHttp) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
                coerceInputValues = true
                prettyPrint = false
            })
        }

        install(Logging) {
            level = LogLevel.HEADERS
        }

        install(HttpTimeout) {
            requestTimeoutMillis = 15_000
            connectTimeoutMillis = 10_000
            socketTimeoutMillis = 15_000
        }

        install(HttpRequestRetry) {
            retryOnServerErrors(maxRetries = 2)
            retryOnException(maxRetries = 2, retryOnTimeout = true)
            exponentialDelay()
            modifyRequest { request ->
                val newUrl = serverDiscovery.getActiveUrl()
                if (newUrl.isNotEmpty()) {
                    val parsed = Url(newUrl)
                    request.url.protocol = parsed.protocol
                    request.url.host = parsed.host
                    request.url.port = parsed.port
                }
            }
        }

        install(WebSockets)

        install(authInterceptorPlugin(tokenManager))

        val dynamicBaseUrlPlugin = createClientPlugin("DynamicBaseUrl") {
            onRequest { request, _ ->
                var baseUrl = serverDiscovery.activeUrl
                if (baseUrl.isEmpty()) {
                    baseUrl = serverDiscovery.getActiveUrl()
                }
                if (baseUrl.isNotEmpty()) {
                    val parsed = Url(baseUrl)
                    request.url.protocol = parsed.protocol
                    request.url.host = parsed.host
                    request.url.port = parsed.port
                }
            }
        }
        install(dynamicBaseUrlPlugin)

        defaultRequest {
            contentType(ContentType.Application.Json)
        }
    }
}

fun createTestHttpClient(): HttpClient {
    return HttpClient(OkHttp) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
                coerceInputValues = true
            })
        }

        install(HttpTimeout) {
            requestTimeoutMillis = 5_000
            connectTimeoutMillis = 3_000
        }
    }
}
