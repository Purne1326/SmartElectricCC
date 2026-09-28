# ☁️ SmartElectric Cloud Platform - Solo Testing Guide

This folder contains the Cloud Server codebase (PostgreSQL models, FastAPI receiver endpoint, sync daemon, and global Streamlit panel). Follow this guide to test the cloud platform in isolation on your development machine, without needing the physical Jetson Nano edge gateway.

---

## 🛠️ Development Setup

1. **Install python dependencies:**
   ```bash
   pip install fastapi uvicorn sqlalchemy psycopg2-binary streamlit pandas plotly requests
   ```
2. **Database Configuration:**
   - The cloud layer utilizes **PostgreSQL** in production.
   - For **solo testing**, if PostgreSQL is not installed, the schema script will automatically fall back to creating a local SQLite file (`smartelectric_cloud.db`) so you can test everything immediately.
   - To connect to a real PostgreSQL instance, export the database connection string:
     ```bash
     # Linux/Mac
     export DATABASE_URL="postgresql://username:password@localhost:5432/smartelectric_cloud"
     # Windows (PowerShell)
     $env:DATABASE_URL="postgresql://username:password@localhost:5432/smartelectric_cloud"
     ```

3. **Initialize Cloud Database Schema:**
   ```bash
   python cloud_db.py
   ```
   *Verify:* This connects to the database and constructs the tables for `edge_devices`, `cloud_sensor_data`, `cloud_dht_data`, and `cloud_logs`.

---

## 🧪 Isolated Testing Procedure

To verify the Cloud API and global Dashboard without a Jetson Nano:

### 1. Launch Cloud API Server
Start the Uvicorn web receiver on port 8000:
```bash
python -m uvicorn cloud_main:app --host 0.0.0.0 --port 8000
```
*Verify:* Navigate to `http://localhost:8000/` in your browser. You should receive:
`{"status":"online","system":"SmartElectric Cloud Sync Receiver", ...}`

### 2. Simulate Edge Sync Payload (Simulate Jetson Sync)
Since you don't have a physical Jetson Nano uploading data, use **Postman** or **curl** to send a synthetic batch JSON payload to the sync receiver endpoint:

- **Endpoint:** `POST http://localhost:8000/api/cloud/sync`
- **Headers:** `Content-Type: application/json`
- **JSON Body:**
  ```json
  {
    "device_id": "test-nano-001122aabbcc",
    "sensor_records": [
      {"appliance_name": "Light", "current": 0.15, "power": 34.5, "voltage": 230.0, "timestamp": "2026-06-18 12:00:00"},
      {"appliance_name": "Fridge", "current": 1.15, "power": 264.5, "voltage": 230.0, "timestamp": "2026-06-18 12:15:00"}
    ],
    "dht_records": [
      {"temperature": 26.4, "humidity": 60.5, "timestamp": "2026-06-18 12:00:00"},
      {"temperature": 26.8, "humidity": 58.2, "timestamp": "2026-06-18 12:15:00"}
    ],
    "log_records": [
      {"level": "INFO", "message": "Simulated boot log", "timestamp": "2026-06-18 12:00:00"},
      {"level": "WARNING", "message": "Simulated sensor anomaly", "timestamp": "2026-06-18 12:10:00"}
    ]
  }
  ```
- **Verification:**
  - Verify that the server returns HTTP 200 with:
    `{"status":"success","device_id":"test-nano-001122aabbcc","records_synced":{"sensors":2,"dht":2,"logs":2}}`
  - Query the database to verify the device `test-nano-001122aabbcc` was dynamically registered and all telemetry records were successfully inserted.

### 3. Launch Global Dashboard
Start the Streamlit dashboard on a different port (e.g. 8501) to verify visual representation:
```bash
streamlit run cloud_dashboard.py --server.port 8501
```
- Open `http://localhost:8501` in your browser.
- In the dropdown selector, select your simulated gateway: `Auto-Registered Edge (test-na)`.
- **Verification:**
  - Check that the KPI cards load the average load, peak load, and climate indicators correctly.
  - Verify that the Plotly line graphs display the power curves and temperature/humidity timeline trends.
  - Verify that the Remote System Log Feed displays your simulated log entries.
