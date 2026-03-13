package com.tonbil.aifirewall.util

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.tonbil.aifirewall.MainActivity
import com.tonbil.aifirewall.R
import com.tonbil.aifirewall.data.remote.dto.SecurityEventDto

object NotificationHelper {

    // Geriye uyumluluk icin eski kanal ID korunuyor
    private const val CHANNEL_ID_LEGACY = "security_alerts"

    // 4 bildirim kanali
    private const val CHANNEL_SECURITY_THREATS = "security_threats"
    private const val CHANNEL_DEVICE_EVENTS = "device_events"
    private const val CHANNEL_TRAFFIC_ALERTS = "traffic_alerts"
    private const val CHANNEL_SYSTEM_NOTIFICATIONS = "system_notifications"

    private var notificationId = 1000

    /**
     * 4 Android bildirim kanalini olusturur.
     * Eski kanal da korunur (backward compat icin).
     */
    fun createNotificationChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = context.getSystemService(NotificationManager::class.java)

            // Eski kanalı koru (backward compat)
            val legacyChannel = NotificationChannel(
                CHANNEL_ID_LEGACY,
                "Guvenlik Bildirimleri",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "Eski bildirim kanali (geriye uyumluluk)"
                enableVibration(true)
                enableLights(true)
            }

            // Tehdit Bildirimleri — yuksek onem, titresim + isik
            val securityChannel = NotificationChannel(
                CHANNEL_SECURITY_THREATS,
                "Tehdit Bildirimleri",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "DDoS saldirilari, IP engelleme ve guvenlik tehditleri"
                enableVibration(true)
                enableLights(true)
            }

            // Cihaz Bildirimleri — varsayilan onem
            val deviceChannel = NotificationChannel(
                CHANNEL_DEVICE_EVENTS,
                "Cihaz Bildirimleri",
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = "Yeni cihaz tespiti ve cihaz durumu degisiklikleri"
            }

            // Trafik Uyarilari — varsayilan onem
            val trafficChannel = NotificationChannel(
                CHANNEL_TRAFFIC_ALERTS,
                "Trafik Uyarilari",
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = "Bant genisligi asimi ve anormal trafik uyarilari"
            }

            // Sistem Bildirimleri — dusuk onem
            val systemChannel = NotificationChannel(
                CHANNEL_SYSTEM_NOTIFICATIONS,
                "Sistem Bildirimleri",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "Genel sistem durum bildirimleri"
            }

            manager.createNotificationChannels(
                listOf(legacyChannel, securityChannel, deviceChannel, trafficChannel, systemChannel)
            )
        }
    }

    /**
     * eventType'a gore dogru bildirim kanalini belirler.
     */
    private fun resolveChannelId(eventType: String): String {
        val lower = eventType.lowercase()
        return when {
            lower.contains("ddos") || lower.contains("threat") ||
                    lower.contains("block") || lower.contains("attack") -> CHANNEL_SECURITY_THREATS
            lower.contains("device") || lower.contains("new_device") -> CHANNEL_DEVICE_EVENTS
            lower.contains("traffic") || lower.contains("bandwidth") -> CHANNEL_TRAFFIC_ALERTS
            else -> CHANNEL_SYSTEM_NOTIFICATIONS
        }
    }

    fun showSecurityNotification(context: Context, event: SecurityEventDto) {
        val intent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            context, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val priority = when (event.severity) {
            "critical" -> NotificationCompat.PRIORITY_HIGH
            "warning" -> NotificationCompat.PRIORITY_DEFAULT
            else -> NotificationCompat.PRIORITY_LOW
        }

        // eventType'a gore dogru kanali sec
        val channelId = resolveChannelId(event.eventType)

        val builder = NotificationCompat.Builder(context, channelId)
        builder.setSmallIcon(R.drawable.ic_splash_logo)
        builder.setContentTitle(event.title)
        builder.setContentText(event.message)
        builder.setStyle(NotificationCompat.BigTextStyle().bigText(event.message))
        builder.priority = priority
        builder.setContentIntent(pendingIntent)
        builder.setAutoCancel(true)
        builder.setVibrate(longArrayOf(0, 300, 100, 300))

        try {
            NotificationManagerCompat.from(context).notify(notificationId++, builder.build())
        } catch (_: SecurityException) {
            // Bildirim izni verilmemis
        }
    }
}
