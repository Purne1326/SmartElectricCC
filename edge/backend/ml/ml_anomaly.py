import os
import sqlite3
import numpy as np
from sklearn.ensemble import IsolationForest

DB_PATH = os.path.join(os.path.dirname(__file__), "edge_iot.db")

# Normal operating parameters (nominal ranges) for fallback checks
NORMAL_LIMITS = {
    "Light": {"max_power": 50.0, "max_current": 0.22},
    "TV": {"max_power": 130.0, "max_current": 0.60},
    "Fridge": {"max_power": 280.0, "max_current": 1.25},
    "Fan": {"max_power": 80.0, "max_current": 0.35}
}

def get_appliance_history(appliance_name):
    """Fetches normal historical telemetry for a specific appliance."""
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Fetch latest 200 normal readings (power < 1.5x expected limit to avoid training on anomalies)
        limit = NORMAL_LIMITS.get(appliance_name, {"max_power": 300.0})["max_power"] * 1.5
        cursor.execute("""
            SELECT current, power, voltage 
            FROM sensor_data 
            WHERE appliance_name = ? AND power < ? 
            ORDER BY timestamp DESC LIMIT 200
        """, (appliance_name, limit))
        return cursor.fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

def detect_anomaly(appliance_name, current, power, voltage):
    """
    Evaluates whether the current telemetry reading is an anomaly.
    Returns a string describing the anomaly type if detected, otherwise None.
    """
    # 1. First check if device is turned off (power ~ 0) - should never be classified as anomaly
    if power < 2.0 and current < 0.02:
        return None

    limits = NORMAL_LIMITS.get(appliance_name)
    
    # Check simple voltage limits first as they apply universally
    if voltage < 180.0:
        return "Under-Voltage"
    if voltage > 260.0:
        return "Voltage Surge"

    history = get_appliance_history(appliance_name)
    is_anomaly = False
    
    # We require at least 30 historical entries to train IsolationForest reliably
    if len(history) >= 30:
        try:
            X_train = np.array(history)
            
            # Fit Isolation Forest
            # contamination=0.02 means we expect ~2% anomalies in historical data max
            clf = IsolationForest(n_estimators=50, contamination=0.02, random_state=42)
            clf.fit(X_train)
            
            # Predict status
            X_test = np.array([[current, power, voltage]])
            pred = clf.predict(X_test)
            
            # pred is -1 for anomaly, 1 for normal
            if pred[0] == -1:
                is_anomaly = True
        except Exception as e:
            # Fallback on estimation error
            print(f"Anomaly inference error for {appliance_name}: {e}. Running threshold fallback.")
            
    # 2. Rule-Based / IsolationForest Check
    if is_anomaly or len(history) < 30:
        if limits:
            if power > limits["max_power"] or current > limits["max_current"]:
                return "Overcurrent (Overload)"
        if is_anomaly:
            return "Unusual Load Signature"
            
    return None

if __name__ == "__main__":
    # Test cases
    print("Fridge normal (0.8A, 184W, 230V):", detect_anomaly("Fridge", 0.8, 184.0, 230.0))
    print("Fridge abnormal (1.5A, 345W, 230V):", detect_anomaly("Fridge", 1.5, 345.0, 230.0))
