#!/bin/bash
# 4-setup-systemd.sh
# Registers the SmartElectric MQTT worker, API backend, and dashboard as systemd services.

set -e

echo "=== SmartElectric: Registering Systemd Services ==="

# Get absolute path of project root (which is parent of edge/scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
echo "Detected Project Root: $PROJECT_ROOT"

SYSTEMD_DIR="$PROJECT_ROOT/edge/systemd"
TARGET_DIR="/etc/systemd/system"

# Ensure systemd folder exists in our package
if [ ! -d "$SYSTEMD_DIR" ]; then
    echo "Error: Systemd templates not found at $SYSTEMD_DIR"
    exit 1
fi

services=("smartelectric-worker.service" "smartelectric-api.service")

for service in "${services[@]}"; do
    echo "Configuring and registering $service..."
    
    # Read service content, replace '/home/jetson/smartelectric' with actual PROJECT_ROOT path,
    # and write directly to /etc/systemd/system/
    sed "s|/home/jetson/smartelectric|$PROJECT_ROOT|g" "$SYSTEMD_DIR/$service" | sudo tee "$TARGET_DIR/$service" > /dev/null
    
    # Reload and enable the service
    sudo systemctl enable "$service"
done

# Reload systemd daemon to pick up the new unit configurations
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "=== Systemd services registered successfully! ==="
echo "You can now start services using 5-start-all.sh"
