package com.chronix.agent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.material3.Surface
import androidx.compose.runtime.*
import com.chronix.agent.ui.ApprovalDialog
import com.chronix.agent.ui.ChatScreen
import com.chronix.agent.ui.MainViewModel
import com.chronix.agent.ui.SettingsScreen
import com.chronix.agent.ui.theme.ChronixMidnight
import com.chronix.agent.ui.theme.ChronixTheme

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ChronixTheme {
                Surface(color = ChronixMidnight) {
                    var showSettings by remember { mutableStateOf(false) }

                    val deviceName by viewModel.deviceName.collectAsState()
                    val connectionState by viewModel.connectionState.collectAsState()
                    val messages by viewModel.messages.collectAsState()
                    val isSending by viewModel.isSending.collectAsState()
                    val pendingApproval by viewModel.pendingApproval.collectAsState()

                    if (showSettings) {
                        SettingsScreen(viewModel = viewModel, onBack = { showSettings = false })
                    } else {
                        ChatScreen(
                            deviceName = deviceName,
                            connectionState = connectionState,
                            messages = messages,
                            isSending = isSending,
                            onSend = { text -> viewModel.sendMessage(text) },
                            onOpenSettings = { showSettings = true },
                        )
                    }

                    pendingApproval?.let { request ->
                        ApprovalDialog(
                            request = request,
                            onDecision = { approve, onDone ->
                                viewModel.respondToApproval(request.requestId, approve) { outcome ->
                                    onDone(outcome)
                                    viewModel.clearPendingApproval()
                                }
                            },
                            onDismiss = { /* must not silently dismiss a high-risk approval */ },
                        )
                    }
                }
            }
        }
    }
}
