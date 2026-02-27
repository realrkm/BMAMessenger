package com.example.bmamessenger

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.telephony.SmsManager
import android.util.Patterns
import android.widget.Toast
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.FileProvider
import androidx.core.net.toUri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import retrofit2.HttpException
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.File
import java.io.FileOutputStream
import java.net.ConnectException
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLHandshakeException

/**
 * The ViewModel for the SMS Gateway screen. This class is responsible for managing the data
 * and business logic of the application.
 *
 * @param settingsManager The [SettingsManager] instance for accessing and storing app settings.
 */
class SmsViewModel(private val settingsManager: SettingsManager) : ViewModel() {
    /** The base URL of the Anvil API. */
    var baseUrl by mutableStateOf("")
    /** The interval in seconds at which to refresh the list of pending SMS messages. */
    var refreshIntervalSeconds by mutableLongStateOf(30L)
    /** Controls whether the app uses dark theme. */
    var isDarkModeEnabled by mutableStateOf(true)
    /** The Retrofit API interface for interacting with the Anvil service. */
    private var api: AnvilApi? = null
    /** The coroutine job that handles the automatic refresh of messages. */
    private var refreshJob: Job? = null
    /** The list of pending SMS messages. */
    var messages by mutableStateOf<List<SmsMessage>>(emptyList())
    /** A flag indicating whether the list of messages is currently being refreshed. */
    var isRefreshing by mutableStateOf(false)
    /** The recipient of a WhatsApp message, used when sharing a message. */
    var whatsAppRecipient: SmsMessage? = null
    /** An error message to be displayed to the user. */
    var errorMessage by mutableStateOf<String?>(null)
    /** Indicates login request is running. */
    var isLoggingIn by mutableStateOf(false)
    /** Login error shown on login screen. */
    var loginErrorMessage by mutableStateOf<String?>(null)

    init {
        // Load settings and start the automatic refresh when the ViewModel is created.
        loadSettingsAndStart()
    }

    /**
     * Loads the settings from the [SettingsManager] and starts the automatic refresh.
     */
    private fun loadSettingsAndStart() {
        viewModelScope.launch {
            baseUrl = settingsManager.baseUrlFlow.first()
            refreshIntervalSeconds = settingsManager.intervalFlow.first()
            isDarkModeEnabled = settingsManager.darkModeFlow.first()
            updateApi()
            startAutomaticRefresh()
        }
    }

