package com.tonbil.aifirewall.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.tonbil.aifirewall.data.remote.ApiRoutes
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "server_config")

class ServerConfig(private val context: Context) {

    val serverUrlFlow: Flow<String> = context.dataStore.data.map { prefs ->
        prefs[SERVER_URL] ?: ApiRoutes.BASE_URL
    }

    suspend fun setServerUrl(url: String) {
        context.dataStore.edit { prefs ->
            prefs[SERVER_URL] = url
        }
    }

    fun isOnboardingCompleted(): Flow<Boolean> = context.dataStore.data.map { prefs ->
        prefs[ONBOARDING_COMPLETED] ?: false
    }

    suspend fun setOnboardingCompleted() {
        context.dataStore.edit { prefs ->
            prefs[ONBOARDING_COMPLETED] = true
        }
    }

    fun getLastConnectedUrl(): Flow<String?> = context.dataStore.data.map { prefs ->
        prefs[LAST_CONNECTED_URL]
    }

    suspend fun setLastConnectedUrl(url: String) {
        context.dataStore.edit { prefs ->
            prefs[LAST_CONNECTED_URL] = url
        }
    }

    companion object {
        private val SERVER_URL = stringPreferencesKey("SERVER_URL")
        private val ONBOARDING_COMPLETED = booleanPreferencesKey("ONBOARDING_COMPLETED")
        private val LAST_CONNECTED_URL = stringPreferencesKey("LAST_CONNECTED_URL")
    }
}
