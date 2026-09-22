package com.chronix.agent.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.chronix.agent.model.ApprovalOutcome
import com.chronix.agent.model.ApprovalRequest
import com.chronix.agent.ui.theme.ChronixDarkBlue
import com.chronix.agent.ui.theme.ChronixGold
import com.chronix.agent.ui.theme.ChronixNearBlack
import com.chronix.agent.ui.theme.ChronixTextPrimary
import com.chronix.agent.ui.theme.ChronixTextSecondary

private val RiskRed = Color(0xFFCF6679)

/**
 * Approval dialog (spec section 11/20). Disables both buttons the moment
 * either is tapped, to prevent duplicate execution from repeated taps or
 * repeated network messages - the actual duplicate-suppression also
 * happens server-side in core/permissions.py, this is defense in depth /
 * UX polish, not the security boundary itself.
 */
@Composable
fun ApprovalDialog(
    request: ApprovalRequest,
    onDecision: (approve: Boolean, onDone: (ApprovalOutcome) -> Unit) -> Unit,
    onDismiss: () -> Unit,
) {
    var processing by remember { mutableStateOf(false) }
    var outcome by remember { mutableStateOf<ApprovalOutcome?>(null) }

    AlertDialog(
        onDismissRequest = { if (!processing) onDismiss() },
        containerColor = ChronixDarkBlue,
        title = { Text("Action Required", color = RiskRed, fontWeight = FontWeight.Bold) },
        text = {
            Column {
                Text(request.description, color = ChronixTextPrimary)
                Spacer(Modifier.height(8.dp))
                Text("Action: ${request.action}", color = ChronixTextSecondary)
                request.target?.let { Text("Target: $it", color = ChronixTextSecondary) }
                Text("Risk: ${request.risk}", color = RiskRed, fontWeight = FontWeight.SemiBold)
                request.estimatedSize?.let {
                    Text("Estimated size: ${it / (1024 * 1024)} MB", color = ChronixTextSecondary)
                }
                Spacer(Modifier.height(8.dp))
                when (val o = outcome) {
                    is ApprovalOutcome.Success -> Text("✓ ${o.message}", color = ChronixGold)
                    is ApprovalOutcome.Failure -> Text("✗ ${o.message}", color = RiskRed)
                    null -> if (processing) Text("Processing...", color = ChronixTextSecondary)
                }
            }
        },
        confirmButton = {
            Button(
                enabled = !processing && outcome == null,
                colors = ButtonDefaults.buttonColors(
                    containerColor = ChronixGold,
                    contentColor = ChronixNearBlack,
                ),
                onClick = {
                    processing = true
                    onDecision(true) { result -> processing = false; outcome = result }
                },
            ) { Text("APPROVE") }
        },
        dismissButton = {
            OutlinedButton(
                enabled = !processing && outcome == null,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = RiskRed),
                onClick = {
                    processing = true
                    onDecision(false) { result -> processing = false; outcome = result }
                },
            ) { Text("REJECT") }
        },
    )
}
