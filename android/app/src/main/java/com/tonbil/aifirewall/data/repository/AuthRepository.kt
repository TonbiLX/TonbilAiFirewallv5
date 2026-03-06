package com.tonbil.aifirewall.data.repository

import com.tonbil.aifirewall.data.local.TokenManager
import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.LoginRequest
import com.tonbil.aifirewall.data.remote.dto.LoginResponse
import com.tonbil.aifirewall.data.remote.dto.UserInfo
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody

class AuthRepository(
    private val httpClient: HttpClient,
    private val tokenManager: TokenManager
) {
    suspend fun login(username: String, password: String): Result<LoginResponse> {
        return try {
            val response: LoginResponse = httpClient.post(ApiRoutes.AUTH_LOGIN) {
                setBody(LoginRequest(username = username, password = password))
            }.body()

            tokenManager.saveToken(response.accessToken)
            tokenManager.saveUserInfo(response.username, response.displayName)

            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getCurrentUser(): Result<UserInfo> {
        return try {
            val user: UserInfo = httpClient.get(ApiRoutes.AUTH_ME).body()
            Result.success(user)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun logout(): Result<Unit> {
        return try {
            httpClient.post(ApiRoutes.AUTH_LOGOUT)
            tokenManager.clearToken()
            Result.success(Unit)
        } catch (e: Exception) {
            tokenManager.clearToken()
            Result.failure(e)
        }
    }

    fun isLoggedIn(): Boolean = tokenManager.isLoggedIn()

    fun getStoredUserInfo(): Pair<String, String?>? = tokenManager.getUserInfo()
}
