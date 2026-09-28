#ifndef RELAYS_H
#define RELAYS_H

/**
 * @brief Configures GPIO relay pins as outputs and initializes them to OFF (0).
 */
void initRelays();

/**
 * @brief Safe relay toggle function by appliance string identifier.
 * Includes anti-chattering safety lockout mechanism.
 * 
 * @param applianceName Name of the appliance ("Light", "TV", "Fridge", "Fan").
 * @param state Desired state (0 for OFF, 1 for ON).
 * @return true If state change was successfully executed.
 * @return false If execution was rejected (lockout active or invalid name).
 */
bool setRelayState(const char* applianceName, int state);

/**
 * @brief Safe relay toggle function by physical GPIO pin.
 * Includes anti-chattering safety lockout mechanism.
 * 
 * @param pin The GPIO pin number to control.
 * @param state Desired state (0 for OFF, 1 for ON).
 * @return true If state change was successfully executed.
 * @return false If execution was rejected (lockout active or invalid pin).
 */
bool setRelayStateByPin(int pin, int state);

/**
 * @brief Retrieves the current state of a relay pin.
 * 
 * @param pin The GPIO pin number.
 * @return int Current state: 1 (HIGH/ON) or 0 (LOW/OFF).
 */
int getRelayState(int pin);

#endif // RELAYS_H
