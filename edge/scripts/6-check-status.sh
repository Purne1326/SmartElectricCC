#!/bin/bash
# 6-check-status.sh
# Summarizes system health and systemd daemon process logs for the SmartElectric gateway.

echo "=== SmartElectric: System Services Status ==="
echo "------------------------------------------------"

services=("smartelectric-worker.service" "smartelectric-api.service")

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo -e "\e[32m● $service - ACTIVE (Running)\e[0m"
    else
        echo -e "\e[31m○ $service - INACTIVE (Stopped)\e[0m"
    fi
    # Print the last 3 log entries from the journal
    echo "Last logs:"
    sudo journalctl -u "$service" -n 3 --no-pager | sed 's/^/  /'
    echo "------------------------------------------------"
done

# Check Mosquitto MQTT Broker
if systemctl is-active --quiet mosquitto; then
    echo -e "\e[32m● mosquitto.service - ACTIVE (Running)\e[0m"
else
    echo -e "\e[31m○ mosquitto.service - INACTIVE (Stopped)\e[0m"
fi
echo "------------------------------------------------"
echo "=== Health check complete ==="
