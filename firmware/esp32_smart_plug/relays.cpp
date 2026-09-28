#include <Arduino.h>
#include "config.h"
#include "relays.h"
#include <string.h>

// Keep track of the last execution timestamp (ms) for each relay pin to enforce safety delays
// Indexes map to: [0]: Light, [1]: TV, [2]: Fridge, [3]: Fan
static unsigned long last_relay_toggle_ms[4] = {0, 0, 0, 0};

// Array of relay pins matching the indexes above
static const int relay_pins[4] = {
    RELAY_LIGHT_PIN,
    RELAY_TV_PIN,
    RELAY_FRIDGE_PIN,
    RELAY_FAN_PIN
};

// Helper function to get relay index from GPIO pin
static int get_relay_index(int pin) {
    for (int i = 0; i < 4; i++) {
        if (relay_pins[i] == pin) {
            return i;
        }
    }
    return -1;
}

void initRelays() {
    for (int i = 0; i < 4; i++) {
        pinMode(relay_pins[i], OUTPUT);
        // Safety: ensure relays boot up in a de-energized/OFF state
        digitalWrite(relay_pins[i], RELAY_INACTIVE_STATE);
        last_relay_toggle_ms[i] = 0;
    }
}

bool setRelayStateByPin(int pin, int state) {
    int idx = get_relay_index(pin);
    if (idx == -1) {
        return false; // Invalid GPIO pin for our relay configuration
    }

    unsigned long current_time = millis();
    
    // Check if the lockout cooldown period has passed to prevent rapid toggling (chattering)
    // which damages relay contacts and inductive appliance motors
    if (current_time - last_relay_toggle_ms[idx] < SAFETY_LOCKOUT_MS) {
        // Reject command: cooldown still active
        return false; 
    }

    // Set state
    digitalWrite(pin, (state == 1) ? RELAY_ACTIVE_STATE : RELAY_INACTIVE_STATE);
    
    // Update last toggle timestamp
    last_relay_toggle_ms[idx] = current_time;
    
    return true;
}

bool setRelayState(const char* applianceName, int state) {
    if (strcmp(applianceName, "Light") == 0) {
        return setRelayStateByPin(RELAY_LIGHT_PIN, state);
    } else if (strcmp(applianceName, "TV") == 0) {
        return setRelayStateByPin(RELAY_TV_PIN, state);
    } else if (strcmp(applianceName, "Fridge") == 0) {
        return setRelayStateByPin(RELAY_FRIDGE_PIN, state);
    } else if (strcmp(applianceName, "Fan") == 0) {
        return setRelayStateByPin(RELAY_FAN_PIN, state);
    }
    return false; // Unknown appliance name
}

int getRelayState(int pin) {
    return digitalRead(pin) == HIGH ? 1 : 0;
}
