# 04. MQTT Topic Schema

SmartElectric utilizes the MQTT protocol for lightweight real-time communications between the ESP32 micro-controller and the Jetson Edge Gateway.

---

## 🗺️ Topic Directory

| Topic Namespace | Publisher | Subscribers | Description |
|-----------------|-----------|-------------|-------------|
| `smartelectric/sensors/power` | ESP32 | MQTT Worker, Streamlit UI | Real-time sensor metrics (5s frequency) |
| `smartelectric/sensors/dht` | ESP32 | MQTT Worker, Streamlit UI | Environmental temperature/humidity |
| `smartelectric/status/relays` | ESP32 | MQTT Worker, FastAPI API | Relay state updates (on toggle change) |
| `smartelectric/status/online` | ESP32 | MQTT Worker, FastAPI API | Connection LWT (Last Will & Testament) |
| `smartelectric/control/relay` | FastAPI | ESP32 | Outgoing appliance toggle commands |
| `smartelectric/logs` | ESP32 | MQTT Worker, UI | Micro-controller boot & warn events |

---

## 📑 Payload Formats

### 1. Real-time Telemetry (Power & Climate)
* **Topic:** `smartelectric/sensors/power`
* **JSON Structure:**
```json
{
  "Light": 0.15,
  "TV": 0.43,
  "Fridge": 1.10,
  "Fan": 0.28,
  "voltage": 230.0
}
```

* **Topic:** `smartelectric/sensors/dht`
* **JSON Structure:**
```json
{
  "temperature": 27.4,
  "humidity": 63.2
}
```

### 2. Relay Control Commands
* **Topic:** `smartelectric/control/relay`
* **JSON Structure:**
```json
{
  "appliance": "Light",
  "state": 1
}
```
* **Payload States:** `state: 1` represents ON, `state: 0` represents OFF.

### 3. System Logs
* **Topic:** `smartelectric/logs`
* **JSON Structure:**
```json
{
  "level": "INFO",
  "message": "Successfully set relay for Light to ON"
}
```
* **Levels:** `INFO`, `WARNING`, `ERROR`.
