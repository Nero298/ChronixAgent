package com.chronix.agent.ui.theme

import androidx.compose.ui.graphics.Color

// Sampled from the Chronix logo mark (compass/clock X):
val ChronixDeepTeal = Color(0xFF033C50)   // logo ring/arm accent
val ChronixNearBlack = Color(0xFF08151D)  // logo dark arm
val ChronixDarkBlue = Color(0xFF0B2434)   // derived surface tone between the two
val ChronixMidnight = Color(0xFF050C12)   // background, darker than the logo black

// Gold accent (not in the source logo - chosen to pair with the teal/black
// mark for user-message bubbles and interactive highlights):
val ChronixGold = Color(0xFFD4AF37)
val ChronixGoldBright = Color(0xFFE8C766)

val ChronixTextPrimary = Color(0xFFF5F0E6)   // warm off-white, pairs with gold
val ChronixTextSecondary = Color(0xFFA9B4BD) // muted blue-gray

val ChronixBubbleAssistant = ChronixDarkBlue
val ChronixBubbleUser = ChronixGold
