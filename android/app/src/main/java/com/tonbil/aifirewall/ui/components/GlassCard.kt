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
import androidx.compose.ui.unit.dp
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme

@Composable
fun GlassCard(
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    val cyberpunk = CyberpunkTheme.colors
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = cyberpunk.glassBg,
        ),
        border = BorderStroke(1.dp, cyberpunk.glassBorder),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            content = content,
        )
    }
}
