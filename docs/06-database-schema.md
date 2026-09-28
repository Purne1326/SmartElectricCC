# 06. Database Schema Design

The SmartElectric platform leverages **SQLite** on the local Edge Gateway for high-speed offline operations and **PostgreSQL** in the cloud for centralized storage and reporting.

---

## 💾 Local Edge Database (SQLite)

Database File: `edge_iot.db`

### 1. Table: `sensor_data`
Tracks real-time aggregate voltage, current, and temperature metrics.

```sql
CREATE TABLE sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    voltage REAL DEFAULT 230.0,
    total_current REAL DEFAULT 0.0,
    total_power REAL DEFAULT 0.0,
    temperature REAL DEFAULT 0.0,
    humidity REAL DEFAULT 0.0,
    motion_detected INTEGER DEFAULT 0,
    synced INTEGER DEFAULT 0 -- 0 = Not Synced, 1 = Synced to Cloud
);
```

### 2. Table: `appliances`
Stores the metadata catalog and active relay states.

```sql
CREATE TABLE appliances (
    name TEXT PRIMARY KEY, -- 'Light', 'TV', 'Fridge', 'Fan'
    gpio_pin INTEGER NOT NULL,
    status INTEGER DEFAULT 0, -- 0 = OFF, 1 = ON
    last_changed DATETIME
);
```

### 3. Table: `system_logs`
Saves diagnostic messages and safety alerts.

```sql
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL, -- 'INFO', 'WARNING', 'ERROR'
    message TEXT NOT NULL
);
```

---

## ☁️ Central Cloud Database (PostgreSQL)

### 1. Table: `edge_devices`
Registers physical gateways uploading synchronizations.

```sql
CREATE TABLE edge_devices (
    device_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(100) DEFAULT 'Home',
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Table: `cloud_sensor_data`
Aggregates sensor history from all edge devices.

```sql
CREATE TABLE cloud_sensor_data (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) REFERENCES edge_devices(device_id) ON DELETE CASCADE,
    appliance_name VARCHAR(50) NOT NULL,
    current DOUBLE PRECISION NOT NULL,
    power DOUBLE PRECISION NOT NULL,
    voltage DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMP NOT NULL
);
CREATE INDEX idx_cloud_sensor_time ON cloud_sensor_data (timestamp DESC, device_id);
```
