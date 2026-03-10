package com.tonbil.aifirewall.feature.ddosmap

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.tonbil.aifirewall.data.remote.dto.DdosAttackPointDto
import com.tonbil.aifirewall.ui.theme.GlassBorder
import com.tonbil.aifirewall.ui.theme.NeonAmber
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import kotlin.math.ln
import kotlin.math.tan

// =========================================================================
// Mercator projection helpers
// =========================================================================
private const val MAX_LAT = 83.0

private fun lonToX(lon: Double, w: Float): Float =
    ((lon + 180.0) / 360.0 * w).toFloat()

private fun latToY(lat: Double, h: Float): Float {
    val clamped = lat.coerceIn(-MAX_LAT, MAX_LAT)
    val rad = Math.toRadians(clamped)
    val maxMerc = ln(tan(Math.PI / 4 + Math.toRadians(MAX_LAT) / 2))
    val merc = ln(tan(Math.PI / 4 + rad / 2))
    return (h / 2 - (merc / maxMerc * h / 2)).toFloat()
}

private fun toOffset(lat: Double, lon: Double, w: Float, h: Float) =
    Offset(lonToX(lon, w), latToY(lat, h))

// =========================================================================
// Attack type → color
// =========================================================================
private fun attackColor(type: String): Color = when {
    type.contains("syn", true) -> NeonRed
    type.contains("udp", true) -> NeonAmber
    type.contains("icmp", true) -> NeonMagenta
    type.contains("conn", true) -> Color(0xFFA855F7)
    else -> Color(0xFF6B7280)
}

// Target: Turkey / Ankara
private const val TGT_LAT = 39.92
private const val TGT_LON = 32.85

// =========================================================================
// Continent polygon data   (lat, lon) pairs — continuous closed outlines
// Each DoubleArray is [lat1,lon1, lat2,lon2, …]
// =========================================================================

// North America  (clockwise from NW Alaska → Arctic → E coast → Gulf → C.Am Pacific coast back)
private val NORTH_AMERICA = doubleArrayOf(
    60.0,-147.0, 64.0,-166.0, 68.0,-164.0, 71.0,-157.0,
    71.0,-136.0, 69.0,-128.0, 71.0,-118.0, 74.0,-95.0,
    73.0,-85.0, 69.0,-68.0, 64.0,-63.0, 60.0,-64.0,
    55.0,-58.0, 52.0,-56.0, 48.0,-53.0, 46.0,-56.0,
    44.0,-60.0, 44.0,-66.0, 42.0,-70.0, 41.0,-72.0,
    38.0,-75.0, 35.0,-76.0, 32.0,-80.0, 30.0,-81.0,
    27.0,-80.0, 25.0,-80.0, 25.0,-82.0, 27.0,-83.0,
    30.0,-86.0, 30.0,-89.0, 29.0,-92.0, 28.0,-96.0,
    26.0,-97.0, 22.0,-98.0, 19.0,-96.0, 17.0,-96.0,
    15.0,-92.0, 14.0,-88.0, 11.0,-84.0, 9.0,-80.0,
    8.0,-78.0, 8.0,-82.0, 10.0,-84.0, 14.0,-92.0,
    17.0,-101.0, 20.0,-105.0, 23.0,-110.0, 25.0,-112.0,
    28.0,-114.0, 31.0,-116.0, 32.0,-117.0, 34.0,-120.0,
    37.0,-122.0, 40.0,-124.0, 43.0,-124.0, 46.0,-124.0,
    48.0,-125.0, 51.0,-128.0, 55.0,-132.0, 57.0,-136.0,
)

private val SOUTH_AMERICA = doubleArrayOf(
    12.0,-72.0, 11.0,-65.0, 10.0,-61.0, 8.0,-58.0,
    6.0,-55.0, 4.0,-52.0, 2.0,-50.0, 0.0,-49.0,
    -2.0,-44.0, -5.0,-37.0, -7.0,-35.0, -10.0,-37.0,
    -13.0,-39.0, -18.0,-39.0, -23.0,-42.0, -25.0,-48.0,
    -29.0,-49.0, -33.0,-52.0, -36.0,-57.0, -40.0,-62.0,
    -45.0,-66.0, -50.0,-68.0, -52.0,-69.0, -54.0,-70.0,
    -54.0,-72.0, -50.0,-75.0, -46.0,-75.0, -42.0,-74.0,
    -38.0,-73.0, -33.0,-72.0, -27.0,-71.0, -22.0,-70.0,
    -18.0,-70.0, -15.0,-75.0, -10.0,-78.0, -5.0,-81.0,
    -1.0,-80.0, 1.0,-79.0, 4.0,-77.0, 7.0,-76.0,
    9.0,-76.0, 12.0,-73.0,
)

