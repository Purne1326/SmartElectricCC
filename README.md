# ⚡ SmartElectric: Comprehensive Setup & Hardware Connection Guide

Welcome to the **SmartElectric** project repository! This guide provides complete, step-by-step instructions for your team to wire the hardware, compile the firmware, set up local databases, run edge gateway services, launch the cloud platform, and configure the mobile app.

---

## 🔌 Part 1: Hardware Wiring & Connection Guide

### 1. ESP32 Pin Mapping (Active Code Mapped)
Connect your hardware components to the ESP32 DevKit according to the active pins configured in [config.h](file:///d:/Smart%20Build/firmware/config.h):

| Component Name | ESP32 GPIO Pin | Connection Details / Direction | Description |
| :--- | :---: | :--- | :--- |
| **DHT22 Climate Sensor** | **GPIO 4** | Data line (Input) | Reads ambient temperature and humidity. |
| **Relay Channel 1 (Light)** | **GPIO 18** | Control line (Output) | Toggles the Light bulb circuit. |
| **Relay Channel 2 (TV)** | **GPIO 19** | Control line (Output) | Toggles the TV power line. |
| **Relay Channel 3 (Fridge)** | **GPIO 21** | Control line (Output) | Toggles the Fridge compressor line. |
| **Relay Channel 4 (Fan)** | **GPIO 22** | Control line (Output) | Toggles the Fan motor circuit. |
| **SCT-013 Sensor #1 (Light)** | **GPIO 32** | Analog Input (ADC1_CH4) | Monitors current draw from the Light circuit. |
| **SCT-013 Sensor #2 (TV)** | **GPIO 33** | Analog Input (ADC1_CH5) | Monitors current draw from the TV circuit. |
| **SCT-013 Sensor #3 (Fridge)** | **GPIO 34** | Analog Input (ADC1_CH6) | Monitors current draw from the Fridge circuit. |
| **SCT-013 Sensor #4 (Fan)** | **GPIO 35** | Analog Input (ADC1_CH7) | Monitors current draw from the Fan circuit. |

---

### 2. SCT-013 Sensor Signal Conditioning Circuit
The ESP32 Analog-to-Digital Converter (ADC) reads voltages only from **0V to 3.3V**. Since the SCT-013 current sensor outputs an alternating current (AC) signal that swings positive and negative, **you must apply a 1.65V DC Bias Offset** to center the AC wave.

Wire each SCT-013 input channel on a breadboard/PCB as follows:

```
                      +3.3V (ESP32 Pin)
                        │
                      [10kΩ] Resistor R1
                        │
  SCT-013 Output        ├───→ To ESP32 Analog GPIO Pin (32, 33, 34, or 35)
  (3.5mm Tip Wire) ───[10kΩ] (Burden Resistor - *Only required for current output type)*
                        │
                      [10kΩ] Resistor R2
                        │
                        ├────[10µF Capacitor (+)]
                        │
                       GND (Capacitor Ground (-) and 3.5mm Jack Sleeve)
```

> [!NOTE]
> **Important Note on Burden Resistors:**
> * If you are using **SCT-013-000 (Current Output)**, you MUST install a burden resistor (typically 20Ω - 33Ω) across the sensor outputs to generate a readable voltage signal.
> * If you are using **SCT-013-030 (Voltage Output, 30A/1V)**, the burden resistor is already built-in, so do **not** add an external burden resistor. Connect the tip wire directly to the voltage divider offset node.

---

### 3. Relay Module Connections
Ensure the 4-Channel Relay board switches the AC mains phase line safely:
*   **VCC:** Connect to ESP32 **VIN** (5V).
*   **GND:** Connect to ESP32 **GND**.
*   **IN1 / IN2 / IN3 / IN4:** Connect to GPIOs **18, 19, 21, and 22** respectively.

---

## 🛠️ Part 2: ESP32 Firmware Installation

### 1. IDE Setup
1. Download and open **Arduino IDE** (or VS Code with PlatformIO).
2. Go to **File -> Preferences**.
3. In **Additional Board Manager URLs**, add:  
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
4. Install the **ESP32** board platform via the Board Manager (**Tools -> Board -> Boards Manager**).

### 2. Install Required Libraries
Open the Library Manager (**Sketch -> Include Library -> Manage Libraries**) and install:
*   **PubSubClient** (by Nick O'Leary) - MQTT client messaging.
*   **ArduinoJson** (by Benoit Blanchon) - Parsing control and compiling telemetry JSONs.
*   **DHT sensor library** (by Adafruit) & **Adafruit Unified Sensor** - Environmental metrics.

### 3. Compile and Flash
1. Open [secrets.h](file:///d:/Smart%20Build/firmware/secrets.h) and set your local network credentials:
   ```cpp
   #define WIFI_SSID "Your_WiFi_SSID"
   #define WIFI_PASSWORD "Your_WiFi_Password"
   #define MQTT_SERVER_IP "192.168.1.XX" // Local IP of your Edge Gateway machine
   ```
2. Connect the ESP32 to your computer via USB.
3. Select **Tools -> Board -> ESP32 Arduino -> ESP32 Dev Module**.
4. Select the correct serial COM port under **Tools -> Port**.
5. Set the upload speed to **115200** or **921600** and click **Upload**.
6. Press the ESP32's **EN/RST** button and check the Serial Monitor at **115200** baud to confirm connection.

---

## 📟 Part 3: Local Edge Gateway Setup (Jetson Nano / Local PC)

The Local Gateway acts as the central hub: it hosts the MQTT broker, stores telemetry records in SQLite, runs FastAPI services, and serves the Streamlit dashboard.

### 1. Prerequisites (MQTT Broker)
Ensure you have a local **Mosquitto** MQTT broker installed and running on port `1883`:
*   **Windows:** Download and run the installer from [mosquitto.org](https://mosquitto.org/download/). Ensure the "Mosquitto Broker" service is running in Windows Services Manager.
*   **Linux / Jetson Nano:** 
    ```bash
    sudo apt update
    sudo apt install mosquitto mosquitto-clients -y
    sudo systemctl enable mosquitto
    sudo systemctl start mosquitto
    ```

---

### 2. Environment & Python Setup
To avoid system conflicts, it is recommended to set up a Python virtual environment:

#### A. Set Up Virtual Environment:
*   **Windows (PowerShell):**
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
*   **Linux / macOS (Bash):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

#### B. Install Python Dependencies:
```bash
pip install --upgrade pip
pip install fastapi uvicorn pydantic paho-mqtt streamlit pandas plotly requests sqlalchemy
```

---

### 3. Detailed Step-by-Step Running Guide

To launch the Local Gateway, execute the following commands in separate terminal sessions. **You must run them in the order listed below.**

#### Step A: Initialize the SQLite Database
This creates the SQLite database structure and inserts initial status data.
*   **Path:** `edge/backend`
*   **Command:**
    ```bash
    cd d:/Smart\ Build/edge/backend
    python edge_db.py
    ```
*   **What it does:** It creates the file `D:\home\jetson\smartelectric\edge\backend\edge_iot.db` (or a local fallback if directories aren't writable) with 4 tables: `appliances`, `sensor_data`, `dht_data`, and `system_logs`. It seeds the `appliances` table with default values: Light, TV, Fridge, and Fan.
*   **Expected Output:**
    ```text
    Initializing database at: /home/jetson/smartelectric/edge/backend/edge_iot.db
    Database initialization completed successfully.
    ```

#### Step B: Start the MQTT Background Worker
This service listens to the MQTT broker for telemetry published by the ESP32 and commits it to the database.
*   **Path:** `edge/backend`
*   **Command:**
    ```bash
    python mqtt_worker.py
    ```
*   **What it does:** Subscribes to `smartelectric/sensors/current`, `smartelectric/sensors/dht`, and `smartelectric/logs`. When a packet arrives, it converts the raw payload to database rows.
*   **Expected Output:**
    ```text
    Starting SmartElectric MQTT Background Worker...
    Connected to MQTT broker at localhost:1883 successfully.
    Subscribed to topics:
     - smartelectric/sensors/current
     - smartelectric/sensors/dht
     - smartelectric/logs
    ```

#### Step C: Start the FastAPI Backend Server
This runs the HTTP server that exposes endpoints for the frontend, mobile app, and machine learning models.
*   **Path:** `edge/backend`
*   **Command:**
    ```bash
    python -m uvicorn main:app --host 0.0.0.0 --port 8000
    ```
*   **What it does:** Spins up a server on port `8000`. Exposes `/api/status`, `/api/metrics`, `/api/control`, `/api/v1/predict/load`, and `/api/v1/predict/decision`.
*   **Expected Output:**
    ```text
    INFO:     Started server process [8980]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
    ```

#### Step D: Run the Real-Time Database Simulator (*Optional - For Offline Testing*)
If you do not have physical ESP32 hardware connected, run this script to simulate live telemetry data.
*   **Path:** `edge/backend`
*   **Command:**
    ```bash
    python simulate_realtime.py
    ```
*   **What it does:** Cycles every 5 seconds, reads the active relay states from `edge_iot.db` (so it reacts to your frontend clicks!), generates realistic power readings (e.g. ~110W for TV, ~230W for Fridge, ~0W if OFF), and inserts them directly into the DB.
*   **Expected Output:**
    ```text
    Starting SmartElectric Real-time Simulator...
    Targeting database: D:\home\jetson\smartelectric\edge\backend\edge_iot.db
    [2026-06-28 20:10:00] Inserted real-time telemetry (Temp: 26.3°C, Hum: 61.2%)
    [2026-06-28 20:10:05] Inserted real-time telemetry (Temp: 25.8°C, Hum: 63.1%)
    ```

#### Step E: Launch the Local Gateway Dashboard
*   **Path:** `edge/frontend`
*   **Command:**
    ```bash
    cd ../frontend
    streamlit run app.py --server.port 8501
    ```
*   **What it does:** Opens the local Streamlit panel on `http://localhost:8501`. It features real-time power consumption bar charts, climate dials, appliance toggles (which send relay HTTP POST requests to the FastAPI backend), and an AI forecasting page.
*   **Expected Output:**
    ```text
      You can now view your Streamlit app in your browser.
      Local URL: http://localhost:8501
    ```

---

## ☁️ Part 4: Centralized Cloud Platform Setup

The Cloud Platform aggregates data from multiple gateways, allowing global administrators to monitor energy consumption.

### 1. Database Setup
By default, the cloud database will attempt to connect to **PostgreSQL** on port `5432`. If no PostgreSQL is active, **it automatically falls back to a local SQLite file** (`smartelectric_cloud.db`).

---

### 2. Detailed Step-by-Step Running Guide

Run these commands from the `cloud/` folder in separate terminals:

#### Step A: Initialize the Cloud Database Schema
*   **Path:** `cloud/`
*   **Command:**
    *   **Windows (PowerShell):**
        ```powershell
        $env:DATABASE_URL="sqlite:///smartelectric_cloud.db"
        python cloud_db.py
        ```
    *   **Linux / macOS (Bash):**
        ```bash
        export DATABASE_URL="sqlite:///smartelectric_cloud.db"
        python3 cloud_db.py
        ```
*   **Expected Output:**
    ```text
    Initializing Cloud Database at: sqlite:///smartelectric_cloud.db
    Cloud Database tables initialized successfully.
    ```

#### Step B: Launch the Cloud Receiver API Server
This server receives synced batches of data uploaded by individual edge gateways.
*   **Path:** `cloud/`
*   **Command:**
    *   **Windows (PowerShell):**
        ```powershell
        $env:DATABASE_URL="sqlite:///smartelectric_cloud.db"
        python -m uvicorn cloud_main:app --host 0.0.0.0 --port 8002
        ```
    *   **Linux / macOS (Bash):**
        ```bash
        export DATABASE_URL="sqlite:///smartelectric_cloud.db"
        python3 -m uvicorn cloud_main:app --host 0.0.0.0 --port 8002
        ```
*   **Expected Output:**
    ```text
    INFO:     Started server process [18480]
    INFO:     Waiting for application startup.
    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://0.0.0.0:8002 (Press CTRL+C to quit)
    ```

#### Step C: Start the Global Cloud Dashboard
*   **Path:** `cloud/`
*   **Command:**
    ```bash
    streamlit run cloud_dashboard.py --server.port 8502
    ```
*   **What it does:** Starts the admin console on `http://localhost:8502`. In the sidebar, the user can select their gateway device and view aggregate metrics and timelines.

#### Step D: Run the Edge-to-Cloud Sync Client
This script must run on your gateway (or on your PC simulating the gateway) to continuously sync local SQLite data with the cloud server.
*   **Path:** `cloud/`
*   **Command:**
    *   **Windows (PowerShell):**
        ```powershell
        while ($true) { python cloud_sync.py; Start-Sleep -Seconds 10 }
        ```
    *   **Linux / macOS (Bash):**
        ```bash
        while true; do python3 cloud_sync.py; sleep 10; done
        ```
*   **Expected Output (every 10 seconds):**
    ```text
    [2026-06-28 20:15:00] Starting Cloud synchronization for device: jetson-70a8d3196689
    Synchronization successful! Response: {'status': 'success', 'device_id': 'jetson-70a8d3196689', 'records_synced': {'sensors': 24, 'dht': 6, 'logs': 10}}
    Locally marked 24 sensor and 6 DHT rows as synced.
    ```

---

## 📱 Part 5: Android Mobile Application Setup

1.  Open **Android Studio**.
2.  Click **File -> Open** and select the [mobile/](file:///d:/Smart%20Build/mobile/) directory.
3.  Allow Gradle to sync and download compiler dependencies.
4.  Launch an Android Virtual Device (Emulator) or connect a physical Android phone with USB Debugging enabled.
5.  Click the **Run** button to compile and install the application.
6.  **Connecting the App to the API:**
    *   In the app, navigate to the **Settings** tab.
    *   Input your Gateway's local IP address (e.g. `192.168.1.XX`, or `10.0.2.2` if running the standard Android emulator pointing to the host's localhost) and specify port `8000`.
    *   Click **Save Configuration**.
    *   Navigate back to the **Dashboard** or **Control** tab to interact with the simulated or physical appliances in real-time!
