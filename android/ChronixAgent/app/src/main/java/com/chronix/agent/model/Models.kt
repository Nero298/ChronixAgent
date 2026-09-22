package com.chronix.agent.model

/**
 * Mirrors the JSON message shapes defined in agent/protocol.py on the
 * Windows side. Keep these two files in sync manually - there is no
 * shared schema codegen in this minimal build.
 */

data class DiscoveredAgent(
    val deviceName: String,
    val ip: String,
    val port: Int,
    val version: String,
)

data class ChatMessage(
    val fromUser: Boolean,
    val text: String,
)

data class ApprovalRequest(
    val requestId: String,
    val action: String,
    val target: String?,
    val risk: String,
    val description: String,
    val estimatedSize: Long?,
)

sealed class ApprovalOutcome {
    data class Success(val message: String) : ApprovalOutcome()
    data class Failure(val message: String) : ApprovalOutcome()
}

enum class ConnectionState {
    DISCONNECTED,
    SCANNING,
    SAVED_NOT_VERIFIED,
    CONNECTED,
}
