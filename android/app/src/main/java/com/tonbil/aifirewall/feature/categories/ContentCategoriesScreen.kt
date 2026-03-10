package com.tonbil.aifirewall.feature.categories

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Category
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SwipeToDismissBox
import androidx.compose.material3.SwipeToDismissBoxValue
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberSwipeToDismissBoxState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.BlocklistDto
import com.tonbil.aifirewall.data.remote.dto.ContentCategoryCreateDto
import com.tonbil.aifirewall.data.remote.dto.ContentCategoryDto
import com.tonbil.aifirewall.data.remote.dto.ContentCategoryUpdateDto
import com.tonbil.aifirewall.ui.components.GlassCard
import com.tonbil.aifirewall.ui.theme.CyberpunkTheme
import com.tonbil.aifirewall.ui.theme.NeonAmber
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonGreen
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import kotlinx.coroutines.launch
import org.koin.androidx.compose.koinViewModel

// Renk hex string → Compose Color donusturme
private fun parseHexColor(hex: String): Color {
    return try {
        val cleaned = hex.removePrefix("#")
        val argb = when (cleaned.length) {
            6 -> "FF$cleaned"
            8 -> cleaned
            else -> "FF00F0FF"
        }
        Color(android.graphics.Color.parseColor("#$argb"))
    } catch (_: Exception) {
        NeonCyan
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ContentCategoriesScreen(
    viewModel: ContentCategoriesViewModel = koinViewModel(),
    onBack: () -> Unit,
) {
    val uiState by viewModel.state.collectAsStateWithLifecycle()
    val colors = CyberpunkTheme.colors
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    // Hata mesajini snackbar'da goster
    LaunchedEffect(uiState.error) {
        uiState.error?.let { msg ->
            snackbarHostState.showSnackbar(msg)
            viewModel.clearError()
        }
    }

    // Silme onay dialog state
    var pendingDeleteId by remember { mutableStateOf<Int?>(null) }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = {
            SnackbarHost(snackbarHostState)
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { viewModel.toggleCreateDialog(true) },
                containerColor = colors.neonCyan,
                contentColor = Color.Black,
                shape = CircleShape,
            ) {
                Icon(Icons.Outlined.Add, contentDescription = "Kategori Ekle")
            }
        },
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
        ) {
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
                Text(
                    text = "Icerik Kategorileri",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f),
                )
                Text(
                    text = "${uiState.categories.size} kategori",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    modifier = Modifier.padding(end = 16.dp),
                )
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
                uiState.categories.isEmpty() -> {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center,
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Outlined.Category,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f),
                                modifier = Modifier.size(64.dp),
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            Text(
                                text = "Henuz kategori eklenmemis",
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            )
                            Text(
                                text = "Yeni kategori eklemek icin + butonuna basin",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.35f),
                                modifier = Modifier.padding(top = 4.dp),
                            )
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        items(
                            items = uiState.categories,
                            key = { it.id },
                        ) { category ->
                            SwipeToDeleteWrapper(
                                onDelete = { pendingDeleteId = category.id },
                            ) {
                                CategoryItem(
                                    category = category,
                                    onClick = { viewModel.setEditing(category) },
                                )
                            }
                        }
                        // FAB icin alt bosluk
                        item { Spacer(modifier = Modifier.height(80.dp)) }
                    }
                }
            }
        }
    }

    // Silme onay dialog
    pendingDeleteId?.let { deleteId ->
        val cat = uiState.categories.find { it.id == deleteId }
        AlertDialog(
            onDismissRequest = { pendingDeleteId = null },
            containerColor = MaterialTheme.colorScheme.surface,
            title = {
                Text(
                    text = "Kategoriyi Sil",
                    color = colors.neonRed,
                    style = MaterialTheme.typography.titleMedium,
                )
            },
            text = {
                Text(
                    text = "\"${cat?.name ?: ""}\" kategorisi silinecek. Bu islem geri alinamaz.",
                    color = MaterialTheme.colorScheme.onSurface,
                    style = MaterialTheme.typography.bodyMedium,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.deleteCategory(deleteId)
                        pendingDeleteId = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = colors.neonRed),
                ) {
                    Text("Sil", color = Color.White)
                }
            },
            dismissButton = {
                TextButton(onClick = { pendingDeleteId = null }) {
                    Text("Iptal", color = colors.neonCyan)
                }
            },
        )
    }

    // Yeni kategori olusturma dialog
    if (uiState.showCreateDialog) {
        CategoryFormDialog(
            title = "Yeni Kategori",
            initialCategory = null,
            blocklists = uiState.blocklists,
            onDismiss = { viewModel.toggleCreateDialog(false) },
            onSave = { key, name, icon, color, customDomains, blocklistIds ->
                viewModel.createCategory(
                    ContentCategoryCreateDto(
                        key = key,
                        name = name,
                        icon = icon,
                        color = color,
                        customDomains = customDomains.ifBlank { null },
                        blocklistIds = blocklistIds,
                    )
                )
                viewModel.toggleCreateDialog(false)
            },
        )
    }

    // Duzenleme dialog
    uiState.editingCategory?.let { cat ->
        CategoryFormDialog(
            title = "Kategoriyi Duzenle",
            initialCategory = cat,
            blocklists = uiState.blocklists,
            onDismiss = { viewModel.setEditing(null) },
            onSave = { _, name, icon, color, customDomains, blocklistIds ->
                viewModel.updateCategory(
                    cat.id,
                    ContentCategoryUpdateDto(
                        name = name,
                        icon = icon,
                        color = color,
                        customDomains = customDomains.ifBlank { null },
                        blocklistIds = blocklistIds,
                    )
                )
                viewModel.setEditing(null)
            },
        )
    }
}

