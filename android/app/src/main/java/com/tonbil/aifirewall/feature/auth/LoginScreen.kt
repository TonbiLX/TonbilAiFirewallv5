package com.tonbil.aifirewall.feature.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.fragment.app.FragmentActivity
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.DarkSurface
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import org.koin.androidx.compose.koinViewModel

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit,
    onNavigateToServerSettings: () -> Unit,
    viewModel: LoginViewModel = koinViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val activity = context as? FragmentActivity
    val focusManager = LocalFocusManager.current
    val cyberpunk = CyberpunkTheme.colors

    // Handle successful login
    LaunchedEffect(state.isLoginSuccess) {
        if (state.isLoginSuccess) {
            if (state.showBiometricOnly) {
                // Returning user with biometric — already authenticated
                onLoginSuccess()
            } else if (activity != null && viewModel.shouldOfferBiometric(context)) {
                // First login — offer biometric enrollment
                BiometricHelper.authenticate(
                    activity = activity,
                    onSuccess = {
                        viewModel.onBiometricResult(true)
                        onLoginSuccess()
                    },
                    onError = {
                        // Biometric optional — continue without
                        onLoginSuccess()
                    },
                )
            } else {
                onLoginSuccess()
            }
        }
    }

    // Auto-trigger biometric for returning users
    LaunchedEffect(state.showBiometricOnly) {
        if (state.showBiometricOnly && activity != null) {
            BiometricHelper.authenticate(
                activity = activity,
                onSuccess = { viewModel.onBiometricLoginSuccess() },
                onError = { /* User pressed "Sifre ile giris" — stays on screen */ },
            )
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(DarkBackground, DarkSurface, DarkBackground),
                )
            ),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            // Logo
            Icon(
                imageVector = Icons.Default.Shield,
                contentDescription = "TonbilAiOS",
                tint = NeonCyan,
                modifier = Modifier.size(72.dp),
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "TonbilAiOS",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold,
                color = NeonCyan,
            )

            Spacer(modifier = Modifier.height(32.dp))

            if (state.showBiometricOnly) {
                // Biometric-only mode for returning users
                BiometricOnlyContent(
                    onRetryBiometric = {
                        if (activity != null) {
                            BiometricHelper.authenticate(
                                activity = activity,
                                onSuccess = { viewModel.onBiometricLoginSuccess() },
                                onError = { /* stays on screen */ },
                            )
                        }
                    },
                    onSwitchToPassword = { viewModel.switchToPasswordLogin() },
                    cyberpunk = cyberpunk,
                )
            } else {
                // Standard login form
                LoginFormContent(
                    state = state,
                    onUsernameChange = viewModel::onUsernameChange,
                    onPasswordChange = viewModel::onPasswordChange,
                    onTogglePasswordVisibility = viewModel::togglePasswordVisibility,
                    onLogin = {
                        focusManager.clearFocus()
                        viewModel.login()
                    },
                    onNextField = { focusManager.moveFocus(FocusDirection.Down) },
                    cyberpunk = cyberpunk,
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Server settings button
            TextButton(
                onClick = onNavigateToServerSettings,
            ) {
                Icon(
                    imageVector = Icons.Default.Settings,
                    contentDescription = null,
                    tint = NeonMagenta,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(modifier = Modifier.size(8.dp))
                Text(
                    text = "Sunucu Ayarlari",
                    color = NeonMagenta,
                )
            }
        }
    }
}

@Composable
private fun BiometricOnlyContent(
    onRetryBiometric: () -> Unit,
    onSwitchToPassword: () -> Unit,
    cyberpunk: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    GlassCard(
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Icon(
                imageVector = Icons.Default.Fingerprint,
                contentDescription = "Biyometrik giris",
                tint = NeonCyan,
                modifier = Modifier.size(64.dp),
            )

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "Dokunarak Giris Yap",
                style = MaterialTheme.typography.titleMedium,
                color = NeonCyan,
            )

            Spacer(modifier = Modifier.height(24.dp))

            FilledTonalButton(
                onClick = onRetryBiometric,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = NeonCyan.copy(alpha = 0.15f),
                    contentColor = NeonCyan,
                ),
            ) {
                Icon(
                    imageVector = Icons.Default.Fingerprint,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(modifier = Modifier.size(8.dp))
                Text("Tekrar Dene")
            }

            Spacer(modifier = Modifier.height(12.dp))

            TextButton(onClick = onSwitchToPassword) {
                Text(
                    text = "Sifre ile Giris",
                    color = NeonMagenta,
                )
            }
        }
    }
}

@Composable
private fun LoginFormContent(
    state: LoginUiState,
    onUsernameChange: (String) -> Unit,
    onPasswordChange: (String) -> Unit,
    onTogglePasswordVisibility: () -> Unit,
    onLogin: () -> Unit,
    onNextField: () -> Unit,
    cyberpunk: com.tonbil.aifirewall.ui.theme.CyberpunkColors,
) {
    val textFieldColors = OutlinedTextFieldDefaults.colors(
        focusedBorderColor = NeonCyan,
        unfocusedBorderColor = cyberpunk.glassBorder,
        focusedLabelColor = NeonCyan,
        unfocusedLabelColor = cyberpunk.glassBorder,
        cursorColor = NeonCyan,
        focusedLeadingIconColor = NeonCyan,
        unfocusedLeadingIconColor = cyberpunk.glassBorder,
        focusedTrailingIconColor = NeonCyan,
        unfocusedTrailingIconColor = cyberpunk.glassBorder,
    )

    GlassCard(
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
        ) {
            OutlinedTextField(
                value = state.username,
                onValueChange = onUsernameChange,
                label = { Text("Kullanici Adi") },
                leadingIcon = {
                    Icon(Icons.Default.Person, contentDescription = null)
                },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = textFieldColors,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                keyboardActions = KeyboardActions(onNext = { onNextField() }),
                enabled = !state.isLoading,
            )

            Spacer(modifier = Modifier.height(16.dp))

            OutlinedTextField(
                value = state.password,
                onValueChange = onPasswordChange,
                label = { Text("Sifre") },
                leadingIcon = {
                    Icon(Icons.Default.Lock, contentDescription = null)
                },
                trailingIcon = {
                    IconButton(onClick = onTogglePasswordVisibility) {
                        Icon(
                            imageVector = if (state.passwordVisible) {
                                Icons.Default.VisibilityOff
                            } else {
                                Icons.Default.Visibility
                            },
                            contentDescription = if (state.passwordVisible) "Gizle" else "Goster",
                        )
                    }
                },
                singleLine = true,
                visualTransformation = if (state.passwordVisible) {
                    VisualTransformation.None
                } else {
                    PasswordVisualTransformation()
                },
                modifier = Modifier.fillMaxWidth(),
                colors = textFieldColors,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { onLogin() }),
                enabled = !state.isLoading,
            )

            // Error message
            if (state.errorMessage != null) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = state.errorMessage,
                    color = NeonRed,
                    style = MaterialTheme.typography.bodySmall,
                )
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Login button
            FilledTonalButton(
                onClick = onLogin,
                modifier = Modifier.fillMaxWidth(),
                enabled = !state.isLoading,
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = NeonCyan.copy(alpha = 0.15f),
                    contentColor = NeonCyan,
                    disabledContainerColor = Color.Gray.copy(alpha = 0.1f),
                    disabledContentColor = Color.Gray,
                ),
            ) {
                if (state.isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = NeonCyan,
                        strokeWidth = 2.dp,
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                }
                Text("Giris Yap")
            }
        }
    }
}
