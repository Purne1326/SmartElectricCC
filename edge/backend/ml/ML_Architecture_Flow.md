# Machine Learning Architecture & Data Flow

This document details the complete end-to-end flow of the Machine Learning (ML) integration within the Smart Electric platform. The AI capabilities are powered by two primary neural network models (GRU and ONNX-based Multi-Task models) running at the edge.

## 1. Directory Structure

The ML components have been isolated into a dedicated package to decouple the AI logic from the core FastAPI application:

```
edge/backend/ml/
│
├── __init__.py           # Makes the directory a Python module
├── ml_onnx.py            # Core ML wrapper, feature engineering, and ONNX inference logic
├── ML_Architecture_Flow.md # This documentation
└── trained_models/       # Contains the pre-trained weights, models, and scalers
    ├── appliance_scaler.pkl
    ├── scaler.pkl
    ├── model1_forecaster.onnx
    ├── model2_decision.onnx
    └── model2_decision_output_layout.json
```

## 2. Core Models Overview

The system uses two pre-trained neural networks executed via `onnxruntime` (which allows lightweight, fast, CPU-bound inference directly on edge devices without requiring heavy frameworks like PyTorch or TensorFlow).

### Model 1: Load Forecaster (GRU)
* **Type**: Gated Recurrent Unit (GRU) Time-Series Forecaster.
* **Input**: A 96-step time-series tensor representing 24 hours of historical data in 15-minute intervals. Each step has 16 features (Active Power, Reactive Power, Voltage, Cyclical Time Encodings, etc.).
* **Output**: Predicts the Active Power load for the next 4 time steps (+15m, +30m, +45m, +60m) into the future.
* **Purpose**: Helps the system anticipate spikes in energy demand before they happen.

### Model 2: Multi-Task Decision Engine
* **Type**: Multi-Task Neural Network.
* **Input**: Uses the exact same 96-step (24-hour) historical tensor as Model 1.
* **Outputs**:
  1. **Load Classification**: Categorizes current grid stress as `Low`, `Normal`, or `High`.
  2. **Appliance Attribution**: Predicts the number of hours each specific appliance (e.g., Fridge, AC, TV) runs daily.
  3. **Optimization Flags**: Recommends binary system actions: `LoadShedding`, `SmartScheduling`, and `HighPowerWarning`.

## 3. The Data Pipeline & Integration Flow

How does the data move from the IoT sensors to the frontend dashboard?

### Step A: Feature Engineering (`ml_onnx.py -> get_historical_features`)
Before passing data to the ONNX models, `ml_onnx.py` must build the 96-step input tensor.
1. **Mathematical Baseline**: The script starts by constructing a default mathematical sequence (a synthetic circadian load profile). This guarantees that even if the hardware is completely disconnected or the system is newly installed, the models won't crash due to empty inputs.
2. **Database Merging**: It then queries the local SQLite database (`edge_iot.db`) for real historical data. If data exists, it aggregates it into 15-minute intervals and replaces the "tail" of the synthetic baseline with real sensor telemetry.
3. **Scaling**: The 96x16 tensor is normalized using the pre-trained `scaler.pkl` to match the data distribution the models were originally trained on.

### Step B: Inference & API Endpoints (`main.py`)
The FastAPI server exposes two endpoints that the frontend calls:
* `POST /api/v1/predict/load`: Calls `ml_onnx.run_forecast(current_watts)`.
* `POST /api/v1/predict/decision`: Calls `ml_onnx.run_decision()`.

If `onnxruntime` fails or the models are missing, `ml_onnx.py` includes a robust fallback mechanism (`_forecast_fallback`) that returns mathematically approximated predictions so the system never breaks.

### Step C: Frontend Visualization (`index.html`)
On the client side, the single-page application orchestrates the visual layer:
1. **Background Polling**: A JavaScript loop (`setInterval`) continuously fetches data from the backend APIs every 3 seconds.
2. **Dashboard Widgets**: A summary banner on the main dashboard instantly updates with the Decision Engine's `NORMAL/WARNING/HIGH` state.
3. **AI Forecasting Tab**:
    * **Simulation Engine**: Users can move a slider to manually inject an override wattage. The frontend sends this simulated wattage to the backend to instantly see how the neural networks react.
    * **Interactive Charts**: The GRU predictions are plotted on a smooth ApexCharts area graph.
    * **Attribution Breakdown**: The Model 2 attribution hours are rendered as horizontal progress bars.

## 4. Summary of Benefits
By isolating the ML inference logic and utilizing a hybrid synthetic-real data pipeline:
* **Resilience**: The system can function 100% offline and in "isolated software mode" without real hardware attached.
* **Edge-Optimized**: Using ONNX prevents memory bloat on edge gateways.
* **Decoupled**: Changes to the ML models or scalers only require dropping new files into the `trained_models/` directory without altering the core FastAPI logic.
