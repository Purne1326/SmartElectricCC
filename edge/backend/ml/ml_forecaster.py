import os
import sqlite3
import datetime
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

DB_PATH = os.path.join(os.path.dirname(__file__), "edge_iot.db")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "gru_forecaster.pt")

# GRU Model Definition
class GRUForecaster(nn.Module):
    def __init__(self, input_dim=1, hidden_dim=64, num_layers=2, output_dim=4):
        super(GRUForecaster, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        self.gru = nn.GRU(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        out, _ = self.gru(x, h0)
        # Select output of the last sequence step
        out = self.fc(out[:, -1, :])
        return out

def get_historical_data():
    """Extracts aggregate active power history from SQLite for training/testing."""
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Fetch timestamp and total_power sorted by time
        cursor.execute("SELECT total_power FROM sensor_data ORDER BY timestamp ASC")
        rows = cursor.fetchall()
        return [r[0] for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

def train_model(epochs=10):
    """Trains the GRU model using SQLite historical telemetry."""
    print("Extracting historical data from database...")
    data = get_historical_data()
    
    if len(data) < 150:
        print(f"Insufficient data for training (found {len(data)} records, need at least 150).")
        print("Pre-training on synthetic load profiles to initialize weights...")
        # Create a synthetic daily load profile (96 steps/day)
        data = []
        for _ in range(5):  # 5 days
            for hour in range(24):
                for _ in range(4):  # 15-min intervals
                    base = 100.0 if hour < 8 or hour > 22 else 350.0
                    data.append(base + np.random.normal(0, 20.0))

    # Construct overlapping windows
    # Window size: 96 steps (24 hours @ 15 min), Target size: 4 steps (1 hour)
    window_size = 96
    target_size = 4
    
    X, Y = [], []
    for i in range(len(data) - window_size - target_size):
        X.append(data[i : i + window_size])
        Y.append(data[i + window_size : i + window_size + target_size])
        
    X_tensor = torch.tensor(X, dtype=torch.float32).unsqueeze(-1) # Shape: (samples, 96, 1)
    Y_tensor = torch.tensor(Y, dtype=torch.float32)              # Shape: (samples, 4)

    print(f"Created training dataset with {X_tensor.shape[0]} windows.")

    model = GRUForecaster()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.005)

    print("Starting training...")
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        outputs = model(X_tensor)
        loss = criterion(outputs, Y_tensor)
        loss.backward()
        optimizer.step()
        if (epoch + 1) % 2 == 0 or epoch == 0:
            print(f"Epoch [{epoch+1}/{epochs}], Loss: {loss.item():.4f}")

    # Save model weights
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Model saved successfully to {MODEL_PATH}!")
    return model

def run_forecast(current_power_watts=300.0):
    """Executes model inference. Uses saved weights or falls back to smart scaling."""
    # Initialize model
    model = GRUForecaster()
    
    # Try loading saved weights
    weights_loaded = False
    if os.path.exists(MODEL_PATH):
        try:
            model.load_state_dict(torch.load(MODEL_PATH))
            model.eval()
            weights_loaded = True
        except Exception as e:
            print(f"Failed to load weights: {e}")

    # If weights are loaded and we have database history, perform real inference
    if weights_loaded:
        history = get_historical_data()
        if len(history) >= 96:
            # Prepare input sequence
            seq = history[-96:]
            input_tensor = torch.tensor([seq], dtype=torch.float32).unsqueeze(-1)
            with torch.no_grad():
                pred = model(input_tensor).numpy()[0]
                return pred.tolist()

    # Fallback to realistic daily projection if database has insufficient data or weights are absent
    # Outputs 4 forecasted values (15-min intervals ahead) centered around the current power value
    print("Inference Fallback: Generating projection based on current load profile...")
    current_hour = datetime.datetime.now().hour
    projections = []
    
    for step in range(1, 5):
        future_hour = (current_hour + int(step * 0.25)) % 24
        # Multipliers based on daily circadian load factors
        if 8 <= future_hour <= 18:
            factor = 1.15 + np.random.uniform(-0.05, 0.05) # normal daytime peak
        elif 18 < future_hour <= 22:
            factor = 1.35 + np.random.uniform(-0.05, 0.05) # evening dinner peak
        else:
            factor = 0.65 + np.random.uniform(-0.05, 0.05) # nighttime idle
            
        projections.append(round(current_power_watts * factor, 2))
        
    return projections

if __name__ == "__main__":
    import sys
    # Train if flag --train is passed
    if len(sys.argv) > 1 and sys.argv[1] == "--train":
        train_model()
    else:
        print("Forecast Test (Current Load: 250W):", run_forecast(250.0))
