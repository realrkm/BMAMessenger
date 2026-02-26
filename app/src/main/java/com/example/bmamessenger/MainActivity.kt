package com.example.bmamessenger

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.ExperimentalAnimationApi
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.Logout
import androidx.compose.material.icons.automirrored.rounded.Notes
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Delete
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.SnackbarResult
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.bmamessenger.ui.theme.AppTheme
import com.example.bmamessenger.ui.theme.GlassyBlack
import com.example.bmamessenger.ui.theme.NightBlue
import kotlinx.coroutines.launch

/**
 * Represents the main screens of the application.
 */
enum class AppScreen { LOGIN, MAIN, SETTINGS }

/**
 * The main activity of the application. This is the entry point for the UI.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Initialize the settings manager, which will be used by the view model.
        val settingsManager = SettingsManager(applicationContext)

        setContent {
            AppTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    // Create the view model, providing it with the settings manager.
                    val viewModel: SmsViewModel = viewModel(factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            return SmsViewModel(settingsManager) as T
                        }
                    })

                    // State to manage the current screen being displayed.
                    // Start with the LOGIN screen as requested.
                    var currentScreen by remember { mutableStateOf(AppScreen.LOGIN) }

                    // Navigate between screens based on currentScreen state.
                    when (currentScreen) {
                        AppScreen.LOGIN -> {
                            LoginScreen(
                                initialBaseUrl = viewModel.baseUrl,
                                isLoading = viewModel.isLoggingIn,
                                errorMessage = viewModel.loginErrorMessage,
                                onLogin = { baseUrl, email, password ->
                                    viewModel.login(baseUrl, email, password) {
                                        currentScreen = AppScreen.MAIN
                                    }
                                }
                            )
                        }
                        AppScreen.MAIN -> {
                            SmsGatewayScreen(
                                viewModel, 
                                onOpenSettings = { currentScreen = AppScreen.SETTINGS }, 
                                onLogout = { currentScreen = AppScreen.LOGIN }
                            )
                        }
                        AppScreen.SETTINGS -> {
                            SettingsScreen(
                                viewModel, 
                                onBack = { currentScreen = AppScreen.MAIN }, 
                                onLogout = { currentScreen = AppScreen.LOGIN }
                            )
                        }
                    }
                }
            }
        }
    }
}

/**
 * The main screen of the application, which displays the list of pending SMS messages.
 *
 * @param viewModel The view model that provides the data for this screen.
 * @param onOpenSettings A callback to navigate to the settings screen.
 * @param onLogout A callback to be invoked when the user logs out.
 */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalAnimationApi::class, ExperimentalFoundationApi::class)
