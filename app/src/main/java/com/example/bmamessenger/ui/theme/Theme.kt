package com.example.bmamessenger.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

/**
 * Defines the dark color scheme for the application.
 */
private val AppDarkColorScheme = darkColorScheme(
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
 * Defines the light color scheme for the application.
 */
private val AppLightColorScheme = lightColorScheme(
    primary = DeepPurple,
    secondary = LightPurple,
    background = White,
    surface = LightSurface,
    onPrimary = White,
    onSecondary = White,
    onBackground = ColorBlack,
    onSurface = ColorBlack
)

/**
 * The main theme for the application.
 *
 * @param darkTheme Whether dark mode is enabled.
 * @param content The content to be displayed within the theme.
 */
@Composable
fun AppTheme(
    darkTheme: Boolean = true,
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) AppDarkColorScheme else AppLightColorScheme,
        typography = AppTypography,
        content = content
    )
}
