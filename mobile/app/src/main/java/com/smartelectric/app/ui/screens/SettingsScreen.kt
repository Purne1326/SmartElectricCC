package com.smartelectric.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun SettingsScreen(
    currentIp: String,
    onIpSaved: (String) -> Unit
) {
    var ipInput by remember { mutableStateOf(currentIp) }
    var saveMessage by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0B0F19))
            .padding(24.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.Start
        ) {
            Text(
                text = "System Settings",
                fontSize = 24.sp,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF818CF8),
                modifier = Modifier.padding(bottom = 8.dp)
            )
            Text(
                text = "Configure the target gateway address to connect the mobile app to the local edge API server.",
                fontSize = 12.sp,
                color = Color(0xFF64748B),
                modifier = Modifier.padding(bottom = 24.dp)
            )

            Text(
                text = "Gateway IP Address / Hostname",
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = Color(0xFFCBD5E1),
                modifier = Modifier.padding(bottom = 8.dp)
            )

            OutlinedTextField(
                value = ipInput,
                onValueChange = { ipInput = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp),
                shape = RoundedCornerShape(12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Color(0xFF818CF8),
                    unfocusedBorderColor = Color(0xFF1E293B),
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White,
                    focusedContainerColor = Color(0xFF161F30),
                    unfocusedContainerColor = Color(0xFF161F30)
                ),
                placeholder = { Text("e.g. 192.168.1.100", color = Color(0xFF475569)) }
            )

            Button(
                onClick = {
                    onIpSaved(ipInput)
                    saveMessage = "IP Settings saved successfully!"
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF818CF8)
                )
            ) {
                Text("Save Configuration", color = Color.White, fontWeight = FontWeight.Bold)
            }

            if (saveMessage.isNotEmpty()) {
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = saveMessage,
                    color = Color(0xFF34D399),
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}
