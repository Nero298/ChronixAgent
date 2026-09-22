package com.chronix.agent.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.chronix.agent.ui.theme.ChronixGold
import com.chronix.agent.ui.theme.ChronixMidnight
import com.chronix.agent.ui.theme.ChronixNearBlack
import com.chronix.agent.ui.theme.ChronixTextPrimary
import com.chronix.agent.ui.theme.ChronixTextSecondary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: MainViewModel,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    var host by remember { mutableStateOf("") }
    var port by remember { mutableStateOf("8765") }
    var deviceName by remember { mutableStateOf("") }
    var pairingCode by remember { mutableStateOf("") }
    var pairingStatus by remember { mutableStateOf<String?>(null) }
    var scanning by remember { mutableStateOf(false) }

    val fieldColors = OutlinedTextFieldDefaults.colors(
        focusedContainerColor = ChronixNearBlack,
        unfocusedContainerColor = ChronixNearBlack,
        focusedBorderColor = ChronixGold,
        unfocusedBorderColor = ChronixTextSecondary.copy(alpha = 0.3f),
        focusedTextColor = ChronixTextPrimary,
        unfocusedTextColor = ChronixTextPrimary,
        focusedLabelColor = ChronixGold,
        unfocusedLabelColor = ChronixTextSecondary,
    )
    val goldButtonColors = ButtonDefaults.buttonColors(
        containerColor = ChronixGold,
        contentColor = ChronixNearBlack,
    )

    Scaffold(
        containerColor = ChronixMidnight,
        topBar = {
            TopAppBar(
                title = { Text("Settings", color = ChronixTextPrimary) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = ChronixMidnight),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .padding(16.dp)
                .fillMaxSize()
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Connect to your PC",
                style = MaterialTheme.typography.titleMedium,
                color = ChronixGold,
                fontWeight = FontWeight.Bold,
            )

            Button(
                enabled = !scanning,
                colors = goldButtonColors,
                onClick = {
                    scanning = true
                    viewModel.scanForAgent(
                        onFound = { foundHost, foundPort, foundName ->
                            host = foundHost
                            port = foundPort.toString()
                            deviceName = foundName
                            scanning = false
                        },
                        onNotFound = { scanning = false },
                    )
                },
            ) { Text(if (scanning) "Scanning..." else "Scan for PC on Wi-Fi") }

            OutlinedTextField(
                value = host, onValueChange = { host = it }, colors = fieldColors,
                label = { Text("PC IP address") }, modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = port, onValueChange = { port = it }, colors = fieldColors,
                label = { Text("Port") }, modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = deviceName, onValueChange = { deviceName = it }, colors = fieldColors,
                label = { Text("Device name") }, modifier = Modifier.fillMaxWidth(),
            )

            Button(
                enabled = host.isNotBlank() && port.toIntOrNull() != null,
                colors = goldButtonColors,
                onClick = {
                    viewModel.saveConnection(context, host, port.toIntOrNull() ?: 8765, deviceName)
                },
            ) { Text("Save connection") }

            Divider(color = ChronixTextSecondary.copy(alpha = 0.2f))

            Text(
                "Pair with this PC",
                style = MaterialTheme.typography.titleMedium,
                color = ChronixGold,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "Being on the same Wi-Fi is not enough on its own — enter the " +
                    "6-digit code shown in the Chronix Agent window on your PC to " +
                    "pair this phone. Only a paired phone can send commands.",
                color = ChronixTextSecondary,
                style = MaterialTheme.typography.bodySmall,
            )
            OutlinedTextField(
                value = pairingCode, onValueChange = { pairingCode = it }, colors = fieldColors,
                label = { Text("Pairing code") }, modifier = Modifier.fillMaxWidth(),
            )
            Button(
                enabled = pairingCode.length == 6,
                colors = goldButtonColors,
                onClick = {
                    viewModel.pair(context, pairingCode) { success ->
                        pairingStatus = if (success) "Paired successfully." else "Pairing failed - check the code."
                    }
                },
            ) { Text("Pair") }
            pairingStatus?.let {
                Text(it, color = if (it.startsWith("Paired")) ChronixGold else ChronixTextSecondary)
            }

            Spacer(Modifier.weight(1f))
            TextButton(onClick = onBack) { Text("Back", color = ChronixTextSecondary) }
        }
    }
}
