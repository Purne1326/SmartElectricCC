#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Toggle between 1 for HiveMQ Cloud TLS (Port 8883) and 0 for Local Mosquitto (Port 1883)
#define USE_HIVEMQ_CLOUD 1

#if USE_HIVEMQ_CLOUD
#define MQTT_PORT 8883
#else
#define MQTT_PORT 1883
#endif

extern const char* mqtt_server; // Defined in secrets.h / config.cpp if overridden

// Relay State Definitions (Set RELAY_ACTIVE_LOW to 1 for standard Active-LOW 4-channel relay boards)
#define RELAY_ACTIVE_LOW 1

#if RELAY_ACTIVE_LOW
#define RELAY_ACTIVE_STATE LOW
#define RELAY_INACTIVE_STATE HIGH
#else
#define RELAY_ACTIVE_STATE HIGH
#define RELAY_INACTIVE_STATE LOW
#endif

// Relay Pin Mappings
#define RELAY_LIGHT_PIN 18
#define RELAY_TV_PIN    19
#define RELAY_FRIDGE_PIN 26
#define RELAY_FAN_PIN    27

// SCT-013 Current Sensor Analog Input Pins (ESP32 ADC pins)
#define SENSOR_LIGHT_PIN 32
#define SENSOR_TV_PIN    33
#define SENSOR_FRIDGE_PIN 34
#define SENSOR_FAN_PIN    35

// AC Electrical Constants (Indian standard grid)
#define GRID_VOLTAGE 230.0    // Nominal RMS Voltage (V)
#define GRID_FREQUENCY 50.0   // AC Frequency (Hz)

// SCT-013 Calibration Factor (Current Calibration value)
// For 100A/50mA sensor with 33-ohm burden resistor on ESP32 (3.3V ADC limit)
// Math: (100A / 0.05A) / BurdenResistor_33_ohms = 60.6
#define SCT_CALIBRATION 60.6

// Noise Floor Threshold (RMS Amps below this threshold are forced to 0.0 to eliminate ADC noise)
#define CURRENT_NOISE_FLOOR_AMPS 0.015

// Demo Bulb Scaling Factors (Maps physical demo bulb current to realistic appliance profiles)
// e.g. FRIDGE_SCALE_FACTOR 2.2 converts a 100W test bulb (~0.43A) to a realistic 220W fridge load
#define LIGHT_SCALE_FACTOR  1.0
#define TV_SCALE_FACTOR     1.0
#define FRIDGE_SCALE_FACTOR 2.2
#define FAN_SCALE_FACTOR    1.0

// ADC Configuration for ESP32
#define ADC_BITS 12
#define ADC_COUNTS 4096

// Loop & Reporting Intervals
#define TELEMETRY_INTERVAL_MS 5000  // Send telemetry every 5 seconds
#define SAFETY_LOCKOUT_MS     3000  // Prevent relay chattering (min 3 seconds between state changes)

// PIR and LDR Sensor Pin Mappings
#define SENSOR_PIR_PIN 4
#define SENSOR_LDR_PIN 36

#endif // CONFIG_H
