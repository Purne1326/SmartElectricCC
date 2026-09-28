import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("EDGE_DB_PATH", os.path.join(BASE_DIR, "edge_iot.db"))

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    global DB_PATH
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            DB_PATH = os.path.join(BASE_DIR, "edge_iot.db")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the database schema and inserts seed data for appliances."""
    print(f"Initializing database at: {DB_PATH}")
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create appliances table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        relay_pin INTEGER UNIQUE NOT NULL,
        status INTEGER NOT NULL CHECK (status IN (0, 1)) DEFAULT 0,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Create sensor telemetry table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appliance_name TEXT NOT NULL,
        current REAL NOT NULL, -- Amps (A)
        power REAL NOT NULL,   -- Watts (W)
        voltage REAL NOT NULL, -- Volts (V)
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        synced INTEGER NOT NULL CHECK (synced IN (0, 1)) DEFAULT 0,
        FOREIGN KEY (appliance_name) REFERENCES appliances(name) ON DELETE CASCADE
    );
    """)

    # Create DHT sensor data table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dht_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        temperature REAL NOT NULL, -- Celsius
        humidity REAL NOT NULL,    -- Percentage (%)
        pir INTEGER DEFAULT 0,     -- Motion PIR state (0=No motion, 1=Motion)
        ldr REAL DEFAULT 0.0,      -- Light level LDR (%)
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        synced INTEGER NOT NULL CHECK (synced IN (0, 1)) DEFAULT 0
    );
    """)

    # Safely migrate existing tables if columns are missing
    for col, col_type in [("pir", "INTEGER DEFAULT 0"), ("ldr", "REAL DEFAULT 0.0")]:
        try:
            cursor.execute(f"ALTER TABLE dht_data ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Create system logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed data for appliances
    # GPIO pin mappings: Light (18), TV (19), Fridge (21), Fan (22)
    appliances_seed = [
        ("Light", 18),
        ("TV", 19),
        ("Fridge", 21),
        ("Fan", 22)
    ]

    for name, pin in appliances_seed:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO appliances (name, relay_pin, status) VALUES (?, ?, 0)",
                (name, pin)
            )
        except sqlite3.Error as e:
            print(f"Failed to seed appliance {name}: {e}")

    conn.commit()
    conn.close()
    print("Database initialization completed successfully.")

if __name__ == "__main__":
    init_db()
