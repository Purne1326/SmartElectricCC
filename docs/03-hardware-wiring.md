# 03. ESP32 Hardware Wiring Manual

This document details the wiring parameters, pin mappings, and signal conditioning circuits for the SmartElectric sensor node.

---

## 📌 ESP32 Pin Mapping

| Pin Name | Direction | Connected Device | Description |
|----------|-----------|------------------|-------------|
| **GPIO 12** | Output | Relay Channel 1 | Control signal for Light Bulb |
| **GPIO 13** | Output | Relay Channel 2 | Control signal for TV/Monitor |
| **GPIO 14** | Output | Relay Channel 3 | Control signal for Fridge |
| **GPIO 15** | Output | Relay Channel 4 | Control signal for Fan |
| **GPIO 34** | Input (ADC) | SCT-013 #1 | Current Sensor (Light) |
| **GPIO 35** | Input (ADC) | SCT-013 #2 | Current Sensor (TV) |
| **GPIO 32** | Input (ADC) | SCT-013 #3 | Current Sensor (Fridge) |
| **GPIO 33** | Input (ADC) | SCT-013 #4 | Current Sensor (Fan) |
| **GPIO 27** | Input (DHT) | DHT22 Sensor | Climate temperature/humidity |
| **GPIO 26** | Input (Digital) | HC-SR501 PIR | Passive Infrared Motion Sensor |

---

## ⚡ SCT-013 Voltage Divider Schematic

The ESP32 Analog-to-Digital Converter (ADC) reads voltages from `0V to 3.3V` only. Since the SCT-013 sensor outputs an alternating current (AC) signal that swings positive and negative, we must apply a **1.65V DC Bias Offset** to center the AC wave.

```
                      +3.3V (ESP32)
                        │
                      [10kΩ] (Resistor R1)
                        │
  SCT-013 Output        ├───→ To ESP32 Analog GPIO (34, 35, 32, or 33)
  (3.5mm Tip Wire) ───[10kΩ] (Burden Resistor if using non-voltage type)*
                        │
                      [10kΩ] (Resistor R2)
                        │
                        ├────[10µF Capacitor (+)]
                        │
                       GND (Capacitor Ground and 3.5mm Sleeve)
```

> **Note on Burden Resistors:**
> * If you are using **SCT-013-000 (Current Output)**, you MUST install a burden resistor (e.g. 22Ω - 33Ω) across the sensor outputs to generate a voltage.
> * If you are using **SCT-013-030 (Voltage Output, 30A/1V)**, the burden resistor is already built-in, so do NOT add one. Connect the tip wire directly to the voltage divider offset node.

---

## 🎛️ Relay Module Connections

The 4-Channel Relay Module is active-low or active-high depending on the trigger jumper. For safe operation, configure it to switch your AC mains line:

```
            Mains Line (220V AC Live)
                     │
                     ▼
             ┌──────────────┐
             │ COM (Common) │
             │   [RELAY]    │
             │ NO (Open)    │
             └──────┬───────┘
                    │
                    ▼
               Appliance Load
                    │
                    ▼
            Mains Neutral Line
```

- Connect **VIN (5V)** from the ESP32 to the VCC pin of the relay board.
- Connect the ESP32 outputs to the input pins:
  - GPIO 12 → IN1
  - GPIO 13 → IN2
  - GPIO 14 → IN3
  - GPIO 15 → IN4
