package com.smartelectric.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFF818CF8),      // Indigo primary accent
    secondary = Color(0xFF34D399),    // Emerald green secondary
    tertiary = Color(0xFFFBBF24),     // Amber highlights
    background = Color(0xFF0B0F19),   // Premium deep space background
    surface = Color(0xFF161F30),      // Slate surface card background
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onBackground = Color(0xFFE2E8F0), // Cool white text
    onSurface = Color(0xFFE2E8F0)
)

@Composable
fun SmartElectricTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    // Forcing dark theme for premium smart home aesthetics, matching local Streamlit gateway
    val colorScheme = DarkColorScheme

    MaterialTheme(
        colorScheme = colorScheme,
        typography = MaterialTheme.typography,
        content = content
    )
}
