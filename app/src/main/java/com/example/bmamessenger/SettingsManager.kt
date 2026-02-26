package com.example.bmamessenger

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/**
 * Extension property to provide a DataStore instance for the application context.
 */
val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

/**
 * Manages the application's settings, which are stored in a DataStore.
 *
 * @param context The application context.
 */
class SettingsManager(private val context: Context) {
    /**
     * Keys for accessing the settings in the DataStore.
     */
    private val URL_KEY = stringPreferencesKey("anvil_url")
    private val INTERVAL_KEY = longPreferencesKey("refresh_interval")

    /**
     * A flow that emits the base URL of the Anvil service whenever it changes.
     */
    val baseUrlFlow: Flow<String> = context.dataStore.data.map { it[URL_KEY] ?: "https://YOUR-APP-NAME.anvil.app/" }

    /**
     * A flow that emits the refresh interval in seconds whenever it changes.
     */
    val intervalFlow: Flow<Long> = context.dataStore.data.map { it[INTERVAL_KEY] ?: 30L }

    /**
     * Saves the provided settings to the DataStore.
     *
     * @param url The base URL of the Anvil service.
     * @param interval The refresh interval in seconds.
     */
    suspend fun saveSettings(url: String, interval: Long) {
        context.dataStore.edit { settings ->
            settings[URL_KEY] = url
            settings[INTERVAL_KEY] = interval
        }
    }
}
