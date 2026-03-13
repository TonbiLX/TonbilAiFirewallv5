package com.tonbil.aifirewall.util

import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.content.pm.ShortcutInfoCompat
import androidx.core.content.pm.ShortcutManagerCompat
import androidx.core.graphics.drawable.IconCompat
import com.tonbil.aifirewall.MainActivity
import com.tonbil.aifirewall.R

/**
 * Dinamik uygulama kisayollarini kaydeder.
 *
 * Uygulama ikonu uzun basilinca 3 kisayol gorunur:
 *  - "status_check"  → Dashboard (Ag Durumu)
 *  - "device_block"  → Cihaz Yonetimi
 *  - "ai_chat"       → AI Asistan (Chat)
 *
 * Shortcut ID'leri sabit tutulur — pinned shortcut kaybolmasin.
 * ShortcutManagerCompat core-ktx (1.15.0) icerisinde — ek bagimlilik gerekmez.
 * Intent.ACTION_VIEW zorunlu — shortcut bos action kabul etmiyor.
 */
object ShortcutHelper {

    fun setupDynamicShortcuts(context: Context) {
        try {
            val shortcuts = listOf(
                buildShortcut(
                    context = context,
                    id = "status_check",
                    shortLabel = "Durum",
                    longLabel = "Ag Durumu",
                    navigateTo = "dashboard",
                ),
                buildShortcut(
                    context = context,
                    id = "device_block",
                    shortLabel = "Cihazlar",
                    longLabel = "Cihaz Yonetimi",
                    navigateTo = "devices",
                ),
                buildShortcut(
                    context = context,
                    id = "ai_chat",
                    shortLabel = "AI Chat",
                    longLabel = "AI Asistan",
                    navigateTo = "chat",
                ),
            )

            ShortcutManagerCompat.setDynamicShortcuts(context, shortcuts)
            Log.d("ShortcutHelper", "3 dinamik kisayol kaydedildi")
        } catch (e: Exception) {
            Log.e("ShortcutHelper", "Kisayol kurulumu basarisiz: ${e.message}")
        }
    }

    private fun buildShortcut(
        context: Context,
        id: String,
        shortLabel: String,
        longLabel: String,
        navigateTo: String,
    ): ShortcutInfoCompat {
        val intent = Intent(context, MainActivity::class.java).apply {
            action = Intent.ACTION_VIEW
            putExtra("navigate_to", navigateTo)
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        return ShortcutInfoCompat.Builder(context, id)
            .setShortLabel(shortLabel)
            .setLongLabel(longLabel)
            .setIcon(IconCompat.createWithResource(context, R.drawable.ic_splash_logo))
            .setIntent(intent)
            .build()
    }
}
