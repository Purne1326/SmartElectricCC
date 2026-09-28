#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include "config.h"
#include "sensors.h"
#include <math.h>

Adafruit_BME280 bme;

void initSensors() {
    // Initialize BME280 sensor (try both common I2C addresses)
    if (!bme.begin(0x76)) {
        if (!bme.begin(0x77)) {
            Serial.println("Could not find BME280!");
            while (1);
        }
    }

    // Set ESP32 ADC resolution (12-bit)
    analogReadResolution(ADC_BITS);

    // Set ADC attenuation (0–3.3V range)
    analogSetAttenuation(ADC_11db);

    // Configure SENSOR_PIR_PIN as input
    pinMode(SENSOR_PIR_PIN, INPUT);
}

double readCurrentRMS(int pin)
{
    const int sampleCount = 400; 
    double sum = 0.0;
    double sumSq = 0.0;

    // 1. Take rapid samples over ~100ms (covers exactly five 50Hz cycles or six 60Hz cycles)
    for (int i = 0; i < sampleCount; i++) {
        int sample = analogRead(pin);
        
        sum += sample;
        sumSq += (double)sample * sample;
        
        // analogRead takes ~20us, + 230us delay = 250us per sample. 
        // 400 samples * 250us = 100,000us (100ms)
        delayMicroseconds(230); 
    }

    // 2. Calculate the Mean (this automatically finds the actual DC offset)
    double mean = sum / sampleCount;

    // 3. Calculate Variance: Average(x^2) - Average(x)^2
    double variance = (sumSq / sampleCount) - (mean * mean);
    
    // Prevent NaN from floating point inaccuracies on zero-current
    if (variance < 0) variance = 0.0; 

    // 4. Calculate RMS counts
    double rmsCounts = sqrt(variance);

    // 5. Convert to Voltage and then Amperes
    double rmsVoltage = rmsCounts * (3.3 / ADC_COUNTS);
    double currentAmps = rmsVoltage * SCT_CALIBRATION;

    double rawAmps = currentAmps;

    // Apply Noise Floor Threshold Cutoff to eliminate phantom readings from ESP32 ADC jitter
    if (currentAmps < CURRENT_NOISE_FLOOR_AMPS) {
        currentAmps = 0.0;
    }

    Serial.printf("Pin %d -> Raw Measured: %.4f A, Final Output: %.3f A (ADC Midpoint: %.1f)\n", pin, rawAmps, currentAmps, mean);

    return currentAmps;
}

bool readBME280(float &temperature, float &humidity) {
    temperature = bme.readTemperature();
    humidity = bme.readHumidity();

    if (isnan(temperature) || isnan(humidity)) {
        return false;
    }

    return true;
}

float readPressure() {
    return bme.readPressure() / 100.0F;
}

int readPIR() {
    return digitalRead(SENSOR_PIR_PIN);
}

float readLDR() {
    int val = analogRead(SENSOR_LDR_PIN);
    // Convert 12-bit ADC reading (0-4095) to percentage (0% = Dark, 100% = Bright)
    float pct = (float)val / 40.95;
    return pct;
}