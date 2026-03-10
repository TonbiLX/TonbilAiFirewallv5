package com.tonbil.aifirewall.feature.usersettings

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Key
import androidx.compose.material.icons.outlined.Logout
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Save
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
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
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.GlassBg
import com.tonbil.aifirewall.ui.theme.GlassBorder
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonRed
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun UserSettingsScreen(
    onBack: () -> Unit,
    onLogout: () -> Unit,
    viewModel: UserSettingsViewModel = koinViewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    var displayNameField by rememberSaveable(uiState.displayName) { mutableStateOf(uiState.displayName) }

    Scaffold(
        containerColor = DarkBackground,
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Outlined.AccountCircle, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(20.dp))
                        Spacer(Modifier.width(8.dp))
                        Text("Kullanici Ayarlari", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground),
            )
        },
    ) { paddingValues ->
        if (uiState.isLoading) {
            Box(Modifier.fillMaxSize().padding(paddingValues), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = NeonCyan)
            }
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Mesajlar
            uiState.error?.let {
                FeedbackBox(message = it, isError = true)
            }
            uiState.successMessage?.let {
                FeedbackBox(message = it, isError = false)
            }

            // Profil bolumu
            SectionCard(title = "Profil") {
                if (uiState.username.isNotBlank()) {
                    Text(
                        text = "Kullanici adi: ${uiState.username}",
                        color = TextSecondary,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(bottom = 8.dp),
                    )
                }
                OutlinedTextField(
                    value = displayNameField,
                    onValueChange = { displayNameField = it },
                    label = { Text("Goruntu Adi", color = TextSecondary, fontSize = 12.sp) },
                    leadingIcon = { Icon(Icons.Outlined.Person, contentDescription = null, tint = NeonCyan) },
                    colors = neonTextFieldColors(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                Spacer(Modifier.height(8.dp))
                Button(
                    onClick = { viewModel.updateProfile(displayNameField) },
                    enabled = !uiState.isSaving,
                    colors = ButtonDefaults.buttonColors(containerColor = NeonCyan.copy(alpha = 0.2f)),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (uiState.isSaving) {
                        CircularProgressIndicator(color = NeonCyan, modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Outlined.Save, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Kaydet", color = NeonCyan)
                    }
                }
            }

            // Sifre degistirme bolumu
            SectionCard(title = "Guvenlik") {
                Button(
                    onClick = { viewModel.showPasswordDialog() },
                    colors = ButtonDefaults.buttonColors(containerColor = NeonCyan.copy(alpha = 0.15f)),
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(Icons.Outlined.Key, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Sifre Degistir", color = NeonCyan)
                }
            }

            // Uygulama bilgisi
            SectionCard(title = "Uygulama") {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Outlined.Info, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(14.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("TonbilAiOS v5.0 — Android", color = TextSecondary, fontSize = 12.sp)
                }
            }

            Spacer(Modifier.height(8.dp))

            // Cikis butonu
            Button(
                onClick = onLogout,
                colors = ButtonDefaults.buttonColors(containerColor = NeonRed.copy(alpha = 0.2f)),
                shape = RoundedCornerShape(8.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Outlined.Logout, contentDescription = null, tint = NeonRed, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(6.dp))
                Text("Cikis Yap", color = NeonRed, fontWeight = FontWeight.Bold)
            }
        }
    }

    // Sifre degistirme dialog
    if (uiState.showPasswordDialog) {
        ChangePasswordDialog(
            isSaving = uiState.isSaving,
            error = uiState.error,
            onConfirm = { current, new -> viewModel.changePassword(current, new) },
            onDismiss = { viewModel.hidePasswordDialog() },
        )
    }
}

@Composable
private fun SectionCard(title: String, content: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(12.dp))
            .background(GlassBg)
            .border(0.5.dp, GlassBorder, RoundedCornerShape(12.dp))
            .padding(16.dp),
    ) {
        Text(title, color = NeonCyan, fontSize = 12.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(10.dp))
        content()
    }
}

