# 10. System Troubleshooting Guide

This document lists common system failure scenarios and provides step-by-step procedures to resolve them.

---

## 🔍 Common Scenarios & Solutions

### 1. Dashboard UI Displays "Gateway Offline"
* **Symptoms:** The HTML5 or Streamlit dashboard loads, but reads "Offline" or shows empty telemetry grids.
* **Causes:**
  1. The background MQTT Worker process has crashed or stopped.
  2. The SQLite database file has not been initialized.
* **Resolution Steps:**
  1. SSH into the Jetson Nano.
  2. Check if the database file exists:
     ```bash
     ls -l edge/backend/edge_iot.db
     ```
     If missing, run: `python edge/backend/edge_db.py` to create and seed it.
  3. Check the status of the MQTT background worker:
     ```bash
     ./edge/scripts/6-check-status.sh
     ```
  4. If stopped, restart all processes:
     ```bash
     ./edge/scripts/5-start-all.sh
     ```

### 2. ESP32 Cannot Connect to MQTT Broker
* **Symptoms:** The ESP32 Serial Monitor continuously prints: `Attempting MQTT connection... failed, rc=-2`.
* **Causes:**
  1. The target `MQTT_SERVER_IP` in `secrets.h` is incorrect.
  2. The Mosquitto service is not running on the Jetson Nano.
  3. The Jetson's local firewall is blocking port 1883.
* **Resolution Steps:**
  1. Confirm your development laptop/Jetson IP address and check if it matches the value in `secrets.h`.
  2. Verify that Mosquitto is active on the host:
     ```bash
     sudo systemctl status mosquitto
     ```
  3. Verify port 1883 is listening:
     ```bash
     sudo netstat -tlnp | grep 1883
     ```
  4. Open port 1883 in the firewall:
     ```bash
     sudo ufw allow 1883/tcp
     ```

### 3. Database is Locked (`sqlite3.OperationalError: database is locked`)
* **Symptoms:** The FastAPI or MQTT worker exits with a database locked exception.
* **Causes:** Multiple processes are writing to the SQLite file simultaneously, causing write lock collisions.
* **Resolution Steps:**
  1. Stop all active Python processes accessing the database:
     ```bash
     sudo systemctl stop smartelectric-api smartelectric-worker
     ```
  2. Find any orphan python processes and terminate them:
     ```bash
     killall python3
     ```
  3. Restart the services using systemd to ensure safe access scheduling:
     ```bash
     ./edge/scripts/5-start-all.sh
     ```
