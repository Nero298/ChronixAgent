package com.chronix.agent.network

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "chronix_settings")

/**
 * Local device settings only: PC host/IP, port, device name, and the
 * pairing token issued after a successful /pair exchange.
 *
 * This store NEVER contains a Gemini API key - that key lives only in
 * the Windows agent's config.json / CHRONIX_GEMINI_API_KEY env var, per
 * spec section 7 ("APK must NOT contain Gemini API key").
 */
object SettingsStore {
    private val KEY_HOST = stringPreferencesKey("pc_host")
    private val KEY_PORT = intPreferencesKey("pc_port")
    private val KEY_DEVICE_NAME = stringPreferencesKey("pc_device_name")
    private val KEY_TOKEN = stringPreferencesKey("pairing_token")

    fun connectionFlow(context: Context): Flow<ConnectionSettings> =
        context.dataStore.data.map { prefs ->
            ConnectionSettings(
                host = prefs[KEY_HOST] ?: "",
                port = prefs[KEY_PORT] ?: 8765,
                deviceName = prefs[KEY_DEVICE_NAME] ?: "",
                token = prefs[KEY_TOKEN],
            )
        }

    suspend fun save(context: Context, host: String, port: Int, deviceName: String) {
        context.dataStore.edit { prefs ->
            prefs[KEY_HOST] = host
            prefs[KEY_PORT] = port
            prefs[KEY_DEVICE_NAME] = deviceName
        }
    }

    suspend fun saveToken(context: Context, token: String) {
        context.dataStore.edit { prefs -> prefs[KEY_TOKEN] = token }
    }

    suspend fun clear(context: Context) {
        context.dataStore.edit { it.clear() }
    }
}

data class ConnectionSettings(
    val host: String,
    val port: Int,
    val deviceName: String,
    val token: String?,
)
