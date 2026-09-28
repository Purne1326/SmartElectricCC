#ifndef SECRETS_H
#define SECRETS_H

// WiFi Configuration
#define WIFI_SSID "SmartElectric_WiFi"
#define WIFI_PASSWORD "SuperSecretWiFiPass"

// MQTT Configuration
// Set this to the static IP address of the Jetson Nano on your local WiFi network
#define MQTT_SERVER_IP "192.168.1.100"

// MQTT Authentication Credentials (if broker authentication is enabled)
#define MQTT_USER ""
#define MQTT_PASS ""

#endif // SECRETS_H
