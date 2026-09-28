# 📟 SmartElectric Local Edge Gateway - Solo Testing Guide

This folder contains the Edge Gateway backend (SQLite, Mosquitto, MQTT Worker, FastAPI) and the local user dashboards. Follow this guide to test the edge gateway services and compile/test the Android Mobile App in isolation without the physical ESP32 hardware.

---

## 🛠️ Gateway Setup & Launch

1. **Install python dependencies:**
   ```bash
   pip install fastapi uvicorn pydantic paho-mqtt streamlit pandas plotly requests sqlalchemy
   ```
2. **Initialize local SQLite database:**
   ```bash
   python backend/edge_db.py
   ```
   *Verify:* This creates the database file `edge_iot.db` preloaded with the default Light, TV, Fridge, and Fan records.

3. **Start local Mosquitto Broker:**
   Ensure your local Mosquitto MQTT broker is running on port 1883.
   
4. **Run Background MQTT Worker:**
   ```bash
   python backend/mqtt_worker.py
   ```
   *Verify:* The terminal logs should print: `Connected to MQTT broker at localhost:1883 successfully.`

5. **Start FastAPI API Server:**
   Run the API server from the `backend/` directory:
   ```bash
   cd backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

---

## 🧪 Isolated Testing (Simulating the Hardware)

To test that data propagates through your backend and UI correctly:

### 1. Inject Mock Telemetry Data
Since the ESP32 is not connected, use a publish tool (like **MQTTX** or a quick Python script) to push simulated sensor payloads to the local broker:

- **Simulate Current Readings:**
  - **Topic:** `smartelectric/sensors/current`
  - **JSON Payload:**
    ```json
    {"Light": 0.15, "TV": 0.40, "Fridge": 1.10, "Fan": 0.0, "voltage": 230.0}
    ```
- **Simulate Climate Readings:**
  - **Topic:** `smartelectric/sensors/dht`
  - **JSON Payload:**
    ```json
    {"temperature": 27.5, "humidity": 65.2}
    ```

### 2. Verify Database Log Insertion
- Inspect the `edge_iot.db` database using an SQLite viewer (like DB Browser for SQLite) or query the tables.
- Verify that `sensor_data` and `dht_data` contain the values you published, with calculated power values (`power = current * voltage`).

### 3. Verify API REST Outputs
Open your web browser and navigate to:
- `http://localhost:8000/api/status` -> Verify it returns a JSON response containing your simulated appliance states, latest currents, and temperature.
- `http://localhost:8000/api/metrics?range_type=today` -> Verify the kWh energy calculations and cost calculations in Indian Rupees (₹) are populated correctly.

---

## 📱 Testing the Android Mobile App (APK)

1. Open **Android Studio**.
2. Click **File -> Open** and select the [mobile/](file:///d:/Smart%20Build/mobile/) folder in this workspace.
3. Allow Gradle to sync and download compile dependencies.
4. Launch an Android Virtual Device (Emulator) or connect a physical Android phone with USB Debugging enabled.
5. Compile and run the app.

### Connecting App to API
- In the mobile app, go to the **Settings** tab.
- Enter your laptop/gateway's IP address (e.g. `192.168.1.5` or `10.0.2.2` if running on the standard Android emulator pointing to host localhost).
- Click **Save Configuration**.
- Go to the **Dashboard** tab -> verify your simulated total load, total current, climate stats, and appliance status cards load immediately.
- Go to the **Control** tab and toggle a switch -> verify the switch updates, the API logs a `POST /api/control` request, and the SQLite `appliances` table status updates.
- Try toggling a switch twice within 3 seconds -> verify a native dialog popup appears: `🔒 Safety Lockout Active... Please wait 3 seconds`.
