package com.chronix.agent.network

import com.chronix.agent.model.ApprovalOutcome
import com.chronix.agent.model.ApprovalRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

/**
 * Talks to agent/server.py's HTTP endpoints. Uses plain HttpURLConnection
 * (no OkHttp/Retrofit) to keep the APK small, per the "lightest practical
 * Android stack" requirement.
 *
 * SECURITY: the Gemini API key is never held, sent, or referenced by this
 * class or anywhere else in the Android app - only the pairing token is
 * stored locally (see SettingsStore) and sent with every authenticated
 * request, matching agent/server.py's _authenticated() check.
 */
class ChronixApiClient(
    private val host: String,
    private val port: Int,
    private var pairingToken: String?,
) {
    private fun endpoint(path: String) = URL("http://$host:$port$path")

    private fun postJson(path: String, body: JSONObject): JSONObject {
        val conn = endpoint(path).openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json")
        conn.connectTimeout = 5000
        conn.readTimeout = 15000

        OutputStreamWriter(conn.outputStream, Charsets.UTF_8).use { it.write(body.toString()) }

        val stream = if (conn.responseCode in 200..299) conn.inputStream else conn.errorStream
        val text = BufferedReader(InputStreamReader(stream, Charsets.UTF_8)).use { it.readText() }
        return JSONObject(text)
    }

    suspend fun sendChat(message: String): String = withContext(Dispatchers.IO) {
        val requestId = UUID.randomUUID().toString().take(12)
        val body = JSONObject().apply {
            put("type", "chat")
            put("request_id", requestId)
            put("message", message)
            pairingToken?.let { put("token", it) }
        }
        val response = postJson("/", body)
        response.optString("message", "(no response)")
    }

    suspend fun sendApprovalDecision(requestId: String, approve: Boolean): ApprovalOutcome =
        withContext(Dispatchers.IO) {
            val body = JSONObject().apply {
                put("type", "approval_response")
                put("request_id", requestId)
                put("decision", if (approve) "approve" else "reject")
                pairingToken?.let { put("token", it) }
            }
            try {
                val response = postJson("/", body)
                val success = response.optBoolean("success", false)
                val message = response.optString("message", "")
                if (success) ApprovalOutcome.Success(message) else ApprovalOutcome.Failure(message)
            } catch (exc: Exception) {
                ApprovalOutcome.Failure("Network error: ${exc.message}")
            }
        }

    /**
     * Polls agent/server.py's pending_approvals_request handler. Called
     * after every chat send and on a short interval while the app is in
     * the foreground - there is no persistent socket/WebSocket in this
     * minimal build (see README "Known limitations").
     */
    suspend fun fetchPendingApprovals(): List<ApprovalRequest> = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("type", "pending_approvals_request")
            pairingToken?.let { put("token", it) }
        }
        try {
            val response = postJson("/", body)
            val arr = response.optJSONArray("approvals") ?: return@withContext emptyList()
            (0 until arr.length()).map { i ->
                val obj = arr.getJSONObject(i)
                ApprovalRequest(
                    requestId = obj.getString("request_id"),
                    action = obj.optString("action"),
                    target = obj.optString("target").ifEmpty { null },
                    risk = obj.optString("risk"),
                    description = obj.optString("description"),
                    estimatedSize = if (obj.isNull("estimated_size")) null else obj.optLong("estimated_size"),
                )
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    /** Pairing does not require an existing token (that's the point). */
    suspend fun pair(pairingCode: String): String? = withContext(Dispatchers.IO) {
        val body = JSONObject().apply {
            put("type", "pair_request")
            put("pairing_code", pairingCode)
        }
        val response = postJson("/", body)
        if (response.optBoolean("accepted", false)) {
            response.optString("token").also { pairingToken = it }
        } else {
            null
        }
    }
}
