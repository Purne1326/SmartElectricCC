package com.smartelectric.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import com.smartelectric.app.model.SystemStatus
import com.smartelectric.app.network.RetrofitClient

@Composable
fun DashboardScreen(gatewayIp: String) {
    var status by remember { mutableStateOf<SystemStatus?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var isError by remember { mutableStateOf(false) }

    // Telemetry polling loop (Fetches every 5 seconds)
    LaunchedEffect(gatewayIp) {
        isLoading = true
        while (true) {
            try {
                val service = RetrofitClient.getService(gatewayIp)
                val response = service.getSystemStatus()
                status = response
                isError = false
            } catch (e: Exception) {
                isError = true
            } finally {
                isLoading = false
            }
            delay(5000)
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0B0F19))
            .padding(16.dp)
    ) {
        if (isLoading && status == null) {
            CircularProgressIndicator(
                modifier = Modifier.align(Alignment.Center),
                color = Color(0xFF818CF8)
            )
        } else if (isError && status == null) {
            Column(
                modifier = Modifier.align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text("⚠️ Gateway Offline", color = Color(0xFFF87171), fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Spacer(modifier = Modifier.height(8.dp))
                Text("Cannot connect to Jetson API at $gatewayIp:8000", color = Color(0xFF94A3B8), fontSize = 14.sp)
            }
        } else {
            status?.let { data ->
                val totalPower = data.latestTelemetry.values.sumOf { it.power }
                val totalCurrent = data.latestTelemetry.values.sumOf { it.current }

                Column(modifier = Modifier.fillMaxSize()) {
                    // Title block
                    Text(
                        text = "SmartElectric Edge",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = Color(0xFF818CF8),
                        modifier = Modifier.padding(bottom = 16.dp)
                    )

                    // 1. KPI Cards Row 1: Power & Climate
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        KpiCard(
                            label = "Total Load",
                            value = String.format("%.1f W", totalPower),
                            color = Color(0xFFFBBF24),
                            modifier = Modifier.weight(1f)
                        )
                        KpiCard(
                            label = "Current",
                            value = String.format("%.2f A", totalCurrent),
                            color = Color(0xFFCBD5E1),
                            modifier = Modifier.weight(1f)
                        )
                        KpiCard(
                            label = "Temp / Hum",
                            value = String.format("%.0f°C / %.0f%%", data.dht.temperature, data.dht.humidity),
                            color = Color(0xFFF87171),
                            modifier = Modifier.weight(1.2f)
                        )
                    }

                    // KPI Cards Row 2: Ambient Sensors (PIR, LDR, Supply)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        KpiCard(
                            label = "Motion (PIR)",
                            value = if ((data.dht.pir ?: 0) == 1) "DETECTED" else "CLEAR",
                            color = if ((data.dht.pir ?: 0) == 1) Color(0xFFA855F7) else Color(0xFF64748B),
                            modifier = Modifier.weight(1f)
                        )
                        KpiCard(
                            label = "Light (LDR)",
                            value = String.format("%.0f%%", data.dht.ldr ?: 0.0),
                            color = Color(0xFFFACC15),
                            modifier = Modifier.weight(1f)
                        )
                        KpiCard(
                            label = "Source",
                            value = data.powerSource ?: "GRID SUPPLY",
                            color = if (data.powerSource == "SOLAR SUPPLY") Color(0xFF10B981) else Color(0xFF3B82F6),
                            modifier = Modifier.weight(1.2f)
                        )
                    }

                    Text(
                        text = "📋 Appliance Summary",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF94A3B8),
                        modifier = Modifier.padding(bottom = 12.dp)
                    )

                    // 2. Appliance Telemetry Grid
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(2),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(data.appliances) { appliance ->
                            val telemetry = data.latestTelemetry[appliance.name]
                            ApplianceTelemetryCard(
                                name = appliance.name,
                                isOn = appliance.status == 1,
                                power = telemetry?.power ?: 0.0,
                                current = telemetry?.current ?: 0.0
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun KpiCard(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(12.dp))
            .background(Color(0xFF161F30), RoundedCornerShape(12.dp))
            .padding(12.dp)
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Text(label.uppercase(), fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF64748B))
            Spacer(modifier = Modifier.height(4.dp))
            Text(value, fontSize = 16.sp, fontWeight = FontWeight.Black, color = color)
        }
    }
}

@Composable
fun ApplianceTelemetryCard(name: String, isOn: Boolean, power: Double, current: Double) {
    val gradient = if (isOn) {
        Brush.verticalGradient(colors = listOf(Color(0xFF1E293B), Color(0xFF152A22)))
    } else {
        Brush.verticalGradient(colors = listOf(Color(0xFF1E293B), Color(0xFF1B1B29)))
    }

    val borderColor = if (isOn) Color(0xFF10B981) else Color(0xFF334155)

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(130.dp)
            .border(1.dp, borderColor, RoundedCornerShape(16.dp))
            .background(gradient, RoundedCornerShape(16.dp))
            .padding(16.dp)
    ) {
        Column(modifier = Modifier.fillMaxSize(), verticalArrangement = Arrangement.SpaceBetween) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(name, fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
                
                // Status Badge
                val badgeColor = if (isOn) Color(0xFF34D399) else Color(0xFFF87171)
                val badgeBg = if (isOn) Color(0xFF0F2D23) else Color(0xFF2D171A)
                
                Box(
                    modifier = Modifier
                        .background(badgeBg, RoundedCornerShape(50.dp))
                        .border(1.dp, badgeColor.copy(alpha = 0.3f), RoundedCornerShape(50.dp))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = if (isOn) "ON" else "OFF",
                        color = badgeColor,
                        fontSize = 10.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Column {
                Text(
                    text = String.format("%.1f W", power),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Black,
                    color = if (isOn) Color(0xFFFBBF24) else Color(0xFF64748B)
                )
                Text(
                    text = String.format("%.2f A", current),
                    fontSize = 12.sp,
                    color = Color(0xFF94A3B8)
                )
            }
        }
    }
}