private val EUROPE = doubleArrayOf(
    36.0,-9.0, 37.0,-7.0, 36.0,-3.0, 37.0,0.0,
    39.0,0.0, 41.0,2.0, 43.0,3.0, 43.0,6.0,
    44.0,8.0, 44.0,12.0, 41.0,16.0, 38.0,16.0,
    38.0,14.0, 40.0,18.0, 42.0,19.0, 40.0,20.0,
    38.0,22.0, 38.0,24.0, 40.0,26.0, 41.0,29.0,
    42.0,28.0, 43.0,28.0, 45.0,30.0, 47.0,37.0,
    52.0,40.0, 56.0,38.0, 60.0,30.0,
    62.0,28.0, 66.0,26.0, 70.0,28.0, 71.0,26.0,
    70.0,20.0, 67.0,15.0, 64.0,12.0, 62.0,5.0,
    58.0,6.0, 57.0,8.0, 56.0,11.0, 55.0,13.0,
    55.0,10.0, 54.0,9.0, 54.0,8.0, 53.0,7.0,
    52.0,4.0, 51.0,2.0, 50.0,0.0,
    49.0,-2.0, 48.0,-5.0, 47.0,-3.0, 46.0,-1.0,
    44.0,-1.0, 43.0,-2.0, 43.0,-8.0, 42.0,-9.0,
    40.0,-9.0, 37.0,-9.0,
)

private val AFRICA = doubleArrayOf(
    36.0,-5.0, 37.0,0.0, 37.0,10.0, 35.0,12.0,
    33.0,12.0, 32.0,20.0, 32.0,25.0, 31.0,32.0,
    29.0,33.0, 22.0,37.0, 15.0,42.0, 12.0,44.0,
    10.0,45.0, 5.0,42.0, 1.0,42.0, -2.0,41.0,
    -5.0,40.0, -10.0,40.0, -15.0,41.0, -22.0,36.0,
    -26.0,33.0, -30.0,32.0, -34.0,26.0, -34.0,20.0,
    -33.0,18.0, -29.0,16.0, -22.0,14.0, -17.0,12.0,
    -10.0,9.0, -5.0,10.0, 0.0,10.0, 4.0,2.0,
    5.0,-4.0, 5.0,-8.0, 7.0,-12.0, 10.0,-15.0,
    14.0,-17.0, 16.0,-16.0, 21.0,-17.0, 25.0,-15.0,
    28.0,-13.0, 30.0,-10.0, 32.0,-8.0, 35.0,-5.0,
)

// Asia: Turkey → Iran → Central Asia → Siberia → Kamchatka → China → SE Asia → India → Arabia
private val ASIA = doubleArrayOf(
    // Turkey / Anatolia
    41.0,29.0, 42.0,33.0, 40.0,36.0, 37.0,36.0,
    36.0,36.0, 33.0,36.0, 32.0,35.0,
    // Arabia
    29.0,35.0, 26.0,37.0, 20.0,40.0, 15.0,43.0,
    13.0,48.0, 14.0,52.0, 22.0,59.0, 25.0,57.0,
    24.0,52.0, 27.0,50.0, 30.0,48.0, 30.0,50.0,
    26.0,56.0, 25.0,62.0,
    // Iran → Pakistan → India
    27.0,63.0, 28.0,66.0, 25.0,68.0,
    24.0,68.0, 20.0,73.0, 15.0,74.0, 10.0,76.0,
    8.0,77.0, 10.0,80.0, 14.0,80.0, 16.0,82.0,
    20.0,87.0, 22.0,89.0, 22.0,92.0,
    // SE Asia / Myanmar / Thailand / Vietnam
    16.0,96.0, 10.0,98.0, 8.0,99.0,
    2.0,103.0, 1.0,104.0, 4.0,104.0,
    10.0,107.0, 15.0,109.0, 21.0,108.0,
    22.0,114.0, 24.0,118.0, 30.0,122.0,
    // China coast → Korea → Japan sea
    34.0,120.0, 37.0,123.0, 39.0,122.0,
    40.0,124.0, 42.0,130.0, 45.0,132.0,
    48.0,135.0, 50.0,140.0, 54.0,137.0,
    55.0,140.0, 58.0,150.0, 60.0,163.0,
    62.0,170.0, 65.0,176.0,
    // Kamchatka → Siberia Arctic coast west
    66.0,170.0, 69.0,172.0, 71.0,180.0,
    71.0,160.0, 73.0,140.0, 74.0,120.0,
    73.0,100.0, 72.0,80.0, 70.0,68.0,
    68.0,55.0, 70.0,52.0, 70.0,42.0,
    // Back to Turkey connection through Caucasus
    65.0,40.0, 55.0,38.0, 52.0,40.0,
    47.0,37.0, 45.0,30.0, 42.0,28.0,
)

