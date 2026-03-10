package com.tonbil.aifirewall.feature.tls

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
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Email
import androidx.compose.material.icons.outlined.Error
import androidx.compose.material.icons.outlined.Key
import androidx.compose.material.icons.outlined.Language
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Security
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.data.remote.dto.TlsConfigUpdateDto
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TlsScreen(
    onBack: () -> Unit,
    viewModel: TlsViewModel = koinViewModel(),
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
                            imageVector = Icons.Outlined.Lock,
                            contentDescription = null,
                            tint = NeonCyan,
                            modifier = Modifier.size(20.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            text = "TLS / DNS-over-TLS",
                            color = NeonCyan,
                            fontWeight = FontWeight.Bold,
                        )
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
                            modifier = Modifier.size(20.dp).padding(end = 16.dp),
                            color = NeonCyan,
                            strokeWidth = 2.dp,
                        )
                    }
                    IconButton(onClick = viewModel::loadConfig) {
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
                CircularProgressIndicator(color = NeonCyan)
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        listOf(DarkBackground, Color(0xFF0A0A1A), DarkBackground),
                    )
                )
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            // Status card
            TlsStatusCard(
                enabled = state.config.enabled,
                certValid = state.config.certValid,
                onToggle = viewModel::toggle,
            )

            // Certificate info card
            TlsCertInfoCard(
                issuer = state.config.certIssuer,
                subject = state.config.certSubject,
                expiry = state.config.certExpiry,
            )

            // Upstream DoT card
            TlsUpstreamCard(
                upstreamDot = state.config.upstreamDot,
                upstreamServer = state.config.upstreamServer ?: "",
                onSave = { dotEnabled, server ->
                    viewModel.updateConfig(
                        TlsConfigUpdateDto(
                            upstreamDot = dotEnabled,
                            upstreamServer = server.ifBlank { null },
                        )
                    )
                },
            )

            // Actions card
            TlsActionsCard(
                onShowCertDialog = viewModel::showCertDialog,
                onShowLetsEncryptDialog = viewModel::showLetsEncryptDialog,
            )

            // Validate result card
            state.validateResult?.let { result ->
                TlsValidateResultCard(
                    valid = result.valid,
                    message = result.message,
                    issuer = result.issuer,
                    expiry = result.expiry,
                    onDismiss = viewModel::clearValidateResult,
                )
            }
        }
    }

    // Certificate paste dialog
    if (state.showCertDialog) {
        TlsCertDialog(
            onDismiss = viewModel::hideCertDialog,
            onValidate = { cert, key -> viewModel.validate(cert, key) },
            onUpload = { cert, key -> viewModel.uploadCert(cert, key) },
        )
    }

    // Let's Encrypt dialog
    if (state.showLetsEncryptDialog) {
        TlsLetsEncryptDialog(
            onDismiss = viewModel::hideLetsEncryptDialog,
            onSubmit = { domain, email -> viewModel.letsEncrypt(domain, email) },
        )
    }
}

@Composable
private fun TlsStatusCard(
    enabled: Boolean,
    certValid: Boolean,
    onToggle: () -> Unit,
) {
    GlassCard(glowColor = if (enabled) NeonGreen else NeonRed) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text(
                    text = "DNS-over-TLS Durumu",
                    color = TextSecondary,
                    fontSize = 12.sp,
                )
                Spacer(Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (enabled) Icons.Outlined.CheckCircle else Icons.Outlined.Error,
                        contentDescription = null,
                        tint = if (enabled) NeonGreen else NeonRed,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = if (enabled) "AKTIF" else "PASIF",
                        color = if (enabled) NeonGreen else NeonRed,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                        fontFamily = FontFamily.Monospace,
                    )
                }
            }

            Column(horizontalAlignment = Alignment.End) {
                // Certificate validity badge
                Box(
                    modifier = Modifier
                        .background(
                            color = if (certValid) NeonGreen.copy(alpha = 0.15f) else NeonAmber.copy(alpha = 0.15f),
                            shape = RoundedCornerShape(8.dp),
                        )
                        .padding(horizontal = 10.dp, vertical = 4.dp),
                ) {
                    Text(
                        text = if (certValid) "Sertifika Gecerli" else "Sertifika Yok",
                        color = if (certValid) NeonGreen else NeonAmber,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
                Spacer(Modifier.height(8.dp))
                Switch(
                    checked = enabled,
                    onCheckedChange = { onToggle() },
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = NeonGreen,
                        checkedTrackColor = NeonGreen.copy(alpha = 0.3f),
                        uncheckedThumbColor = TextSecondary,
                        uncheckedTrackColor = GlassBorder,
                    ),
                )
            }
        }
    }
}

