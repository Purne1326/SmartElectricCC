import os
import sqlite3
import numpy as np
from sklearn.ensemble import RandomForestRegressor

DB_PATH = os.path.join(os.path.dirname(__file__), "edge_iot.db")

def generate_synthetic_solar_data():
    """Generates synthetic historical training data correlating climate and solar output."""
    X, y = [], []
    for _ in range(500):
        # Random temperature between 15°C and 40°C
        temp = np.random.uniform(15, 40)
        # Random humidity between 30% and 90%
        hum = np.random.uniform(30, 90)
        # Random hour between 0 and 23
        hour = np.random.uniform(0, 24)
        
        # Calculate expected base solar power based on diurnal curve (bell curve peaking at 12 PM)
        if 6 <= hour <= 18:
            # Peak power of 500W at midday
            base = 500.0 * np.sin(np.pi * (hour - 6) / 12)
            # Reduce generation if humidity is high (simulating clouds/rain)
            cloud_factor = 1.0 - max(0.0, (hum - 45.0) / 100.0) # hum > 45 starts reducing solar
            power = base * cloud_factor + np.random.normal(0, 15.0)
            power = max(0.0, power)
        else:
            power = 0.0
            
        X.append([temp, hum, hour])
        y.append(power)
        
    return np.array(X), np.array(y)

def predict_solar_forecast(current_temp, current_hum, current_hour):
    """
    Predicts solar generation output (in Watts) for the next 3 hours.
    Uses RandomForestRegressor trained on synthetic/DB data.
    """
    X_train, y_train = generate_synthetic_solar_data()
    
    # Train the RandomForest model
    regr = RandomForestRegressor(n_estimators=30, random_state=42)
    regr.fit(X_train, y_train)
    
    forecasts = []
    for step in range(1, 4):
        future_hour = (current_hour + step) % 24
        # Assume humidity climbs slightly at night or fluctuates
        future_hum = min(100.0, max(0.0, current_hum + np.random.normal(0, 2.0)))
        future_temp = current_temp + np.random.normal(-0.5, 0.5)
        
        pred = regr.predict([[future_temp, future_hum, future_hour]])
        forecasts.append(round(max(0.0, float(pred[0])), 2))
        
    return forecasts

if __name__ == "__main__":
    # Test cases
    print("Solar Forecast (Temp: 28°C, Hum: 50%, Hour: 10 AM):", predict_solar_forecast(28.0, 50.0, 10))