private val AUSTRALIA = doubleArrayOf(
    -12.0,130.0, -12.0,136.0, -14.0,137.0, -13.0,141.0,
    -16.0,146.0, -19.0,147.0, -23.0,151.0, -28.0,154.0,
    -33.0,152.0, -36.0,150.0, -38.0,148.0, -39.0,146.0,
    -38.0,141.0, -35.0,137.0, -35.0,135.0, -33.0,134.0,
    -32.0,132.0, -34.0,123.0, -34.0,118.0, -31.0,115.0,
    -25.0,113.0, -22.0,114.0, -18.0,122.0, -15.0,125.0,
    -14.0,130.0,
)

private val GREENLAND = doubleArrayOf(
    60.0,-46.0, 62.0,-52.0, 66.0,-54.0, 72.0,-56.0,
    76.0,-60.0, 78.0,-55.0, 80.0,-48.0, 82.0,-40.0,
    83.0,-32.0, 81.0,-20.0, 76.0,-18.0, 72.0,-22.0,
    68.0,-26.0, 64.0,-38.0, 61.0,-43.0,
)

private val UK = doubleArrayOf(
    50.0,-5.0, 51.0,1.0, 53.0,0.0, 54.0,-1.0,
    55.0,-2.0, 56.0,-5.0, 58.0,-5.0, 58.0,-3.0,
    57.0,-2.0, 56.0,-3.0, 55.0,-6.0, 53.0,-5.0,
    52.0,-4.0,
)

private val JAPAN = doubleArrayOf(
    31.0,131.0, 33.0,132.0, 34.0,135.0, 35.0,137.0,
    37.0,137.0, 38.0,139.0, 40.0,140.0, 42.0,140.0,
    43.0,145.0, 44.0,145.0, 44.0,143.0, 42.0,141.0,
    40.0,140.0, 37.0,140.0, 35.0,139.0, 34.0,137.0,
    33.0,134.0, 32.0,131.0,
)

private val NEW_ZEALAND = doubleArrayOf(
    -35.0,174.0, -37.0,176.0, -39.0,178.0, -42.0,174.0,
    -44.0,169.0, -46.0,167.0, -46.0,169.0, -44.0,172.0,
    -42.0,174.0, -40.0,176.0, -38.0,178.0, -37.0,175.0,
)

private val MADAGASCAR = doubleArrayOf(
    -12.0,49.0, -16.0,50.0, -20.0,44.0, -24.0,44.0,
    -25.0,47.0, -22.0,48.0, -18.0,50.0, -15.0,50.0,
)

private val ALL_POLYGONS: List<DoubleArray> = listOf(
    NORTH_AMERICA, SOUTH_AMERICA, EUROPE, AFRICA, ASIA,
    AUSTRALIA, GREENLAND, UK, JAPAN, NEW_ZEALAND, MADAGASCAR,
)

// =========================================================================
// Path builder
// =========================================================================
private fun buildLandPath(w: Float, h: Float): Path {
    val path = Path()
    for (coords in ALL_POLYGONS) {
        val n = coords.size / 2
        if (n < 3) continue
        path.moveTo(lonToX(coords[1], w), latToY(coords[0], h))
        for (i in 1 until n) {
            path.lineTo(lonToX(coords[i * 2 + 1], w), latToY(coords[i * 2], h))
        }
        path.close()
    }
    return path
}

