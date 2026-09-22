package com.chronix.agent.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.chronix.agent.model.ChatMessage
import com.chronix.agent.model.ConnectionState
import com.chronix.agent.ui.theme.ChronixBubbleAssistant
import com.chronix.agent.ui.theme.ChronixBubbleUser
import com.chronix.agent.ui.theme.ChronixGold
import com.chronix.agent.ui.theme.ChronixMidnight
import com.chronix.agent.ui.theme.ChronixNearBlack
import com.chronix.agent.ui.theme.ChronixTextPrimary
import com.chronix.agent.ui.theme.ChronixTextSecondary
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    deviceName: String,
    connectionState: ConnectionState,
    messages: List<ChatMessage>,
    isSending: Boolean,
    onSend: (String) -> Unit,
    onOpenSettings: () -> Unit,
) {
    var input by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            scope.launch { listState.animateScrollToItem(messages.size - 1) }
        }
    }

    Scaffold(
        containerColor = ChronixMidnight,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Chronix Agent", fontWeight = FontWeight.SemiBold, color = ChronixTextPrimary)
                        StatusLine(deviceName, connectionState)
                    }
                },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Filled.Settings, contentDescription = "Settings", tint = ChronixTextSecondary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = ChronixMidnight),
            )
        },
        bottomBar = {
            ChatInputBar(
                input = input,
                onInputChange = { input = it },
                enabled = !isSending,
                onSend = {
                    if (input.isNotBlank()) {
                        onSend(input.trim())
                        input = ""
                    }
                },
            )
        },
    ) { padding ->
        if (messages.isEmpty()) {
            EmptyState(modifier = Modifier.padding(padding).fillMaxSize())
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .padding(padding)
                    .fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                items(messages) { msg -> MessageBubble(msg) }
                if (isSending) {
                    item { TypingIndicator() }
                }
            }
        }
    }
}

@Composable
private fun StatusLine(deviceName: String, state: ConnectionState) {
    val (label, color) = when (state) {
        ConnectionState.CONNECTED -> "Connected" to ChronixGold
        ConnectionState.SCANNING -> "Scanning..." to ChronixTextSecondary
        ConnectionState.SAVED_NOT_VERIFIED -> "Not verified" to ChronixTextSecondary
        ConnectionState.DISCONNECTED -> "Disconnected" to Color(0xFFCF6679)
    }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(
            text = deviceName.ifBlank { "No PC configured" } + "  •  ",
            style = MaterialTheme.typography.bodySmall,
            color = ChronixTextSecondary,
        )
        Text("● $label", style = MaterialTheme.typography.bodySmall, color = color)
    }
}

@Composable
private fun EmptyState(modifier: Modifier = Modifier) {
    Box(modifier = modifier, contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                "Chronix Agent",
                style = MaterialTheme.typography.headlineSmall,
                color = ChronixGold,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                "\"Open Chrome\", \"Xóa cache Chrome\", \"Restart PC\"...",
                style = MaterialTheme.typography.bodyMedium,
                color = ChronixTextSecondary,
            )
        }
    }
}

@Composable
private fun MessageBubble(msg: ChatMessage) {
    val alignment = if (msg.fromUser) Alignment.CenterEnd else Alignment.CenterStart
    val bubbleColor = if (msg.fromUser) ChronixBubbleUser else ChronixBubbleAssistant
    val textColor = if (msg.fromUser) ChronixNearBlack else ChronixTextPrimary
    val shape = if (msg.fromUser) {
        RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp, bottomStart = 18.dp, bottomEnd = 4.dp)
    } else {
        RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp, bottomStart = 4.dp, bottomEnd = 18.dp)
    }

    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = alignment) {
        Surface(
            color = bubbleColor,
            shape = shape,
            modifier = Modifier.fillMaxWidth(0.82f),
        ) {
            Text(
                text = msg.text,
                color = textColor,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                style = MaterialTheme.typography.bodyLarge,
            )
        }
    }
}

@Composable
private fun TypingIndicator() {
    Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.CenterStart) {
        Surface(
            color = ChronixBubbleAssistant,
            shape = RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp, bottomStart = 4.dp, bottomEnd = 18.dp),
        ) {
            Text(
                "Chronix is thinking...",
                color = ChronixTextSecondary,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

@Composable
private fun ChatInputBar(
    input: String,
    onInputChange: (String) -> Unit,
    enabled: Boolean,
    onSend: () -> Unit,
) {
    Surface(color = ChronixMidnight) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 10.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = input,
                onValueChange = onInputChange,
                modifier = Modifier.weight(1f),
                placeholder = { Text("Message Chronix Agent...", color = ChronixTextSecondary) },
                shape = RoundedCornerShape(24.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = ChronixNearBlack,
                    unfocusedContainerColor = ChronixNearBlack,
                    focusedBorderColor = ChronixGold,
                    unfocusedBorderColor = ChronixTextSecondary.copy(alpha = 0.3f),
                    focusedTextColor = ChronixTextPrimary,
                    unfocusedTextColor = ChronixTextPrimary,
                ),
                maxLines = 4,
            )
            Spacer(Modifier.width(8.dp))
            FilledIconButton(
                onClick = onSend,
                enabled = enabled && input.isNotBlank(),
                colors = IconButtonDefaults.filledIconButtonColors(
                    containerColor = ChronixGold,
                    disabledContainerColor = ChronixTextSecondary.copy(alpha = 0.2f),
                ),
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send", tint = ChronixNearBlack)
            }
        }
    }
}
