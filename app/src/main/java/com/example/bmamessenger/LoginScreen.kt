package com.example.bmamessenger

import android.content.Context
import android.view.inputmethod.InputMethodManager
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowForward
import androidx.compose.material.icons.rounded.Email
import androidx.compose.material.icons.rounded.Lock
import androidx.compose.material.icons.rounded.Public
import androidx.compose.material.icons.rounded.Visibility
import androidx.compose.material.icons.rounded.VisibilityOff
import androidx.compose.material.icons.rounded.VpnKey
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusDirection
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.bmamessenger.ui.theme.AppTheme
import com.example.bmamessenger.ui.theme.DeepPurple
import com.example.bmamessenger.ui.theme.GlassyBlack
import com.example.bmamessenger.ui.theme.NightBlue
import com.example.bmamessenger.ui.theme.White

/**
 * A composable function that displays the login screen.
 * It maintains a design consistent with the provided HTML code, using a dark glassy theme.
 *
 * @param initialBaseUrl A preloaded base URL value.
 * @param isLoading Indicates whether login call is running.
 * @param errorMessage A login error message, if any.
 * @param onLogin A callback invoked with base URL, email, and password.
 */
@Composable
fun LoginScreen(
    initialBaseUrl: String,
    isLoading: Boolean,
    errorMessage: String?,
    onLogin: (String, String, String) -> Unit
) {
    // State for tracking user input and password visibility
    val focusManager = LocalFocusManager.current
    val keyboardController = LocalSoftwareKeyboardController.current
    val view = LocalView.current
    var baseUrl by remember(initialBaseUrl) { mutableStateOf(initialBaseUrl) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isPasswordVisible by remember { mutableStateOf(false) }
    var localError by remember { mutableStateOf<String?>(null) }
    val shownError = localError ?: errorMessage

    val submitLogin = {
        dismissKeyboard(view, keyboardController, focusManager)
        val error = when {
            baseUrl.isBlank() -> "Please enter your Anvil Base URL."
            email.isBlank() -> "Please enter your email address."
            password.isBlank() -> "Please enter your password."
            else -> null
        }
        localError = error
        if (error == null) {
            onLogin(baseUrl, email, password)
        }
    }

    // Main container with a dark vertical gradient background
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(NightBlue, Color(0xFF0B1120))
                )
            )
    ) {
        // Decorative background "glow" effects
        Box(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .offset(x = 100.dp, y = (-100).dp)
                .size(400.dp)
                .background(DeepPurple.copy(alpha = 0.1f), CircleShape)
        )
        Box(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .offset(x = (-100).dp, y = 100.dp)
                .size(400.dp)
                .background(Color.Blue.copy(alpha = 0.1f), CircleShape)
        )

        // Main content layout
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Spacer(modifier = Modifier.height(40.dp))

            // Icon section with a glassy border
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(
                        brush = Brush.verticalGradient(
                            colors = listOf(
                                GlassyBlack.copy(alpha = 0.6f),
                                Color(0x990F172A)
                            )
                        )
                    )
                    .border(1.dp, Color.White.copy(alpha = 0.1f), RoundedCornerShape(16.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    Icons.Rounded.Lock,
                    contentDescription = null,
                    tint = DeepPurple,
                    modifier = Modifier.size(32.dp)
                )
            }
            Spacer(modifier = Modifier.height(24.dp))
            
            // Header text
            Text(
                text = "Welcome Back",
                color = White,
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Sign in to send SMS and WhatsApp messages",
                color = White,
                fontSize = 14.sp,
                textAlign = TextAlign.Center
            )
            Spacer(modifier = Modifier.height(40.dp))

            GlassyTextField(
                value = baseUrl,
                onValueChange = {
                    baseUrl = it
                    localError = null
                },
                placeholder = "Anvil Base URL (https://<app>.anvil.app)",
                leadingIcon = {
                    Icon(
                        Icons.Rounded.Public,
                        contentDescription = null,
                        tint = Color.Gray
                    )
                },
                keyboardType = KeyboardType.Uri,
                imeAction = ImeAction.Next,
                keyboardActions = KeyboardActions(
                    onNext = { focusManager.moveFocus(FocusDirection.Down) }
                )
            )
            Spacer(modifier = Modifier.height(24.dp))

            // Email Input Field using a custom glassy style
            GlassyTextField(
                value = email,
                onValueChange = {
                    email = it
                    localError = null
                },
                placeholder = "Email Address",
                leadingIcon = {
                    Icon(
                        Icons.Rounded.Email,
                        contentDescription = null,
                        tint = Color.Gray
                    )
                },
                keyboardType = KeyboardType.Email,
                imeAction = ImeAction.Next,
                keyboardActions = KeyboardActions(
                    onNext = { focusManager.moveFocus(FocusDirection.Down) }
                )
            )
            Spacer(modifier = Modifier.height(24.dp))

            // Password Input Field with visibility toggle
            GlassyTextField(
                value = password,
                onValueChange = {
                    password = it
                    localError = null
                },
                placeholder = "Password",
                leadingIcon = {
                    Icon(
                        Icons.Rounded.VpnKey,
                        contentDescription = null,
                        tint = Color.Gray
                    )
                },
                trailingIcon = {
                    IconButton(onClick = { isPasswordVisible = !isPasswordVisible }) {
                        Icon(
                            if (isPasswordVisible) Icons.Rounded.VisibilityOff else Icons.Rounded.Visibility,
                            contentDescription = if (isPasswordVisible) "Hide password" else "Show password",
                            tint = Color.Gray
                        )
                    }
                },
                visualTransformation = if (isPasswordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                keyboardType = KeyboardType.Password,
                imeAction = ImeAction.Done,
                keyboardActions = KeyboardActions(
                    onDone = {
                        dismissKeyboard(view, keyboardController, focusManager)
                        if (baseUrl.isNotBlank() && email.isNotBlank() && password.isNotBlank()) {
                            submitLogin()
                        } else {
                            localError = "Please complete all fields before signing in."
                        }
                    }
                )
            )
            Spacer(modifier = Modifier.height(24.dp))

            // Main Login Button with rounded corners and primary color
            Button(
                onClick = submitLogin,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                shape = RoundedCornerShape(50),
                colors = ButtonDefaults.buttonColors(containerColor = DeepPurple),
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        strokeWidth = 2.dp,
                        color = White
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = "Signing In...", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                } else {
                    Text(text = "Login", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(modifier = Modifier.width(8.dp))
                    Icon(
                        Icons.AutoMirrored.Rounded.ArrowForward,
                        contentDescription = null,
                        modifier = Modifier.size(20.dp)
                    )
                }
            }
            if (!shownError.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = shownError,
                    color = Color(0xFFFFB4AB),
                    fontSize = 13.sp,
                    textAlign = TextAlign.Center
                )
            }
            Spacer(modifier = Modifier.height(40.dp))

        }
    }
}