@Composable
fun SmsGatewayScreen(viewModel: SmsViewModel, onOpenSettings: () -> Unit, onLogout: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbarHostState = remember { SnackbarHostState() }

    // Show a toast message if an error occurs.
    val errorMessage = viewModel.errorMessage
    LaunchedEffect(errorMessage) {
        errorMessage?.let {
            Toast.makeText(context, it, Toast.LENGTH_LONG).show()
        }
    }

    // Check for and request SMS permission.
    var hasPermission by remember { mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.SEND_SMS) == PackageManager.PERMISSION_GRANTED) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { hasPermission = it }
    LaunchedEffect(Unit) { if (!hasPermission) launcher.launch(Manifest.permission.SEND_SMS) }

    var showShareOptions by remember { mutableStateOf(false) }

    // Show the share dialog when `showShareOptions` is true.
    if (showShareOptions) {
        ShareDialog(
            onDismiss = { showShareOptions = false },
            onSendText = {
                showShareOptions = false
                viewModel.whatsAppRecipient?.let { msg ->
                    viewModel.sendToWhatsApp(context, msg.phone, msg.message)
                }
            },
            onSendPdf = {
                showShareOptions = false
                viewModel.whatsAppRecipient?.let { msg ->
                    viewModel.generateAndSendPdf(context, msg)
                }
            }
        )
    }

    Scaffold(
        containerColor = Color.Transparent,
        snackbarHost = { SnackbarHost(snackbarHostState) },
        topBar = {
            TopAppBar(
                title = { Text("BMA Messenger", fontWeight = FontWeight.ExtraBold) },
                actions = {
                    IconButton(onClick = onOpenSettings) {
                        Icon(Icons.Rounded.Settings, contentDescription = "Settings", tint = Color.White)
                    }
                    IconButton(onClick = onLogout) {
                        Icon(Icons.AutoMirrored.Rounded.Logout, contentDescription = "Logout", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color.Transparent,
                    titleContentColor = Color.White
                )
            )
        }
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = viewModel.isRefreshing,
            onRefresh = { viewModel.fetchMessages() },
            modifier = Modifier.padding(padding).fillMaxSize()
        ) {
            Column(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                // Show the "Clear All" button if there are messages.
                if (viewModel.messages.isNotEmpty()) {
                    OutlinedButton(
                        onClick = { viewModel.cancelAllSms() },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.5f))
                    ) {
                        Icon(Icons.Rounded.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Spacer(Modifier.width(8.dp))
                        Text("Clear All", fontWeight = FontWeight.Medium, color = Color.White)
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                }

                // Show a message if there are no messages.
                if (viewModel.messages.isEmpty() && !viewModel.isRefreshing) {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(Icons.Rounded.CheckCircle, contentDescription = null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.primary.copy(alpha = 0.4f))
                            Spacer(Modifier.height(16.dp))
                            Text("All messages sent!", style = MaterialTheme.typography.titleMedium, color = Color.Gray)
                        }
                    }
                } else {
                    // Display the list of messages.
                    LazyColumn(modifier = Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 100.dp)) {
                        itemsIndexed(items = viewModel.messages, key = { _, msg -> msg.id }) { _, msg ->
                            SmsCard(
                                msg = msg,
                                onSend = { viewModel.sendSingleSms(context, msg) },
                                onCancel = {
                                    viewModel.removeMessageOptimistically(msg)
                                    scope.launch {
                                        val result = snackbarHostState.showSnackbar(
                                            message = "Message removed",
                                            actionLabel = "UNDO",
                                            duration = SnackbarDuration.Short,
                                        )
                                        if (result == SnackbarResult.ActionPerformed) viewModel.undoRemoveMessage(msg)
                                        else viewModel.confirmCancelMessage(msg)
                                    }
                                },
                                onShareWhatsApp = {
                                    viewModel.whatsAppRecipient = msg
                                    showShareOptions = true
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

/**
 * A dialog that asks the user whether to send a message with or without a PDF.
 *
 * @param onDismiss A callback to dismiss the dialog.
 * @param onSendText A callback to send the message without a PDF.
 * @param onSendPdf A callback to send the message with a PDF.
 */
@Composable
fun ShareDialog(onDismiss: () -> Unit, onSendText: () -> Unit, onSendPdf: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = MaterialTheme.colorScheme.background,
        title = {
            Text("Share via WhatsApp", fontWeight = FontWeight.Bold, color = Color.White, fontSize = 20.sp)
        },
        text = {
            Column(Modifier.fillMaxWidth().padding(start = 24.dp, end = 24.dp, top = 20.dp, bottom = 24.dp)) {
                Text("Do you want to send only the text or attach a PDF?", color = Color.White.copy(alpha = 0.7f))
                Spacer(Modifier.height(24.dp))
                Button(
                    onClick = onSendText,
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Icon(Icons.AutoMirrored.Rounded.Notes, contentDescription = "Send Text Only")
                    Spacer(Modifier.width(8.dp))
                    Text("Send Text Only", fontWeight = FontWeight.Bold)
                }
                Spacer(Modifier.height(24.dp))
                Button(
                    onClick = onSendPdf,
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.8f))
                ) {
                    Icon(Icons.Filled.PictureAsPdf, contentDescription = "Send with PDF")
                    Spacer(Modifier.width(8.dp))
                    Text("Send with PDF", fontWeight = FontWeight.Bold)
                }
            }
        },
        confirmButton = {},
        dismissButton = {},
        modifier = Modifier
            .padding(horizontal = 24.dp)
            .clip(RoundedCornerShape(24.dp))
            .background(GlassyBlack)
            .border(1.dp, Color.White.copy(alpha = 0.2f), RoundedCornerShape(24.dp)),
        shape = RoundedCornerShape(24.dp),
        titleContentColor = Color.White,
        textContentColor = Color.White,
        tonalElevation = 0.dp,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    )
}


/**
 * A card that displays the details of a single SMS message.
 *
 * @param msg The SMS message to display.
 * @param onSend A callback to send the SMS message.
 * @param onCancel A callback to cancel the SMS message.
 * @param onShareWhatsApp A callback to share the message on WhatsApp.
 */
@Composable
fun SmsCard(
    msg: SmsMessage,
    onSend: () -> Unit,
    onCancel: () -> Unit,
    onShareWhatsApp: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp).clickable { onShareWhatsApp() },
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = GlassyBlack),
        border = BorderStroke(1.dp, Color.White.copy(alpha = 0.2f))
    ) {
        Column(modifier = Modifier.padding(20.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                // Display the recipient's initials.
                Box(
                    modifier = Modifier
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = msg.fullname.split(" ").mapNotNull { it.firstOrNull() }.joinToString("").take(2).uppercase(),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                }
                Spacer(modifier = Modifier.width(16.dp))
                // Display the recipient's name and phone number.
                Column(modifier = Modifier.weight(1f)) {
                    Text(text = msg.fullname, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, fontSize = 18.sp, color = Color.White)
                    Text(text = msg.phone, style = MaterialTheme.typography.bodyLarge, color = Color.Gray)
                }
                // Display the share button.
                IconButton(onClick = onShareWhatsApp) {
                    Icon(Icons.Rounded.Share, contentDescription = "Share on WhatsApp", tint = Color.White)
                }
                Spacer(modifier = Modifier.width(8.dp))
                val documentLabel = msg.document?.trim().orEmpty().ifEmpty { "No Document" }
                Surface(
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.6f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = documentLabel,
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelMedium,
                        color = Color.White,
                        fontWeight = FontWeight.Medium
                    )
                }
                Spacer(modifier = Modifier.width(8.dp))
                // Display the pending status.
                Surface(
                    color = MaterialTheme.colorScheme.primary.copy(alpha = 0.8f),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(text = "Pending", modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp), style = MaterialTheme.typography.labelMedium, color = Color.White, fontWeight = FontWeight.Medium)
                }
            }
            Spacer(Modifier.height(16.dp))
            // Display the message body.
            Box(modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(NightBlue).padding(16.dp)) {
                Text(text = msg.message, style = MaterialTheme.typography.bodyLarge, color = Color.White.copy(alpha = 0.8f))
            }
            Spacer(Modifier.height(16.dp))
            // Display the send and cancel buttons.
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Button(
                    onClick = onSend,
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Text("Send SMS", fontWeight = FontWeight.Medium)
                }
                OutlinedButton(
                    onClick = onCancel,
                    modifier = Modifier.weight(1f).height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                    border = BorderStroke(1.dp, Color.White.copy(alpha = 0.5f))
                ) {
                    Text("Cancel SMS", fontWeight = FontWeight.Medium)
                }
            }
        }
    }
}

