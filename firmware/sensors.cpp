#include <Arduino.h>
#include <DHT.h>
#include "config.h"
#include "sensors.h"
#include <math.h>

// Initialize the DHT sensor
static DHT dht(DHT_PIN, DHT_TYPE);

void initSensors() {
    // Start the DHT temperature/humidity sensor
    dht.begin();

    // Set ESP32 ADC resolution (12 bits: 0 to 4095)
    analogReadResolution(ADC_BITS);
    
    // Set attenuation to 11dB for 0-3.3V full scale range
    // By default, ESP32 ADCs are configured with attenuation, but setting it explicitly is safer
    analogSetAttenuation(ADC_11db);
}

double readCurrentRMS(int pin) {
    // Number of samples to capture (spanning multiple AC cycles at 50Hz)
    const int num_samples = 1000;
    
    double sum_squared_current = 0.0;
    double offset = ADC_COUNTS / 2.0; // Initialize DC offset at mid-point (~2048 for 12-bit ADC)
    
    for (int i = 0; i < num_samples; i++) {
        int sample = analogRead(pin);
        
        // Digital high-pass filter to track and remove the 1.65V DC offset dynamically
        // EmonLib algorithm: offset = (prev_offset + (current_sample - prev_offset) / filter_constant)
        offset = offset + ((double)(sample - offset) / 1024.0);
        double filtered_sample = (double)sample - offset;
        
        // Square the filtered AC sample and accumulate
        sum_squared_current += filtered_sample * filtered_sample;
        
        // Slight delay to space out samples (1000 samples * 100us = 100ms, covering 5 complete 50Hz cycles)
        delayMicroseconds(100);
    }
    
    // Calculate root-mean-square of raw filtered units
    double rms_raw = sqrt(sum_squared_current / num_samples);
    
    // Convert raw ADC value to voltage, then apply calibration factor to get Amperes
    // Current (A) = RMS_ADC_counts * (Reference_Voltage / Max_ADC_counts) * Calibration_Factor
    double irms = rms_raw * (GRID_VOLTAGE / ADC_COUNTS) * (SCT_CALIBRATION / GRID_VOLTAGE);
    // Which simplifies to:
    // irms = rms_raw * (3.3 / ADC_COUNTS) * SCT_CALIBRATION; 
    // Let's use the explicit conversion formula:
    double current_amps = rms_raw * (3.3 / (double)ADC_COUNTS) * SCT_CALIBRATION;

    // Noise Gate: Ignore tiny ambient current readings caused by RF/crosstalk noise
    // 0.05A is roughly 11W of power at 230V. Any appliance consuming less is considered OFF.
    if (current_amps < 0.05) {
        current_amps = 0.0;
    }
    
    return current_amps;
}

bool readDHT(float &temperature, float &humidity) {
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    
    // Check if the readings are valid numbers
    if (isnan(t) || isnan(h)) {
        return false;
    }
    
    temperature = t;
    humidity = h;
    return true;
}
