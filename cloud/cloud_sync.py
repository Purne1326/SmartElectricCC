import os
import sys
import sqlite3
import requests
import json
import uuid
from datetime import datetime

# Dynamically add the edge/backend directory to sys.path to import edge_db
current_dir = os.path.dirname(os.path.abspath(__file__))
edge_backend_dir = os.path.join(current_dir, "..", "edge", "backend")
sys.path.append(edge_backend_dir)
# Also add absolute path standard location
sys.path.append("/home/jetson/smartelectric/edge/backend")

try:
    from edge_db import get_db_connection, DB_PATH
except ImportError:
    # Manual fallback if path mapping fails during isolated execution
    print("Warning: Could not import edge_db from standard paths. Implementing inline fallback database connection.")
    DB_PATH = "/home/jetson/smartelectric/edge/backend/edge_iot.db"
    if not os.path.exists(os.path.dirname(DB_PATH)):
        DB_PATH = os.path.join(current_dir, "..", "edge", "backend", "edge_iot.db")
    def get_db_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

# Configurations
CLOUD_API_URL = os.getenv("CLOUD_API_URL", "http://localhost:8002") # Replace with your public Cloud URL
SYNC_BATCH_LIMIT = 200
CHECKPOINT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_checkpoint.json")

def get_device_id():
    """Generates a stable, unique identifier for the edge gateway using hardware MAC address."""
    mac = uuid.getnode()
    return f"jetson-{mac:012x}"

def load_checkpoint():
    """Loads the last successfully synced log ID to prevent log duplication."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_log_id": 0}

def save_checkpoint(state):
    """Saves the last successfully synced log ID state."""
    try:
        with open(CHECKPOINT_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving sync checkpoint file: {e}")

def run_sync():
    device_id = get_device_id()
    print(f"[{datetime.now()}] Starting Cloud synchronization for device: {device_id}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"Error connecting to local SQLite DB: {e}")
        return

    # 1. Fetch unsynced sensor telemetry records
    cursor.execute("""
        SELECT id, appliance_name, current, power, voltage, timestamp 
        FROM sensor_data 
        WHERE synced = 0 
        ORDER BY timestamp ASC LIMIT ?
    """, (SYNC_BATCH_LIMIT,))
    sensor_rows = cursor.fetchall()

    # 2. Fetch unsynced DHT climate records
    cursor.execute("""
        SELECT id, temperature, humidity, timestamp 
        FROM dht_data 
        WHERE synced = 0 
        ORDER BY timestamp ASC LIMIT ?
    """, (SYNC_BATCH_LIMIT,))
    dht_rows = cursor.fetchall()

    # 3. Fetch unsynced logs based on checkpoint ID
    checkpoint = load_checkpoint()
    last_log_id = checkpoint.get("last_log_id", 0)
    
    cursor.execute("""
        SELECT id, level, message, timestamp 
        FROM system_logs 
        WHERE id > ? 
        ORDER BY id ASC LIMIT ?
    """, (last_log_id, SYNC_BATCH_LIMIT))
    log_rows = cursor.fetchall()

    # If no data to sync, exit early
    if not sensor_rows and not dht_rows and not log_rows:
        print("Everything is up to date. No new records to sync.")
        conn.close()
        return

    # Structure payload
    payload = {
        "device_id": device_id,
        "sensor_records": [
            {
                "appliance_name": row["appliance_name"],
                "current": row["current"],
                "power": row["power"],
                "voltage": row["voltage"],
                "timestamp": row["timestamp"]
            } for row in sensor_rows
        ],
        "dht_records": [
            {
                "temperature": row["temperature"],
                "humidity": row["humidity"],
                "timestamp": row["timestamp"]
            } for row in dht_rows
        ],
        "log_records": [
            {
                "level": row["level"],
                "message": row["message"],
                "timestamp": row["timestamp"]
            } for row in log_rows
        ]
    }

    # Transmit payload to Cloud API
    sync_url = f"{CLOUD_API_URL}/api/cloud/sync"
    try:
        # First register device if not done already (or let sync endpoint handle auto-registration)
        response = requests.post(sync_url, json=payload, timeout=10.0)
        
        if response.status_code == 200:
            res_json = response.json()
            print(f"Synchronization successful! Response: {res_json}")

            # Update SQLite records to mark them as synced
            sensor_ids = [row["id"] for row in sensor_rows]
            dht_ids = [row["id"] for row in dht_rows]
            
            if sensor_ids:
                cursor.execute(
                    f"UPDATE sensor_data SET synced = 1 WHERE id IN ({','.join(['?']*len(sensor_ids))})",
                    sensor_ids
                )
            
            if dht_ids:
                cursor.execute(
                    f"UPDATE dht_data SET synced = 1 WHERE id IN ({','.join(['?']*len(dht_ids))})",
                    dht_ids
                )

            # Save log checkpoint index
            if log_rows:
                max_log_id = max(row["id"] for row in log_rows)
                checkpoint["last_log_id"] = max_log_id
                save_checkpoint(checkpoint)

            conn.commit()
            print(f"Locally marked {len(sensor_ids)} sensor and {len(dht_ids)} DHT rows as synced.")
        else:
            print(f"Cloud server returned error code {response.status_code}: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Network error during cloud sync: {e}. Is Cloud API running at {CLOUD_API_URL}?")
    
    conn.close()

if __name__ == "__main__":
    run_sync()