@Composable
private fun TlsCertInfoCard(
    issuer: String?,
    subject: String?,
    expiry: String?,
) {
    GlassCard(glowColor = NeonCyan.copy(alpha = 0.5f)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Outlined.Shield,
                contentDescription = null,
                tint = NeonCyan,
                modifier = Modifier.size(18.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                text = "Sertifika Bilgileri",
                color = NeonCyan,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp,
            )
        }
        Spacer(Modifier.height(12.dp))

        TlsInfoRow(label = "Issuer", value = issuer ?: "-")
        Spacer(Modifier.height(6.dp))
        TlsInfoRow(label = "Subject", value = subject ?: "-")
        Spacer(Modifier.height(6.dp))
        TlsInfoRow(label = "Son Gecerlilik", value = expiry ?: "-")
    }
}

@Composable
private fun TlsInfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(text = label, color = TextSecondary, fontSize = 12.sp)
        Text(
            text = value,
            color = TextPrimary,
            fontSize = 12.sp,
            fontFamily = FontFamily.Monospace,
        )
    }
}

@Composable
private fun TlsUpstreamCard(
    upstreamDot: Boolean,
    upstreamServer: String,
    onSave: (Boolean, String) -> Unit,
) {
    var dotEnabled by remember(upstreamDot) { mutableStateOf(upstreamDot) }
    var serverText by remember(upstreamServer) { mutableStateOf(upstreamServer) }

    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Outlined.Language,
                contentDescription = null,
                tint = NeonMagenta,
                modifier = Modifier.size(18.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                text = "Upstream DoT",
                color = NeonMagenta,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp,
            )
        }
        Spacer(Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(text = "Upstream DoT Aktif", color = TextPrimary, fontSize = 13.sp)
            Switch(
                checked = dotEnabled,
                onCheckedChange = { dotEnabled = it },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = NeonMagenta,
                    checkedTrackColor = NeonMagenta.copy(alpha = 0.3f),
                    uncheckedThumbColor = TextSecondary,
                    uncheckedTrackColor = GlassBorder,
                ),
            )
        }

        Spacer(Modifier.height(10.dp))

        OutlinedTextField(
            value = serverText,
            onValueChange = { serverText = it },
            label = { Text("Sunucu Adresi", fontSize = 12.sp) },
            placeholder = { Text("1.1.1.1", color = TextSecondary) },
            modifier = Modifier.fillMaxWidth(),
            enabled = dotEnabled,
            singleLine = true,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = NeonMagenta,
                unfocusedBorderColor = GlassBorder,
                focusedLabelColor = NeonMagenta,
                unfocusedLabelColor = TextSecondary,
                focusedTextColor = TextPrimary,
                unfocusedTextColor = TextPrimary,
                cursorColor = NeonMagenta,
            ),
        )

        Spacer(Modifier.height(12.dp))

        Button(
            onClick = { onSave(dotEnabled, serverText) },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = NeonMagenta.copy(alpha = 0.2f),
                contentColor = NeonMagenta,
            ),
            shape = RoundedCornerShape(8.dp),
        ) {
            Text("Kaydet", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun TlsActionsCard(
    onShowCertDialog: () -> Unit,
    onShowLetsEncryptDialog: () -> Unit,
) {
    GlassCard {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Outlined.Key,
                contentDescription = null,
                tint = NeonAmber,
                modifier = Modifier.size(18.dp),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                text = "Sertifika Islemleri",
                color = NeonAmber,
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp,
            )
        }
        Spacer(Modifier.height(14.dp))

        Button(
            onClick = onShowCertDialog,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = NeonCyan.copy(alpha = 0.15f),
                contentColor = NeonCyan,
            ),
            shape = RoundedCornerShape(8.dp),
        ) {
            Icon(Icons.Outlined.Security, contentDescription = null, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
            Text("Sertifika Yapistir", fontWeight = FontWeight.SemiBold)
        }

        Spacer(Modifier.height(8.dp))

        Button(
            onClick = onShowLetsEncryptDialog,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = NeonGreen.copy(alpha = 0.15f),
                contentColor = NeonGreen,
            ),
            shape = RoundedCornerShape(8.dp),
        ) {
            Icon(Icons.Outlined.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
            Spacer(Modifier.width(8.dp))
            Text("Let's Encrypt", fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun TlsValidateResultCard(
    valid: Boolean,
    message: String,
    issuer: String?,
    expiry: String?,
    onDismiss: () -> Unit,
) {
    GlassCard(glowColor = if (valid) NeonGreen else NeonRed) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (valid) Icons.Outlined.CheckCircle else Icons.Outlined.Error,
                        contentDescription = null,
                        tint = if (valid) NeonGreen else NeonRed,
                        modifier = Modifier.size(16.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text(
                        text = "Dogrulama Sonucu",
                        color = if (valid) NeonGreen else NeonRed,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 13.sp,
                    )
                }
                Spacer(Modifier.height(8.dp))
                Text(text = message, color = TextPrimary, fontSize = 12.sp)
                issuer?.let {
                    Spacer(Modifier.height(4.dp))
                    Text(text = "Issuer: $it", color = TextSecondary, fontSize = 11.sp)
                }
                expiry?.let {
                    Spacer(Modifier.height(4.dp))
                    Text(text = "Gecerlilik: $it", color = TextSecondary, fontSize = 11.sp)
                }
            }
            TextButton(onClick = onDismiss) {
                Text("Kapat", color = TextSecondary, fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun TlsCertDialog(
    onDismiss: () -> Unit,
    onValidate: (String, String) -> Unit,
    onUpload: (String, String) -> Unit,
) {
    var cert by remember { mutableStateOf("") }
    var key by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF0E0E1C),
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Security, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("Sertifika Yapistir", color = NeonCyan, fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = cert,
                    onValueChange = { cert = it },
                    label = { Text("Sertifika (PEM)", fontSize = 12.sp) },
                    placeholder = { Text("-----BEGIN CERTIFICATE-----", color = TextSecondary, fontSize = 11.sp) },
                    modifier = Modifier.fillMaxWidth().height(140.dp),
                    maxLines = 8,
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
                    value = key,
                    onValueChange = { key = it },
                    label = { Text("Ozel Anahtar (PEM)", fontSize = 12.sp) },
                    placeholder = { Text("-----BEGIN PRIVATE KEY-----", color = TextSecondary, fontSize = 11.sp) },
                    modifier = Modifier.fillMaxWidth().height(140.dp),
                    maxLines = 8,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = NeonMagenta,
                        unfocusedBorderColor = GlassBorder,
                        focusedLabelColor = NeonMagenta,
                        unfocusedLabelColor = TextSecondary,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        cursorColor = NeonMagenta,
                    ),
                )
            }
        },
        confirmButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(
                    onClick = { onValidate(cert, key) },
                    enabled = cert.isNotBlank() && key.isNotBlank(),
                ) {
                    Text("Dogrula", color = NeonAmber)
                }
                Button(
                    onClick = { onUpload(cert, key) },
                    enabled = cert.isNotBlank() && key.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = NeonCyan.copy(alpha = 0.2f),
                        contentColor = NeonCyan,
                    ),
                ) {
                    Text("Yukle")
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = TextSecondary)
            }
        },
    )
}

