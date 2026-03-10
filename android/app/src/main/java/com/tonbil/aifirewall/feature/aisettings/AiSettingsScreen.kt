package com.tonbil.aifirewall.feature.aisettings

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.outlined.BarChart
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Error
import androidx.compose.material.icons.outlined.Key
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.RestartAlt
import androidx.compose.material.icons.outlined.Save
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.GlassBorder
import com.tonbil.aifirewall.ui.theme.NeonAmber
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AiSettingsScreen(
    onBack: () -> Unit,
    viewModel: AiSettingsViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.actionMessage) {
        state.actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }

    Scaffold(
        containerColor = DarkBackground,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Outlined.AutoAwesome,
                            contentDescription = null,
                            tint = NeonMagenta,
                            modifier = Modifier.size(20.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text("AI Ayarlari", color = NeonMagenta, fontWeight = FontWeight.Bold)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Geri", tint = TextSecondary)
                    }
                },
                actions = {
                    if (state.isActionLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(20.dp),
                            color = NeonMagenta,
                            strokeWidth = 2.dp,
                        )
                        Spacer(Modifier.width(12.dp))
                    }
                    IconButton(onClick = viewModel::loadAll) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = TextSecondary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground),
            )
        },
    ) { paddingValues ->
        if (state.isLoading) {
            Box(
                modifier = Modifier.fillMaxSize().padding(paddingValues),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = NeonMagenta)
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(listOf(DarkBackground, Color(0xFF0A0A1A), DarkBackground))
                )
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // Provider selector
            AiProviderCard(
                providers = state.providers,
                selectedProvider = state.editProvider,
                selectedModel = state.editModel,
                onProviderChange = viewModel::setProvider,
                onModelChange = viewModel::setModel,
            )

            // API Key
            AiApiKeyCard(
                apiKey = state.editApiKey,
                requiresApiKey = state.providers.find { it.id == state.editProvider }?.requiresApiKey ?: true,
                onApiKeyChange = viewModel::setApiKey,
            )

            // Chat settings
            AiChatSettingsCard(
                chatEnabled = state.editChatEnabled,
                temperature = state.editTemperature,
                maxTokens = state.editMaxTokens,
                dailyLimit = state.editDailyLimit,
                onChatEnabledChange = viewModel::setChatEnabled,
                onTemperatureChange = viewModel::setTemperature,
                onMaxTokensChange = viewModel::setMaxTokens,
                onDailyLimitChange = viewModel::setDailyLimit,
            )

            // Log analysis
            AiLogAnalysisCard(
                enabled = state.editLogAnalysisEnabled,
                interval = state.editLogAnalysisInterval,
                onEnabledChange = viewModel::setLogAnalysisEnabled,
                onIntervalChange = viewModel::setLogAnalysisInterval,
            )

            // Stats card
            AiStatsCard(state = state)

            // Save + Test + Reset buttons
            AiActionsCard(
                isDirty = state.isDirty,
                isTestLoading = state.isTestLoading,
                testResult = state.testResult,
                onSave = viewModel::saveCurrentEdits,
                onTest = viewModel::test,
                onResetCounter = viewModel::resetCounter,
                onDismissTest = viewModel::clearTestResult,
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AiProviderCard(
    providers: List<com.tonbil.aifirewall.data.remote.dto.AiProviderDto>,
    selectedProvider: String,
    selectedModel: String,
    onProviderChange: (String) -> Unit,
    onModelChange: (String) -> Unit,
) {
    var providerExpanded by remember { mutableStateOf(false) }
    var modelExpanded by remember { mutableStateOf(false) }

    val currentProvider = providers.find { it.id == selectedProvider }
    val availableModels = currentProvider?.models ?: emptyList()

    GlassCard(glowColor = NeonMagenta.copy(alpha = 0.4f)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Settings, contentDescription = null, tint = NeonMagenta, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("Saglayici & Model", color = NeonMagenta, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        }
        Spacer(Modifier.height(14.dp))

        // Provider dropdown
        ExposedDropdownMenuBox(
            expanded = providerExpanded,
            onExpandedChange = { providerExpanded = it },
            modifier = Modifier.fillMaxWidth(),
        ) {
            OutlinedTextField(
                value = currentProvider?.name ?: selectedProvider,
                onValueChange = {},
                readOnly = true,
                label = { Text("Saglayici", fontSize = 12.sp) },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = providerExpanded) },
                modifier = Modifier.fillMaxWidth().menuAnchor(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = NeonMagenta,
                    unfocusedBorderColor = GlassBorder,
                    focusedLabelColor = NeonMagenta,
                    unfocusedLabelColor = TextSecondary,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary,
                    focusedTrailingIconColor = NeonMagenta,
                    unfocusedTrailingIconColor = TextSecondary,
                ),
            )
            ExposedDropdownMenu(
                expanded = providerExpanded,
                onDismissRequest = { providerExpanded = false },
                containerColor = Color(0xFF0E0E1C),
            ) {
                if (providers.isEmpty()) {
                    listOf("openai" to "OpenAI", "anthropic" to "Anthropic", "ollama" to "Ollama", "custom" to "Custom")
                        .forEach { (id, name) ->
                            DropdownMenuItem(
                                text = { Text(name, color = TextPrimary) },
                                onClick = { onProviderChange(id); providerExpanded = false },
                            )
                        }
                } else {
                    providers.forEach { provider ->
                        DropdownMenuItem(
                            text = { Text(provider.name, color = TextPrimary) },
                            onClick = { onProviderChange(provider.id); providerExpanded = false },
                        )
                    }
                }
            }
        }

        Spacer(Modifier.height(10.dp))

        // Model dropdown
        ExposedDropdownMenuBox(
            expanded = modelExpanded,
            onExpandedChange = { if (availableModels.isNotEmpty()) modelExpanded = it },
            modifier = Modifier.fillMaxWidth(),
        ) {
            OutlinedTextField(
                value = selectedModel.ifBlank { "Model seciniz" },
                onValueChange = { onModelChange(it) },
                readOnly = availableModels.isNotEmpty(),
                label = { Text("Model", fontSize = 12.sp) },
                trailingIcon = {
                    if (availableModels.isNotEmpty()) {
                        ExposedDropdownMenuDefaults.TrailingIcon(expanded = modelExpanded)
                    }
                },
                modifier = Modifier.fillMaxWidth().menuAnchor(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = NeonCyan,
                    unfocusedBorderColor = GlassBorder,
                    focusedLabelColor = NeonCyan,
                    unfocusedLabelColor = TextSecondary,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary,
                    focusedTrailingIconColor = NeonCyan,
                    unfocusedTrailingIconColor = TextSecondary,
                ),
            )
            if (availableModels.isNotEmpty()) {
                ExposedDropdownMenu(
                    expanded = modelExpanded,
                    onDismissRequest = { modelExpanded = false },
                    containerColor = Color(0xFF0E0E1C),
                ) {
                    availableModels.forEach { model ->
                        DropdownMenuItem(
                            text = { Text(model, color = TextPrimary, fontFamily = FontFamily.Monospace, fontSize = 13.sp) },
                            onClick = { onModelChange(model); modelExpanded = false },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AiApiKeyCard(
    apiKey: String,
    requiresApiKey: Boolean,
    onApiKeyChange: (String) -> Unit,
) {
    var showKey by remember { mutableStateOf(false) }

    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Key, contentDescription = null, tint = NeonAmber, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("API Anahtari", color = NeonAmber, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            if (!requiresApiKey) {
                Spacer(Modifier.width(8.dp))
                Box(
                    modifier = Modifier
                        .background(NeonGreen.copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                        .padding(horizontal = 6.dp, vertical = 2.dp),
                ) {
                    Text("Gerekli Degil", color = NeonGreen, fontSize = 10.sp)
                }
            }
        }
        Spacer(Modifier.height(12.dp))

        OutlinedTextField(
            value = apiKey,
            onValueChange = onApiKeyChange,
            label = { Text("API Key", fontSize = 12.sp) },
            placeholder = { Text("sk-...", color = TextSecondary) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = requiresApiKey,
            visualTransformation = if (showKey) VisualTransformation.None else PasswordVisualTransformation(),
            trailingIcon = {
                IconButton(onClick = { showKey = !showKey }) {
                    Icon(
                        imageVector = if (showKey) Icons.Outlined.VisibilityOff else Icons.Outlined.Visibility,
                        contentDescription = if (showKey) "Gizle" else "Goster",
                        tint = TextSecondary,
                        modifier = Modifier.size(18.dp),
                    )
                }
            },
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = NeonAmber,
                unfocusedBorderColor = GlassBorder,
                focusedLabelColor = NeonAmber,
                unfocusedLabelColor = TextSecondary,
                focusedTextColor = TextPrimary,
                unfocusedTextColor = TextPrimary,
                cursorColor = NeonAmber,
                disabledBorderColor = GlassBorder.copy(alpha = 0.4f),
                disabledTextColor = TextSecondary,
                disabledLabelColor = TextSecondary.copy(alpha = 0.5f),
            ),
        )
    }
}

@Composable
private fun AiChatSettingsCard(
    chatEnabled: Boolean,
    temperature: Float,
    maxTokens: String,
    dailyLimit: String,
    onChatEnabledChange: (Boolean) -> Unit,
    onTemperatureChange: (Float) -> Unit,
    onMaxTokensChange: (String) -> Unit,
    onDailyLimitChange: (String) -> Unit,
) {
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.Settings, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("Sohbet Ayarlari", color = NeonCyan, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        }
        Spacer(Modifier.height(14.dp))

        // Chat enabled toggle
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("AI Sohbet Aktif", color = TextPrimary, fontSize = 13.sp)
            Switch(
                checked = chatEnabled,
                onCheckedChange = onChatEnabledChange,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = NeonCyan,
                    checkedTrackColor = NeonCyan.copy(alpha = 0.3f),
                    uncheckedThumbColor = TextSecondary,
                    uncheckedTrackColor = GlassBorder,
                ),
            )
        }

        Spacer(Modifier.height(14.dp))

        // Temperature slider
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("Sicaklik (Temperature)", color = TextSecondary, fontSize = 12.sp)
            Text(
                text = "%.2f".format(temperature),
                color = NeonCyan,
                fontSize = 12.sp,
                fontFamily = FontFamily.Monospace,
            )
        }
        Slider(
            value = temperature,
            onValueChange = onTemperatureChange,
            valueRange = 0f..2f,
            steps = 39,
            modifier = Modifier.fillMaxWidth(),
            colors = SliderDefaults.colors(
                thumbColor = NeonCyan,
                activeTrackColor = NeonCyan,
                inactiveTrackColor = GlassBorder,
            ),
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("0.0 (Kesin)", color = TextSecondary, fontSize = 10.sp)
            Text("2.0 (Yaratici)", color = TextSecondary, fontSize = 10.sp)
        }

        Spacer(Modifier.height(14.dp))

        // Max tokens + Daily limit in a row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            OutlinedTextField(
                value = maxTokens,
                onValueChange = onMaxTokensChange,
                label = { Text("Max Token", fontSize = 11.sp) },
                modifier = Modifier.weight(1f),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = NeonCyan,
                    unfocusedBorderColor = GlassBorder,
                    focusedLabelColor = NeonCyan,
                    unfocusedLabelColor = TextSecondary,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary,
                    cursorColor = NeonCyan,
                ),
            )
            OutlinedTextField(
                value = dailyLimit,
                onValueChange = onDailyLimitChange,
                label = { Text("Gunluk Limit", fontSize = 11.sp) },
                modifier = Modifier.weight(1f),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = NeonAmber,
                    unfocusedBorderColor = GlassBorder,
                    focusedLabelColor = NeonAmber,
                    unfocusedLabelColor = TextSecondary,
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary,
                    cursorColor = NeonAmber,
                ),
            )
        }
    }
}

