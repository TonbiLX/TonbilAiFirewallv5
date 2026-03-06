package com.tonbil.aifirewall.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

private val CyberpunkColorScheme = darkColorScheme(
    primary = NeonCyan,
    onPrimary = Color.Black,
    secondary = NeonMagenta,
    onSecondary = Color.Black,
    tertiary = NeonGreen,
    onTertiary = Color.Black,
    error = NeonRed,
    onError = Color.Black,
    background = DarkBackground,
    onBackground = TextPrimary,
    surface = DarkSurface,
    onSurface = TextPrimary,
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = TextSecondary,
    outline = GlassBorder,
)

/**
 * Extended cyberpunk colors accessible via CompositionLocal.
 * Use CyberpunkTheme.colors to access neon colors not in Material 3 scheme.
 */
data class CyberpunkColors(
    val neonCyan: Color = NeonCyan,
    val neonMagenta: Color = NeonMagenta,
    val neonGreen: Color = NeonGreen,
    val neonAmber: Color = NeonAmber,
    val neonRed: Color = NeonRed,
    val glassBg: Color = GlassBg,
    val glassBorder: Color = GlassBorder,
)

val LocalCyberpunkColors = staticCompositionLocalOf { CyberpunkColors() }

@Composable
fun CyberpunkTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalCyberpunkColors provides CyberpunkColors()) {
        MaterialTheme(
            colorScheme = CyberpunkColorScheme,
            typography = CyberpunkTypography,
            shapes = CyberpunkShapes,
            content = content
        )
    }
}

// Easy access companion
object CyberpunkTheme {
    val colors: CyberpunkColors
        @Composable get() = LocalCyberpunkColors.current
}
