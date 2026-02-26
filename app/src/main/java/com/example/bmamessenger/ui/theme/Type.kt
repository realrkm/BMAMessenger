package com.example.bmamessenger.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import com.example.bmamessenger.R

/**
 * Defines the custom font family used in the application.
 */
val MozillaHeadline = FontFamily(
    Font(R.font.mozilla_headline, FontWeight.Normal),
    Font(R.font.mozilla_headline, FontWeight.Bold)
)

/**
 * Overrides the default typography with the custom font family.
 */
val AppTypography = Typography().run {
    copy(
        bodyLarge = bodyLarge.copy(fontFamily = MozillaHeadline),
        bodyMedium = bodyMedium.copy(fontFamily = MozillaHeadline),
        titleLarge = titleLarge.copy(fontFamily = MozillaHeadline),
        titleMedium = titleMedium.copy(fontFamily = MozillaHeadline),
        labelLarge = labelLarge.copy(fontFamily = MozillaHeadline)
    )
}
