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
    }

    onResponse { response ->
        if (response.status == HttpStatusCode.Unauthorized) {
            val requestUrl = response.call.request.url.toString()
            if (requestUrl.contains("auth/login")) {
                tokenManager.clearToken()
            }
        }
    }
}
