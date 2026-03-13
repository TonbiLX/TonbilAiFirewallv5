package com.tonbil.aifirewall.widget

import android.content.Context
import androidx.compose.ui.graphics.Color
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.GlanceTheme
import androidx.glance.action.actionStartActivity
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.provideContent
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.padding
import androidx.glance.layout.width
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import com.tonbil.aifirewall.MainActivity
import kotlinx.coroutines.flow.first

// Widget'a ozel DataStore — "server_config" ile karismasin
val Context.widgetDataStore: DataStore<Preferences> by preferencesDataStore(name = "tonbil_widget")

class TonbilWidget : GlanceAppWidget() {

    companion object {
        val DEVICE_COUNT_KEY = intPreferencesKey("widget_device_count")
        val BLOCKED_COUNT_KEY = intPreferencesKey("widget_blocked_count")
        val LAST_THREAT_KEY = stringPreferencesKey("widget_last_threat")
        val BANDWIDTH_KEY = stringPreferencesKey("widget_bandwidth")

        // Cyberpunk renk paleti
        private val ColorBg = Color(0xFF0D001A)
        private val ColorCyan = Color(0xFF00F0FF)
        private val ColorRed = Color(0xFFFF003C)
        private val ColorGreen = Color(0xFF39FF14)
        private val ColorAmber = Color(0xFFFFB800)
        private val ColorWhite = Color(0xFFFFFFFF)
        private val ColorGray = Color(0xFF888888)
    }

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        // DataStore'dan widget verilerini oku
        val prefs = context.widgetDataStore.data.first()
        val deviceCount = prefs[DEVICE_COUNT_KEY] ?: 0
        val blockedCount = prefs[BLOCKED_COUNT_KEY] ?: 0
        val lastThreat = prefs[LAST_THREAT_KEY] ?: "-"
        val bandwidth = prefs[BANDWIDTH_KEY] ?: "0 Mbps"

        provideContent {
            GlanceTheme {
                Column(
                    modifier = GlanceModifier
                        .fillMaxSize()
                        .background(ColorProvider(ColorBg))
                        .padding(horizontal = 12, vertical = 8)
                        .clickable(actionStartActivity<MainActivity>()),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Baslik
                    Text(
                        text = "TonbilAiOS",
                        style = TextStyle(
                            color = ColorProvider(ColorCyan),
                            fontWeight = FontWeight.Bold
                        )
                    )

                    Spacer(modifier = GlanceModifier.padding(top = 4))

                    // Istatistikler satiri
                    Row(
                        modifier = GlanceModifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        // Cihaz sayisi
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(
                                text = "$deviceCount",
                                style = TextStyle(
                                    color = ColorProvider(ColorWhite),
                                    fontWeight = FontWeight.Bold
                                )
                            )
                            Text(
                                text = "Cihaz",
                                style = TextStyle(color = ColorProvider(ColorGray))
                            )
                        }

                        Spacer(modifier = GlanceModifier.width(16))

                        // Engellenen sorgu
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(
                                text = "$blockedCount",
                                style = TextStyle(
                                    color = ColorProvider(ColorAmber),
                                    fontWeight = FontWeight.Bold
                                )
                            )
                            Text(
                                text = "Engellenen",
                                style = TextStyle(color = ColorProvider(ColorGray))
                            )
                        }

                        Spacer(modifier = GlanceModifier.width(16))

                        // Bandwidth
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(
                                text = bandwidth,
                                style = TextStyle(
                                    color = ColorProvider(ColorGreen),
                                    fontWeight = FontWeight.Bold
                                )
                            )
                            Text(
                                text = "Bant Genisligi",
                                style = TextStyle(color = ColorProvider(ColorGray))
                            )
                        }
                    }

                    Spacer(modifier = GlanceModifier.padding(top = 4))

                    // Son tehdit
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "Son Tehdit: ",
                            style = TextStyle(color = ColorProvider(ColorGray))
                        )
                        Text(
                            text = lastThreat,
                            style = TextStyle(color = ColorProvider(ColorRed))
                        )
                    }
                }
            }
        }
    }
}
