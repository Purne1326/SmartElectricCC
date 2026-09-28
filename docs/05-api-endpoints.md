# 05. REST API Specifications

The Edge and Cloud layers expose FastAPI REST web services. Here is the comprehensive API dictionary.

---

## 🖥️ Local Edge Backend API (Port 8000)

### 1. System Health
* **Endpoint:** `GET /health`
* **Response (HTTP 200):**
```json
{
  "status": "online",
  "database": "connected",
  "timestamp": "2026-06-21T18:00:00Z"
}
```

### 2. Get Telemetry History
* **Endpoint:** `GET /api/v1/sensors/history`
* **Query Parameters:**
  - `limit`: Default `100` (Max database rows to fetch)
* **Response (HTTP 200):**
```json
[
  {
    "id": 2341,
    "timestamp": "2026-06-21 17:55:00",
    "voltage": 230.0,
    "total_current": 1.96,
    "total_power": 450.8,
    "temperature": 26.5,
    "humidity": 58.4,
    "motion_detected": 0
  }
]
```

### 3. Relay Controls
* **Endpoint:** `POST /api/v1/control/relay`
* **Request Body:**
```json
{
  "appliance": "Light",
  "state": 1
}
```
* **Response (HTTP 200):**
```json
{
  "status": "success",
  "message": "Control payload published for Light"
}
```
* **Error (HTTP 429 - Safety Lockout Cooldown):**
```json
{
  "detail": "Relay control cooldown active. Please wait."
}
```

---

## ☁️ Cloud Sync API (Port 8000)

### 1. Synchronize Historical Data Batch
* **Endpoint:** `POST /api/cloud/sync`
* **Request Body:**
```json
{
  "device_id": "test-gateway-jetson-99",
  "sensor_records": [
    {
      "appliance_name": "Light",
      "current": 0.15,
      "power": 34.5,
      "voltage": 230.0,
      "timestamp": "2026-06-21 12:00:00"
    }
  ],
  "dht_records": [
    {
      "temperature": 26.4,
      "humidity": 60.5,
      "timestamp": "2026-06-21 12:00:00"
    }
  ],
  "log_records": []
}
```
* **Response (HTTP 200):**
```json
{
  "status": "success",
  "device_id": "test-gateway-jetson-99",
  "records_synced": {
    "sensors": 1,
    "dht": 1,
    "logs": 0
  }
}
```
