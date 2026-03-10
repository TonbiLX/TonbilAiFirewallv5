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

    private const val CHANNEL_ID = "security_alerts"
    private const val CHANNEL_NAME = "Guvenlik Bildirimleri"
    private const val CHANNEL_DESC = "DDoS, IP engelleme, yeni cihaz ve AI guvenlik bildirimleri"

    private var notificationId = 1000

    fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = CHANNEL_DESC
                enableVibration(true)
                enableLights(true)
            }
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
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

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
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
