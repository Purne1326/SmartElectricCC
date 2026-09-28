# 08. ESP32 Firmware Deployment Guide

This document describes how to compile, configure, and flash the ESP32 sensing node using the Arduino IDE.

---

## 💻 Arduino IDE Setup

### 1. Board Manager Configuration
1. Open **Arduino IDE**.
2. Go to **File -> Preferences**.
3. In the **Additional Board Manager URLs**, insert:
   `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
4. Go to **Tools -> Board -> Boards Manager**, search for `esp32` (by Espressif Systems), and install version `2.0.x` or later.

### 2. Dependency Libraries Installation
Go to **Sketch -> Include Library -> Manage Libraries** and install the following:
* **PubSubClient** (by Nick O'Leary) - MQTT messaging client.
* **ArduinoJson** (by Benoit Blanchon) - Payload serialization.
* **DHT sensor library** (by Adafruit) - Temperature & humidity readings.
* **Adafruit Unified Sensor** (by Adafruit) - Base driver dependency.

---

## ⚙️ Configuration & Secrets

Before uploading the code, configure network credentials in [`secrets.h`](file:///d:/Smart%20Build/firmware/secrets.h):

1. **Wi-Fi Settings:** Set your wireless router SSID name and security key:
   ```cpp
   #define WIFI_SSID "Your_WiFi_Name"
   #define WIFI_PASSWORD "Your_WiFi_Password"
   ```
2. **Gateway Location:** Input the target Jetson Nano IP address running the Mosquitto broker:
   ```cpp
   #define MQTT_SERVER_IP "192.168.1.100"
   ```

---

## ⚡ Flashing the Board

1. Connect the ESP32 to your PC using a micro-USB cable.
2. In Arduino IDE, select your board: **Tools -> Board -> ESP32 Arduino -> ESP32 Dev Module**.
3. Select the correct serial COM port: **Tools -> Port**.
4. Set the upload speed to **115200** or **921600** baud.
5. Click **Upload** (right arrow icon).
6. Open the **Serial Monitor** at **115200** baud. Press the EN/RST button on the ESP32 to verify Wi-Fi and MQTT connection logs.
