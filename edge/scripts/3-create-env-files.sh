#!/bin/bash
# 3-create-env-files.sh
# Generates configuration environment templates for local and cloud environments.

set -e

echo "=== SmartElectric: Generating Configuration Templates ==="

# Local Backend Env
LOCAL_ENV_PATH="$(dirname "$0")/../backend/.env"
echo "Generating local edge environment file at $LOCAL_ENV_PATH..."
cat > "$LOCAL_ENV_PATH" <<EOF
# SmartElectric Local Edge Configuration
PORT=8000
HOST=0.0.0.0
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
DATABASE_URL=sqlite:///edge_iot.db
DEBUG=True

# Tariff configurations (₹ per kWh)
TARIFF_FLAT_RATE=7.0
TARIFF_SLAB_1_PRICE=4.50
TARIFF_SLAB_2_PRICE=6.50
TARIFF_SLAB_3_PRICE=8.00
EOF

# Cloud Server Env
CLOUD_ENV_PATH="$(dirname "$0")/../../cloud/.env"
echo "Generating remote cloud environment file at $CLOUD_ENV_PATH..."
cat > "$CLOUD_ENV_PATH" <<EOF
# SmartElectric Cloud Configuration
PORT=8000
HOST=0.0.0.0
# Change to your real PostgreSQL server connection URL in production
DATABASE_URL=postgresql://postgres:password@localhost:5432/smartelectric_cloud
DEBUG=False
EOF

echo "=== Environment configuration template generation complete! ==="