/**
 * The settings screen, where the user can configure the application.
 *
 * @param viewModel The view model that provides the data for this screen.
 * @param onBack A callback to navigate back to the main screen.
 * @param onLogout A callback to be invoked when the user logs out.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: SmsViewModel, onBack: () -> Unit, onLogout: () -> Unit) {
    var tempUrl by remember { mutableStateOf(viewModel.baseUrl) }
    var tempInterval by remember { mutableStateOf(viewModel.refreshIntervalSeconds.toString()) }
    val focusManager = LocalFocusManager.current

    // Save the settings and navigate back to the main screen.
    val saveAction = {
        val interval = tempInterval.toLongOrNull() ?: 30L
        viewModel.saveAndApplySettings(tempUrl, interval)
        onBack()
    }

    Scaffold(
        containerColor = Color.Transparent,
        topBar = {
            TopAppBar(
                title = { Text("Configuration Settings", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Back", tint = Color.White)
                    }
                },
                actions = {
                    IconButton(onClick = onLogout) {
                        Icon(Icons.AutoMirrored.Rounded.Logout, contentDescription = "Logout", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color.Transparent,
                    titleContentColor = Color.White
                )
            )
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding).fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            // Text field for the Anvil Base URL.
            SettingTextField(
                value = tempUrl, 
                onValueChange = { tempUrl = it }, 
                label = "Anvil Base URL", 
                placeholder = "https://<your-app>.anvil.app",
                keyboardOptions = KeyboardOptions.Default.copy(imeAction = ImeAction.Next),
                keyboardActions = KeyboardActions(onNext = { focusManager.moveFocus(FocusDirection.Down) })
            )
            // Text field for the refresh interval.
            SettingTextField(
                value = tempInterval, 
                onValueChange = { tempInterval = it }, 
                label = "Refresh Interval (Seconds)", 
                placeholder = "30",
                keyboardOptions = KeyboardOptions.Default.copy(imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { saveAction() })
            )

            Spacer(modifier = Modifier.weight(1f))

            // Button to save the changes.
            Button(
                onClick = saveAction,
                modifier = Modifier.fillMaxWidth().height(56.dp),
                shape = RoundedCornerShape(16.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text("Save Changes", fontWeight = FontWeight.Bold, fontSize = 16.sp)
            }
        }
    }
}

/**
 * A text field for the settings screen.
 *
 * @param value The current value of the text field.
 * @param onValueChange A callback to be invoked when the value of the text field changes.
 * @param label The label to be displayed above the text field.
 * @param placeholder The placeholder to be displayed in the text field.
 * @param singleLine Whether the text field should be a single line.
 * @param keyboardOptions The keyboard options to be used for the text field.
 * @param keyboardActions The keyboard actions to be used for the text field.
 */
@Composable
fun SettingTextField(
    value: String, 
    onValueChange: (String) -> Unit, 
    label: String, 
    placeholder: String, 
    singleLine: Boolean = true,
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    keyboardActions: KeyboardActions = KeyboardActions.Default
) {
    Column {
        Text(text = label, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 14.sp)
        Spacer(Modifier.height(8.dp))
        TextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth(),
            placeholder = { Text(placeholder, color = Color.Gray) },
            shape = RoundedCornerShape(16.dp),
            colors = TextFieldDefaults.colors(
                focusedContainerColor = GlassyBlack,
                unfocusedContainerColor = GlassyBlack,
                disabledContainerColor = GlassyBlack,
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
                disabledIndicatorColor = Color.Transparent,
                cursorColor = MaterialTheme.colorScheme.primary,
                focusedTextColor = Color.White,
                unfocusedTextColor = Color.White
            ),
            singleLine = singleLine,
            keyboardOptions = keyboardOptions,
            keyboardActions = keyboardActions
        )
    }
}