@Composable
private fun AiLogAnalysisCard(
    enabled: Boolean,
    interval: String,
    onEnabledChange: (Boolean) -> Unit,
    onIntervalChange: (String) -> Unit,
) {
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.BarChart, contentDescription = null, tint = NeonGreen, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("Log Analizi", color = NeonGreen, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        }
        Spacer(Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("Otomatik Log Analizi", color = TextPrimary, fontSize = 13.sp)
            Switch(
                checked = enabled,
                onCheckedChange = onEnabledChange,
                colors = SwitchDefaults.colors(
                    checkedThumbColor = NeonGreen,
                    checkedTrackColor = NeonGreen.copy(alpha = 0.3f),
                    uncheckedThumbColor = TextSecondary,
                    uncheckedTrackColor = GlassBorder,
                ),
            )
        }

        Spacer(Modifier.height(10.dp))

        OutlinedTextField(
            value = interval,
            onValueChange = onIntervalChange,
            label = { Text("Analiz Araligi (dakika)", fontSize = 12.sp) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = enabled,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = NeonGreen,
                unfocusedBorderColor = GlassBorder,
                focusedLabelColor = NeonGreen,
                unfocusedLabelColor = TextSecondary,
                focusedTextColor = TextPrimary,
                unfocusedTextColor = TextPrimary,
                cursorColor = NeonGreen,
                disabledBorderColor = GlassBorder.copy(alpha = 0.4f),
                disabledTextColor = TextSecondary,
                disabledLabelColor = TextSecondary.copy(alpha = 0.5f),
            ),
        )
    }
}

