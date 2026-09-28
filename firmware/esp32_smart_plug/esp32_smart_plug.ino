#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include "config.h"
#include "secrets.h"
#include "sensors.h"
#include "relays.h"

// Instantiate network clients
#if USE_HIVEMQ_CLOUD
WiFiClientSecure espClient;
const char* target_mqtt_server = MQTT_SERVER_IP;
#else
WiFiClient espClient;
const char* target_mqtt_server = MQTT_SERVER_IP;
#endif

PubSubClient mqttClient(espClient);

// Timing variables
unsigned long last_telemetry_time = 0;
unsigned long last_mqtt_reconnect_time = 0;

void setup_wifi() {
    delay(10);
    Serial.println();
    Serial.print("Connecting to Wi-Fi SSID: ");
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    randomSeed(micros());

    Serial.println("");
    Serial.println("Wi-Fi connected successfully!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}

// MQTT callback to handle incoming command messages
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Message arrived on topic [");
    Serial.print(topic);
    Serial.println("] ");

    // Parse payload into JSON
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, payload, length);

    if (error) {
        Serial.print("JSON deserialization failed: ");
        Serial.println(error.c_str());
        return;
    }

    // Process relay control commands
    if (strcmp(topic, "smartelectric/control/relay") == 0) {
        const char* appliance = doc["appliance"];
        int state = doc["state"];

        if (appliance != NULL) {
            Serial.printf("Received relay control command: %s -> %d\n", appliance, state);
            
            // Execute state change with safety checks
            bool success = setRelayState(appliance, state);
            
            // Publish acknowledgement log back to broker
            StaticJsonDocument<256> logDoc;
            char logBuffer[256];
            
            if (success) {
                logDoc["level"] = "INFO";
                logDoc["message"] = String("Successfully set relay for ") + appliance + " to " + (state == 1 ? "ON" : "OFF");
            } else {
                logDoc["level"] = "WARNING";
                logDoc["message"] = String("Rejected relay command for ") + appliance + " (lockout active or invalid name)";
            }
            
            serializeJson(logDoc, logBuffer);
            mqttClient.publish("smartelectric/logs", logBuffer);
        }
    }
}

void reconnect_mqtt() {
    unsigned long current_time = millis();
    // Only attempt to reconnect every 5 seconds to avoid blocking the main loop
    if (current_time - last_mqtt_reconnect_time >= 5000) {
        last_mqtt_reconnect_time = current_time;
        Serial.print("Attempting MQTT connection to ");
        Serial.print(target_mqtt_server);
        Serial.print(":");
        Serial.print(MQTT_PORT);
        Serial.print("...");
        
        // Create a unique client ID using ESP32 MAC address
        String clientId = "SmartElectric-ESP32-Client-";
        clientId += String(WiFi.macAddress());
        
        // Attempt to connect
        bool connected = false;
        if (strlen(MQTT_USER) > 0) {
            connected = mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASS);
        } else {
            connected = mqttClient.connect(clientId.c_str());
        }

        if (connected) {
            Serial.println("connected!");
            // Once connected, publish boot log
            StaticJsonDocument<128> bootDoc;
            bootDoc["level"] = "INFO";
            bootDoc["message"] = "ESP32 Firmware booted and connected to broker.";
            char bootBuffer[128];
            serializeJson(bootDoc, bootBuffer);
            mqttClient.publish("smartelectric/logs", bootBuffer);
            
            // Resubscribe to control topic
            mqttClient.subscribe("smartelectric/control/relay");
        } else {
            Serial.print("failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" will try again in 5 seconds");
        }
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("SmartElectric ESP32 Firmware Starting...");

    // Initialize relays first (safety: force low state immediately)
    initRelays();

    // Hardware Relay Self-Test: Cycle each relay for 300ms on boot for instant physical verification
    Serial.println("Running Relay Hardware Self-Test...");
    const char* testAppliances[] = {"Light", "TV", "Fridge", "Fan"};
    for (int i = 0; i < 4; i++) {
        setRelayState(testAppliances[i], 1);
        delay(300);
        setRelayState(testAppliances[i], 0);
        delay(100);
    }
    Serial.println("Relay Self-Test Complete!");

    // Initialize sensors
    initSensors();

    // Configure WiFi connection
    setup_wifi();

    #if USE_HIVEMQ_CLOUD
    espClient.setCACert(HIVEMQ_CA_CERT); // Apply Let's Encrypt ISRG Root X1 CA for HiveMQ Cloud TLS
    #endif

    // Configure MQTT Broker settings
    mqttClient.setServer(target_mqtt_server, MQTT_PORT);
    mqttClient.setCallback(mqtt_callback);
}

void loop() {
    // Ensure WiFi and MQTT connections are maintained
    if (WiFi.status() != WL_CONNECTED) {
        setup_wifi();
    }
    
    if (!mqttClient.connected()) {
        reconnect_mqtt();
    }
    
    mqttClient.loop();

    // Telemetry Publishing Loop (Non-blocking timer)
    unsigned long current_time = millis();
    if (current_time - last_telemetry_time >= TELEMETRY_INTERVAL_MS) {
        last_telemetry_time = current_time;

        // 1. Read SCT-013 current values directly from physical sensors
        double current_light  = readCurrentRMS(SENSOR_LIGHT_PIN)  * LIGHT_SCALE_FACTOR;
        double current_tv     = readCurrentRMS(SENSOR_TV_PIN)     * TV_SCALE_FACTOR;
        double current_fridge = readCurrentRMS(SENSOR_FRIDGE_PIN) * FRIDGE_SCALE_FACTOR;
        double current_fan    = readCurrentRMS(SENSOR_FAN_PIN)    * FAN_SCALE_FACTOR;

        // Construct current telemetry JSON payload
        StaticJsonDocument<512> currentDoc;
        currentDoc["Light_Amps"] = current_light;
        currentDoc["Light_Watts"] = current_light * GRID_VOLTAGE;
        currentDoc["TV_Amps"] = current_tv;
        currentDoc["TV_Watts"] = current_tv * GRID_VOLTAGE;
        currentDoc["Fridge_Amps"] = current_fridge;
        currentDoc["Fridge_Watts"] = current_fridge * GRID_VOLTAGE;
        currentDoc["Fan_Amps"] = current_fan;
        currentDoc["Fan_Watts"] = current_fan * GRID_VOLTAGE;
        currentDoc["voltage"] = GRID_VOLTAGE;

        char currentBuffer[512];
        serializeJson(currentDoc, currentBuffer);
        mqttClient.publish("smartelectric/sensors/current", currentBuffer);

        // 2. Read BME280 temperature and humidity values, along with PIR and LDR
        float temperature = 0.0;
        float humidity = 0.0;
        bool bme_success = readBME280(temperature, humidity);
        int pir_val = readPIR();
        float ldr_val = readLDR();

        if (bme_success) {
            StaticJsonDocument<256> dhtDoc;
            dhtDoc["temperature"] = temperature;
            dhtDoc["humidity"] = humidity;
            dhtDoc["pir"] = pir_val;
            dhtDoc["ldr"] = ldr_val;

            char dhtBuffer[256];
            serializeJson(dhtDoc, dhtBuffer);
            mqttClient.publish("smartelectric/sensors/dht", dhtBuffer);
        } else {
            StaticJsonDocument<128> errDoc;
            errDoc["level"] = "WARNING";
            errDoc["message"] = "BME280 sensor reading failed!";
            char errBuffer[128];
            serializeJson(errDoc, errBuffer);
            mqttClient.publish("smartelectric/logs", errBuffer);
            Serial.println("BME280 Sensor reading failed!");
        }
        
        // Output debug to serial console
        Serial.printf("Telemetry Sent - Current (A) -> Light: %.3f, TV: %.3f, Fridge: %.3f, Fan: %.3f. DHT -> Temp: %.1f C, Hum: %.1f%%\n",
                      current_light, current_tv, current_fridge, current_fan, temperature, humidity);
    }
}