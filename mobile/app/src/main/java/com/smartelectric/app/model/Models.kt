package com.smartelectric.app.model

import com.google.gson.annotations.SerializedName

// Status models
data class SystemStatus(
    val appliances: List<Appliance>,
    @SerializedName("latest_telemetry") val latestTelemetry: Map<String, TelemetryRecord>,
    val dht: DhtRecord,
    val anomalies: Map<String, Boolean>? = emptyMap(),
    @SerializedName("auto_shedding_enabled") val autoSheddingEnabled: Boolean? = false,
    @SerializedName("power_source") val powerSource: String? = "GRID SUPPLY"
)

data class Appliance(
    val id: Int,
    val name: String,
    @SerializedName("relay_pin") val relayPin: Int,
    val status: Int,
    @SerializedName("last_updated") val lastUpdated: String
)

data class TelemetryRecord(
    val current: Double,
    val power: Double,
    val voltage: Double,
    val timestamp: String?
)

data class DhtRecord(
    val temperature: Double,
    val humidity: Double,
    val pir: Int? = 0,
    val ldr: Double? = 0.0,
    val timestamp: String?
)

// Control models
data class RelayControlRequest(
    val appliance: String,
    val state: Int
)

data class ControlResponse(
    val status: String,
    val appliance: String,
    val state: Int,
    @SerializedName("mqtt_published") val mqttPublished: Boolean
)

// Metrics models
data class MetricsResponse(
    val range: String,
    val appliances: Map<String, ApplianceMetrics>,
    val totals: TotalMetrics
)

data class ApplianceMetrics(
    @SerializedName("average_power_w") val averagePowerW: Double,
    @SerializedName("duration_hours") val durationHours: Double,
    val kwh: Double,
    @SerializedName("flat_cost_inr") val flatCostInr: Double,
    @SerializedName("tiered_cost_inr") val tieredCostInr: Double
)

data class TotalMetrics(
    val kwh: Double,
    @SerializedName("flat_cost_inr") val flatCostInr: Double,
    @SerializedName("tiered_cost_inr") val tieredCostInr: Double
)

// History & Logs models
data class HistoryRecord(
    val timestamp: String,
    @SerializedName("appliance_name") val applianceName: String?,
    val current: Double,
    val power: Double,
    val voltage: Double
)

data class LogRecord(
    val id: Int,
    val level: String,
    val message: String,
    val timestamp: String
)
