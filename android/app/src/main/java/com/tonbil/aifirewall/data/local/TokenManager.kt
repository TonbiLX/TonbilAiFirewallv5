package com.tonbil.aifirewall.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.time.LocalDate

class TokenManager(context: Context) {

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs: SharedPreferences = EncryptedSharedPreferences.create(
        context,
        PREFS_NAME,
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun saveToken(token: String) {
        prefs.edit().putString(KEY_TOKEN, token).apply()
    }

    fun getToken(): String? {
        return prefs.getString(KEY_TOKEN, null)
    }

    fun clearToken() {
        prefs.edit()
            .remove(KEY_TOKEN)
            .remove(KEY_USERNAME)
            .remove(KEY_DISPLAY_NAME)
            .apply()
    }

    fun saveUserInfo(username: String, displayName: String?) {
        prefs.edit()
            .putString(KEY_USERNAME, username)
            .putString(KEY_DISPLAY_NAME, displayName)
            .apply()
    }

    fun getUserInfo(): Pair<String, String?>? {
        val username = prefs.getString(KEY_USERNAME, null) ?: return null
        val displayName = prefs.getString(KEY_DISPLAY_NAME, null)
        return Pair(username, displayName)
    }

    fun isLoggedIn(): Boolean {
        return getToken() != null
    }

    fun setBiometricEnabled(enabled: Boolean) {
        prefs.edit().putBoolean(KEY_BIOMETRIC_ENABLED, enabled).apply()
    }

    fun isBiometricEnabled(): Boolean {
        return prefs.getBoolean(KEY_BIOMETRIC_ENABLED, false)
    }

    fun shouldShowSplashToday(): Boolean {
        val lastShown = prefs.getString(KEY_SPLASH_LAST_DATE, null)
        val today = LocalDate.now().toString()
        return lastShown != today
    }

    fun markSplashShownToday() {
        prefs.edit().putString(KEY_SPLASH_LAST_DATE, LocalDate.now().toString()).apply()
    }

    companion object {
        private const val PREFS_NAME = "tonbilai_secure_prefs"
        private const val KEY_TOKEN = "jwt_token"
        private const val KEY_USERNAME = "username"
        private const val KEY_DISPLAY_NAME = "display_name"
        private const val KEY_BIOMETRIC_ENABLED = "biometric_enabled"
        private const val KEY_SPLASH_LAST_DATE = "splash_last_date"
    }
}
