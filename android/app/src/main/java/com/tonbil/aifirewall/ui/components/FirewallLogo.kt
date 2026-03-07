package com.tonbil.aifirewall.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

private val NeonCyan = Color(0xFF00F0FF)
private val NeonMagenta = Color(0xFFFF00E5)
private val DarkBg = Color(0xFF0A0A0F)

@Composable
fun FirewallLogo(size: Dp = 120.dp, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier.size(size)) {
        val s = this.size.minDimension
        val scale = s / 512f

        drawShield(scale)
        drawBricks(scale)
        drawAiEye(scale)
        drawCircuitNodes(scale)
        drawLockKeyhole(scale)
    }
}

private fun DrawScope.drawShield(scale: Float) {
    // Shield body path
    val shieldPath = Path().apply {
        moveTo(256f * scale, 28f * scale)
        lineTo(462f * scale, 120f * scale)
        cubicTo(462f * scale, 120f * scale, 472f * scale, 300f * scale, 256f * scale, 484f * scale)
        cubicTo(40f * scale, 300f * scale, 50f * scale, 120f * scale, 50f * scale, 120f * scale)
        close()
    }

    // Fill with gradient
    val fillBrush = Brush.linearGradient(
        colors = listOf(
            NeonCyan.copy(alpha = 0.15f),
            DarkBg.copy(alpha = 0.9f),
            NeonMagenta.copy(alpha = 0.1f),
        ),
        start = Offset(0f, 0f),
        end = Offset(size.width, size.height),
    )
    drawPath(shieldPath, fillBrush)

    // Stroke with gradient
    val strokeBrush = Brush.linearGradient(
        colors = listOf(NeonCyan, NeonCyan.copy(alpha = 0.4f), NeonMagenta.copy(alpha = 0.8f)),
        start = Offset(0f, 0f),
        end = Offset(size.width, size.height),
    )
    drawPath(shieldPath, strokeBrush, style = Stroke(width = 6f * scale))

    // Inner shield
    val innerPath = Path().apply {
        moveTo(256f * scale, 62f * scale)
        lineTo(430f * scale, 140f * scale)
        cubicTo(430f * scale, 140f * scale, 438f * scale, 290f * scale, 256f * scale, 450f * scale)
        cubicTo(74f * scale, 290f * scale, 82f * scale, 140f * scale, 82f * scale, 140f * scale)
        close()
    }
    drawPath(innerPath, NeonCyan.copy(alpha = 0.25f), style = Stroke(width = 1.5f * scale))
}

private fun DrawScope.drawBricks(scale: Float) {
    // Horizontal lines
    val hLines = listOf(
        Triple(130f, 382f, 190f) to 0.3f,
        Triple(120f, 392f, 240f) to 0.25f,
        Triple(130f, 382f, 290f) to 0.2f,
        Triple(150f, 362f, 340f) to 0.15f,
    )
    for ((line, alpha) in hLines) {
        drawLine(
            NeonCyan.copy(alpha = alpha),
            Offset(line.first * scale, line.third * scale),
            Offset(line.second * scale, line.third * scale),
            strokeWidth = 2f * scale,
        )
    }

    // Vertical lines (brick joints)
    val vLines = listOf(
        listOf(220f to (190f to 240f), 310f to (190f to 240f)),
        listOf(180f to (240f to 290f), 265f to (240f to 290f), 345f to (240f to 290f)),
    )
    for (group in vLines) {
        for ((x, yRange) in group) {
            drawLine(
                NeonCyan.copy(alpha = 0.2f),
                Offset(x * scale, yRange.first * scale),
                Offset(x * scale, yRange.second * scale),
                strokeWidth = 1.5f * scale,
            )
        }
    }
}

