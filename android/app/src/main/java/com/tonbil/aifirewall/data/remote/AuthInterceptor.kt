package com.tonbil.aifirewall.data.remote

import com.tonbil.aifirewall.data.local.TokenManager
import io.ktor.client.plugins.api.createClientPlugin
import io.ktor.http.HttpStatusCode

fun authInterceptorPlugin(tokenManager: TokenManager) = createClientPlugin("AuthInterceptor") {
    onRequest { request, _ ->
        val token = tokenManager.getToken()
        if (token != null) {
            request.headers.append("Authorization", "Bearer $token")
        }
        request.headers.append("User-Agent", "TonbilAiOS-Android/5.0.0")
    }

    onResponse { response ->
        if (response.status == HttpStatusCode.Unauthorized) {
            // Any 401 means token is invalid/expired — clear and force re-login
            tokenManager.clearToken()
        }
    }
}
