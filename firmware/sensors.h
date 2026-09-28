#ifndef SENSORS_H
#define SENSORS_H

/**
 * @brief Initializes sensors (DHT22 and ADC configuration).
 */
void initSensors();

/**
 * @brief Computes True RMS current (Amps) for a given SCT-013 current sensor pin.
 * 
 * @param pin The ESP32 analog pin connected to the burden resistor output.
 * @return double Calculated RMS current in Amperes.
 */
double readCurrentRMS(int pin);

/**
 * @brief Reads temperature and humidity from the DHT22 sensor.
 * 
 * @param temperature Reference to write temperature value (°C).
 * @param humidity Reference to write humidity value (%).
 * @return true If reading was successful.
 * @return false If reading failed (nan returned).
 */
bool readDHT(float &temperature, float &humidity);

#endif // SENSORS_H
