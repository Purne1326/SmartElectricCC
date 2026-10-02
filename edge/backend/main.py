import os
import sys

# Ensure backend directory is in sys.path for cloud deployment (Render/Railway)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from paho.mqtt import client as mqtt

# Import ML anomaly, solar forecaster, and ONNX models
try:
    from ml.ml_anomaly import detect_anomaly
    from ml.ml_solar_forecaster import predict_solar_forecast
except ImportError:
    # Dummy fallbacks
    def detect_anomaly(app_name, current, power, voltage):
        return False
    def predict_solar_forecast(temp, hum, hour):
        return [100.0, 50.0, 0.0]

# Import Machine Learning Models
try:
    from ml import ml_onnx
except ImportError as e:
    print(f"Warning: Failed to load ONNX models. Starting without AI capabilities. ({e})")
    ml_onnx = None

# Global Auto-Shedding Flag
auto_shedding_enabled = False

# Resolve path to the static HTML frontend index.html
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_FILE_PATH = os.path.join(os.path.dirname(BASE_DIR), "frontend_static", "index.html")

# Import DB configurations
from edge_db import get_db_connection, DB_PATH

# FastAPI App Setup
app = FastAPI(
    title="SmartElectric Edge API",
    description="REST backend for the local Jetson Nano Smart Home Energy Management System",
    version="1.0.0"
)

# Enable CORS for Streamlit and Web/Mobile Frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# MQTT Broker Details
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASS = os.getenv("MQTT_PASS", "")
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() in ("true", "1", "yes")

# Pydantic schemas for requests
class RelayControlRequest(BaseModel):
    appliance: str
    state: int  # 0 for OFF, 1 for ON

class ApplianceResponse(BaseModel):
    id: int
    name: str
    relay_pin: int
    status: int
    last_updated: str

def publish_mqtt_command(appliance: str, state: int):
    """Connects to the MQTT broker (local or HiveMQ Cloud), publishes a relay command, and disconnects reliably."""
    def run_publish():
        try:
            if hasattr(mqtt, "CallbackAPIVersion"):
                client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
            else:
                client = mqtt.Client()

            if MQTT_USER and MQTT_PASS:
                client.username_pw_set(MQTT_USER, MQTT_PASS)

            if MQTT_USE_TLS or MQTT_PORT == 8883:
                import ssl
                client.tls_set(cert_reqs=ssl.CERT_NONE, tls_version=ssl.PROTOCOL_TLSv1_2)

            client.connect(MQTT_BROKER, MQTT_PORT, 10)
            client.loop_start()
            
            # Topic payload structure matching the ESP32 expectations
            payload = {
                "appliance": appliance,
                "state": state
            }
            pub_info = client.publish("smartelectric/control/relay", json.dumps(payload), qos=1)
            pub_info.wait_for_publish(timeout=3.0)
            
            client.loop_stop()
            client.disconnect()
            print(f"Successfully published MQTT command to HiveMQ: {appliance} -> {state}")
        except Exception as e:
            print(f"Non-blocking MQTT Publish failed: {e}", file=sys.stderr)

    import threading
    threading.Thread(target=run_publish, daemon=True).start()
    return True

def calculate_kwh_and_cost(avg_power_w: float, hours: float):
    """Calculates kWh and tiered energy costs in INR (₹) based on Average Power and duration."""
    kwh = (avg_power_w * hours) / 1000.0
    
    # Standard Flat Tariff (₹7 per kWh)
    flat_rate = 7.00
    flat_cost = kwh * flat_rate

    # Indian Tiered Tariff Model
    # Tier 1: 0 - 100 kWh @ ₹4.50
    # Tier 2: 101 - 300 kWh @ ₹6.50
    # Tier 3: > 300 kWh @ ₹8.00
    tiered_cost = 0.0
    if kwh <= 100:
        tiered_cost = kwh * 4.50
    elif kwh <= 300:
        tiered_cost = (100 * 4.50) + ((kwh - 100) * 6.50)
    else:
        tiered_cost = (100 * 4.50) + (200 * 6.50) + ((kwh - 300) * 8.00)

    return {
        "kwh": round(kwh, 4),
        "flat_cost_inr": round(flat_cost, 2),
        "tiered_cost_inr": round(tiered_cost, 2)
    }

