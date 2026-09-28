# 09. SCT-013 Current Sensor Calibration Guide

This document explains the mathematical formulas, digital filters, and calibration constants used to calculate Root-Mean-Square (RMS) AC current using the SCT-013 sensor.

---

## 📐 Mathematical Formulas

The current transformer output is an AC voltage representation of the AC current in the wire.

### 1. DC Offset Removal (High-Pass Filter)
Because the circuit offsets the input signal by 1.65V, we must filter out this DC component in software to isolate the alternating AC wave. We use a digital high-pass filter:

$$\text{Filtered}(n) = \alpha \times (\text{Filtered}(n-1) + \text{Raw}(n) - \text{Raw}(n-1))$$

*Where $\alpha$ (alpha) is typically set to `0.996` to preserve grid frequency (50Hz) amplitudes.*

### 2. Root-Mean-Square Calculation
To compute the RMS current ($I_{RMS}$):

$$I_{RMS} = \text{Calibration Coefficient} \times \sqrt{\frac{1}{N} \sum_{i=1}^{N} \text{Filtered}(i)^2}$$

*Where $N$ is the total number of samples taken over multiple full mains cycles (usually 3000 to 4000 samples).*

---

## ⚙️ Calibration Coefficient Scaling

In [`sensors.cpp`](file:///d:/Smart%20Build/firmware/sensors.cpp):
```cpp
const float CALIBRATION_COEFF = 30.0; // Converts ADC voltage levels to target Amps
```
- **SCT-013-030 (30A/1V):** A primary current of 30A outputs 1V RMS. The calibration coefficient maps the raw 12-bit ADC values (0-4095 representing 0-3.3V) back to primary current amps.
- **Adjustment Wizard:** If the reported load differs from a benchmark multimeter check, adjust `CALIBRATION_COEFF` inside `config.h`:
  - If readings are **too low**, *increase* the coefficient.
  - If readings are **too high**, *decrease* the coefficient.

---

## 🚫 Noise Gate Filter
To prevent the ADC from logging small noise spikes (caused by electromagnetic interference or switching power supplies) when an appliance is completely off, we enforce a software noise gate in `sensors.cpp`:
```cpp
if (currentRMS < 0.05) {
    currentRMS = 0.0; // Filter out anything below 50mA (approx. 11 Watts)
}
```
This keeps database rows clean and prevents accumulating tiny false consumption costs.