    /**
     * Updates the Retrofit API instance with the current base URL.
     */
    fun updateApi() {
        try {
            val okHttpClient = OkHttpClient.Builder()
                .readTimeout(60, TimeUnit.SECONDS)
                .connectTimeout(60, TimeUnit.SECONDS)
                .build()

            val sanitizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
            api = Retrofit.Builder()
                .baseUrl(sanitizedUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(AnvilApi::class.java)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    /**
     * Attempts to authenticate user against the Anvil verify-login endpoint.
     */
    fun login(url: String, email: String, password: String, onSuccess: () -> Unit) {
        viewModelScope.launch {
            val trimmedUrl = url.trim()
            val trimmedEmail = email.trim()
            if (trimmedUrl.isBlank() || trimmedEmail.isBlank() || password.isBlank()) {
                loginErrorMessage = "Base URL, email, and password are required."
                return@launch
            }
            if (!Patterns.EMAIL_ADDRESS.matcher(trimmedEmail).matches()) {
                loginErrorMessage = "Please enter a valid email address."
                return@launch
            }

            isLoggingIn = true
            loginErrorMessage = null
            try {
                settingsManager.saveSettings(trimmedUrl, refreshIntervalSeconds, isDarkModeEnabled)
                baseUrl = trimmedUrl
                updateApi()

                val response = api?.login(trimmedEmail, password)
                if (response == null) {
                    loginErrorMessage = "Unable to initialize API client."
                    return@launch
                }

                if (response.isSuccessful) {
                    val body = response.body()
                    if (body?.success == true && body.user != null) {
                        onSuccess()
                    } else {
                        loginErrorMessage = body?.error ?: "Login failed. Please try again."
                    }
                } else {
                    val serverError = response.errorBody()?.string()
                    val parsedError = parseApiErrorMessage(serverError)
                    loginErrorMessage = when (response.code()) {
                        400 -> parsedError ?: "Email and password are required."
                        401 -> parsedError ?: "Invalid email or password."
                        404 -> "Login endpoint not found. Confirm your Anvil Base URL."
                        500 -> parsedError ?: "Server error while signing in. Please try again."
                        else -> parsedError ?: "Unable to sign in right now. Please try again."
                    }
                }
            } catch (e: SSLHandshakeException) {
                loginErrorMessage = "SSL handshake failed. Check certificate and URL."
            } catch (e: ConnectException) {
                loginErrorMessage = "Failed to connect. Confirm the Anvil Base URL."
            } catch (e: Exception) {
                loginErrorMessage = e.message ?: "Login error."
            } finally {
                isLoggingIn = false
            }
        }
    }

    private fun parseApiErrorMessage(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        return try {
            val error = com.google.gson.Gson().fromJson(raw, LoginResponse::class.java)
            error?.error
        } catch (_: Exception) {
            null
        }
    }

    /**
     * Starts the automatic refresh of pending SMS messages.
     */
    fun startAutomaticRefresh() {
        refreshJob?.cancel()
        refreshJob = viewModelScope.launch {
            while (true) {
                fetchMessages()
                delay(refreshIntervalSeconds * 1000)
            }
        }
    }

    /**
     * Fetches the list of pending SMS messages from the Anvil API.
     */
    fun fetchMessages() {
        viewModelScope.launch {
            isRefreshing = true
            try {
                messages = api?.getPendingSms() ?: emptyList()
            } catch (e: SSLHandshakeException) {
                errorMessage = "BMA Messenger SSL handshake failed. Please ensure the certificate file is installed."
                delay(5000) // Keep message displayed for 5 seconds
                errorMessage = null
            } catch (e: ConnectException) {
                errorMessage = "Failed to connect to Anvil Base URL, under Settings. Confirm URL details."
                delay(5000)
                errorMessage = null
            } catch (e: Exception) {
                e.printStackTrace()
            } finally {
                isRefreshing = false
            }
        }
    }

    /**
     * Saves the provided settings and applies them to the application.
     *
     * @param url The new base URL for the Anvil API.
     * @param interval The new refresh interval in seconds.
     */
    fun saveAndApplySettings(url: String, interval: Long, darkModeEnabled: Boolean) {
        viewModelScope.launch {
            settingsManager.saveSettings(url, interval, darkModeEnabled)
            baseUrl = url
            refreshIntervalSeconds = interval
            isDarkModeEnabled = darkModeEnabled
            updateApi()
            startAutomaticRefresh()
        }
    }

    /**
     * Sends a single SMS message.
     *
     * @param context The application context.
     * @param msg The [SmsMessage] to send.
     */
    fun sendSingleSms(context: Context, msg: SmsMessage) {
        viewModelScope.launch {
            try {
                getSmsManager(context)?.sendTextMessage(msg.phone, null, msg.message, null, null)
                api?.markAsSent(msg.id)
                messages = messages.filter { it.id != msg.id }
            } catch (e: Exception) {
                Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    /**
     * Generates a PDF for the given message and sends it via WhatsApp.
     *
     * @param context The application context.
     * @param msg The [SmsMessage] for which to generate the PDF.
     */
    fun generateAndSendPdf(context: Context, msg: SmsMessage) {
        viewModelScope.launch {
            try {
                // The backend now expects both the job card id and selected document.
                val selectedDocument = msg.document?.trim().orEmpty()
                if (selectedDocument.isBlank()) {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(context, "No document type selected for this message.", Toast.LENGTH_SHORT).show()
                    }
                    return@launch
                }

                val responseBody = api?.generatePdf(msg.jobcardrefid, selectedDocument)
                if (responseBody == null || responseBody.contentLength() == 0L) {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(context, "No relevant document to attach.", Toast.LENGTH_SHORT).show()
                    }
                    return@launch
                }

                responseBody.let { body ->
                    withContext(Dispatchers.IO) {
                        // File name now mirrors the document value from the API payload.
                        val pdfFileName = toPdfFileName(selectedDocument)
                        val file = File(context.cacheDir, pdfFileName)
                        try {
                            body.byteStream().use { inputStream ->
                                FileOutputStream(file).use { outputStream ->
                                    val buffer = ByteArray(4 * 1024)
                                    var bytesRead: Int
                                    while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                                        outputStream.write(buffer, 0, bytesRead)
                                    }
                                    outputStream.flush()
                                }
                            }

                            val pdfUri = FileProvider.getUriForFile(context, "${context.packageName}.provider", file)
                            sendToWhatsApp(context, msg.phone, msg.message, pdfUri)
                        } catch (e: Exception) {
                            e.printStackTrace()
                            withContext(Dispatchers.Main) {
                                Toast.makeText(context, "Error generating or sharing PDF.", Toast.LENGTH_SHORT).show()
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
                withContext(Dispatchers.Main) {
                    val errorMessage = if (e is HttpException) {
                        "PDF generation failed (${e.code()}). Check document type."
                    } else {
                        "The PDF is missing or not generated."
                    }
                    Toast.makeText(context, errorMessage, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    /**
     * Converts a document label into a safe filename and ensures the file ends with .pdf.
     */
    private fun toPdfFileName(documentValue: String): String {
        val cleaned = documentValue.trim()
            .replace(Regex("[\\\\/:*?\"<>|]"), "_")
            .ifEmpty { "document" }
        return if (cleaned.lowercase().endsWith(".pdf")) cleaned else "$cleaned.pdf"
    }

    /**
     * Sends a message to WhatsApp.
     *
     * @param context The application context.
     * @param phoneNumber The phone number of the recipient.
     * @param message The message to send.
     * @param pdfUri An optional URI to a PDF file to attach to the message.
     */
    fun sendToWhatsApp(context: Context, phoneNumber: String, message: String, pdfUri: Uri? = null) {
        try {
            val cleanPhone = phoneNumber.replace(Regex("[^0-9]"), "")

            val intent = if (pdfUri != null) {
                Intent(Intent.ACTION_SEND).apply {
                    type = "application/pdf"
                    putExtra(Intent.EXTRA_STREAM, pdfUri)
                    setPackage("com.whatsapp")
                    putExtra("jid", "$cleanPhone@s.whatsapp.net")
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
            } else {
                val uri = "https://api.whatsapp.com/send?phone=$cleanPhone&text=${Uri.encode(message)}".toUri()
                Intent(Intent.ACTION_VIEW, uri).apply {
                    setPackage("com.whatsapp")
                }
            }

            context.startActivity(intent)

        } catch (_: Exception) {
            Toast.makeText(context, "WhatsApp not installed or error sharing.", Toast.LENGTH_SHORT).show()
        }
    }

    /**
     * Cancels all pending SMS messages by marking them as sent in the API.
     */
    fun cancelAllSms() {
        viewModelScope.launch {
            isRefreshing = true
            messages.forEach { try { api?.markAsSent(it.id) } catch (e: Exception) { e.printStackTrace() } }
            fetchMessages()
        }
    }

    /**
     * Optimistically removes a message from the list of pending messages.
     *
     * @param msg The [SmsMessage] to remove.
     */
    fun removeMessageOptimistically(msg: SmsMessage) {
        messages = messages.filter { it.id != msg.id }
    }

    /**
     * Undoes the removal of a message.
     *
     * @param msg The [SmsMessage] to restore.
     */
    fun undoRemoveMessage(msg: SmsMessage) {
        messages = listOf(msg) + messages
    }

    /**
     * Confirms the cancellation of a message by marking it as sent in the API.
     *
     * @param msg {SmsMessage} to cancel.
     */
    fun confirmCancelMessage(msg: SmsMessage) {
        viewModelScope.launch {
            try { api?.markAsSent(msg.id) } catch (e: Exception) { e.printStackTrace() }
        }
    }

    /**
     * Returns the appropriate [SmsManager] instance for the current Android version.
     *
     * @param context The application context.
     * @return The [SmsManager] instance.
     */
    private fun getSmsManager(context: Context): SmsManager? {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) context.getSystemService(SmsManager::class.java)
        else @Suppress("DEPRECATION") SmsManager.getDefault()
    }
}
