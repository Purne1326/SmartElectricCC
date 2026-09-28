#!/bin/bash
# 8-setup-log-rotation.sh
# Hardens systemd logging to prevent journalctl from filling the Jetson Nano's SD card.

set -e

echo "=== SmartElectric: Hardening Systemd Logging ==="

JOURNALD_CONF="/etc/systemd/journald.conf"

echo "Configuring log limits in $JOURNALD_CONF..."

# Uncomment or replace the SystemMaxUse line
sudo sed -i 's/^#SystemMaxUse=.*/SystemMaxUse=200M/' "$JOURNALD_CONF" || true
if ! grep -q "^SystemMaxUse=" "$JOURNALD_CONF"; then
    echo "SystemMaxUse=200M" | sudo tee -a "$JOURNALD_CONF" > /dev/null
fi

# Uncomment or replace the SystemKeepFree line
sudo sed -i 's/^#SystemKeepFree=.*/SystemKeepFree=500M/' "$JOURNALD_CONF" || true
if ! grep -q "^SystemKeepFree=" "$JOURNALD_CONF"; then
    echo "SystemKeepFree=500M" | sudo tee -a "$JOURNALD_CONF" > /dev/null
fi

# Uncomment or replace the MaxRetentionSec line
sudo sed -i 's/^#MaxRetentionSec=.*/MaxRetentionSec=1month/' "$JOURNALD_CONF" || true
if ! grep -q "^MaxRetentionSec=" "$JOURNALD_CONF"; then
    echo "MaxRetentionSec=1month" | sudo tee -a "$JOURNALD_CONF" > /dev/null
fi

echo "Restarting systemd-journald to apply changes..."
sudo systemctl restart systemd-journald

echo "=== Log rotation setup complete! ==="
