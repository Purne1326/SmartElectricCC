import os
import json
import pickle
import sqlite3
import datetime
import numpy as np
import onnxruntime as ort

# Paths
ML_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(ML_DIR)
DB_PATH = os.path.join(BACKEND_DIR, "edge_iot.db")
MODELS_DIR = os.path.join(ML_DIR, "trained_models")

MODEL1_PATH = os.path.join(MODELS_DIR, "model1_forecaster.onnx")
MODEL2_PATH = os.path.join(MODELS_DIR, "model2_decision.onnx")
LAYOUT_PATH = os.path.join(MODELS_DIR, "model2_decision_output_layout.json")
SCALER_PATH = os.path.join(MODELS_DIR, "scaler.pkl")
APP_SCALER_PATH = os.path.join(MODELS_DIR, "appliance_scaler.pkl")

# Lazy-loaded sessions and scalers
_sessions = {}
_scalers = {}

def get_session(model_path):
    if model_path not in _sessions:
        if os.path.exists(model_path):
            try:
                # Use CPU execution provider for portability and low footprint
                _sessions[model_path] = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
            except Exception as e:
                print(f"Error loading ONNX model {model_path}: {e}")
                _sessions[model_path] = None
        else:
            _sessions[model_path] = None
    return _sessions[model_path]

def get_scaler(scaler_path):
    if scaler_path not in _scalers:
        if os.path.exists(scaler_path):
            try:
                with open(scaler_path, 'rb') as f:
                    _scalers[scaler_path] = pickle.load(f)
            except Exception as e:
                print(f"Error loading scaler {scaler_path}: {e}")
                _scalers[scaler_path] = None
        else:
            _scalers[scaler_path] = None
    return _scalers[scaler_path]

