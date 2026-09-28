#!/bin/bash
# 5-start-all.sh
# Starts all SmartElectric background processes on the Jetson Nano edge gateway.

set -e

echo "=== SmartElectric: Starting Background Services ==="

services=("smartelectric-worker.service" "smartelectric-api.service")

for service in "${services[@]}"; do
    echo "Starting $service..."
    sudo systemctl restart "$service"
done

echo "Waiting for services to initialize..."
sleep 2

# Check status using the status checker script
"$(dirname "$0")/6-check-status.sh"

echo "=== All services successfully initiated! ==="
