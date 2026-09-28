# 02. SmartElectric System Architecture

This document describes the architectural layers and components of the SmartElectric platform.

---

## 🏗️ System Block Diagram

```mermaid
graph TD
    subgraph Layer 1: Hardware
        ESP32[ESP32 Microcontroller] -->|WiFi / MQTT JSON| Mosquitto[Mosquitto Broker]
    end

    subgraph Layer 2: Local Edge Gateway (Jetson Nano)
        Mosquitto -->|Sub: smartelectric/sensors/#| Worker[mqtt_worker.py]
        Worker -->|Write SQLite| DB[(edge_iot.db)]
        API[FastAPI Backend - main.py] -->|Read / Write| DB
        API -.->|Publish Toggle Command| Mosquitto
        
        subgraph User Access UIs
            Streamlit[Streamlit Dashboard - app.py] -->|REST HTTP| API
            StaticHTML[Static HTML5 Dashboard] -->|REST HTTP| API
        end
    end

    subgraph Layer 3: Mobile Access
        AndroidApp[Android Mobile App] -->|REST HTTP| API
    end

    subgraph Layer 4: Cloud synchronization
        DB -->|Query Unsynced| Sync[cloud_sync.py]
        Sync -->|REST POST JSON| CloudAPI[FastAPI Cloud Receiver]
        CloudAPI -->|Write PostgreSQL| CloudDB[(Cloud Database)]
        CloudDB -->|Query| CloudUI[Streamlit Global Panel]
    end
```

---

## 🧱 Component Breakdown

### 1. Hardware Sensing Layer (ESP32)
The physical micro-controller parses analog AC voltage patterns from 4 SCT-013 current transformers, averages environmental data, and publishes formatted JSON data packets onto local MQTT topics every 5 seconds.

### 2. Edge Processing Layer (Jetson Nano)
- **Mosquitto MQTT Broker:** Coordinates messages between physical sensors, background workers, and REST control handlers.
- **SQLite Database (`edge_iot.db`):** Stores real-time datasets including historical current levels, temperature metrics, relay actions, and debug warning logs.
- **MQTT Worker Daemon:** A background Python service executing `paho-mqtt` callbacks. It listens for sensor payloads and writes them cleanly to the DB.
- **FastAPI API Server:** Computes cost slabs, manages database access, publishes outgoing MQTT relay control frames, and serves prediction endpoints.
- **Streamlit & HTML5 UIs:** Local visual charts and relay switches for local network devices.

### 3. Native Android Client
A Kotlin Jetpack Compose application designed for lightweight mobile viewing. It targets the edge gateway API over local WiFi.

### 4. Cloud Synchronizer & Receiver
- **Sync Daemon (`cloud_sync.py`):** Runs on a schedule. It gathers local SQLite records flagged as `synced = 0`, sends them to the Cloud sync endpoint, and marks them as synced locally.
- **FastAPI Cloud Receiver:** Consolidates batch uploads from multiple edge gateways, registering new devices dynamically and storing records in the main database.
- **Streamlit Global Dashboard:** Provides global maps, load comparison curves across multiple gateways, and centralized log audits.