def get_historical_features():
    """
    Queries SQLite and constructs the (96, 16) feature matrix for the last 24 hours.
    Resamples telemetry to 15-minute intervals. If insufficient data is present,
    it pads the sequence with a realistic baseline.
    """
    # Default baseline sequence of 96 steps
    now = datetime.datetime.now()
    times = [now - datetime.timedelta(minutes=15 * (95 - i)) for i in range(96)]
    
    # Baseline raw features:
    # [active_power, reactive_power, voltage, intensity, sub1, sub2, sub3]
    raw_data = []
    for t in times:
        hour = t.hour
        # Base circadian load profile in Watts
        base_watts = 150.0 if hour < 8 or hour > 22 else 350.0
        base_watts += np.random.normal(0, 15.0)
        base_watts = max(10.0, base_watts)
        
        voltage = 230.0 + np.random.normal(0, 1.5)
        current = base_watts / voltage
        
        # Split into sub-meterings (Wh per 15 mins)
        fridge_watts = 90.0 if (t.minute < 20 or 30 <= t.minute < 50) else 5.0
        sub1 = fridge_watts * 0.25 # Fridge in kitchen (Sub1)
        sub2 = 0.0 # Laundry (Sub2)
        sub3 = max(0.0, base_watts - fridge_watts) * 0.25 # AC/Others (Sub3)
        
        raw_data.append({
            'timestamp': t,
            'active_power': base_watts / 1000.0, # kW
            'reactive_power': (base_watts * 0.1) / 1000.0, # kW
            'voltage': voltage,
            'intensity': current,
            'sub1': sub1,
            'sub2': sub2,
            'sub3': sub3
        })
        
    # Attempt to load real data from database
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Fetch last 24 hours of aggregate appliance readings
            # Grouped in 15-minute windows
            fifteen_mins_ago = (now - datetime.timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m-%d %H:', timestamp) || 
                    printf('%02d', (cast(strftime('%M', timestamp) as integer) / 15) * 15) || ':00' as interval_time,
                    SUM(power) as total_power,
                    AVG(voltage) as avg_voltage,
                    SUM(current) as total_current,
                    SUM(CASE WHEN appliance_name = 'Fridge' THEN power ELSE 0 END) as fridge_power,
                    SUM(CASE WHEN appliance_name IN ('TV', 'Fan', 'Light') THEN power ELSE 0 END) as other_power
                FROM sensor_data
                WHERE timestamp >= ?
                GROUP BY interval_time
                ORDER BY interval_time ASC
                LIMIT 96
            """, (fifteen_mins_ago,))
            
            rows = cursor.fetchall()
            if len(rows) > 5:
                # Merge DB data into the tail of our baseline template
                db_data = []
                for row in rows:
                    interval_dt = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                    active_kw = (row[1] or 0.0) / 1000.0
                    volts = row[2] or 230.0
                    amps = row[3] or 0.0
                    
                    sub1 = ((row[4] or 0.0) * 0.25) # Wh
                    sub2 = 0.0
                    sub3 = ((row[5] or 0.0) * 0.25) # Wh
                    
                    db_data.append({
                        'timestamp': interval_dt,
                        'active_power': active_kw,
                        'reactive_power': active_kw * 0.1,
                        'voltage': volts,
                        'intensity': amps,
                        'sub1': sub1,
                        'sub2': sub2,
                        'sub3': sub3
                    })
                
                # Replace tail of baseline with real DB measurements
                num_db_steps = min(96, len(db_data))
                raw_data[-num_db_steps:] = db_data[-num_db_steps:]
                
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to fetch real history from DB ({e}). Using baseline data.")

    # 1. Feature Engineering
    features = np.zeros((96, 16), dtype=np.float32)
    for i, item in enumerate(raw_data):
        dt = item['timestamp']
        hour = dt.hour
        dow = dt.weekday()
        
        # Cyclical encoding
        hour_sin = np.sin(2 * np.pi * hour / 24.0)
        hour_cos = np.cos(2 * np.pi * hour / 24.0)
        dow_sin = np.sin(2 * np.pi * dow / 7.0)
        dow_cos = np.cos(2 * np.pi * dow / 7.0)
        is_weekend = 1.0 if dow >= 5 else 0.0
        
        features[i, 0] = item['active_power']
        features[i, 1] = item['reactive_power']
        features[i, 2] = item['voltage']
        features[i, 3] = item['intensity']
        features[i, 4] = item['sub1']
        features[i, 5] = item['sub2']
        features[i, 6] = item['sub3']
        features[i, 7] = hour_sin
        features[i, 8] = hour_cos
        features[i, 9] = dow_sin
        features[i, 10] = dow_cos
        features[i, 11] = is_weekend

    # 2. Rolling and Lag Features
    # Since we have the full sequence, we calculate rolling stats on active_power (index 0)
    active_powers = features[:, 0]
    
    # Lag 1h (4 steps) and 24h (96 steps - we default to first step or fill)
    for i in range(96):
        # Mean & Std (rolling window size 96 or available lookback)
        window = active_powers[max(0, i - 95): i + 1]
        features[i, 12] = np.mean(window)
        features[i, 13] = np.std(window) if len(window) > 1 else 0.0
        
        # Lag 1h (4 steps)
        features[i, 14] = active_powers[i - 4] if i >= 4 else active_powers[0]
        # Lag 24h (96 steps - default to first step value)
        features[i, 15] = active_powers[0]

    # 3. Apply MinMaxScaler
    scaler = get_scaler(SCALER_PATH)
    if scaler is not None:
        try:
            features = scaler.transform(features).astype(np.float32)
        except Exception as e:
            print(f"Warning: Scaling failed ({e}), using raw features.")
            
    return features

def run_forecast(current_watts=300.0):
    """
    Runs Model-1 Load Forecaster.
    Returns 4 forecasted future active power load values in Watts.
    """
    session = get_session(MODEL1_PATH)
    scaler = get_scaler(SCALER_PATH)
    
    # Fallback if model is not loaded
    if session is None or scaler is None:
        return _forecast_fallback(current_watts)
        
    try:
        features = get_historical_features() # (96, 16)
        input_tensor = np.expand_dims(features, axis=0) # (1, 96, 16)
        
        # Run ONNX inference
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_tensor})
        predictions = outputs[0] # (1, 4)
        
        # Denormalize predictions using scaler parameters for Global_active_power (index 0)
        min_val = float(scaler.data_min_[0])
        max_val = float(scaler.data_max_[0])
        
        denorm_preds = predictions[0] * (max_val - min_val) + min_val # kW
        watts_preds = [round(max(0.0, float(val * 1000.0)), 2) for val in denorm_preds]
        
        return watts_preds
    except Exception as e:
        print(f"ONNX Model-1 forecasting error: {e}. Falling back.")
        return _forecast_fallback(current_watts)

def run_decision():
    """
    Runs Model-2 Multi-Task Decision Model.
    Returns:
        - load_class: 'Low', 'Normal', or 'High'
        - attributions: dict of predicted appliance usage hours
        - optimization: dict of active optimization decisions
    """
    session = get_session(MODEL2_PATH)
    scaler = get_scaler(SCALER_PATH)
    app_scaler = get_scaler(APP_SCALER_PATH)
    
    # Fallback dictionary if model or scalers are missing
    default_res = {
        "load_class": "Normal",
        "attributions": {
            "Fan": 14.5, "Refrigerator": 20.0, "AirConditioner": 1.2, 
            "Television": 12.0, "Monitor": 6.5, "MotorPump": 0.0
        },
        "optimization": {
            "LoadShedding": False,
            "SmartScheduling": False,
            "HighPowerWarning": False
        }
    }
    
    if session is None or scaler is None or app_scaler is None:
        return default_res
        
    try:
        features = get_historical_features() # (96, 16)
        input_tensor = np.expand_dims(features, axis=0) # (1, 96, 16)
        
        # Run ONNX inference
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_tensor})
        concatenated_outputs = outputs[0] # (1, 12)
        
        # Load layout to unpack
        if os.path.exists(LAYOUT_PATH):
            with open(LAYOUT_PATH) as f:
                layout = json.load(f)
            unpack = layout["unpack_info"]
        else:
            unpack = {
                "classification": {"start": 0, "end": 3},
                "attribution": {"start": 3, "end": 9},
                "optimization": {"start": 9, "end": 12}
            }
            
        # 1. Unpack classification (Low/Normal/High)
        cls_start = unpack["classification"]["start"]
        cls_end = unpack["classification"]["end"]
        cls_logits = concatenated_outputs[0, cls_start:cls_end]
        cls_idx = int(np.argmax(cls_logits))
        classes = ["Low", "Normal", "High"]
        load_class = classes[cls_idx]
        
        # 2. Unpack attribution hours (Fan, Refrigerator, AC, TV, Monitor, MotorPump)
        attr_start = unpack["attribution"]["start"]
        attr_end = unpack["attribution"]["end"]
        attr_vals = concatenated_outputs[0, attr_start:attr_end]
        
        # Denormalize hours using appliance scaler min/max
        app_names = ["Fan", "Refrigerator", "AirConditioner", "Television", "Monitor", "MotorPump"]
        raw_attributions = {}
        for idx, app in enumerate(app_names):
            min_val = float(app_scaler.data_min_[idx])
            max_val = float(app_scaler.data_max_[idx])
            hours = float(attr_vals[idx]) * (max_val - min_val) + min_val
            raw_attributions[app] = round(max(0.0, hours), 2)
            
        # --- APPLIANCE MASKING & MAPPING LAYER ---
        # Map neural network labels to our system's actual hardware labels
        name_map = {
            "Television": "TV",
            "Refrigerator": "Refrigerator",
            "Fan": "Fan",
            "AirConditioner": "AC",
            "Monitor": "Monitor",
            "MotorPump": "Pump"
        }
        
        attributions = {}
        # Fetch physically connected appliances from the database
        connected_apps = set(["TV", "Refrigerator", "Fan", "Light"]) # Default fallbacks
        if os.path.exists(DB_PATH):
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT appliance_name FROM sensor_data")
                rows = cursor.fetchall()
                if rows:
                    connected_apps = {row[0] for row in rows}
                conn.close()
            except Exception:
                pass
                
        for model_name, hours in raw_attributions.items():
            system_name = name_map.get(model_name, model_name)
            # Only keep the prediction if the appliance actually exists in the real hardware setup!
            if system_name in connected_apps:
                attributions[system_name] = hours
                
        # If no appliances matched (e.g., completely different names), fallback to returning everything
        if not attributions:
            attributions = {name_map.get(k, k): v for k, v in raw_attributions.items()}
            
        # 3. Unpack optimization actions (LoadShedding, SmartScheduling, HighPowerWarning)
        opt_start = unpack["optimization"]["start"]
        opt_end = unpack["optimization"]["end"]
        opt_logits = concatenated_outputs[0, opt_start:opt_end]
        # Apply sigmoid mapping
        opt_probs = 1.0 / (1.0 + np.exp(-opt_logits))
        
        optimization = {
            "LoadShedding": bool(opt_probs[0] > 0.5),
            "SmartScheduling": bool(opt_probs[1] > 0.5),
            "HighPowerWarning": bool(opt_probs[2] > 0.5)
        }
        
        return {
            "load_class": load_class,
            "attributions": attributions,
            "optimization": optimization
        }
        
    except Exception as e:
        print(f"ONNX Model-2 decision error: {e}. Falling back.")
        return default_res

def _forecast_fallback(current_watts):
    """Fallback circadian-aware load forecaster."""
    hour = datetime.datetime.now().hour
    projections = []
    for step in range(1, 5):
        future_hour = (hour + int(step * 0.25)) % 24
        if 8 <= future_hour <= 18:
            factor = 1.15 + np.random.uniform(-0.05, 0.05)
        elif 18 < future_hour <= 22:
            factor = 1.35 + np.random.uniform(-0.05, 0.05)
        else:
            factor = 0.65 + np.random.uniform(-0.05, 0.05)
        projections.append(round(current_watts * factor, 2))
    return projections

if __name__ == "__main__":
    print("Testing ONNX wrapper...")
    print("Forecasting predictions (from 350W):", run_forecast(350.0))
    print("Decision predictions:", run_decision())
