package com.tonbil.aifirewall.tile

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import android.util.Log
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStoreFile
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.tonbil.aifirewall.data.remote.ApiRoutes
import com.tonbil.aifirewall.data.remote.dto.DeviceResponseDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json

class DeviceBlockTileService : TileService() {

    companion object {
        private const val TAG = "DeviceBlockTile"
        private const val PREFS_NAME = "tonbilai_secure_prefs"
        private const val KEY_TOKEN = "jwt_token"
        private val SERVER_URL_KEY = stringPreferencesKey("SERVER_URL")
        private val LAST_CONNECTED_KEY = stringPreferencesKey("LAST_CONNECTED_URL")
        private const val BASE_URL = "http://wall.tonbilx.com/api/v1/"
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private var lastBlockedDeviceId: Int? = null
    private var lastBlockedDeviceName: String? = null

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

                // Cihaz listesini al ve engellenmis olanlari bul
                val devices: List<DeviceResponseDto> = httpClient.get("${baseUrl}${ApiRoutes.DEVICES}") {
                    header("Authorization", "Bearer $token")
                }.body()

                val blockedDevices = devices.filter { it.isBlocked }

                if (blockedDevices.isNotEmpty()) {
                    val firstBlocked = blockedDevices.first()
                    lastBlockedDeviceId = firstBlocked.id
                    lastBlockedDeviceName = firstBlocked.hostname
                        ?: firstBlocked.ipAddress
                        ?: "Cihaz #${firstBlocked.id}"

                    setTileActive(lastBlockedDeviceName!!)
                    Log.d(TAG, "${blockedDevices.size} engellenmis cihaz bulundu. Ilk: $lastBlockedDeviceName")
                } else {
                    lastBlockedDeviceId = null
                    lastBlockedDeviceName = null
                    setTileInactive("Engelli yok")
                    Log.d(TAG, "Engellenmis cihaz yok")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Cihaz listesi yuklenirken hata: ${e.message}")
                setTileUnavailable("Baglanti hatasi")
            }
        }
    }

    override fun onClick() {
        super.onClick()
        val deviceId = lastBlockedDeviceId
        val deviceName = lastBlockedDeviceName

        if (deviceId == null) {
            // Engellenmis cihaz yok — bilgi goster
            qsTile?.let { tile ->
                tile.subtitle = "Engelli cihaz yok"
                tile.updateTile()
            }
            return
        }

        serviceScope.launch {
            try {
                val token = readToken() ?: run {
                    setTileUnavailable("Giris gerekli")
                    return@launch
                }
                val baseUrl = readServerUrl() ?: BASE_URL

                // Cihaz engelini kaldir
                httpClient.post("${baseUrl}${ApiRoutes.deviceUnblock(deviceId)}") {
                    header("Authorization", "Bearer $token")
                }

                lastBlockedDeviceId = null
                lastBlockedDeviceName = null
                setTileInactive("Engel kaldirildi")
                Log.d(TAG, "Cihaz engeli kaldirildi: $deviceName (id=$deviceId)")
            } catch (e: Exception) {
                Log.e(TAG, "Engel kaldirma hatasi: ${e.message}")
                // Hata durumunda orijinal duruma don
                deviceName?.let { setTileActive(it) }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
        httpClient.close()
    }

    private fun setTileActive(subtitle: String) {
        qsTile?.let { tile ->
            tile.state = Tile.STATE_ACTIVE
            tile.label = "Cihaz Engel"
            tile.subtitle = subtitle
            tile.updateTile()
        }
    }

    private fun setTileInactive(subtitle: String) {
        qsTile?.let { tile ->
            tile.state = Tile.STATE_INACTIVE
            tile.label = "Cihaz Engel"
            tile.subtitle = subtitle
            tile.updateTile()
        }
    }

    private fun setTileUnavailable(subtitle: String) {
        qsTile?.let { tile ->
            tile.state = Tile.STATE_UNAVAILABLE
            tile.label = "Cihaz Engel"
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
