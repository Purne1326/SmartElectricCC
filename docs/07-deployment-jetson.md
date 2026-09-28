# 07. Jetson Nano Edge Deployment Guide

This document describes how to deploy, configure, and manage the local SmartElectric backend on a NVIDIA Jetson Nano edge gateway.

---

## 🛠️ Step-by-Step Installation

### Step 1: Clone the Codebase
Extract the codebase package on the Jetson Nano. Navigate to the scripts helper directory:
```bash
cd edge/scripts
```

### Step 2: Make Scripts Executable
Ensure all automation shell scripts have executable permissions:
```bash
chmod +x *.sh
```

### Step 3: Install Mosquitto MQTT Broker
Run script `1-install-mosquitto.sh`. This will download, enable, and configure the broker:
```bash
./1-install-mosquitto.sh
```

### Step 4: Configure the Python Environment
Run script `2-setup-venv.sh`. This creates a local Python virtual environment (`.venv`) and installs core libraries along with a CPU version of PyTorch for forecasting:
```bash
./2-setup-venv.sh
```

### Step 5: Initialize Configuration Files
Run script `3-create-env-files.sh` to generate local and cloud environment configuration templates:
```bash
./3-create-env-files.sh
```
*Note:* Open the generated `.env` file under `edge/backend/.env` to customize settings like tariff calculations or IP interfaces.

### Step 6: Register systemd Daemons
Run script `4-setup-systemd.sh`. This registers the background services so they run automatically when the Jetson Nano boots up:
```bash
./4-setup-systemd.sh
```

---

## 🚦 System Service Operations

Use the following scripts to operate and monitor the running services:

### Start / Restart All Services
```bash
./5-start-all.sh
```

### Check Active Daemon Status
```bash
./6-check-status.sh
```
This output is color-coded and prints the active status of the MQTT Worker, REST API server, Streamlit dashboard, and Mosquitto broker along with recent logs.
