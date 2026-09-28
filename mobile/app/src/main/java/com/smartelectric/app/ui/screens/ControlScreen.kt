package com.smartelectric.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import com.smartelectric.app.model.Appliance
import com.smartelectric.app.model.RelayControlRequest
import com.smartelectric.app.network.RetrofitClient

@Composable
fun ControlScreen(gatewayIp: String) {
    val coroutineScope = rememberCoroutineScope()
    var appliances by remember { mutableStateOf<List<Appliance>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var isError by remember { mutableStateOf(false) }

    // Safety lockout dialog state
    var showLockoutDialog by remember { mutableStateOf(false) }
    var lockoutApplianceName by remember { mutableStateOf("") }

    fun loadStatus() {
        coroutineScope.launch {
            try {
                val service = RetrofitClient.getService(gatewayIp)
                val response = service.getSystemStatus()
                appliances = response.appliances
                isError = false
            } catch (e: Exception) {
                isError = true
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(gatewayIp) {
        loadStatus()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0B0F19))
            .padding(16.dp)
    ) {
        if (isLoading && appliances.isEmpty()) {
            CircularProgressIndicator(
                modifier = Modifier.align(Alignment.Center),
                color = Color(0xFF818CF8)
            )
        } else if (isError && appliances.isEmpty()) {
            Text(
                "⚠️ Failed to connect to local gateway controls.",
                color = Color(0xFFF87171),
                modifier = Modifier.align(Alignment.Center)
            )
        } else {
            Column(modifier = Modifier.fillMaxSize()) {
                Text(
                    text = "Appliance Control",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = Color(0xFF818CF8),
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                Text(
                    text = "Double-buffered relay toggles protected by safety lockout.",
                    fontSize = 12.sp,
                    color = Color(0xFF64748B),
                    modifier = Modifier.padding(bottom = 20.dp)
                )

                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(appliances) { app ->
                        ControlCard(
                            appliance = app,
                            onToggle = { desiredState ->
                                coroutineScope.launch {
                                    try {
                                        val service = RetrofitClient.getService(gatewayIp)
                                        val response = service.controlRelay(
                                            RelayControlRequest(app.name, desiredState)
                                        )
                                        
                                        if (response.status == "success") {
                                            // Refresh local lists
                                            loadStatus()
                                        } else {
                                            // Lockout trigger (API response contains error metadata)
                                            lockoutApplianceName = app.name
                                            showLockoutDialog = true
                                        }
                                    } catch (e: Exception) {
                                        // Lockout or connection error during request
                                        lockoutApplianceName = app.name
                                        showLockoutDialog = true
                                    }
                                }
                            }
                        )
                    }
                }
            }
        }

        // Safety lockout dialog
        if (showLockoutDialog) {
            AlertDialog(
                onDismissRequest = { showLockoutDialog = false },
                title = { Text("🔒 Safety Lockout Active", color = Color(0xFFF87171), fontWeight = FontWeight.Bold) },
                text = {
                    Text(
                        "Command for $lockoutApplianceName was rejected. " +
                        "Rapid switching triggers contact chattering, which can damage induction loads. " +
                        "Please wait 3 seconds before toggling this relay again.",
                        color = Color(0xFFCBD5E1)
                    )
                },
                confirmButton = {
                    TextButton(onClick = { showLockoutDialog = false }) {
                        Text("Acknowledge", color = Color(0xFF818CF8))
                    }
                },
                containerColor = Color(0xFF1E293B)
            )
        }
    }
}

@Composable
fun ControlCard(appliance: Appliance, onToggle: (Int) -> Unit) {
    val isOn = appliance.status == 1
    val cardBg = if (isOn) Color(0xFF162521) else Color(0xFF151D2A)
    val borderColor = if (isOn) Color(0xFF10B981) else Color(0xFF1E293B)

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, borderColor, RoundedCornerShape(16.dp))
            .background(cardBg, RoundedCornerShape(16.dp))
            .padding(20.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(appliance.name, fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color.White)
                Spacer(modifier = Modifier.height(4.dp))
                Text("Relay: GPIO ${appliance.relayPin}", fontSize = 12.sp, color = Color(0xFF64748B))
            }

            Switch(
                checked = isOn,
                onCheckedChange = { isChecked ->
                    onToggle(if (isChecked) 1 else 0)
                },
                colors = SwitchDefaults.colors(
                    checkedThumbColor = Color(0xFF10B981),
                    checkedTrackColor = Color(0xFF0F3628),
                    uncheckedThumbColor = Color(0xFF94A3B8),
                    uncheckedTrackColor = Color(0xFF1E293B)
                )
            )
        }
    }
}
