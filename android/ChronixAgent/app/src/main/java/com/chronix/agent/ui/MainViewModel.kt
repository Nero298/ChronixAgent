package com.chronix.agent.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.chronix.agent.model.ApprovalOutcome
import com.chronix.agent.model.ApprovalRequest
import com.chronix.agent.model.ChatMessage
import com.chronix.agent.model.ConnectionState
import com.chronix.agent.network.ChronixApiClient
import com.chronix.agent.network.DiscoveryClient
import com.chronix.agent.network.SettingsStore
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _deviceName = MutableStateFlow("")
    val deviceName: StateFlow<String> = _deviceName.asStateFlow()

    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    val messages: StateFlow<List<ChatMessage>> = _messages.asStateFlow()

    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()

    private val _pendingApproval = MutableStateFlow<ApprovalRequest?>(null)
    val pendingApproval: StateFlow<ApprovalRequest?> = _pendingApproval.asStateFlow()

    private var apiClient: ChronixApiClient? = null
    private var host: String = ""
    private var port: Int = 8765
    private var token: String? = null
    private var pollingStarted = false

    private fun startApprovalPolling() {
        if (pollingStarted) return
        pollingStarted = true
        viewModelScope.launch {
            while (true) {
                delay(4000)
                val client = apiClient ?: continue
                // Don't fetch a replacement while one is already showing -
                // avoids swapping the dialog out from under the user.
                if (_pendingApproval.value != null) continue
                val approvals = client.fetchPendingApprovals()
                if (approvals.isNotEmpty()) {
                    _pendingApproval.value = approvals.first()
                }
            }
        }
    }

    fun clearPendingApproval() {
        _pendingApproval.value = null
    }

    init {
        viewModelScope.launch {
            SettingsStore.connectionFlow(application).collect { settings ->
                host = settings.host
                port = settings.port
                token = settings.token
                _deviceName.value = settings.deviceName
                if (host.isNotBlank()) {
                    apiClient = ChronixApiClient(host, port, token)
                    _connectionState.value = ConnectionState.SAVED_NOT_VERIFIED
                    startApprovalPolling()
                }
            }
        }
    }

    fun scanForAgent(onFound: (String, Int, String) -> Unit, onNotFound: () -> Unit) {
        viewModelScope.launch {
            _connectionState.value = ConnectionState.SCANNING
            val found = DiscoveryClient.listenOnce()
            if (found != null) {
                onFound(found.ip, found.port, found.deviceName)
            } else {
                _connectionState.value = ConnectionState.DISCONNECTED
                onNotFound()
            }
        }
    }

    fun saveConnection(context: android.content.Context, host: String, port: Int, deviceName: String) {
        viewModelScope.launch {
            SettingsStore.save(context, host, port, deviceName)
        }
    }

    fun pair(context: android.content.Context, pairingCode: String, onResult: (Boolean) -> Unit) {
        val client = apiClient ?: return onResult(false)
        viewModelScope.launch {
            val newToken = client.pair(pairingCode)
            if (newToken != null) {
                SettingsStore.saveToken(context, newToken)
                _connectionState.value = ConnectionState.CONNECTED
                onResult(true)
            } else {
                onResult(false)
            }
        }
    }

    fun sendMessage(text: String) {
        val client = apiClient ?: run {
            _messages.value = _messages.value + ChatMessage(false, "Not connected to a PC yet.")
            return
        }
        _messages.value = _messages.value + ChatMessage(true, text)
        _isSending.value = true
        viewModelScope.launch {
            try {
                val reply = client.sendChat(text)
                _messages.value = _messages.value + ChatMessage(false, reply)
                _connectionState.value = ConnectionState.CONNECTED
            } catch (exc: Exception) {
                _messages.value = _messages.value + ChatMessage(false, "Connection error: ${exc.message}")
                _connectionState.value = ConnectionState.DISCONNECTED
            } finally {
                _isSending.value = false
            }
        }
    }

    fun respondToApproval(requestId: String, approve: Boolean, onResult: (ApprovalOutcome) -> Unit) {
        val client = apiClient ?: return onResult(ApprovalOutcome.Failure("Not connected."))
        viewModelScope.launch {
            val outcome = client.sendApprovalDecision(requestId, approve)
            onResult(outcome)
        }
    }
}
