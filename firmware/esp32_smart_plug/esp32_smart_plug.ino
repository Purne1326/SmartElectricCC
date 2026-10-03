#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "esp_wifi.h"

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
unsigned long last_csi_pub_time = 0;
unsigned long last_mqtt_reconnect_time = 0;

// WiFi CSI Spatial Presence Sensing Variables
static float csi_amplitude_variance = 0.0;
static int detected_zone = 0; // 0 = vacant, 1..4 = zones
static float estimated_pos_x = -1.0; // -1 = vacant

// ESP32 Wi-Fi CSI Subcarrier Rx Callback
void _esp_wifi_csi_cb(void *ctx, wifi_csi_info_t *info) {
    if (!info || !info->buf) return;
    
    int8_t *csi_buf = (int8_t *)info->buf;
    int len = info->len;
    
    // Calculate subcarrier magnitude variance to detect human Doppler/phase shift
    double sum_mag = 0.0;
    double sum_sq_mag = 0.0;
    int count = len / 2;
    
    if (count <= 0) return;
    
    for (int i = 0; i < len; i += 2) {
        int8_t real = csi_buf[i];
        int8_t imag = csi_buf[i + 1];
        double mag = sqrt(real * real + imag * imag);
        sum_mag += mag;
        sum_sq_mag += mag * mag;
    }
    
    double mean_mag = sum_mag / count;
    double var = (sum_sq_mag / count) - (mean_mag * mean_mag);
    csi_amplitude_variance = 0.85f * csi_amplitude_variance + 0.15f * (float)var;
    
    // Zonal presence thresholding across 3.2m table span (Node 1 @ 0m, Node 2 @ 3.2m)
    // High variance (> 25.0) indicates human movement disturbing the 2.4GHz RF subcarriers
    if (csi_amplitude_variance > 25.0f) {
        // Map RSSI ratio to distance (0.0m to 3.2m)
        int rssi = info->rx_ctrl.rssi;
        float dist = map(rssi, -85, -30, 32, 0) / 10.0f;
        if (dist < 0.0f) dist = 0.4f;
        if (dist > 3.2f) dist = 2.8f;
        
        estimated_pos_x = dist;
        if (dist <= 0.8f) detected_zone = 1;
        else if (dist <= 1.6f) detected_zone = 2;
        else if (dist <= 2.4f) detected_zone = 3;
        else detected_zone = 4;
    } else {
        detected_zone = 0;
        estimated_pos_x = -1.0f; // Vacant
    }
}

void initWiFiCSI() {
    wifi_csi_config_t csi_config = {
        .lltf_en = true,
        .htft_en = true,
        .stbc_htltf2_en = true,
        .ltf2_en = true,
        .rx_filter_info_en = true,
        .channel_filter_en = false,
        .manu_scale = false,
        .shift = false
    };
    
    esp_wifi_set_csi_config(&csi_config);
    esp_wifi_set_csi_rx_cb(_esp_wifi_csi_cb, NULL);
    esp_wifi_set_csi(true);
    Serial.println("✅ ESP32 Wi-Fi CSI Subcarrier Spatial Sensing Engine initialized!");
}

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

    // Initialize ESP32 Wi-Fi CSI spatial sensing engine
    initWiFiCSI();
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

    // Fast CSI Presence Telemetry Publisher (Every 200ms)
    unsigned long current_time = millis();
    if (current_time - last_csi_pub_time >= 200) {
        last_csi_pub_time = current_time;

        StaticJsonDocument<256> csiDoc;
        csiDoc["variance"] = csi_amplitude_variance;
        if (estimated_pos_x >= 0.0f) {
            csiDoc["position_x"] = estimated_pos_x;
            csiDoc["active_zone"] = detected_zone;
        } else {
            csiDoc["position_x"] = nullptr;
            csiDoc["active_zone"] = nullptr;
        }

        char csiBuffer[256];
        serializeJson(csiDoc, csiBuffer);
        mqttClient.publish("smartelectric/csi/data", csiBuffer);
    }

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