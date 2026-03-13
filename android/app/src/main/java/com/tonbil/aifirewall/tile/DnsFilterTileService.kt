package com.tonbil.aifirewall.tile

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import android.util.Log
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStoreFile
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.SecurityConfigDto
import com.tonbil.aifirewall.data.remote.dto.SecurityConfigUpdateDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.patch
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json

class DnsFilterTileService : TileService() {

    companion object {
        private const val TAG = "DnsFilterTile"
        private const val PREFS_NAME = "tonbilai_secure_prefs"
        private const val KEY_TOKEN = "jwt_token"
        private val SERVER_URL_KEY = stringPreferencesKey("SERVER_URL")
        private val LAST_CONNECTED_KEY = stringPreferencesKey("LAST_CONNECTED_URL")
        private const val BASE_URL = "http://wall.tonbilx.com/api/v1/"
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var currentDnsEnabled: Boolean? = null

    private val httpClient by lazy {
        HttpClient(OkHttp) {
            install(ContentNegotiation) {
                json(Json {
                    ignoreUnknownKeys = true
                    isLenient = true
                    coerceInputValues = true
                })
            }
        }
    }

    override fun onStartListening() {
        super.onStartListening()
        serviceScope.launch {
            try {
                val token = readToken() ?: run {
                    setTileUnavailable("Giris gerekli")
                    return@launch
                }
                val baseUrl = readServerUrl() ?: BASE_URL

                val config: SecurityConfigDto = httpClient.get("${baseUrl}${ApiRoutes.SECURITY_CONFIG}") {
                    header("Authorization", "Bearer $token")
                }.body()

                // Tum 4 DNS alani true ise aktif sayiyoruz
                val isActive = config.dnssecEnabled &&
                        config.dnsTunnelingEnabled &&
                        config.dohEnabled &&
                        config.threatAnalysis.dgaDetectionEnabled

                currentDnsEnabled = isActive
                updateTileState(isActive)
            } catch (e: Exception) {
                Log.e(TAG, "Config yuklenirken hata: ${e.message}")
                setTileUnavailable("Baglanti hatasi")
            }
        }
    }

    override fun onClick() {
        super.onClick()
        serviceScope.launch {
            try {
                val token = readToken() ?: run {
                    setTileUnavailable("Giris gerekli")
                    return@launch
                }
                val baseUrl = readServerUrl() ?: BASE_URL

                // Mevcut durumun tersini hesapla
                val currentState = currentDnsEnabled ?: false
                val newState = !currentState

                val updateDto = SecurityConfigUpdateDto(
                    dnssecEnabled = newState,
                    dnsTunnelingEnabled = newState,
                    dohEnabled = newState,
                    dgaDetectionEnabled = newState
                )

                httpClient.patch("${baseUrl}${ApiRoutes.SECURITY_CONFIG}") {
                    header("Authorization", "Bearer $token")
                    contentType(ContentType.Application.Json)
                    setBody(updateDto)
                }

                currentDnsEnabled = newState
                updateTileState(newState)
                Log.d(TAG, "DNS filtre: ${if (newState) "Acildi" else "Kapandi"}")
            } catch (e: Exception) {
                Log.e(TAG, "Toggle sirasinda hata: ${e.message}")
                // Hata durumunda orijinal state'e don
                currentDnsEnabled?.let { updateTileState(it) }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
        httpClient.close()
    }

    private fun updateTileState(isActive: Boolean) {
        qsTile?.let { tile ->
            tile.state = if (isActive) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
            tile.label = "DNS Filtre"
            tile.subtitle = if (isActive) "Acik" else "Kapali"
            tile.updateTile()
        }
    }

    private fun setTileUnavailable(subtitle: String) {
        qsTile?.let { tile ->
            tile.state = Tile.STATE_UNAVAILABLE
            tile.label = "DNS Filtre"
            tile.subtitle = subtitle
            tile.updateTile()
        }
    }

    private fun readToken(): String? {
        return try {
            val masterKey = MasterKey.Builder(applicationContext)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            val securePrefs = EncryptedSharedPreferences.create(
                applicationContext,
                PREFS_NAME,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
            securePrefs.getString(KEY_TOKEN, null)
        } catch (e: Exception) {
            Log.e(TAG, "Token okuma hatasi: ${e.message}")
            null
        }
    }

    private suspend fun readServerUrl(): String? {
        return try {
            val dataStoreFile = applicationContext.preferencesDataStoreFile("server_config")
            val serverConfigDs = androidx.datastore.preferences.core.PreferenceDataStoreFactory.create {
                dataStoreFile
            }
            val prefs = serverConfigDs.data.first()
            prefs[LAST_CONNECTED_KEY] ?: prefs[SERVER_URL_KEY]
        } catch (e: Exception) {
            Log.w(TAG, "server_config DataStore okunamadi: ${e.message}")
            null
        }
    }
}
