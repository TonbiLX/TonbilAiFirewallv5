package com.tonbil.aifirewall.feature.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.AutoAwesome
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material.icons.outlined.Send
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.tonbil.aifirewall.data.remote.dto.ChatMessageDto
import com.tonbil.aifirewall.ui.theme.DarkBackground
import com.tonbil.aifirewall.ui.theme.GlassBg
import com.tonbil.aifirewall.ui.theme.GlassBorder
import com.tonbil.aifirewall.ui.theme.NeonCyan
import com.tonbil.aifirewall.ui.theme.NeonMagenta
import com.tonbil.aifirewall.ui.theme.NeonRed
import com.tonbil.aifirewall.ui.theme.TextPrimary
import com.tonbil.aifirewall.ui.theme.TextSecondary
import org.koin.androidx.compose.koinViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    onBack: () -> Unit,
    viewModel: ChatViewModel = koinViewModel(),
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val snackbarHostState = remember { SnackbarHostState() }
    val listState = rememberLazyListState()

    LaunchedEffect(state.actionMessage) {
        state.actionMessage?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearActionMessage()
        }
    }

    // Auto-scroll to bottom when new messages arrive
    LaunchedEffect(state.messages.size) {
        if (state.messages.isNotEmpty()) {
            listState.animateScrollToItem(state.messages.size - 1)
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
                        Text("AI Sohbet", color = NeonMagenta, fontWeight = FontWeight.Bold)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Outlined.ArrowBack, contentDescription = "Geri", tint = TextSecondary)
                    }
                },
                actions = {
                    IconButton(onClick = viewModel::clearHistory) {
                        Icon(Icons.Outlined.DeleteOutline, contentDescription = "Gecmisi Temizle", tint = NeonRed.copy(alpha = 0.7f))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground),
            )
        },
        bottomBar = {
            ChatInput(
                text = state.inputText,
                onTextChange = viewModel::setInputText,
                onSend = viewModel::send,
                isSending = state.isSending,
            )
        },
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(listOf(DarkBackground, Color(0xFF0A0A1A), DarkBackground))
                )
                .padding(paddingValues),
        ) {
            if (state.isLoading) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator(color = NeonMagenta)
                }
                return@Column
            }

            if (state.messages.isEmpty() && !state.isSending) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            imageVector = Icons.Outlined.AutoAwesome,
                            contentDescription = null,
                            tint = NeonMagenta.copy(alpha = 0.4f),
                            modifier = Modifier.size(48.dp),
                        )
                        Spacer(Modifier.height(12.dp))
                        Text(
                            text = "AI asistana bir soru sorun",
                            color = TextSecondary,
                            fontSize = 14.sp,
                        )
                        Text(
                            text = "Ag durumu, guvenlik ve yapilandirma hakkinda",
                            color = TextSecondary.copy(alpha = 0.6f),
                            fontSize = 12.sp,
                        )
                    }
                }
                return@Column
            }

            LazyColumn(
                state = listState,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 12.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 8.dp),
            ) {
                items(state.messages, key = { "${it.role}_${it.timestamp}_${it.content.hashCode()}" }) { message ->
                    ChatBubble(message = message)
                }

                if (state.isSending) {
                    item {
                        TypingIndicator()
                    }
                }
            }
        }
    }
}

@Composable
private fun ChatBubble(message: ChatMessageDto) {
    val isUser = message.role == "user"

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Box(
            modifier = Modifier
                .widthIn(max = 300.dp)
                .clip(
                    RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = if (isUser) 16.dp else 4.dp,
                        bottomEnd = if (isUser) 4.dp else 16.dp,
                    )
                )
                .background(
                    if (isUser) NeonCyan.copy(alpha = 0.15f) else GlassBg,
                )
                .then(
                    if (!isUser) {
                        Modifier.background(Color.Transparent)
                    } else {
                        Modifier
                    }
                )
                .padding(12.dp),
        ) {
            Column {
                Text(
                    text = message.content,
                    color = if (isUser) NeonCyan else TextPrimary,
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                )
                message.timestamp?.let { ts ->
                    Spacer(Modifier.height(4.dp))
                    Text(
                        text = ts.takeLast(8).take(5), // HH:MM from timestamp
                        color = TextSecondary.copy(alpha = 0.5f),
                        fontSize = 10.sp,
                        textAlign = if (isUser) TextAlign.End else TextAlign.Start,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}

@Composable
private fun TypingIndicator() {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Start,
    ) {
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(16.dp, 16.dp, 16.dp, 4.dp))
                .background(GlassBg)
                .padding(horizontal = 16.dp, vertical = 10.dp),
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(12.dp),
                    color = NeonMagenta,
                    strokeWidth = 1.5.dp,
                )
                Spacer(Modifier.width(6.dp))
                Text("Dusunuyor...", color = TextSecondary, fontSize = 12.sp)
            }
        }
    }
}

@Composable
private fun ChatInput(
    text: String,
    onTextChange: (String) -> Unit,
    onSend: () -> Unit,
    isSending: Boolean,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(DarkBackground)
            .imePadding()
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        OutlinedTextField(
            value = text,
            onValueChange = onTextChange,
            placeholder = { Text("Mesajinizi yazin...", color = TextSecondary, fontSize = 14.sp) },
            modifier = Modifier.weight(1f),
            maxLines = 3,
            colors = OutlinedTextFieldDefaults.colors(
                focusedBorderColor = NeonMagenta,
                unfocusedBorderColor = GlassBorder,
                focusedTextColor = TextPrimary,
                unfocusedTextColor = TextPrimary,
                cursorColor = NeonMagenta,
            ),
            shape = RoundedCornerShape(24.dp),
        )

        IconButton(
            onClick = onSend,
            enabled = text.isNotBlank() && !isSending,
            colors = IconButtonDefaults.iconButtonColors(
                containerColor = if (text.isNotBlank()) NeonMagenta.copy(alpha = 0.2f) else Color.Transparent,
            ),
        ) {
            if (isSending) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color = NeonMagenta,
                    strokeWidth = 2.dp,
                )
            } else {
                Icon(
                    imageVector = Icons.Outlined.Send,
                    contentDescription = "Gonder",
                    tint = if (text.isNotBlank()) NeonMagenta else TextSecondary,
                )
            }
        }
    }
}
