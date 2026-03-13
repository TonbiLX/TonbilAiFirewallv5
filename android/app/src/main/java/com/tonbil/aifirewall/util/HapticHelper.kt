package com.tonbil.aifirewall.util

import android.app.Activity
import android.view.HapticFeedbackConstants
import java.lang.ref.WeakReference

/**
 * Haptic feedback yardimci sinifi.
 *
 * Aktif Activity'yi WeakReference ile tutar — memory leak yok.
 * View.performHapticFeedback() kullanir — hic izin gerektirmez.
 * Uygulama arka plandayken (activity null) tetikleme YAPILMAZ;
 * arka planda sistem bildirimi zaten vibrate pattern icerir.
 */
object HapticHelper {

    private var currentActivity: WeakReference<Activity>? = null

    /** ActivityLifecycleCallbacks.onActivityResumed'dan cagrilmali */
    fun registerActivity(activity: Activity) {
        currentActivity = WeakReference(activity)
    }

    /** ActivityLifecycleCallbacks.onActivityPaused'dan cagrilmali */
    fun unregisterActivity() {
        currentActivity = null
    }

    /**
     * severity'e gore titresim tetikler.
     *
     * @param severity "critical" -> REJECT (guclu), "warning" -> CONFIRM (hafif),
     *                 diger degerler -> titresim yok
     */
    fun triggerHaptic(severity: String) {
        val activity = currentActivity?.get() ?: return
        val view = activity.window.decorView
        when (severity) {
            "critical" -> view.performHapticFeedback(HapticFeedbackConstants.REJECT)
            "warning" -> view.performHapticFeedback(HapticFeedbackConstants.CONFIRM)
            else -> return
        }
    }
}
