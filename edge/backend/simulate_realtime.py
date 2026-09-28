import os
import sys
import sqlite3
import random
import time
from datetime import datetime, timedelta

# Dynamically resolve DB path using the same logic as edge_db.py
DB_PATH = "/home/jetson/smartelectric/edge/backend/edge_iot.db"
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    # relative path on Windows fallback
    DB_PATH = "D:\\home\\jetson\\smartelectric\\edge\\backend\\edge_iot.db"
    if not os.path.exists(DB_PATH):
        DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edge_iot.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def main():
    print(f"Starting SmartElectric Real-time Simulator...")
    print(f"Targeting database: {DB_PATH}")
    
    voltage = 230.0
    appliances = ["Light", "TV", "Fridge", "Fan"]
    current_source = "Grid"
    cycle_count = 0

    while True:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cycle_count += 1

            # Get current states of appliances from the database (so we respect user toggles!)
            cursor.execute("SELECT name, status FROM appliances")
            states = {row["name"]: row["status"] for row in cursor.fetchall()}

            current_time = datetime.now()
            timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S')

            # 1. Generate and insert DHT sensor reading (including PIR and LDR)
            temp = 26.0 + random.uniform(-1.0, 1.0)
            hum = 62.0 + random.uniform(-4.0, 4.0)
            
            # Generate LDR based on current hour
            hour = current_time.hour
            if 7 <= hour <= 17:
                ldr = 80.0 + random.uniform(-5.0, 5.0)
            elif hour == 6 or hour == 18:
                ldr = 40.0 + random.uniform(-5.0, 5.0)
            else:
                ldr = 2.0 + random.uniform(-1.0, 1.0)
                
            # Model room occupancy (30 minute cycles: 10 minutes occupied, 20 minutes empty)
            # 10 minutes = 120 cycles; 20 minutes = 240 cycles
            cycle_phase = cycle_count % 360
            if cycle_phase < 120:
                # Occupied: motion is detected occasionally (40% chance)
                pir = 1 if random.random() < 0.4 else 0
            else:
                # Empty: strictly 0 motion
                pir = 0

            cursor.execute("""
                INSERT INTO dht_data (temperature, humidity, pir, ldr, timestamp, synced)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (temp, hum, pir, ldr, timestamp_str))

            # 2. Generate and insert sensor data for each appliance
            total_simulated_power = 0.0
            anomaly_app = None
            # Inject an anomaly cycle once every 12 iterations (1 minute)
            if cycle_count % 12 == 0:
                active_apps = [a for a in appliances if states.get(a, 0) == 1]
                if active_apps:
                    anomaly_app = random.choice(active_apps)
                    print(f"[{timestamp_str}] [SIMULATOR] Injecting anomaly into active {anomaly_app}...")

            # Determine Fridge compressor cycle status (ON for minutes 0-19 and 30-49, OFF otherwise)
            minute_of_hour = datetime.now().minute
            fridge_compressor_on = (minute_of_hour < 20) or (30 <= minute_of_hour < 50)

            for app in appliances:
                if app == anomaly_app:
                    # High current draw anomaly (realistic fault limits)
                    if app == "Fridge":
                        current = 1.95 + random.uniform(-0.01, 0.01)
                    elif app == "TV":
                        current = 0.95 + random.uniform(-0.01, 0.01)
                    elif app == "Light":
                        current = 0.45 + random.uniform(-0.005, 0.005)
                    else: # Fan
                        current = 0.65 + random.uniform(-0.005, 0.005)
                else:
                    status = states.get(app, 0)
                    if status == 1:
                        # Generate steady, realistic active loads with minor line/sensor noise
                        if app == "Light":
                            # Steady LED bulb/tube load around 32 Watts
                            current = 0.14 + random.uniform(-0.002, 0.002)
                        elif app == "TV":
                            # Steady LED TV load around 90 Watts
                            current = 0.39 + random.uniform(-0.008, 0.008)
                        elif app == "Fridge":
                            # Compressor duty cycle modeling (spikes to 180W, cycles to 4.5W)
                            if fridge_compressor_on:
                                current = 0.78 + random.uniform(-0.01, 0.01)
                            else:
                                current = 0.02 + random.uniform(-0.001, 0.001)
                        elif app == "Fan":
                            # Steady ceiling fan load around 60 Watts
                            current = 0.26 + random.uniform(-0.003, 0.003)
                    else:
                        # Zero load when OFF
                        current = 0.0

                power = current * voltage
                total_simulated_power += power
                cursor.execute("""
                    INSERT INTO sensor_data (appliance_name, current, power, voltage, timestamp, synced)
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (app, current, power, voltage, timestamp_str))

            # Auto-switching simulation logic based on 400W threshold
            if total_simulated_power > 400.0 and current_source == "Grid":
                current_source = "Solar"
                log_msg = f"System automatically switched to Solar power (Total load: {total_simulated_power:.2f} W exceeds 400W threshold)"
                cursor.execute("""
                    INSERT INTO system_logs (level, message, timestamp)
                    VALUES (?, ?, ?)
                """, ("INFO", log_msg, timestamp_str))
                print(f"[{timestamp_str}] [POWER SOURCE SWITCH] -> SOLAR ({total_simulated_power:.2f} W)")

            elif total_simulated_power <= 400.0 and current_source == "Solar":
                current_source = "Grid"
                log_msg = f"System switched back to Main Grid power (Total load: {total_simulated_power:.2f} W <= 400W)"
                cursor.execute("""
                    INSERT INTO system_logs (level, message, timestamp)
                    VALUES (?, ?, ?)
                """, ("INFO", log_msg, timestamp_str))
                print(f"[{timestamp_str}] [POWER SOURCE SWITCH] -> GRID ({total_simulated_power:.2f} W)")

            # 3. Keep database lightweight by removing logs/readings older than 24 hours
            cutoff_time = (current_time - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("DELETE FROM sensor_data WHERE timestamp < ?", (cutoff_time,))
            cursor.execute("DELETE FROM dht_data WHERE timestamp < ?", (cutoff_time,))

            conn.commit()
            conn.close()

            print(f"[{timestamp_str}] Inserted real-time telemetry (Temp: {temp:.1f}°C, Hum: {hum:.1f}%, PIR: {pir}, LDR: {ldr:.1f}%)")

        except Exception as e:
            print(f"Error in simulator: {e}", file=sys.stderr)

        # Sleep for 5 seconds before next update
        time.sleep(5)

if __name__ == "__main__":
    main()