private fun DrawScope.drawAiEye(scale: Float) {
    val cx = 256f * scale
    val cy = 230f * scale

    // Outer ring
    drawCircle(NeonCyan.copy(alpha = 0.9f), radius = 52f * scale, center = Offset(cx, cy), style = Stroke(width = 3f * scale))
    // Middle ring
    drawCircle(NeonMagenta.copy(alpha = 0.7f), radius = 36f * scale, center = Offset(cx, cy), style = Stroke(width = 2f * scale))
    // Inner filled
    drawCircle(NeonCyan.copy(alpha = 0.8f), radius = 18f * scale, center = Offset(cx, cy))
    // Center dot
    drawCircle(Color.White.copy(alpha = 0.9f), radius = 8f * scale, center = Offset(cx, cy))
}

private fun DrawScope.drawCircuitNodes(scale: Float) {
    // Cardinal direction lines + nodes
    // Up
    drawLine(NeonCyan.copy(alpha = 0.8f), Offset(256f * scale, 178f * scale), Offset(256f * scale, 155f * scale), strokeWidth = 2f * scale)
    drawCircle(NeonCyan.copy(alpha = 0.8f), radius = 4f * scale, center = Offset(256f * scale, 152f * scale))

    // Down
    drawLine(NeonCyan.copy(alpha = 0.8f), Offset(256f * scale, 282f * scale), Offset(256f * scale, 310f * scale), strokeWidth = 2f * scale)
    drawCircle(NeonCyan.copy(alpha = 0.8f), radius = 4f * scale, center = Offset(256f * scale, 313f * scale))

    // Left
    drawLine(NeonCyan.copy(alpha = 0.8f), Offset(204f * scale, 230f * scale), Offset(175f * scale, 230f * scale), strokeWidth = 2f * scale)
    drawCircle(NeonCyan.copy(alpha = 0.8f), radius = 4f * scale, center = Offset(172f * scale, 230f * scale))

    // Right
    drawLine(NeonCyan.copy(alpha = 0.8f), Offset(308f * scale, 230f * scale), Offset(337f * scale, 230f * scale), strokeWidth = 2f * scale)
    drawCircle(NeonCyan.copy(alpha = 0.8f), radius = 4f * scale, center = Offset(340f * scale, 230f * scale))

    // Diagonal nodes (magenta)
    // Top-left
    drawLine(NeonCyan.copy(alpha = 0.5f), Offset(219f * scale, 193f * scale), Offset(200f * scale, 174f * scale), strokeWidth = 1.5f * scale)
    drawCircle(NeonMagenta.copy(alpha = 0.6f), radius = 3f * scale, center = Offset(197f * scale, 171f * scale))
    // Top-right
    drawLine(NeonCyan.copy(alpha = 0.5f), Offset(293f * scale, 193f * scale), Offset(312f * scale, 174f * scale), strokeWidth = 1.5f * scale)
    drawCircle(NeonMagenta.copy(alpha = 0.6f), radius = 3f * scale, center = Offset(315f * scale, 171f * scale))
    // Bottom-left
    drawLine(NeonCyan.copy(alpha = 0.5f), Offset(219f * scale, 267f * scale), Offset(200f * scale, 286f * scale), strokeWidth = 1.5f * scale)
    drawCircle(NeonMagenta.copy(alpha = 0.6f), radius = 3f * scale, center = Offset(197f * scale, 289f * scale))
    // Bottom-right
    drawLine(NeonCyan.copy(alpha = 0.5f), Offset(293f * scale, 267f * scale), Offset(312f * scale, 286f * scale), strokeWidth = 1.5f * scale)
    drawCircle(NeonMagenta.copy(alpha = 0.6f), radius = 3f * scale, center = Offset(315f * scale, 289f * scale))
}

private fun DrawScope.drawLockKeyhole(scale: Float) {
    // Lock circle
    drawCircle(NeonCyan.copy(alpha = 0.5f), radius = 12f * scale, center = Offset(256f * scale, 358f * scale), style = Stroke(width = 2.5f * scale))
    // Keyhole rect
    drawRect(
        NeonCyan.copy(alpha = 0.5f),
        topLeft = Offset(248f * scale, 360f * scale),
        size = Size(16f * scale, 20f * scale),
    )
}
