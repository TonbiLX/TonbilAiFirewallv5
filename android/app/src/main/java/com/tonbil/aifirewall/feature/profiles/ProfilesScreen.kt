package com.tonbil.aifirewall.feature.profiles

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.Speed
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.ProfileResponseDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.DarkSurface
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
fun ProfilesScreen(
    onBack: () -> Unit,
    viewModel: ProfilesViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(state.actionMessage) {
        state.actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }

    // Add dialog
    if (state.showAddDialog) {
        AddProfileDialog(
            name = state.addName,
            bandwidth = state.addBandwidth,
            isAdding = state.isAdding,
            onNameChange = viewModel::setAddName,
            onBandwidthChange = viewModel::setAddBandwidth,
            onConfirm = viewModel::createProfile,
            onDismiss = viewModel::dismissAddDialog,
        )
    }

    // Delete confirmation
    state.deleteTarget?.let { target ->
        AlertDialog(
            onDismissRequest = viewModel::dismissDeleteConfirm,
            containerColor = DarkSurface,
            title = { Text("Profili Sil", color = NeonRed) },
            text = {
                Text(
                    "'${target.name}' profili silinecek. Bu islem geri alinamaz.",
                    color = TextPrimary,
                )
            },
            confirmButton = {
                TextButton(
                    onClick = viewModel::deleteProfile,
                    enabled = !state.isDeleting,
                ) {
                    if (state.isDeleting) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), color = NeonRed, strokeWidth = 2.dp)
                    } else {
                        Text("Sil", color = NeonRed)
                    }
                }
            },
            dismissButton = {
                TextButton(onClick = viewModel::dismissDeleteConfirm) {
                    Text("Iptal", color = TextSecondary)
                }
            },
        )
    }

    Scaffold(
        containerColor = DarkBackground,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Outlined.Person,
                            contentDescription = null,
                            tint = NeonGreen,
                            modifier = Modifier.size(20.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text("Profiller", color = NeonGreen, fontWeight = FontWeight.Bold)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Geri", tint = TextSecondary)
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::load) {
                        Icon(Icons.Outlined.Refresh, contentDescription = "Yenile", tint = TextSecondary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground),
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = viewModel::showAddDialog,
                containerColor = NeonGreen.copy(alpha = 0.2f),
                contentColor = NeonGreen,
            ) {
                Icon(Icons.Outlined.Add, contentDescription = "Profil Ekle")
            }
        },
    ) { paddingValues ->
        if (state.isLoading) {
            Box(
                modifier = Modifier.fillMaxSize().padding(paddingValues),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = NeonGreen)
            }
            return@Scaffold
        }

        state.error?.let { error ->
            Box(
                modifier = Modifier.fillMaxSize().padding(paddingValues),
                contentAlignment = Alignment.Center,
            ) {
                Text(text = error, color = NeonAmber, fontSize = 14.sp)
            }
            return@Scaffold
        }

        if (state.profiles.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize().padding(paddingValues),
                contentAlignment = Alignment.Center,
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(
                        imageVector = Icons.Outlined.Person,
                        contentDescription = null,
                        tint = TextSecondary.copy(alpha = 0.4f),
                        modifier = Modifier.size(48.dp),
                    )
                    Spacer(Modifier.height(12.dp))
                    Text("Henuz profil yok", color = TextSecondary, fontSize = 14.sp)
                    Text("Yeni profil olusturmak icin + butonuna basin", color = TextSecondary.copy(alpha = 0.6f), fontSize = 12.sp)
                }
            }
            return@Scaffold
        }

        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(listOf(DarkBackground, Color(0xFF0A0A1A), DarkBackground))
                )
                .padding(paddingValues)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 12.dp),
        ) {
            items(state.profiles, key = { it.id }) { profile ->
                ProfileCard(
                    profile = profile,
                    onDelete = { viewModel.showDeleteConfirm(profile) },
                )
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ProfileCard(
    profile: ProfileResponseDto,
    onDelete: () -> Unit,
) {
    GlassCard(glowColor = NeonGreen.copy(alpha = 0.3f)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = profile.name,
                    color = TextPrimary,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 15.sp,
                )
                profile.profileType?.let { type ->
                    Text(
                        text = type,
                        color = NeonGreen,
                        fontSize = 11.sp,
                    )
                }
            }
            IconButton(onClick = onDelete) {
                Icon(Icons.Outlined.DeleteOutline, contentDescription = "Sil", tint = NeonRed.copy(alpha = 0.7f), modifier = Modifier.size(20.dp))
            }
        }

        // Bandwidth limit
        profile.bandwidthLimitMbps?.let { bw ->
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Speed, contentDescription = null, tint = NeonAmber, modifier = Modifier.size(14.dp))
                Spacer(Modifier.width(6.dp))
                Text("Bant Genisligi: ", color = TextSecondary, fontSize = 12.sp)
                Text(
                    text = "${bw.toInt()} Mbps",
                    color = NeonAmber,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    fontFamily = FontFamily.Monospace,
                )
            }
        }

        // Content filters
        if (profile.contentFilters.isNotEmpty()) {
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Shield, contentDescription = null, tint = NeonMagenta, modifier = Modifier.size(14.dp))
                Spacer(Modifier.width(6.dp))
                Text("Icerik Filtreleri:", color = TextSecondary, fontSize = 12.sp)
            }
            Spacer(Modifier.height(6.dp))
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                profile.contentFilters.forEach { filter ->
                    FilterChip(label = filter)
                }
            }
        }
    }
}

@Composable
private fun FilterChip(label: String) {
    val color = when {
        label.contains("adult", ignoreCase = true) -> NeonRed
        label.contains("gambling", ignoreCase = true) -> NeonAmber
        label.contains("social", ignoreCase = true) -> NeonCyan
        label.contains("malware", ignoreCase = true) -> NeonRed
        else -> NeonMagenta
    }

    Box(
        modifier = Modifier
            .background(color.copy(alpha = 0.12f), RoundedCornerShape(6.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
    ) {
        Text(
            text = label,
            color = color,
            fontSize = 11.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}

@Composable
private fun AddProfileDialog(
    name: String,
    bandwidth: String,
    isAdding: Boolean,
    onNameChange: (String) -> Unit,
    onBandwidthChange: (String) -> Unit,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = DarkSurface,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Outlined.Add, contentDescription = null, tint = NeonGreen, modifier = Modifier.size(20.dp))
                Spacer(Modifier.width(8.dp))
                Text("Yeni Profil", color = NeonGreen, fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = onNameChange,
                    label = { Text("Profil Adi", fontSize = 12.sp) },
                    placeholder = { Text("ornegin: Cocuk", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
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
                    value = bandwidth,
                    onValueChange = onBandwidthChange,
                    label = { Text("Bant Genisligi Limiti (Mbps)", fontSize = 12.sp) },
                    placeholder = { Text("ornegin: 50", color = TextSecondary) },
                    modifier = Modifier.fillMaxWidth(),
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
        },
        confirmButton = {
            Button(
                onClick = onConfirm,
                enabled = name.isNotBlank() && !isAdding,
                colors = ButtonDefaults.buttonColors(
                    containerColor = NeonGreen.copy(alpha = 0.2f),
                    contentColor = NeonGreen,
                ),
                shape = RoundedCornerShape(8.dp),
            ) {
                if (isAdding) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), color = NeonGreen, strokeWidth = 2.dp)
                    Spacer(Modifier.width(8.dp))
                }
                Text("Olustur", fontWeight = FontWeight.SemiBold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = TextSecondary)
            }
        },
    )
}
