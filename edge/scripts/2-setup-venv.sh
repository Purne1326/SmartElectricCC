#!/bin/bash
# 2-setup-venv.sh
# Sets up a Python virtual environment and installs backend dependencies.

set -e

echo "=== SmartElectric: Setting up Python Virtual Environment ==="

# Navigate to the backend directory
cd "$(dirname "$0")/../backend"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies from requirements file
REQ_FILE="../../cloud/requirements.txt"
if [ -f "$REQ_FILE" ]; then
    echo "Installing core dependencies from requirements.txt..."
    pip install -r "$REQ_FILE"
else
    echo "Warning: requirements.txt not found at $REQ_FILE. Installing standard packages..."
    pip install fastapi uvicorn sqlalchemy paho-mqtt requests
fi

# Install PyTorch for Machine Learning forecasting features
# We install the CPU version by default to preserve RAM on the Jetson Nano (4GB)
echo "Installing PyTorch (CPU-only) for forecasting features..."
pip install torch --extra-index-url https://download.pytorch.org/whl/cpu

echo "=== Python virtual environment setup complete! ==="
echo "To activate manually, run: source edge/backend/.venv/bin/activate"