// =========================================================================
// Composable
// =========================================================================

@Composable
fun DdosWorldMap(
    attacks: List<DdosAttackPointDto>,
    modifier: Modifier = Modifier,
) {
    val transition = rememberInfiniteTransition(label = "ddos")
    val pulse by transition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "pulse",
    )

    val uniqueAttacks = remember(attacks) {
        attacks
            .filter { it.lat != 0.0 || it.lon != 0.0 }
            .distinctBy { "${it.lat.toInt()}_${it.lon.toInt()}_${it.type}" }
            .take(40)
    }

    Box(
        modifier = modifier
            .fillMaxWidth()
            .height(230.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(
                Brush.verticalGradient(
                    colors = listOf(Color(0xFF050510), Color(0xFF0a0a20), Color(0xFF050510)),
                ),
            )
            .border(1.dp, GlassBorder, RoundedCornerShape(12.dp)),
    ) {
        Canvas(modifier = Modifier.fillMaxSize().padding(6.dp)) {
            val w = size.width
            val h = size.height

            drawGrid(w, h)
            drawLand(w, h)
            drawAttacks(uniqueAttacks, pulse, w, h)
        }
    }
}

// =========================================================================
// Drawing helpers
// =========================================================================

private fun DrawScope.drawGrid(w: Float, h: Float) {
    val gridColor = Color.White.copy(alpha = 0.03f)
    // Longitude lines
    for (lon in -180..180 step 30) {
        val x = lonToX(lon.toDouble(), w)
        drawLine(gridColor, Offset(x, 0f), Offset(x, h), strokeWidth = 0.5f)
    }
    // Latitude lines
    for (lat in -60..80 step 30) {
        val y = latToY(lat.toDouble(), h)
        drawLine(gridColor, Offset(0f, y), Offset(w, y), strokeWidth = 0.5f)
    }
    // Equator (slightly brighter)
    val eq = latToY(0.0, h)
    drawLine(Color.White.copy(alpha = 0.05f), Offset(0f, eq), Offset(w, eq), strokeWidth = 0.5f)
}

private fun DrawScope.drawLand(w: Float, h: Float) {
    val path = buildLandPath(w, h)
    // Fill
    drawPath(path, color = Color(0xFF0d2a22), style = Fill)
    // Subtle border glow
    drawPath(path, color = Color(0xFF1a5c44), style = Stroke(width = 0.8f))
}

private fun DrawScope.drawAttacks(
    attacks: List<DdosAttackPointDto>,
    pulse: Float,
    w: Float,
    h: Float,
) {
    val tx = lonToX(TGT_LON, w)
    val ty = latToY(TGT_LAT, h)

    // Target concentric rings
    drawCircle(NeonCyan.copy(alpha = pulse * 0.12f), radius = 24f, center = Offset(tx, ty))
    drawCircle(NeonCyan.copy(alpha = pulse * 0.3f), radius = 12f, center = Offset(tx, ty))
    drawCircle(NeonCyan, radius = 4.5f, center = Offset(tx, ty))

    for (atk in attacks) {
        val ax = lonToX(atk.lon, w)
        val ay = latToY(atk.lat, h)
        val col = attackColor(atk.type)

        // Glow line (wide, transparent)
        drawLine(
            color = col.copy(alpha = 0.10f),
            start = Offset(ax, ay),
            end = Offset(tx, ty),
            strokeWidth = 5f,
        )
        // Dashed main line
        drawLine(
            color = col.copy(alpha = 0.55f),
            start = Offset(ax, ay),
            end = Offset(tx, ty),
            strokeWidth = 1.2f,
            pathEffect = PathEffect.dashPathEffect(floatArrayOf(8f, 5f)),
        )

        // Attack origin rings
        drawCircle(col.copy(alpha = pulse * 0.18f), radius = 12f, center = Offset(ax, ay))
        drawCircle(col.copy(alpha = pulse * 0.5f), radius = 6f, center = Offset(ax, ay))
        drawCircle(col, radius = 3f, center = Offset(ax, ay))
    }
}