@Composable
private fun FeedbackBox(message: String, isError: Boolean) {
    val color = if (isError) NeonRed else NeonGreen
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(color.copy(alpha = 0.1f), RoundedCornerShape(8.dp))
            .border(0.5.dp, color.copy(alpha = 0.4f), RoundedCornerShape(8.dp))
            .padding(12.dp),
    ) {
        Text(text = message, color = color, fontSize = 12.sp)
    }
}

@Composable
private fun ChangePasswordDialog(
    isSaving: Boolean,
    error: String?,
    onConfirm: (String, String) -> Unit,
    onDismiss: () -> Unit,
) {
    var current by rememberSaveable { mutableStateOf("") }
    var newPw by rememberSaveable { mutableStateOf("") }
    var confirmPw by rememberSaveable { mutableStateOf("") }
    var showCurrent by remember { mutableStateOf(false) }
    var showNew by remember { mutableStateOf(false) }
    var localError by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Text("Sifre Degistir", color = NeonCyan, fontWeight = FontWeight.Bold, fontSize = 16.sp)
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                (error ?: localError)?.let {
                    Text(text = it, color = NeonRed, fontSize = 11.sp)
                }
                OutlinedTextField(
                    value = current,
                    onValueChange = { current = it },
                    label = { Text("Mevcut Sifre", color = TextSecondary, fontSize = 11.sp) },
                    visualTransformation = if (showCurrent) VisualTransformation.None else PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    trailingIcon = {
                        IconButton(onClick = { showCurrent = !showCurrent }) {
                            Icon(
                                imageVector = if (showCurrent) Icons.Outlined.VisibilityOff else Icons.Outlined.Visibility,
                                contentDescription = null,
                                tint = TextSecondary,
                            )
                        }
                    },
                    colors = neonTextFieldColors(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                OutlinedTextField(
                    value = newPw,
                    onValueChange = { newPw = it },
                    label = { Text("Yeni Sifre", color = TextSecondary, fontSize = 11.sp) },
                    visualTransformation = if (showNew) VisualTransformation.None else PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    trailingIcon = {
                        IconButton(onClick = { showNew = !showNew }) {
                            Icon(
                                imageVector = if (showNew) Icons.Outlined.VisibilityOff else Icons.Outlined.Visibility,
                                contentDescription = null,
                                tint = TextSecondary,
                            )
                        }
                    },
                    colors = neonTextFieldColors(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
                OutlinedTextField(
                    value = confirmPw,
                    onValueChange = { confirmPw = it },
                    label = { Text("Yeni Sifre (Tekrar)", color = TextSecondary, fontSize = 11.sp) },
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    colors = neonTextFieldColors(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    localError = when {
                        current.isBlank() -> "Mevcut sifre bos olamaz"
                        newPw.length < 6 -> "Yeni sifre en az 6 karakter olmali"
                        newPw != confirmPw -> "Sifreler eslesmiyor"
                        else -> null
                    }
                    if (localError == null) onConfirm(current, newPw)
                },
                enabled = !isSaving,
                colors = ButtonDefaults.buttonColors(containerColor = NeonCyan.copy(alpha = 0.2f)),
                shape = RoundedCornerShape(8.dp),
            ) {
                if (isSaving) {
                    CircularProgressIndicator(color = NeonCyan, modifier = Modifier.size(14.dp), strokeWidth = 2.dp)
                } else {
                    Text("Degistir", color = NeonCyan)
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun neonTextFieldColors() = OutlinedTextFieldDefaults.colors(
    focusedTextColor = TextPrimary,
    unfocusedTextColor = TextPrimary,
    focusedBorderColor = NeonCyan,
    unfocusedBorderColor = GlassBorder,
    cursorColor = NeonCyan,
    focusedLabelColor = NeonCyan,
    unfocusedLabelColor = TextSecondary,
)
