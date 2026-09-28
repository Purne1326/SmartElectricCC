package com.smartelectric.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import com.smartelectric.app.model.LogRecord
import com.smartelectric.app.network.RetrofitClient

@Composable
fun SystemLogsScreen(gatewayIp: String) {
    val coroutineScope = rememberCoroutineScope()
    var logs by remember { mutableStateOf<List<LogRecord>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var isError by remember { mutableStateOf(false) }

    fun loadLogs() {
        isLoading = true
        coroutineScope.launch {
            try {
                val service = RetrofitClient.getService(gatewayIp)
                logs = service.getLogs(50)
                isError = false
            } catch (e: Exception) {
                isError = true
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(gatewayIp) {
        loadLogs()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0B0F19))
            .padding(16.dp)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Gateway Logs",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color = Color(0xFF818CF8)
                )

                IconButton(
                    onClick = { loadLogs() },
                    colors = IconButtonDefaults.iconButtonColors(
                        containerColor = Color(0xFF1E293B)
                    )
                ) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Refresh Logs",
                        tint = Color.White
                    )
                }
            }

            if (isLoading && logs.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize()) {
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center),
                        color = Color(0xFF818CF8)
                    )
                }
            } else if (isError && logs.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize()) {
                    Text(
                        "⚠️ Connection error loading logs.",
                        color = Color(0xFFF87171),
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.fillMaxSize()
                ) {
                    items(logs) { record ->
                        LogRecordRow(record)
                    }
                }
            }
        }
    }
}

@Composable
fun LogRecordRow(record: LogRecord) {
    val levelColor = when (record.level.uppercase()) {
        "ERROR" -> Color(0xFFF87171)
        "WARNING" -> Color(0xFFFBBF24)
        "INFO" -> Color(0xFF60A5FA)
        else -> Color(0xFF94A3B8)
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(8.dp))
            .background(Color(0xFF161F30), RoundedCornerShape(8.dp))
            .padding(12.dp)
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = record.level,
                    color = levelColor,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = record.timestamp,
                    color = Color(0xFF64748B),
                    fontSize = 10.sp
                )
            }
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = record.message,
                color = Color(0xFFE2E8F0),
                fontSize = 13.sp,
                fontFamily = FontFamily.Monospace
            )
        }
    }
}
