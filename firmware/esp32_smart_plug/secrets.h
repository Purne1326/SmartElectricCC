#ifndef SECRETS_H
#define SECRETS_H

// WiFi Configuration
#define WIFI_SSID "CSE_AIML_IEDC"
#define WIFI_PASSWORD "#AIML_IEDC@UEM-304#"

// HiveMQ Cloud MQTT Configuration
// Set this to your HiveMQ Cloud Cluster URL (e.g. xxxxx.s1.eu.hivemq.cloud)
#define MQTT_SERVER_IP "265aefae9e544fb5bddce420a89fb4b3.s1.eu.hivemq.cloud"
#define MQTT_PORT 8883

// HiveMQ Cloud Authentication Credentials
#define MQTT_USER "SmartElectric"
#define MQTT_PASS "rassp123#"

// HiveMQ Cloud Let's Encrypt ISRG Root X1 Root CA Certificate
const char* HIVEMQ_CA_CERT = \
"-----BEGIN CERTIFICATE-----\n" \
"MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw\n" \
"TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh\n" \
"cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4\n" \
"WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu\n" \
"ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY\n" \
"MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJErDunmHMrvh0U1J\n" \
"nMpvahJuE34D0vPye6DCHcKfUiVhs6n7wVzwxmE28g0bX1Etlku3v28fZHnEGGLS\n" \
"myy4Vkcg14F4n809gWwM2A//a3yvF6w1vB/cK0rLdK141kP6sC27j0P/F8W2A2a/\n" \
"Hg8h8nB4s5qE8lq6d3S6+G12d8T8JtFmHn2fK1S6Kz2gV3bF8qYh6g7x3L0l9wK/\n" \
"-----END CERTIFICATE-----\n";

#endif // SECRETS_H