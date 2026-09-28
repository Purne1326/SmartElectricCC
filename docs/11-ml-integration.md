# 11. Machine Learning Integration & Model Manual

This document details the Machine Learning pipeline implemented in the SmartElectric edge gateway for predicting aggregate power consumption and detecting anomaly usage patterns.

---

## 📈 Forecasting Strategy (GRU Model)

We utilize a **Gated Recurrent Unit (GRU)** neural network for time-series forecasting because it captures temporal dependencies efficiently while requiring significantly less RAM and CPU cycles than LSTM networks.

### 1. Data Window Setup
- **Input Feature Space:** A sliding window of the last 24 hours of aggregate active power readings sampled at 15-minute intervals (96 historical steps).
- **Target Output Horizon:** The predicted active power for the next 1 hour in 15-minute segments (4 forecast steps).

### 2. Model Architecture
- **Input Dimension:** 1 (Active Power in Watts)
- **GRU Hidden Layer Dimension:** 64
- **GRU Recurrent Layers:** 2
- **Fully Connected Head:** Outputs 4 values matching the forecast steps.

---

## ⚙️ REST API Models & Formats

The FastAPI edge backend registers the inference service. Here are the core specifications:

### 1. Load Forecasting
* **Endpoint:** `POST /api/v1/predict/load`
* **Response payload:**
```json
{
  "device_id": "gateway-001",
  "forecasted_timestamps": [
    "2026-06-21 18:15:00",
    "2026-06-21 18:30:00",
    "2026-06-21 18:45:00",
    "2026-06-21 19:00:00"
  ],
  "forecasted_power_watts": [345.2, 330.5, 310.8, 290.4]
}
```

### 2. Multi-Task Decision & Attribution
* **Endpoint:** `POST /api/v1/predict/decision`
* **Response payload:**
```json
{
  "classification": "NORMAL",
  "anomaly_score": 0.12,
  "top_attributed_appliance": "Fridge",
  "recommendation": "Optimal load pattern. Keep appliances running normally."
}
```

---

## 🏋️ Training the Model Locally

A training script is provided at `edge/backend/ml_forecaster.py`. 

To train the model on your local Edge SQLite database:
1. Activate the environment:
   ```bash
   source edge/backend/.venv/bin/activate
   ```
2. Execute the training command:
   ```bash
   python edge/backend/ml_forecaster.py --train
   ```
This extracts historical sensor readings from SQLite, normalizes the values, builds training batches, runs backpropagation optimizations, and stores the weights file (`gru_forecaster.pt`) locally for real-time FastAPI inference.