@Composable
private fun TlsLetsEncryptDialog(
    onDismiss: () -> Unit,
    onSubmit: (String, String) -> Unit,
) {
    var domain by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Color(0xFF0E0E1C),
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.CheckCircle, contentDescription = null, tint = NeonGreen, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("Let's Encrypt", color = NeonGreen, fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = domain,
                    onValueChange = { domain = it },
                    label = { Text("Domain", fontSize = 12.sp) },
                    placeholder = { Text("router.example.com", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    leadingIcon = {
                        Icon(Icons.Outlined.Language, contentDescription = null, tint = NeonGreen, modifier = Modifier.size(18.dp))
                    },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = NeonGreen,
                        unfocusedBorderColor = GlassBorder,
                        focusedLabelColor = NeonGreen,
                        unfocusedLabelColor = TextSecondary,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        cursorColor = NeonGreen,
                    ),
                )
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("E-posta", fontSize = 12.sp) },
                    placeholder = { Text("admin@example.com", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    leadingIcon = {
                        Icon(Icons.Outlined.Email, contentDescription = null, tint = NeonGreen, modifier = Modifier.size(18.dp))
                    },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = NeonGreen,
                        unfocusedBorderColor = GlassBorder,
                        focusedLabelColor = NeonGreen,
                        unfocusedLabelColor = TextSecondary,
                        focusedTextColor = TextPrimary,
                        unfocusedTextColor = TextPrimary,
                        cursorColor = NeonGreen,
                    ),
                )
                Text(
                    text = "Domain internetten erisebilir olmali ve port 80/443 acik olmalidir.",
                    color = TextSecondary,
                    fontSize = 11.sp,
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onSubmit(domain, email) },
                enabled = domain.isNotBlank() && email.isNotBlank(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = NeonGreen.copy(alpha = 0.2f),
                    contentColor = NeonGreen,
                ),
            ) {
                Text("Baslat")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = TextSecondary)
            }
        },
    )
}
