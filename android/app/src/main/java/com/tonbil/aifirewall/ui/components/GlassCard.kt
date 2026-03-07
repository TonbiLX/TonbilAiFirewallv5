package com.tonbil.aifirewall.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme

@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    glowColor: Color? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val cyberpunk = CyberpunkTheme.colors
    val border = if (glowColor != null) {
        BorderStroke(
            1.dp,
            Brush.linearGradient(
                listOf(
                    glowColor.copy(alpha = 0.6f),
                    cyberpunk.glassBorder,
                    glowColor.copy(alpha = 0.4f),
                )
            ),
        )
    } else {
        BorderStroke(1.dp, cyberpunk.glassBorder)
    }

    val glowModifier = if (glowColor != null) {
        modifier.drawBehind {
            drawRoundRect(
                color = glowColor.copy(alpha = 0.08f),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(16.dp.toPx()),
                style = Stroke(width = 6.dp.toPx()),
            )
        }
    } else {
        modifier
    }

    Card(
        modifier = glowModifier,
        colors = CardDefaults.cardColors(
            containerColor = cyberpunk.glassBg,
        ),
        border = border,
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            content = content,
        )
    }
}
