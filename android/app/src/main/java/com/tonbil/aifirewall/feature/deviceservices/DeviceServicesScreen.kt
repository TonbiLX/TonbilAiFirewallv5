package com.tonbil.aifirewall.feature.deviceservices

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Block
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.Clear
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshDefaults
import androidx.compose.material3.pulltorefresh.pullToRefresh
import androidx.compose.material3.pulltorefresh.rememberPullToRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.DeviceServiceDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import org.koin.androidx.compose.koinViewModel
import org.koin.core.parameter.parametersOf

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceServicesScreen(
    deviceId: Int,
    deviceName: String,
    viewModel: DeviceServicesViewModel = koinViewModel { parametersOf(deviceId) },
    onBack: () -> Unit,
) {
    val uiState by viewModel.state.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val snackbarHostState = remember { SnackbarHostState() }
    val pullToRefreshState = rememberPullToRefreshState()

    LaunchedEffect(uiState.error) {
        uiState.error?.let { msg ->
            snackbarHostState.showSnackbar(msg)
            viewModel.clearError()
        }
    }

    // Filtrelenmis servisler (secili gruba + aramaya gore)
    val filteredServices = remember(uiState.services, uiState.selectedGroup, uiState.searchQuery) {
        var list = uiState.services
        val group = uiState.selectedGroup
        if (group != null) {
            list = list.filter { it.group == group }
        }
        val q = uiState.searchQuery.lowercase()
        if (q.isNotBlank()) {
            list = list.filter { it.displayName.lowercase().contains(q) || it.serviceId.lowercase().contains(q) }
        }
        list
    }

    val blockedCount = filteredServices.count { it.blocked }
    val totalCount = filteredServices.size

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .pullToRefresh(
                    isRefreshing = uiState.isLoading,
                    state = pullToRefreshState,
                    onRefresh = { viewModel.loadAll() },
                ),
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                // Ust bar
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 8.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Outlined.ArrowBack,
                            contentDescription = "Geri",
                            tint = colors.neonCyan,
                        )
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Servis Yonetimi",
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                        Text(
                            text = deviceName,
                            style = MaterialTheme.typography.labelSmall,
                            color = colors.neonCyan,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    // Engellenen / toplam ozeti
                    if (!uiState.isLoading) {
                        Column(horizontalAlignment = Alignment.End) {
                            Text(
                                text = "$blockedCount engelli",
                                style = MaterialTheme.typography.labelSmall,
                                color = colors.neonRed,
                            )
                            Text(
                                text = "$totalCount servis",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                            )
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    IconButton(onClick = { viewModel.loadAll() }) {
                        Icon(
                            imageVector = Icons.Outlined.Refresh,
                            contentDescription = "Yenile",
                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                        )
                    }
                }

                when {
                    uiState.isLoading -> {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center,
                        ) {
                            CircularProgressIndicator(color = colors.neonCyan)
                        }
                    }
                    else -> {
                        // Arama kutusu
                        OutlinedTextField(
                            value = uiState.searchQuery,
                            onValueChange = { viewModel.setSearchQuery(it) },
                            placeholder = { Text("Servis ara...") },
                            leadingIcon = {
                                Icon(
                                    imageVector = Icons.Outlined.Search,
                                    contentDescription = null,
                                    tint = colors.neonCyan,
                                    modifier = Modifier.size(20.dp),
                                )
                            },
                            trailingIcon = {
                                if (uiState.searchQuery.isNotEmpty()) {
                                    IconButton(onClick = { viewModel.setSearchQuery("") }) {
                                        Icon(
                                            imageVector = Icons.Outlined.Clear,
                                            contentDescription = "Temizle",
                                            tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                                        )
                                    }
                                }
                            },
                            singleLine = true,
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = colors.neonCyan,
                                unfocusedBorderColor = colors.glassBorder,
                                cursorColor = colors.neonCyan,
                            ),
                        )

                        // Grup filtre chipler
                        if (uiState.groups.isNotEmpty()) {
                            GroupFilterRow(
                                groups = uiState.groups.map { it.name to it.displayName },
                                selectedGroup = uiState.selectedGroup,
                                onGroupSelected = { viewModel.selectGroup(it) },
                            )
                        }

                        // Servis kartlari grid
                        if (filteredServices.isEmpty()) {
                            Box(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(32.dp),
                                contentAlignment = Alignment.Center,
                            ) {
                                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                    Icon(
                                        imageVector = Icons.Outlined.Settings,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f),
                                        modifier = Modifier.size(56.dp),
                                    )
                                    Spacer(modifier = Modifier.height(16.dp))
                                    Text(
                                        text = "Bu grupta servis yok",
                                        style = MaterialTheme.typography.bodyLarge,
                                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                                    )
                                }
                            }
                        } else {
                            LazyVerticalGrid(
                                columns = GridCells.Fixed(2),
                                contentPadding = PaddingValues(
                                    start = 12.dp,
                                    end = 12.dp,
                                    top = 8.dp,
                                    bottom = 24.dp,
                                ),
                                horizontalArrangement = Arrangement.spacedBy(10.dp),
                                verticalArrangement = Arrangement.spacedBy(10.dp),
                                modifier = Modifier.fillMaxSize(),
                            ) {
                                items(
                                    items = filteredServices,
                                    key = { it.serviceId },
                                ) { service ->
                                    ServiceCard(
                                        service = service,
                                        isToggling = uiState.togglingServiceId == service.serviceId,
                                        onToggle = { blocked ->
                                            viewModel.toggleService(service.serviceId, blocked)
                                        },
                                    )
                                }
                            }
                        }
                    }
                }
            }

            PullToRefreshDefaults.Indicator(
                state = pullToRefreshState,
                isRefreshing = uiState.isLoading,
                modifier = Modifier.align(Alignment.TopCenter),
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun GroupFilterRow(
    groups: List<Pair<String, String>>,
    selectedGroup: String?,
    onGroupSelected: (String?) -> Unit,
) {
    val colors = CyberpunkTheme.colors

    androidx.compose.foundation.lazy.LazyRow(
        contentPadding = PaddingValues(horizontal = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
    ) {
        item {
            FilterChip(
                selected = selectedGroup == null,
                onClick = { onGroupSelected(null) },
                label = { Text("Tumü") },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = colors.neonCyan.copy(alpha = 0.2f),
                    selectedLabelColor = colors.neonCyan,
                    containerColor = Color.Transparent,
                    labelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                ),
                border = FilterChipDefaults.filterChipBorder(
                    enabled = true,
                    selected = selectedGroup == null,
                    selectedBorderColor = colors.neonCyan.copy(alpha = 0.5f),
                    borderColor = colors.glassBorder,
                ),
            )
        }
        items(groups.size) { idx ->
            val (key, displayName) = groups[idx]
            FilterChip(
                selected = selectedGroup == key,
                onClick = { onGroupSelected(key) },
                label = { Text(displayName) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = colors.neonCyan.copy(alpha = 0.2f),
                    selectedLabelColor = colors.neonCyan,
                    containerColor = Color.Transparent,
                    labelColor = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                ),
                border = FilterChipDefaults.filterChipBorder(
                    enabled = true,
                    selected = selectedGroup == key,
                    selectedBorderColor = colors.neonCyan.copy(alpha = 0.5f),
                    borderColor = colors.glassBorder,
                ),
            )
        }
    }
}

@Composable
private fun ServiceCard(
    service: DeviceServiceDto,
    isToggling: Boolean,
    onToggle: (Boolean) -> Unit,
) {
    val colors = CyberpunkTheme.colors
    val isBlocked = service.blocked

    // Servis ikonunu adi'nin ilk 2 harfinden olustur
    val iconLabel = service.displayName
        .split(" ")
        .take(2)
        .mapNotNull { it.firstOrNull()?.toString() }
        .joinToString("")
        .uppercase()
        .ifBlank { service.displayName.take(2).uppercase() }

    val accentColor = if (isBlocked) colors.neonRed else colors.neonGreen

    GlassCard(
        modifier = Modifier.fillMaxWidth(),
        glowColor = accentColor.copy(alpha = 0.4f),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            // Servis ikon dairesel arkaplan
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(accentColor.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center,
            ) {
                if (isToggling) {
                    CircularProgressIndicator(
                        color = accentColor,
                        modifier = Modifier.size(24.dp),
                        strokeWidth = 2.dp,
                    )
                } else {
                    Text(
                        text = iconLabel,
                        style = MaterialTheme.typography.titleSmall,
                        color = accentColor,
                        fontWeight = FontWeight.Bold,
                    )
                }
            }

            // Servis adi
            Text(
                text = service.displayName,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                textAlign = TextAlign.Center,
                fontWeight = FontWeight.Medium,
            )

            // Durum + toggle satiri
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                // Durum badge
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    Icon(
                        imageVector = if (isBlocked) Icons.Outlined.Block else Icons.Outlined.CheckCircle,
                        contentDescription = null,
                        tint = accentColor,
                        modifier = Modifier.size(14.dp),
                    )
                    Text(
                        text = if (isBlocked) "Engelli" else "Izinli",
                        style = MaterialTheme.typography.labelSmall,
                        color = accentColor,
                    )
                }

                // Toggle switch — blocked=NeonRed, allowed=NeonGreen
                Switch(
                    checked = isBlocked,
                    onCheckedChange = { checked -> onToggle(checked) },
                    enabled = !isToggling,
                    colors = SwitchDefaults.colors(
                        checkedThumbColor = Color.White,
                        checkedTrackColor = colors.neonRed.copy(alpha = 0.8f),
                        checkedBorderColor = colors.neonRed,
                        uncheckedThumbColor = Color.White,
                        uncheckedTrackColor = colors.neonGreen.copy(alpha = 0.3f),
                        uncheckedBorderColor = colors.neonGreen.copy(alpha = 0.6f),
                        disabledCheckedTrackColor = colors.neonRed.copy(alpha = 0.4f),
                        disabledUncheckedTrackColor = colors.neonGreen.copy(alpha = 0.15f),
                    ),
                    modifier = Modifier.size(width = 44.dp, height = 24.dp),
                )
            }

            // Grup etiketi
            if (service.group.isNotBlank()) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(4.dp))
                        .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.07f))
                        .padding(horizontal = 6.dp, vertical = 2.dp),
                ) {
                    Text(
                        text = service.group,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}
