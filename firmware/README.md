# 🔌 SmartElectric Firmware - Solo Testing Guide

This folder contains the ESP32 firmware code. Follow this guide to test the firmware in isolation on your development machine, without needing the Jetson Nano Edge Gateway or the Cloud infrastructure.

---

## 🛠️ Development Setup

1. **Install Arduino IDE** or **VS Code with PlatformIO**.
2. **Install Required Libraries** (Sketch -> Include Library -> Manage Libraries):
   - **PubSubClient** (by Nick O'Leary) - MQTT client messaging.
   - **ArduinoJson** (by Benoit Blanchon) - Parsing control commands and formatting telemetry JSON.
   - **DHT sensor library** (by Adafruit) - Temperature/Humidity sensing driver.
   - **Adafruit Unified Sensor** (by Adafruit) - Prerequisite for DHT library.

3. **Configure Wi-Fi & Broker Settings:**
   - Open [secrets.h](file:///d:/Smart%20Build/firmware/secrets.h) and set your local home Wi-Fi SSID and Password.
   - For **solo testing**, you can set `MQTT_SERVER_IP` to the local IP of your development laptop.

---

## 🧪 Isolated Testing Procedure

To test your code before final integration with the gateway:

### 1. Run a Local MQTT Broker
To simulate the Jetson Nano's broker, you can run a broker on your laptop:
- **Windows/Mac:** Download and run [Mosquitto Broker](https://mosquitto.org/download/) or use [MQTTX Desktop Client](https://mqttx.app/) which has built-in broker-testing capabilities.
- Alternatively, for rapid sandbox testing, you can change `MQTT_SERVER_IP` in `secrets.h` to a public test broker like `"broker.emqx.io"` or `"test.mosquitto.org"`.

### 2. Connect an MQTT Client Tool
Download **MQTTX** (or any MQTT desktop client) on your PC:
- Connect it to the same MQTT broker as your ESP32.
- **Subscribe** to these topics to monitor the ESP32's telemetry:
  - `smartelectric/sensors/current`
  - `smartelectric/sensors/dht`
  - `smartelectric/logs`

### 3. Verify Telemetry Publishing
- Flash the code onto the ESP32.
- Open the **Serial Monitor** at `115200` baud.
- You should see the boot logs, Wi-Fi connection progress, and MQTT connection confirmation.
- Every 5 seconds, the ESP32 will log telemetry to the serial port and publish JSON packages to the broker. Verify that your MQTTX client receives payloads like:
  ```json
  {
    "Light": 0.0,
    "TV": 0.0,
    "Fridge": 0.95,
    "Fan": 0.23,
    "voltage": 230.0
  }
  ```

### 4. Test Relay Actuation Control (Incoming commands)
From your MQTTX client, publish a test JSON command payload to the control topic:
- **Topic:** `smartelectric/control/relay`
- **Payload:**
  ```json
  {
    "appliance": "Light",
    "state": 1
  }
  ```
- **Verification:**
  - Verify that the physical relay on pin 18 switches ON (or that pin 18 reads 3.3V / HIGH on a multimeter).
  - Verify that the ESP32 publishes an acknowledgement log to `smartelectric/logs`:
    `{"level":"INFO","message":"Successfully set relay for Light to ON"}`
  - Publish the same payload with `"state": 0` and verify the relay switches OFF.

### 5. Test the Anti-Chattering Safety Lockout
- Publish `{"appliance": "TV", "state": 1}`.
- Immediately (within 1–2 seconds) publish `{"appliance": "TV", "state": 0}`.
- **Verification:**
  - The second command must be **ignored** by the ESP32.
  - The ESP32 should publish a warning message to the `smartelectric/logs` topic:
    `{"level":"WARNING","message":"Rejected relay command for TV (lockout active or invalid name)"}`
  - Verify that the Serial Monitor outputs: `Rejected command: cooldown still active`.
