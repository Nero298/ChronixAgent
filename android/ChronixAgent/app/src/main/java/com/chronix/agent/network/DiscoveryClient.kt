package com.chronix.agent.network

import com.chronix.agent.model.DiscoveredAgent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetSocketAddress

/**
 * Listens for UDP broadcast beacons sent by agent/discovery.py.
 * Matches DISCOVERY_UDP_PORT / DISCOVERY_SERVICE_ID from core/constants.py.
 */
object DiscoveryClient {
    private const val DISCOVERY_PORT = 8766
    private const val SERVICE_ID = "chronix-agent"
    private const val LISTEN_TIMEOUT_MS = 6000

    /**
     * Listens for a single beacon and returns it, or null on timeout.
     * Call repeatedly (e.g. from a "Scan for PC" button) rather than
     * running an indefinite background loop, to keep battery usage low.
     */
    suspend fun listenOnce(): DiscoveredAgent? = withContext(Dispatchers.IO) {
        var socket: DatagramSocket? = null
        try {
            socket = DatagramSocket(null).apply {
                reuseAddress = true
                bind(InetSocketAddress(DISCOVERY_PORT))
                soTimeout = LISTEN_TIMEOUT_MS
            }
            val buffer = ByteArray(1024)
            val packet = DatagramPacket(buffer, buffer.size)
            socket.receive(packet)

            val text = String(packet.data, 0, packet.length, Charsets.UTF_8)
            val json = JSONObject(text)
            if (json.optString("service") != SERVICE_ID) return@withContext null

            DiscoveredAgent(
                deviceName = json.optString("device_name", "Chronix-PC"),
                ip = packet.address.hostAddress ?: return@withContext null,
                port = json.optInt("port", 8765),
                version = json.optString("version", "unknown"),
            )
        } catch (_: Exception) {
            // Timeout or malformed packet - treat both as "nothing found yet".
            null
        } finally {
            socket?.close()
        }
    }
}
