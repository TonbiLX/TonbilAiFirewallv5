package com.tonbil.aifirewall.ui.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonMagenta

/**
 * Modifier that adds a pulsing neon glow behind a composable.
 */
@Composable
fun Modifier.neonGlow(
    color: Color = NeonCyan,
    radius: Dp = 16.dp,
    pulseEnabled: Boolean = true,
): Modifier {
    val infiniteTransition = rememberInfiniteTransition(label = "neonGlow")
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = if (pulseEnabled) 0.15f else 0.25f,
        targetValue = if (pulseEnabled) 0.35f else 0.25f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "glowAlpha",
    )

    return this.drawBehind {
        drawRoundRect(
            color = color.copy(alpha = glowAlpha),
            cornerRadius = CornerRadius(radius.toPx()),
            style = Stroke(width = 4.dp.toPx()),
        )
        drawRoundRect(
            color = color.copy(alpha = glowAlpha * 0.3f),
            cornerRadius = CornerRadius(radius.toPx()),
            style = Stroke(width = 12.dp.toPx()),
        )
    }
}

/**
 * Box with animated gradient border (cyan → magenta → cyan).
 */
@Composable
fun GradientBorderBox(
    modifier: Modifier = Modifier,
    borderWidth: Dp = 1.dp,
    cornerRadius: Dp = 16.dp,
    content: @Composable () -> Unit,
) {
    val infiniteTransition = rememberInfiniteTransition(label = "gradBorder")
    val animPhase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "gradPhase",
    )

    val gradientColors = listOf(
        NeonCyan.copy(alpha = 0.3f + animPhase * 0.4f),
        NeonMagenta.copy(alpha = 0.3f + (1f - animPhase) * 0.4f),
        NeonCyan.copy(alpha = 0.3f + animPhase * 0.4f),
    )

    Box(
        modifier = modifier
            .border(
                width = borderWidth,
                brush = Brush.linearGradient(gradientColors),
                shape = RoundedCornerShape(cornerRadius),
            )
            .padding(borderWidth),
    ) {
        content()
    }
}

/**
 * Pulsing dot indicator for live data.
 */
@Composable
fun PulsingDot(
    color: Color = NeonCyan,
    size: Dp = 8.dp,
    modifier: Modifier = Modifier,
) {
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val scale by infiniteTransition.animateFloat(
        initialValue = 0.6f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "pulseScale",
    )

    Box(
        modifier = modifier
            .drawBehind {
                // Outer glow
                drawCircle(
                    color = color.copy(alpha = 0.3f * scale),
                    radius = this.size.minDimension * 0.8f,
                )
                // Inner solid
                drawCircle(
                    color = color.copy(alpha = 0.7f + 0.3f * scale),
                    radius = this.size.minDimension * 0.4f * scale,
                )
            }
            .background(Color.Transparent)
            .padding(size),
    )
}
