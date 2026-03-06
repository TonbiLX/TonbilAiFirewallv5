package com.tonbil.aifirewall.feature.splash

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import kotlinx.coroutines.delay
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

@Composable
fun SplashScreen(
    onSplashFinished: () -> Unit,
) {
    // Main shield glow animation
    val shieldAlpha = remember { Animatable(0f) }
    val shieldScale = remember { Animatable(0.3f) }

    // Typing effect
    val fullText = "TonbilAiOS"
    var typedLength by remember { mutableIntStateOf(0) }

    // Radar sweep
    val infiniteTransition = rememberInfiniteTransition(label = "radar")
    val radarAngle by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(2000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart,
        ),
        label = "radarAngle",
    )

    // Neon pulse
    val glowPulse by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "glowPulse",
    )

    // Scan lines
    val scanLineOffset by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(3000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart,
        ),
        label = "scanLine",
    )

    LaunchedEffect(Unit) {
        // Fade in + scale up shield
        shieldAlpha.animateTo(1f, tween(800, easing = FastOutSlowInEasing))
        shieldScale.animateTo(1f, tween(600, easing = FastOutSlowInEasing))

        // Typing effect
        for (i in 1..fullText.length) {
            delay(100)
            typedLength = i
        }

        // Wait then navigate
        delay(1000)
        onSplashFinished()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.radialGradient(
                    colors = listOf(
                        Color(0xFF1A0A2E),
                        Color(0xFF0A0A1A),
                    ),
                    radius = 1000f,
                )
            ),
        contentAlignment = Alignment.Center,
    ) {
        // Scan lines overlay
        Canvas(modifier = Modifier.fillMaxSize()) {
            drawScanLines(scanLineOffset)
        }

        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            // Shield with radar + neon glow
            Box(contentAlignment = Alignment.Center) {
                Canvas(
                    modifier = Modifier.size(200.dp),
                ) {
                    val cx = size.width / 2
                    val cy = size.height / 2
                    val shieldSize = size.minDimension * 0.8f * shieldScale.value

                    // Outer glow rings
                    for (i in 3 downTo 1) {
                        drawCircle(
                            color = NeonCyan.copy(alpha = 0.05f * glowPulse * i),
                            radius = shieldSize * 0.6f + i * 20f,
                            center = Offset(cx, cy),
                        )
                    }

                    // Radar sweep
                    rotate(radarAngle, pivot = Offset(cx, cy)) {
                        drawArc(
                            brush = Brush.sweepGradient(
                                0f to Color.Transparent,
                                0.15f to NeonCyan.copy(alpha = 0.3f * shieldAlpha.value),
                                0.3f to Color.Transparent,
                                colors = listOf(
                                    Color.Transparent,
                                    NeonCyan.copy(alpha = 0.3f * shieldAlpha.value),
                                    Color.Transparent,
                                ),
                            ),
                            startAngle = 0f,
                            sweepAngle = 90f,
                            useCenter = true,
                            topLeft = Offset(cx - shieldSize * 0.5f, cy - shieldSize * 0.5f),
                            size = Size(shieldSize, shieldSize),
                        )
                    }

                    // Shield path
                    val shieldPath = createShieldPath(cx, cy, shieldSize * 0.45f)

                    // Shield fill
                    drawPath(
                        path = shieldPath,
                        brush = Brush.verticalGradient(
                            colors = listOf(
                                NeonCyan.copy(alpha = 0.15f * shieldAlpha.value),
                                NeonMagenta.copy(alpha = 0.08f * shieldAlpha.value),
                            ),
                            startY = cy - shieldSize * 0.4f,
                            endY = cy + shieldSize * 0.4f,
                        ),
                    )

                    // Shield border with neon glow
                    drawPath(
                        path = shieldPath,
                        color = NeonCyan.copy(alpha = shieldAlpha.value * glowPulse),
                        style = Stroke(width = 3f, cap = StrokeCap.Round),
                    )
                    // Outer glow stroke
                    drawPath(
                        path = shieldPath,
                        color = NeonCyan.copy(alpha = 0.3f * shieldAlpha.value * glowPulse),
                        style = Stroke(width = 8f, cap = StrokeCap.Round),
                    )

                    // Checkmark inside shield
                    if (shieldScale.value > 0.8f) {
                        val checkPath = Path().apply {
                            moveTo(cx - shieldSize * 0.15f, cy + shieldSize * 0.02f)
                            lineTo(cx - shieldSize * 0.03f, cy + shieldSize * 0.15f)
                            lineTo(cx + shieldSize * 0.18f, cy - shieldSize * 0.12f)
                        }
                        drawPath(
                            path = checkPath,
                            color = NeonGreen.copy(alpha = shieldAlpha.value * glowPulse),
                            style = Stroke(width = 4f, cap = StrokeCap.Round),
                        )
                    }

                    // Small dots around (particle effect)
                    for (i in 0 until 8) {
                        val angle = (i * 45f + radarAngle * 0.5f) * PI.toFloat() / 180f
                        val dist = shieldSize * 0.55f
                        val dotX = cx + cos(angle) * dist
                        val dotY = cy + sin(angle) * dist
                        drawCircle(
                            color = NeonCyan.copy(alpha = 0.4f * glowPulse * shieldAlpha.value),
                            radius = 2f,
                            center = Offset(dotX, dotY),
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Typing text
            Text(
                text = fullText.take(typedLength),
                style = MaterialTheme.typography.headlineLarge.copy(
                    fontSize = 32.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 4.sp,
                ),
                color = NeonCyan.copy(alpha = shieldAlpha.value),
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Subtitle
            if (typedLength >= fullText.length) {
                Text(
                    text = "AI-Powered Router Security",
                    style = MaterialTheme.typography.bodyMedium.copy(
                        letterSpacing = 2.sp,
                    ),
                    color = NeonMagenta.copy(alpha = 0.7f),
                )
            }
        }
    }
}

private fun createShieldPath(cx: Float, cy: Float, radius: Float): Path {
    return Path().apply {
        // Shield shape: rounded top, pointed bottom
        moveTo(cx, cy - radius) // top center
        // Top-right curve
        cubicTo(
            cx + radius * 0.6f, cy - radius,
            cx + radius, cy - radius * 0.6f,
            cx + radius, cy - radius * 0.1f,
        )
        // Right side curve down to point
        cubicTo(
            cx + radius, cy + radius * 0.2f,
            cx + radius * 0.5f, cy + radius * 0.6f,
            cx, cy + radius,
        )
        // Left side curve up from point
        cubicTo(
            cx - radius * 0.5f, cy + radius * 0.6f,
            cx - radius, cy + radius * 0.2f,
            cx - radius, cy - radius * 0.1f,
        )
        // Top-left curve
        cubicTo(
            cx - radius, cy - radius * 0.6f,
            cx - radius * 0.6f, cy - radius,
            cx, cy - radius,
        )
        close()
    }
}

private fun DrawScope.drawScanLines(offset: Float) {
    val lineSpacing = 4f
    val totalLines = (size.height / lineSpacing).toInt()
    for (i in 0 until totalLines) {
        val y = i * lineSpacing
        val alpha = if ((i + (offset * 100).toInt()) % 3 == 0) 0.03f else 0.01f
        drawLine(
            color = NeonCyan.copy(alpha = alpha),
            start = Offset(0f, y),
            end = Offset(size.width, y),
            strokeWidth = 1f,
        )
    }
}