@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serves the ultra-fast HTML5/JS dashboard static single page application."""
    try:
        if os.path.exists(FRONTEND_FILE_PATH):
            with open(FRONTEND_FILE_PATH, "r", encoding="utf-8") as f:
                return f.read()
        else:
            return f"<html><body><h3>Static UI not found at {FRONTEND_FILE_PATH}</h3></body></html>"
    except Exception as e:
        return f"<html><body><h3>Error loading static UI: {e}</h3></body></html>"

class SheddingRequest(BaseModel):
    enabled: bool

@app.post("/api/control/shedding")
def toggle_auto_shedding(req: SheddingRequest):
    """Enables or disables automatic preemptive load-shedding."""
    global auto_shedding_enabled
    auto_shedding_enabled = req.enabled
    return {"status": "success", "auto_shedding_enabled": auto_shedding_enabled}

@app.get("/api/solar/forecast")
def get_solar_forecast():
    """Predicts solar generation output for the next 3 hours based on current climate metrics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT temperature, humidity FROM dht_data ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        temp = row["temperature"] if row else 25.0
        hum = row["humidity"] if row else 60.0
        hour = datetime.now().hour
        
        forecast = predict_solar_forecast(temp, hum, hour)
        return {
            "status": "success",
            "temperature": temp,
            "humidity": hum,
            "hour": hour,
            "forecast": forecast
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solar forecast model prediction failed: {e}")

@app.get("/api/status")
def get_system_status():
    """Retrieves real-time statuses of all appliances, latest telemetry readings, anomalies, and DHT logs."""
    global auto_shedding_enabled
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all appliances
        cursor.execute("SELECT id, name, relay_pin, status, last_updated FROM appliances")
        appliances = [dict(row) for row in cursor.fetchall()]

        # Fetch latest sensor telemetry and run anomaly detection for each appliance
        telemetry = {}
        anomaly_status = {}
        total_power = 0.0
        for app in appliances:
            cursor.execute("""
                SELECT current, power, voltage, timestamp 
                FROM sensor_data 
                WHERE appliance_name = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (app["name"],))
            row = cursor.fetchone()
            if row:
                r_dict = dict(row)
                telemetry[app["name"]] = r_dict
                total_power += float(row["power"] or 0.0)
                
                # Check for anomalies
                try:
                    anomaly_status[app["name"]] = detect_anomaly(
                        app["name"], 
                        float(r_dict["current"]), 
                        float(r_dict["power"]), 
                        float(r_dict["voltage"])
                    )
                except Exception:
                    anomaly_status[app["name"]] = None
            else:
                telemetry[app["name"]] = {"current": 0.0, "power": 0.0, "voltage": 230.0, "timestamp": None}
                anomaly_status[app["name"]] = None

        # Fetch latest DHT22 reading (includes PIR and LDR now)
        cursor.execute("SELECT temperature, humidity, pir, ldr, timestamp FROM dht_data ORDER BY timestamp DESC LIMIT 1")
        dht_row = cursor.fetchone()
        if dht_row:
            dht = dict(dht_row)
            dht["pir"] = dht.get("pir") if dht.get("pir") is not None else 0
            dht["ldr"] = dht.get("ldr") if dht.get("ldr") is not None else 0.0
        else:
            dht = {"temperature": 0.0, "humidity": 0.0, "pir": 0, "ldr": 0.0, "timestamp": None}

        # Query last 15 minutes of PIR readings to see if room is empty
        # Telemetry is every 5 seconds, so 15 mins is 180 readings. We verify at least 15 readings exist.
        fifteen_mins_ago = (datetime.now() - timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("SELECT pir FROM dht_data WHERE timestamp >= ? AND pir IS NOT NULL", (fifteen_mins_ago,))
        pir_rows = [row[0] for row in cursor.fetchall()]
        
        room_empty_15m = False
        if len(pir_rows) >= 15 and all(p == 0 for p in pir_rows):
            room_empty_15m = True

        # Run GRU forecast to determine future load peaks
        preemptive_warning = False
        shed_triggered = False
        shedded_appliance = None
        predicted_max = total_power

        try:
            if ml_onnx is not None:
                forecast_vals = ml_onnx.run_forecast(total_power)
            else:
                forecast_vals = run_forecast(total_power)
            predicted_max = max(forecast_vals)
            if predicted_max > 400.0:
                preemptive_warning = True
        except Exception:
            pass

        # Perform Preemptive Auto-Shedding if enabled and warning is active
        if preemptive_warning and auto_shedding_enabled and total_power > 10.0:
            # Non-essential shedding order: Fan, TV, Light
            shed_priority = ["Fan", "TV", "Light"]
            for target_app in shed_priority:
                # Find if it is currently ON
                app_entry = next((a for a in appliances if a["name"] == target_app), None)
                if app_entry and app_entry["status"] == 1:
                    # Switch OFF in database
                    cursor.execute("""
                        UPDATE appliances 
                        SET status = 0, last_updated = CURRENT_TIMESTAMP 
                        WHERE name = ?
                    """, (target_app,))
                    
                    # Log to system journal
                    log_msg = f"Preemptive Auto-Shedding Triggered: Turned OFF {target_app} to prevent predicted grid overload ({predicted_max:.2f} W > 400W)"
                    cursor.execute(
                        "INSERT INTO system_logs (level, message) VALUES (?, ?)",
                        ("INFO", log_msg)
                    )
                    
                    # Publish MQTT off command
                    publish_mqtt_command(target_app, 0)
                    
                    shed_triggered = True
                    shedded_appliance = target_app
                    
                    # Update local state immediately
                    app_entry["status"] = 0
                    app_entry["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    break

        # AI Rules Engine & Efficiency Predictions
        ai_recommendations = []
        
        # Rule 1: No motion + Light ON
        light_power = telemetry.get("Light", {}).get("power", 0.0)
        if dht["pir"] == 0 and light_power > 5.0:
            ai_recommendations.append({
                "rule": "No motion + Light ON",
                "severity": "CAUTION",
                "appliance": "Light",
                "message": "Light is ON but no motion is detected in the room.",
                "recommendation": "Turn OFF Light to save energy."
            })
            
        # Rule 2: High temperature + Fan OFF
        fan_power = telemetry.get("Fan", {}).get("power", 0.0)
        if dht["temperature"] > 30.0 and fan_power < 2.0:
            ai_recommendations.append({
                "rule": "High temperature + Fan OFF",
                "severity": "INFO",
                "appliance": "Fan",
                "message": f"Room temperature is high ({dht['temperature']:.1f}°C) but the Fan is OFF.",
                "recommendation": "Recommend turning Fan ON for comfort."
            })
            
        # Rule 3: TV drawing current at 3 AM
        tv_power = telemetry.get("TV", {}).get("power", 0.0)
        current_hour = datetime.now().hour
        if current_hour in [0, 1, 2, 3, 4] and tv_power > 10.0:
            ai_recommendations.append({
                "rule": "TV active at night",
                "severity": "WARNING",
                "appliance": "TV",
                "message": f"TV is active at {current_hour} AM.",
                "recommendation": "Possible unnecessary overnight usage. Turn OFF TV."
            })
            
        # Rule 4: Fridge current unusually high
        fridge_power = telemetry.get("Fridge", {}).get("power", 0.0)
        if fridge_power > 280.0:
            ai_recommendations.append({
                "rule": "Fridge high current",
                "severity": "WARNING",
                "appliance": "Fridge",
                "message": f"Fridge power consumption is unusually high ({fridge_power:.1f} W).",
                "recommendation": "Possible compressor fault or maintenance needed."
            })
            
        # Rule 5: Room empty for 15 minutes
        if room_empty_15m:
            active_unnecessary = []
            for app in ["Fan", "TV", "Light"]:
                if telemetry.get(app, {}).get("power", 0.0) > 5.0:
                    active_unnecessary.append(app)
                    
            if active_unnecessary:
                ai_recommendations.append({
                    "rule": "Room empty for 15 minutes",
                    "severity": "CAUTION",
                    "appliance": ", ".join(active_unnecessary),
                    "message": f"Room has been empty for 15 minutes but {', '.join(active_unnecessary)} is/are still ON.",
                    "recommendation": "Turn OFF all unnecessary appliances."
                })
                
                # If Auto-Shedding is enabled, auto turn them off!
                if auto_shedding_enabled:
                    for app in active_unnecessary:
                        cursor.execute("UPDATE appliances SET status = 0, last_updated = CURRENT_TIMESTAMP WHERE name = ?", (app,))
                        publish_mqtt_command(app, 0)
                        log_msg = f"Auto-Shedding: Turned OFF {app} because room was empty for 15 minutes."
                        cursor.execute("INSERT INTO system_logs (level, message) VALUES (?, ?)", ("INFO", log_msg))
                        
                        # Update local state immediately
                        app_entry = next((a for a in appliances if a["name"] == app), None)
                        if app_entry:
                            app_entry["status"] = 0
                            app_entry["last_updated"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.commit()
        conn.close()

        # Determine active power source based on 400W threshold
        power_source = "Solar" if total_power > 400.0 else "Grid"

        return {
            "appliances": appliances,
            "latest_telemetry": telemetry,
            "anomaly_status": anomaly_status,
            "dht": dht,
            "total_power": round(total_power, 2),
            "power_source": power_source,
            "auto_shedding_enabled": auto_shedding_enabled,
            "preemptive_warning": preemptive_warning,
            "predicted_max_power": round(predicted_max, 2),
            "shed_triggered": shed_triggered,
            "shedded_appliance": shedded_appliance,
            "room_empty_15m": room_empty_15m,
            "ai_recommendations": ai_recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failure: {e}")

@app.post("/api/control")
def control_relay(req: RelayControlRequest):
    """Sends control command to ESP32 via MQTT and updates local database."""
    if req.state not in (0, 1):
        raise HTTPException(status_code=400, detail="State must be 0 (OFF) or 1 (ON)")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify appliance exists
        cursor.execute("SELECT name FROM appliances WHERE name = ?", (req.appliance,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail=f"Appliance '{req.appliance}' not found")

        # Attempt to publish control command via MQTT
        mqtt_success = publish_mqtt_command(req.appliance, req.state)
        
        if not mqtt_success:
            # We still log to DB, but report the warning
            print(f"Warning: Failed to transmit MQTT command for {req.appliance} to broker.", file=sys.stderr)

        # Update local DB relay state
        cursor.execute("""
            UPDATE appliances 
            SET status = ?, last_updated = CURRENT_TIMESTAMP 
            WHERE name = ?
        """, (req.state, req.appliance))

        # Log system command
        log_message = f"Relay command sent: {req.appliance} -> {'ON' if req.state == 1 else 'OFF'} (MQTT Sync: {mqtt_success})"
        cursor.execute(
            "INSERT INTO system_logs (level, message) VALUES (?, ?)",
            ("INFO" if mqtt_success else "WARNING", log_message)
        )

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "appliance": req.appliance,
            "state": req.state,
            "mqtt_published": mqtt_success
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal database/control error: {e}")

@app.get("/api/metrics")
def get_metrics(range_type: str = Query("today", regex="^(today|month|total)$")):
    """Calculates active hours, energy consumption (kWh), and costs in ₹ per appliance."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Define date filter
        if range_type == "today":
            start_date = datetime.combine(date.today(), datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
        elif range_type == "month":
            start_date = date.today().replace(day=1).strftime('%Y-%m-%d 00:00:00')
        else: # total
            start_date = "1970-01-01 00:00:00"

        # Fetch list of appliances
        cursor.execute("SELECT name FROM appliances")
        appliances = [row["name"] for row in cursor.fetchall()]

        metrics = {}
        total_kwh = 0.0
        total_cost_flat = 0.0
        total_cost_tiered = 0.0

        for name in appliances:
            # Query avg power and duration for this appliance
            cursor.execute("""
                SELECT 
                    AVG(power) as avg_power,
                    MIN(timestamp) as min_ts,
                    MAX(timestamp) as max_ts,
                    COUNT(*) as count
                FROM sensor_data
                WHERE appliance_name = ? AND timestamp >= ?
            """, (name, start_date))
            
            row = cursor.fetchone()
            if row and row["count"] > 0 and row["avg_power"] is not None:
                avg_power = float(row["avg_power"])
                try:
                    min_dt = datetime.strptime(row["min_ts"], '%Y-%m-%d %H:%M:%S')
                    max_dt = datetime.strptime(row["max_ts"], '%Y-%m-%d %H:%M:%S')
                    duration_hours = max((max_dt - min_dt).total_seconds() / 3600.0, 0.05) # Minimum 3 minutes to avoid zero division
                except Exception:
                    # Fallback if parsing fails or timestamps are in a different format
                    duration_hours = 0.0

                calc = calculate_kwh_and_cost(avg_power, duration_hours)
                metrics[name] = {
                    "average_power_w": round(avg_power, 2),
                    "duration_hours": round(duration_hours, 2),
                    "kwh": calc["kwh"],
                    "flat_cost_inr": calc["flat_cost_inr"],
                    "tiered_cost_inr": calc["tiered_cost_inr"]
                }
                total_kwh += calc["kwh"]
                total_cost_flat += calc["flat_cost_inr"]
                total_cost_tiered += calc["tiered_cost_inr"]
            else:
                metrics[name] = {
                    "average_power_w": 0.0,
                    "duration_hours": 0.0,
                    "kwh": 0.0,
                    "flat_cost_inr": 0.0,
                    "tiered_cost_inr": 0.0
                }

        conn.close()

        return {
            "range": range_type,
            "appliances": metrics,
            "totals": {
                "kwh": round(total_kwh, 4),
                "flat_cost_inr": round(total_cost_flat, 2),
                "tiered_cost_inr": round(total_cost_tiered, 2)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metrics calculation failure: {e}")

@app.get("/api/history")
def get_historical_data(
    appliance: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """Retrieves historical power consumption logs for plotting."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if appliance:
            cursor.execute("""
                SELECT timestamp, current, power, voltage 
                FROM sensor_data 
                WHERE appliance_name = ? 
                ORDER BY timestamp DESC LIMIT ?
            """, (appliance, limit))
        else:
            cursor.execute("""
                SELECT timestamp, appliance_name, current, power, voltage 
                FROM sensor_data 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))

        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History query failure: {e}")

@app.get("/api/logs")
def get_system_logs(limit: int = Query(50, ge=1, le=200)):
    """Retrieves the latest local system logs from database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, level, message, timestamp FROM system_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logs query failure: {e}")

# Import ML forecaster modules safely
try:
    if ml_onnx is not None:
        from ml_onnx import run_forecast
    else:
        from ml_forecaster import run_forecast
except Exception as e:
    # Fallback to dummy generator if ML packages are missing in environment
    def run_forecast(current_power_watts=300.0):
        import random
        return [round(current_power_watts * f, 2) for f in [1.1, 1.25, 0.9, 0.7]]

class PredictLoadRequest(BaseModel):
    current_load: Optional[float] = 250.0

@app.post("/api/v1/predict/load")
def predict_future_load(req: PredictLoadRequest):
    """Predicts future active power curve (4 steps of 15-min intervals) using GRU."""
    try:
        if ml_onnx is not None:
            forecast = ml_onnx.run_forecast(req.current_load)
        else:
            forecast = run_forecast(req.current_load)
            
        timestamps = []
        now = datetime.now()
        for idx in range(1, 5):
            future_time = now + timedelta(minutes=15 * idx)
            timestamps.append(future_time.strftime('%Y-%m-%d %H:%M:%S'))
            
        return {
            "device_id": "jetson-edge-gateway-01",
            "forecasted_timestamps": timestamps,
            "forecasted_power_watts": forecast
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failure: {e}")

@app.post("/api/v1/predict/decision")
def predict_decision(req: PredictLoadRequest):
    """Attributes peak appliance load and determines severity level classification."""
    try:
        if ml_onnx is not None:
            decision = ml_onnx.run_decision()
            
            # Sort attributions to find top appliance by hours
            attributions = decision["attributions"]
            top_app = max(attributions, key=attributions.get)
            
            load_class = decision["load_class"]
            if load_class == "High":
                rec = "Power load is projected to spike above safety thresholds. Consider scheduling washing machines or heavy loads during off-peak hours."
                anomaly_score = 0.85
            elif load_class == "Normal":
                rec = "Optimal consumption pattern. Keep appliances running normally."
                anomaly_score = 0.45
            else:
                rec = "System load is low. Energy saving optimization is active."
                anomaly_score = 0.15
                
            return {
                "classification": load_class.upper(),
                "anomaly_score": anomaly_score,
                "top_attributed_appliance": top_app,
                "recommendation": rec,
                "appliance_hours": attributions,
                "optimization_flags": decision["optimization"]
            }
        else:
            forecast = run_forecast(req.current_load)
            max_forecast = max(forecast)
            
            # Determine classification category
            if max_forecast > 400.0:
                classification = "HIGH"
                rec = "Power load is projected to spike above safety thresholds. Consider scheduling washing machines or heavy loads during off-peak hours."
            elif max_forecast > 200.0:
                classification = "NORMAL"
                rec = "Optimal consumption pattern. Keep appliances running normally."
            else:
                classification = "LOW"
                rec = "System load is low. Energy saving optimization is active."
                
            # Determine top attributed appliance
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT appliance_name, MAX(power) 
                FROM sensor_data 
                WHERE timestamp >= ?
                GROUP BY appliance_name
            """, ((datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),))
            row = cursor.fetchone()
            conn.close()
            
            top_app = row["appliance_name"] if (row and row["appliance_name"]) else "Fridge"
            
            return {
                "classification": classification,
                "anomaly_score": round(min(max((max_forecast - 200.0) / 300.0, 0.0), 1.0), 2),
                "top_attributed_appliance": top_app,
                "recommendation": rec
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision classification failure: {e}")

# ==========================================
# WiFi CSI Zonal Auto-Mapping & Tracking Engine
# ==========================================

class CSIScanRequest(BaseModel):
    table_length: Optional[float] = 3.2
    num_zones: Optional[int] = 4

class CSIPresenceSimulateRequest(BaseModel):
    position_x: float  # Human position along table in meters (0.0 to 3.2m)

# In-memory CSI Zonal Tracking State (Mapped directly to SmartElectric Database Appliances)
csi_tracking_state = {
    "calibrated": False,
    "last_scanned": None,
    "table_length": 3.2,
    "num_zones": 4,
    "active_zone": None,
    "user_position_x": None,
    "nodes": [
        {"id": "node_1", "rssi": -38, "status": "ONLINE", "location": "Table Start (0.0m)"},
        {"id": "node_2", "rssi": -42, "status": "ONLINE", "location": "Table End (3.2m)"}
    ],
    "zones": [
        {"id": 1, "name": "Zone 1 (Bulb 1)", "range": [0.0, 0.8], "appliance": "Light", "active": False},
        {"id": 2, "name": "Zone 2 (Bulb 2)", "range": [0.8, 1.6], "appliance": "Fan", "active": False},
        {"id": 3, "name": "Zone 3 (Bulb 3)", "range": [1.6, 2.4], "appliance": "TV", "active": False},
        {"id": 4, "name": "Zone 4 (Bulb 4)", "range": [2.4, 3.2], "appliance": "Fridge", "active": False}
    ]
}

@app.post("/api/csi/auto-scan")
def trigger_csi_auto_scan(req: CSIScanRequest):
    """Triggers WiFi CSI Auto-Ranging and Auto-Segmentation across table zones."""
    global csi_tracking_state
    try:
        length = req.table_length or 3.2
        num_zones = req.num_zones or 4
        zone_width = length / num_zones
        
        # Publish MQTT Auto-Scan Trigger command to ESP32 nodes
        try:
            publish_mqtt_command("csi_gateway", 1)
        except Exception:
            pass
        
        app_names = ["Light", "Fan", "TV", "Fridge"]
        zones = []
        for i in range(num_zones):
            z_id = i + 1
            z_start = round(i * zone_width, 2)
            z_end = round((i + 1) * zone_width, 2)
            app_name = app_names[i % len(app_names)]
            zones.append({
                "id": z_id,
                "name": f"Zone {z_id} (Bulb {z_id})",
                "range": [z_start, z_end],
                "appliance": app_name,
                "active": False
            })
            
        csi_tracking_state.update({
            "calibrated": True,
            "last_scanned": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "table_length": length,
            "num_zones": num_zones,
            "active_zone": None,
            "user_position_x": None,
            "zones": zones
        })
        
        return {
            "status": "success",
            "message": f"Auto-calibration complete! 4 Zonal Relays mapped to Smart Appliances across {length}m table.",
            "csi_state": csi_tracking_state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSI Auto-Scan failed: {e}")

@app.get("/api/csi/status")
def get_csi_status():
    """Returns live WiFi CSI Zonal Tracking and Auto-Calibration Status."""
    global csi_tracking_state
    return {
        "status": "success",
        "csi_state": csi_tracking_state
    }

class CSIPresenceUpdate(BaseModel):
    position_x: Optional[float] = None  # None or < 0 means vacant
    active_zone: Optional[int] = None   # None or 0 means vacant

@app.post("/api/csi/presence-event")
def process_real_csi_presence(req: CSIPresenceUpdate):
    """Processes real hardware ESP32 CSI presence events. If position_x/active_zone is None, room is VACANT."""
    global csi_tracking_state
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        pos_x = req.position_x
        target_zone = req.active_zone
        
        if pos_x is not None and pos_x >= 0 and target_zone is None:
            for z in csi_tracking_state["zones"]:
                r_start, r_end = z["range"]
                if r_start <= pos_x <= r_end:
                    target_zone = z["id"]
                    break
        
        # If vacant / no human detected
        if pos_x is None or pos_x < 0 or target_zone is None or target_zone == 0:
            csi_tracking_state["user_position_x"] = None
            csi_tracking_state["active_zone"] = None
            
            # Turn OFF all 4 zonal appliances
            for z in csi_tracking_state["zones"]:
                z["active"] = False
                app_name = z["appliance"]
                cursor.execute("UPDATE appliances SET status = 0, last_updated = ? WHERE name = ?", 
                               (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), app_name))
                try:
                    publish_mqtt_command(app_name, 0)
                except Exception:
                    pass
        else:
            pos_x = round(pos_x, 2)
            csi_tracking_state["user_position_x"] = pos_x
            csi_tracking_state["active_zone"] = target_zone
            
            for z in csi_tracking_state["zones"]:
                is_active = (z["id"] == target_zone)
                z["active"] = is_active
                app_name = z["appliance"]
                state_val = 1 if is_active else 0
                
                cursor.execute("UPDATE appliances SET status = ?, last_updated = ? WHERE name = ?", 
                               (state_val, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), app_name))
                try:
                    publish_mqtt_command(app_name, state_val)
                except Exception:
                    pass

        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "vacant": csi_tracking_state["active_zone"] is None,
            "csi_state": csi_tracking_state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSI Tracking update failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