@Composable
private fun AiStatsCard(state: AiSettingsUiState) {
    GlassCard(glowColor = NeonCyan.copy(alpha = 0.3f)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.BarChart, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("Kullanim Istatistikleri", color = NeonCyan, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        }
        Spacer(Modifier.height(12.dp))

        val s = state.stats
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            AiStatItem(
                label = "Bugun",
                value = "${s.requestsToday} / ${s.dailyLimit}",
                color = if (s.requestsToday >= s.dailyLimit) NeonRed else NeonGreen,
                modifier = Modifier.weight(1f),
            )
            AiStatItem(
                label = "Toplam",
                value = "${s.totalRequests}",
                color = NeonCyan,
                modifier = Modifier.weight(1f),
            )
        }
        Spacer(Modifier.height(8.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            AiStatItem(
                label = "Token",
                value = formatLargeNumber(s.totalTokensUsed),
                color = NeonMagenta,
                modifier = Modifier.weight(1f),
            )
            AiStatItem(
                label = "Ort. Sure",
                value = "${s.avgResponseTimeMs.roundToInt()}ms",
                color = NeonAmber,
                modifier = Modifier.weight(1f),
            )
        }
        s.lastRequest?.let {
            Spacer(Modifier.height(6.dp))
            Text("Son istek: $it", color = TextSecondary, fontSize = 10.sp)
        }
    }
}

