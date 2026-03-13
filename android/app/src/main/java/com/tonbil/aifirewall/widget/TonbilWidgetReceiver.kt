package com.tonbil.aifirewall.widget

import androidx.glance.appwidget.GlanceAppWidgetReceiver

class TonbilWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget = TonbilWidget()
}