@Composable
private fun CategoryItem(
    category: ContentCategoryDto,
    onClick: () -> Unit,
) {
    val colors = CyberpunkTheme.colors
    val categoryColor = remember(category.color) { parseHexColor(category.color) }

    GlassCard(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
        glowColor = if (category.enabled) categoryColor.copy(alpha = 0.5f) else null,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // Renkli daire ikon
            Box(
                modifier = Modifier
                    .size(44.dp)
                    .clip(CircleShape)
                    .background(categoryColor.copy(alpha = 0.2f)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = category.icon.take(2).uppercase(),
                    style = MaterialTheme.typography.labelLarge,
                    color = categoryColor,
                    fontWeight = FontWeight.Bold,
                )
            }

            // Ad ve domain sayisi
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = category.name,
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    // Domain sayisi badge
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(colors.neonCyan.copy(alpha = 0.12f))
                            .padding(horizontal = 6.dp, vertical = 2.dp),
                    ) {
                        Text(
                            text = "${category.domainCount} domain",
                            style = MaterialTheme.typography.labelSmall,
                            color = colors.neonCyan,
                        )
                    }
                    // Blocklist sayisi
                    if (category.blocklistIds.isNotEmpty()) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(4.dp))
                                .background(colors.neonMagenta.copy(alpha = 0.12f))
                                .padding(horizontal = 6.dp, vertical = 2.dp),
                        ) {
                            Text(
                                text = "${category.blocklistIds.size} liste",
                                style = MaterialTheme.typography.labelSmall,
                                color = colors.neonMagenta,
                            )
                        }
                    }
                }
            }

            // Aktif/pasif badge
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .background(
                        if (category.enabled) colors.neonGreen.copy(alpha = 0.15f)
                        else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.08f),
                    )
                    .padding(horizontal = 8.dp, vertical = 4.dp),
            ) {
                Text(
                    text = if (category.enabled) "Aktif" else "Pasif",
                    style = MaterialTheme.typography.labelSmall,
                    color = if (category.enabled) colors.neonGreen
                    else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SwipeToDeleteWrapper(
    onDelete: () -> Unit,
    content: @Composable () -> Unit,
) {
    val colors = CyberpunkTheme.colors
    val dismissState = rememberSwipeToDismissBoxState(
        confirmValueChange = { value ->
            if (value == SwipeToDismissBoxValue.EndToStart) {
                onDelete()
                false // Dismiss'i iptal et, dialog onay bekleyecek
            } else {
                false
            }
        },
    )

    SwipeToDismissBox(
        state = dismissState,
        backgroundContent = {
            val bgColor by animateColorAsState(
                targetValue = when (dismissState.dismissDirection) {
                    SwipeToDismissBoxValue.EndToStart -> colors.neonRed.copy(alpha = 0.2f)
                    else -> Color.Transparent
                },
                label = "swipe_bg",
            )
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .clip(RoundedCornerShape(16.dp))
                    .background(bgColor)
                    .padding(end = 24.dp),
                contentAlignment = Alignment.CenterEnd,
            ) {
                Icon(
                    imageVector = Icons.Outlined.Delete,
                    contentDescription = "Sil",
                    tint = colors.neonRed,
                    modifier = Modifier.size(24.dp),
                )
            }
        },
        enableDismissFromStartToEnd = false,
        enableDismissFromEndToStart = true,
    ) {
        content()
    }
}

@Composable
private fun CategoryFormDialog(
    title: String,
    initialCategory: ContentCategoryDto?,
    blocklists: List<BlocklistDto>,
    onDismiss: () -> Unit,
    onSave: (key: String, name: String, icon: String, color: String, customDomains: String, blocklistIds: List<Int>) -> Unit,
) {
    val colors = CyberpunkTheme.colors

    var keyText by remember { mutableStateOf(initialCategory?.key ?: "") }
    var nameText by remember { mutableStateOf(initialCategory?.name ?: "") }
    var iconText by remember { mutableStateOf(initialCategory?.icon ?: "shield") }
    var colorText by remember { mutableStateOf(initialCategory?.color ?: "#00F0FF") }
    var customDomainsText by remember { mutableStateOf(initialCategory?.customDomains ?: "") }
    var selectedBlocklistIds by remember {
        mutableStateOf(initialCategory?.blocklistIds?.toSet() ?: emptySet())
    }

    val isEditing = initialCategory != null
    val presetColors = listOf(
        "#00F0FF", "#FF00E5", "#39FF14", "#FFB800", "#FF003C",
        "#7B68EE", "#FF6B35", "#00CED1", "#FF1493", "#32CD32",
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = MaterialTheme.colorScheme.surface,
        title = {
            Text(
                text = title,
                color = colors.neonCyan,
                style = MaterialTheme.typography.titleMedium,
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .verticalScroll(rememberScrollState())
                    .fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                // Anahtar (key) — sadece yeni kategoride goster
                if (!isEditing) {
                    OutlinedTextField(
                        value = keyText,
                        onValueChange = { keyText = it.lowercase().replace(" ", "_") },
                        label = { Text("Anahtar (key)", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)) },
                        placeholder = { Text("ornek: adult_content", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = colors.neonCyan,
                            unfocusedBorderColor = colors.glassBorder,
                            focusedTextColor = MaterialTheme.colorScheme.onSurface,
                            unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
                        ),
                    )
                }

                // Ad
                OutlinedTextField(
                    value = nameText,
                    onValueChange = { nameText = it },
                    label = { Text("Kategori Adi", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonCyan,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedTextColor = MaterialTheme.colorScheme.onSurface,
                        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
                    ),
                )

                // Ikon
                OutlinedTextField(
                    value = iconText,
                    onValueChange = { iconText = it },
                    label = { Text("Ikon", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)) },
                    placeholder = { Text("shield, star, lock...", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonCyan,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedTextColor = MaterialTheme.colorScheme.onSurface,
                        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
                    ),
                )

                // Renk secici
                Text(
                    text = "Renk",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    presetColors.forEach { preset ->
                        val presetColor = parseHexColor(preset)
                        val isSelected = colorText == preset
                        Box(
                            modifier = Modifier
                                .size(28.dp)
                                .clip(CircleShape)
                                .background(presetColor)
                                .clickable { colorText = preset },
                            contentAlignment = Alignment.Center,
                        ) {
                            if (isSelected) {
                                Icon(
                                    imageVector = Icons.Outlined.Check,
                                    contentDescription = null,
                                    tint = Color.Black,
                                    modifier = Modifier.size(16.dp),
                                )
                            }
                        }
                    }
                }

                // Ozel renk girisi
                OutlinedTextField(
                    value = colorText,
                    onValueChange = { colorText = it },
                    label = { Text("Renk (hex)", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)) },
                    placeholder = { Text("#00F0FF", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = parseHexColor(colorText),
                        unfocusedBorderColor = colors.glassBorder,
                        focusedTextColor = MaterialTheme.colorScheme.onSurface,
                        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
                    ),
                )

                // Ozel domainler
                OutlinedTextField(
                    value = customDomainsText,
                    onValueChange = { customDomainsText = it },
                    label = { Text("Ozel Domainler", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)) },
                    placeholder = { Text("Her satira bir domain\nornek.com\n*.sosyal.net", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(110.dp),
                    maxLines = 5,
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = colors.neonCyan,
                        unfocusedBorderColor = colors.glassBorder,
                        focusedTextColor = MaterialTheme.colorScheme.onSurface,
                        unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
                    ),
                )

                // Blocklist secimi
                if (blocklists.isNotEmpty()) {
                    Text(
                        text = "Engelleme Listeleri",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    )
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        blocklists.forEach { blocklist ->
                            val isChecked = blocklist.id in selectedBlocklistIds
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(8.dp))
                                    .clickable {
                                        selectedBlocklistIds = if (isChecked) {
                                            selectedBlocklistIds - blocklist.id
                                        } else {
                                            selectedBlocklistIds + blocklist.id
                                        }
                                    }
                                    .padding(vertical = 4.dp, horizontal = 2.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                Checkbox(
                                    checked = isChecked,
                                    onCheckedChange = { checked ->
                                        selectedBlocklistIds = if (checked) {
                                            selectedBlocklistIds + blocklist.id
                                        } else {
                                            selectedBlocklistIds - blocklist.id
                                        }
                                    },
                                    colors = CheckboxDefaults.colors(
                                        checkedColor = colors.neonCyan,
                                        uncheckedColor = colors.glassBorder,
                                        checkmarkColor = Color.Black,
                                    ),
                                )
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = blocklist.name,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurface,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    if (blocklist.domainCount > 0) {
                                        Text(
                                            text = "${blocklist.domainCount} domain",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f),
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val key = if (isEditing) initialCategory!!.key else keyText.trim()
                    if (key.isNotBlank() && nameText.isNotBlank()) {
                        onSave(
                            key,
                            nameText.trim(),
                            iconText.trim().ifBlank { "shield" },
                            colorText.trim().ifBlank { "#00F0FF" },
                            customDomainsText.trim(),
                            selectedBlocklistIds.toList(),
                        )
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = colors.neonCyan),
                enabled = nameText.isNotBlank() && (isEditing || keyText.isNotBlank()),
            ) {
                Text("Kaydet", color = Color.Black, fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Iptal", color = colors.neonCyan)
            }
        },
    )
}
