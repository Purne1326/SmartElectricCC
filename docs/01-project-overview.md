# 01. SmartElectric Project Overview

SmartElectric is an advanced **Hybrid Edge-Cloud Home Energy Management System (HEMS)** designed to monitor, analyze, and control domestic electrical appliances. The platform uses local edge computing to maintain fast, private control operations while syncing metrics to the cloud for global dashboards and fleet administration.

---

## ⚡ Core Features

- **Granular Appliance Monitoring:** Calculates true Root-Mean-Square (RMS) current, power factor, active power, and voltage across 4 distinct appliance sub-circuits (Light, TV, Fridge, Fan).
- **Physical Relay Control:** Safe physical toggle switches with built-in anti-chattering lockout algorithms (minimum 3-second delay).
- **Environmental Tracking:** Monitors temperature, humidity, and indoor motion.
- **Offline-First Operation:** Local data persistence (SQLite) ensures dashboards, scheduling, and automation rules run even when the internet is offline.
- **Indian Slab Cost Estimator:** Real-time cost computation comparing flat-rate and tiered electricity slabs (e.g., First 100 kWh @ ₹4.50, next 200 kWh @ ₹6.50, and >300 kWh @ ₹8.00).
- **Multi-Client Visualizer:** Accessible via high-performance web interfaces (Streamlit, local static HTML5/JS dashboard) and a Native Android Mobile Application.
- **AI Forecasting & Analytics:** Predicts next-hour aggregate electrical load utilizing machine learning (GRU time-series forecasting).

---

## 🎯 Target Specifications

| Parameter | Specification |
|-----------|---------------|
| **Voltage Range** | 220V - 240V AC (50Hz nominal) |
| **Appliance Channels** | 4 (Light, TV, Fridge, Fan) |
| **Max Current (per Channel)** | 30 Amps (SCT-013 rating) |
| **Local Logging Frequency** | 5 seconds (Telemetry packet upload) |
| **Local Sync Frequency** | 1 minute (Historical batch upload to cloud) |
| **MQTT Broker Port** | 1883 |
| **REST API Server Port** | 8000 |
| **Local Dashboard UI Port** | 8501 (Streamlit) / 8000 (Static HTML) |
| **Cloud Sync API Port** | 8000 |
| **Safety Cooldown** | 3000ms minimum relay toggle lockout |
