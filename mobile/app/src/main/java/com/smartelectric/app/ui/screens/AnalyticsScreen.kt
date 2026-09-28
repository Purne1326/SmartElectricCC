package com.smartelectric.app.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import com.smartelectric.app.model.MetricsResponse
import com.smartelectric.app.model.HistoryRecord
import com.smartelectric.app.network.RetrofitClient

@Composable
fun AnalyticsScreen(gatewayIp: String) {
    var rangeType by remember { mutableStateOf("today") }
    var metrics by remember { mutableStateOf<MetricsResponse?>(null) }
    var history by remember { mutableStateOf<List<HistoryRecord>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var isError by remember { mutableStateOf(false) }

    LaunchedEffect(gatewayIp, rangeType) {
        isLoading = true
        try {
            val service = RetrofitClient.getService(gatewayIp)
            metrics = service.getMetrics(rangeType)
            history = service.getHistory(50) // Fetch latest 50 history rows
            isError = false
        } catch (e: Exception) {
            isError = true
        } finally {
            isLoading = false
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0B0F19))
            .padding(16.dp)
    ) {
        if (isLoading && metrics == null) {
            CircularProgressIndicator(
                modifier = Modifier.align(Alignment.Center),
                color = Color(0xFF818CF8)
            )
        } else if (isError && metrics == null) {
            Text(
                "⚠️ Failed to load analytics metrics",
                color = Color(0xFFF87171),
                modifier = Modifier.align(Alignment.Center)
            )
        } else {
            metrics?.let { data ->
                val totals = data.totals
                val carbon = totals.kwh * 0.82

                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                ) {
                    // Header
                    Text(
                        text = "Analytics & Billing",
                        fontSize = 24.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color = Color(0xFF818CF8),
                        modifier = Modifier.padding(bottom = 16.dp)
                    )

                    // Period Selector Row
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        listOf("today" to "Today", "month" to "Month", "total" to "Total").forEach { (type, label) ->
                            Button(
                                onClick = { rangeType = type },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (rangeType == type) Color(0xFF818CF8) else Color(0xFF1E293B)
                                ),
                                shape = RoundedCornerShape(20.dp),
                                modifier = Modifier.weight(1f)
                            ) {
                                Text(label, color = Color.White, fontSize = 12.sp)
                            }
                        }
                    }

                    // KPI Cards Row
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 16.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        ColumnKpiCard(
                            label = "Energy",
                            value = String.format("%.2f kWh", totals.kwh),
                            color = Color(0xFFFBBF24),
                            modifier = Modifier.weight(1f)
                        )
                        ColumnKpiCard(
                            label = "Flat Cost",
                            value = String.format("₹%.2f", totals.flatCostInr),
                            color = Color(0xFF34D399),
                            modifier = Modifier.weight(1f)
                        )
                        ColumnKpiCard(
                            label = "Tiered Cost",
                            value = String.format("₹%.2f", totals.tieredCostInr),
                            color = Color(0xFF60A5FA),
                            modifier = Modifier.weight(1f)
                        )
                    }

                    // CO2 Carbon Card
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 20.dp)
                            .border(1.dp, Color(0xFF2A1E20), RoundedCornerShape(12.dp))
                            .background(Color(0xFF1E1416), RoundedCornerShape(12.dp))
                            .padding(16.dp)
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column {
                                Text("Carbon Footprint (CO2)", fontSize = 12.sp, color = Color(0xFF94A3B8))
                                Text("Indian electrical grid average factor", fontSize = 10.sp, color = Color(0xFF64748B))
                            }
                            Text(String.format("%.2f kg", carbon), fontSize = 20.sp, fontWeight = FontWeight.Bold, color = Color(0xFFF87171))
                        }
                    }

                    // 3. Native Canvas Chart representation
                    Text(
                        text = "📈 Live Load Timeline (Watts)",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF94A3B8),
                        modifier = Modifier.padding(bottom = 12.dp)
                    )

                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(180.dp)
                            .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(16.dp))
                            .background(Color(0xFF111827), RoundedCornerShape(16.dp))
                            .padding(16.dp)
                    ) {
                        if (history.isEmpty()) {
                            Text(
                                "No telemetry logs registered for graphing.",
                                color = Color(0xFF64748B),
                                modifier = Modifier.align(Alignment.Center)
                            )
                        } else {
                            // Render Native Canvas Line Graph
                            Canvas(modifier = Modifier.fillMaxSize()) {
                                val width = size.width
                                val height = size.height

                                val maxPower = history.maxOfOrNull { it.power }?.coerceAtLeast(100.0) ?: 100.0
                                val points = history.reversed()

                                val stepX = width / (points.size - 1).coerceAtLeast(1)
                                
                                val path = Path()
                                points.forEachIndexed { idx, item ->
                                    val x = idx * stepX
                                    val y = height - ((item.power / maxPower) * height).toFloat()
                                    if (idx == 0) {
                                        path.moveTo(x, y)
                                    } else {
                                        path.lineTo(x, y)
                                    }
                                }

                                drawPath(
                                    path = path,
                                    color = Color(0xFF818CF8),
                                    style = Stroke(width = 4f)
                                )

                                // Draw baseline
                                drawLine(
                                    color = Color(0xFF334155),
                                    start = Offset(0f, height),
                                    end = Offset(width, height),
                                    strokeWidth = 2f
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ColumnKpiCard(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .border(1.dp, Color(0xFF1E293B), RoundedCornerShape(12.dp))
            .background(Color(0xFF161F30), RoundedCornerShape(12.dp))
            .padding(16.dp)
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(label.uppercase(), fontSize = 10.sp, fontWeight = FontWeight.Bold, color = Color(0xFF64748B))
            Spacer(modifier = Modifier.height(6.dp))
            Text(value, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = color)
        }
    }
}
