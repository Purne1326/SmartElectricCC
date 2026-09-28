#!/bin/bash
# 1-install-mosquitto.sh
# Installs and configures the Mosquitto MQTT Broker on the Jetson Nano.

set -e

echo "=== SmartElectric: Installing Mosquitto MQTT Broker ==="

# Update package lists
sudo apt-get update

# Install Mosquitto and client tools
sudo apt-get install -y mosquitto mosquitto-clients

# Enable Mosquitto to start on boot
sudo systemctl enable mosquitto

# Copy our custom configuration file
CONFIG_SRC="../backend/mosquitto.conf"
CONFIG_DEST="/etc/mosquitto/conf.d/smartelectric.conf"

if [ -f "$CONFIG_SRC" ]; then
    echo "Copying custom Mosquitto configuration..."
    sudo cp "$CONFIG_SRC" "$CONFIG_DEST"
else
    echo "Warning: Custom configuration not found at $CONFIG_SRC."
    echo "Creating a default custom configuration..."
    sudo tee "$CONFIG_DEST" > /dev/null <<EOF
listener 1883 0.0.0.0
allow_anonymous true
persistence true
persistence_location /var/lib/mosquitto/
EOF
fi

# Restart Mosquitto to apply config
echo "Restarting Mosquitto Broker..."
sudo systemctl restart mosquitto

echo "Mosquitto Broker status:"
sudo systemctl status mosquitto --no-pager | grep -E "Active:"

echo "=== Mosquitto installation complete! ==="
