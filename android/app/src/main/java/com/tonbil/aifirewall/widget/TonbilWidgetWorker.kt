package com.tonbil.aifirewall.widget

import android.content.Context
import android.util.Log
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStoreFile
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.tonbil.aifirewall.data.remote.dto.DashboardSummaryDto
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.flow.first
import kotlinx.serialization.json.Json

class TonbilWidgetWorker(
    private val context: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(context, workerParams) {

    companion object {
        private const val TAG = "TonbilWidgetWorker"
        private const val PREFS_NAME = "tonbilai_secure_prefs"
        private const val KEY_TOKEN = "jwt_token"
        private val SERVER_URL_KEY = stringPreferencesKey("SERVER_URL")
        private val LAST_CONNECTED_KEY = stringPreferencesKey("LAST_CONNECTED_URL")
        private const val BASE_URL = "http://wall.tonbilx.com/api/v1/"
    }

    override suspend fun doWork(): Result {
        return try {
            // Token'i EncryptedSharedPreferences'tan oku
            val masterKey = MasterKey.Builder(context)
                .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                .build()

            val securePrefs = EncryptedSharedPreferences.create(
                context,
                PREFS_NAME,
                masterKey,
                EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
            val token = securePrefs.getString(KEY_TOKEN, null)

            if (token.isNullOrBlank()) {
                Log.d(TAG, "Token yok, widget placeholder yaziliyor")
                writeWidgetData(deviceCount = 0, blockedCount = 0, lastThreat = "Giris yap", bandwidth = "-")
                return Result.success()
            }

            // server_config DataStore'dan son URL'yi oku
            val baseUrl = readServerUrl() ?: BASE_URL

            // Ktor client — Koin kullanmadan dogrudan olustur
            val client = HttpClient(OkHttp) {
                install(ContentNegotiation) {
                    json(Json {
                        ignoreUnknownKeys = true
                        isLenient = true
                        coerceInputValues = true
                    })
                }
            }

            try {
                val url = "${baseUrl}dashboard/summary"
                Log.d(TAG, "Widget guncelleme: $url")

                val summary: DashboardSummaryDto = client.get(url) {
                    header("Authorization", "Bearer $token")
                }.body()

                val deviceCount = summary.devices.online
                val blockedCount = summary.dns.blockedQueries24h
                val lastThreat = summary.topBlockedDomains.firstOrNull()?.domain ?: "-"
                val bandwidth = "${summary.dns.totalQueries24h} sorgu/gun"

                writeWidgetData(deviceCount, blockedCount, lastThreat, bandwidth)

                // Aktif tum widget instance'larini guncelle
                val glanceIds = androidx.glance.appwidget.GlanceAppWidgetManager(context)
                    .getGlanceIds(TonbilWidget::class.java)
                glanceIds.forEach { glanceId ->
                    TonbilWidget().update(context, glanceId)
                }

                Log.d(TAG, "Widget guncellendi: $deviceCount cihaz, $blockedCount engellenen")
                Result.success()
            } finally {
                client.close()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Widget guncelleme hatasi: ${e.message}")
            Result.retry()
        }
    }

    private suspend fun writeWidgetData(
        deviceCount: Int,
        blockedCount: Int,
        lastThreat: String,
        bandwidth: String
    ) {
        context.widgetDataStore.edit { prefs ->
            prefs[TonbilWidget.DEVICE_COUNT_KEY] = deviceCount
            prefs[TonbilWidget.BLOCKED_COUNT_KEY] = blockedCount
            prefs[TonbilWidget.LAST_THREAT_KEY] = lastThreat
            prefs[TonbilWidget.BANDWIDTH_KEY] = bandwidth
        }
    }

    /**
     * server_config DataStore'dan sunucu URL'sini oku.
     * preferencesDataStore extension'i tek bir Context uzantisi olarak tanimlanabilir,
     * bu yuzden burada DataStoreFactory kullanarak dosyayi direkt aciyoruz.
     */
    private suspend fun readServerUrl(): String? {
        return try {
            val dataStoreFile = context.preferencesDataStoreFile("server_config")
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
