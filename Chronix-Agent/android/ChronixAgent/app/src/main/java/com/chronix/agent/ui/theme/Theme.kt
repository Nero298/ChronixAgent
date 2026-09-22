package com.chronix.agent.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

/**
 * Chronix Agent uses a single dark theme by design (gold / blue / dark
 * blue / black, ChatGPT-style layout) rather than switching with system
 * light/dark mode - the brand palette only reads correctly on dark.
 */
private val ChronixColorScheme = darkColorScheme(
    primary = ChronixGold,
    onPrimary = ChronixNearBlack,
    secondary = ChronixDeepTeal,
    onSecondary = ChronixTextPrimary,
    background = ChronixMidnight,
    onBackground = ChronixTextPrimary,
    surface = ChronixDarkBlue,
    onSurface = ChronixTextPrimary,
    surfaceVariant = ChronixNearBlack,
    onSurfaceVariant = ChronixTextSecondary,
    error = Color(0xFFCF6679),
)

@Composable
fun ChronixTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = ChronixColorScheme,
        content = content,
    )
}