/**
 * A custom TextField component with a "glassmorphism" effect.
 * It features a background gradient, subtle border, and custom Material 3 colors.
 */
@Composable
fun GlassyTextField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    leadingIcon: @Composable (() -> Unit)? = null,
    trailingIcon: @Composable (() -> Unit)? = null,
    visualTransformation: VisualTransformation = VisualTransformation.None,
    keyboardType: KeyboardType = KeyboardType.Text,
    imeAction: ImeAction = ImeAction.Default,
    keyboardActions: KeyboardActions = KeyboardActions.Default
) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(16.dp))
            .background(
                brush = Brush.verticalGradient(
                    colors = listOf(
                        GlassyBlack.copy(alpha = 0.5f),
                        Color(0x800F172A)
                    )
                )
            )
            .border(1.dp, Color.White.copy(alpha = 0.1f), RoundedCornerShape(16.dp))
            .padding(1.dp)
    ) {
        TextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF111827), RoundedCornerShape(15.dp)),
            placeholder = { Text(placeholder, color = Color.Gray) },
            leadingIcon = leadingIcon,
            trailingIcon = trailingIcon,
            singleLine = true,
            visualTransformation = visualTransformation,
            keyboardOptions = KeyboardOptions(
                keyboardType = keyboardType,
                imeAction = imeAction
            ),
            keyboardActions = keyboardActions,
            colors = TextFieldDefaults.colors(
                focusedContainerColor = Color.Transparent,
                unfocusedContainerColor = Color.Transparent,
                disabledContainerColor = Color.Transparent,
                cursorColor = DeepPurple,
                focusedIndicatorColor = Color.Transparent,
                unfocusedIndicatorColor = Color.Transparent,
                disabledIndicatorColor = Color.Transparent,
                focusedTextColor = White,
                unfocusedTextColor = White,
                focusedPlaceholderColor = Color.Gray,
                unfocusedPlaceholderColor = Color.Gray,
                focusedLeadingIconColor = DeepPurple,
                unfocusedLeadingIconColor = Color.Gray,
            )
        )
    }
}

@Preview(showBackground = true)
@Composable
fun LoginScreenPreview() {
    AppTheme {
        LoginScreen(
            initialBaseUrl = "https://your-app.anvil.app/",
            isLoading = false,
            errorMessage = null,
            onLogin = { _, _, _ -> }
        )
    }
}

private fun dismissKeyboard(
    view: android.view.View,
    keyboardController: androidx.compose.ui.platform.SoftwareKeyboardController?,
    focusManager: androidx.compose.ui.focus.FocusManager
) {
    keyboardController?.hide()
    focusManager.clearFocus(force = true)
    view.clearFocus()
    val imm = view.context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager
    imm?.hideSoftInputFromWindow(view.windowToken, 0)
}