@Composable
private fun AiStatItem(
    label: String,
    value: String,
    color: Color,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .background(color.copy(alpha = 0.08f), RoundedCornerShape(8.dp))
            .padding(10.dp),
    ) {
        Column {
            Text(text = label, color = TextSecondary, fontSize = 10.sp)
            Spacer(Modifier.height(2.dp))
            Text(
                text = value,
                color = color,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
                fontFamily = FontFamily.Monospace,
            )
        }
    }
}

@Composable
private fun AiActionsCard(
    isDirty: Boolean,
    isTestLoading: Boolean,
    testResult: com.tonbil.aifirewall.data.remote.dto.AiTestResponseDto?,
    onSave: () -> Unit,
    onTest: () -> Unit,
    onResetCounter: () -> Unit,
    onDismissTest: () -> Unit,
) {
    GlassCard {
        // Save button
        Button(
            onClick = onSave,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = NeonCyan.copy(alpha = if (isDirty) 0.25f else 0.1f),
                contentColor = if (isDirty) NeonCyan else TextSecondary,
            ),
            shape = RoundedCornerShape(8.dp),
        ) {
            Icon(Icons.Outlined.Save, contentDescription = null, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                text = if (isDirty) "Degisiklikleri Kaydet" else "Kaydedildi",
                fontWeight = FontWeight.SemiBold,
            )
        }

        Spacer(Modifier.height(8.dp))

        // Test button
        Button(
            onClick = onTest,
            modifier = Modifier.fillMaxWidth(),
            enabled = !isTestLoading,
            colors = ButtonDefaults.buttonColors(
                containerColor = NeonMagenta.copy(alpha = 0.2f),
                contentColor = NeonMagenta,
            ),
            shape = RoundedCornerShape(8.dp),
        ) {
            if (isTestLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    color = NeonMagenta,
                    strokeWidth = 2.dp,
                )
                Spacer(Modifier.width(8.dp))
                Text("Test Ediliyor...")
            } else {
                Icon(Icons.Outlined.PlayArrow, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(8.dp))
                Text("Baglantiy Test Et", fontWeight = FontWeight.SemiBold)
            }
        }

        // Test result
        testResult?.let { result ->
            Spacer(Modifier.height(10.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        if (result.success) NeonGreen.copy(alpha = 0.1f) else NeonRed.copy(alpha = 0.1f),
                        RoundedCornerShape(8.dp),
                    )
                    .padding(10.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = if (result.success) Icons.Outlined.CheckCircle else Icons.Outlined.Error,
                            contentDescription = null,
                            tint = if (result.success) NeonGreen else NeonRed,
                            modifier = Modifier.size(14.dp),
                        )
                        Spacer(Modifier.width(4.dp))
                        Text(
                            text = if (result.success) "Basarili" else "Basarisiz",
                            color = if (result.success) NeonGreen else NeonRed,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 12.sp,
                        )
                    }
                    Text(text = result.message, color = TextSecondary, fontSize = 11.sp)
                    if (result.success) {
                        Text(
                            text = "${result.responseTimeMs}ms · ${result.model}",
                            color = TextSecondary,
                            fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                }
                TextButton(onClick = onDismissTest) {
                    Text("Kapat", color = TextSecondary, fontSize = 11.sp)
                }
            }
        }

        Spacer(Modifier.height(8.dp))

        // Reset counter button
        Button(
            onClick = onResetCounter,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = NeonAmber.copy(alpha = 0.15f),
                contentColor = NeonAmber,
            ),
            shape = RoundedCornerShape(8.dp),
        ) {
            Icon(Icons.Outlined.RestartAlt, contentDescription = null, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
            Text("Gunluk Sayaci Sifirla", fontWeight = FontWeight.SemiBold)
        }
    }
}

private fun formatLargeNumber(n: Long): String = when {
    n >= 1_000_000 -> "%.1fM".format(n / 1_000_000.0)
    n >= 1_000 -> "%.1fK".format(n / 1_000.0)
    else -> n.toString()
}
