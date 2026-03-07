package com.tonbil.aifirewall.feature.splash

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
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
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.ui.components.FirewallLogo
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import kotlinx.coroutines.delay

@Composable
fun SplashScreen(
    onSplashFinished: () -> Unit,
) {
    val logoAlpha = remember { Animatable(0f) }
    val logoScale = remember { Animatable(0.5f) }

    val fullText = "TonbilAiOS"
    var typedLength by remember { mutableIntStateOf(0) }

    // Neon pulse for logo glow
    val infiniteTransition = rememberInfiniteTransition(label = "splash")
    val glowAlpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 0.8f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "glow",
    )

    LaunchedEffect(Unit) {
        // Fade in + scale up logo
        logoAlpha.animateTo(1f, tween(600))
        logoScale.animateTo(1f, tween(500, easing = FastOutSlowInEasing))

        // Typing effect
        for (i in 1..fullText.length) {
            delay(80)
            typedLength = i
        }

        delay(800)
        onSplashFinished()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.radialGradient(
                    colors = listOf(Color(0xFF1A0A2E), Color(0xFF0A0A1A)),
                    radius = 1200f,
                )
            ),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            // Firewall shield logo with neon glow
            Box(contentAlignment = Alignment.Center) {
                // Glow behind logo
                FirewallLogo(
                    size = 160.dp,
                    modifier = Modifier
                        .scale(1.15f)
                        .alpha(glowAlpha * logoAlpha.value * 0.4f),
                )
                // Main logo
                FirewallLogo(
                    size = 160.dp,
                    modifier = Modifier
                        .scale(logoScale.value)
                        .alpha(logoAlpha.value),
                )
            }

            Spacer(modifier = Modifier.height(28.dp))

            // Typing text
            Text(
                text = fullText.take(typedLength),
                style = MaterialTheme.typography.headlineLarge.copy(
                    fontSize = 30.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 3.sp,
                ),
                color = NeonCyan.copy(alpha = logoAlpha.value),
            )

            Spacer(modifier = Modifier.height(8.dp))

            if (typedLength >= fullText.length) {
                Text(
                    text = "AI-Powered Router Security",
                    style = MaterialTheme.typography.bodyMedium.copy(letterSpacing = 1.sp),
                    color = NeonMagenta.copy(alpha = 0.7f),
                )
            }
        }
    }
}
