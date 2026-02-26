package com.example.bmamessenger.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

/**
 * Defines the color scheme for the application.
 */
private val AppColorScheme = darkColorScheme(
    primary = DeepPurple,
    secondary = LightPurple,
    background = NightBlue,
    surface = GlassyBlack,
    onPrimary = White,
    onSecondary = White,
    onBackground = White,
    onSurface = White
)

/**
 * The main theme for the application.
 *
 * @param content The content to be displayed within the theme.
 */
@Composable
fun AppTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = AppColorScheme,
        typography = AppTypography,
        content = content
    )
}
