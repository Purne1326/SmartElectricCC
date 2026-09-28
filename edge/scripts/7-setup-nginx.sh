#!/bin/bash
# 7-setup-nginx.sh
# Installs and configures NGINX to serve the static frontend and reverse proxy the API.

set -e

echo "=== SmartElectric: Setting up NGINX Reverse Proxy ==="

# Get absolute path of project root
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND_STATIC_DIR="$PROJECT_ROOT/edge/frontend_static"

echo "Detected Project Root: $PROJECT_ROOT"
echo "Frontend Static Directory: $FRONTEND_STATIC_DIR"

if [ ! -d "$FRONTEND_STATIC_DIR" ]; then
    echo "Error: Frontend static directory not found at $FRONTEND_STATIC_DIR"
    exit 1
fi

# Update package lists and install NGINX
sudo apt-get update
sudo apt-get install -y nginx

# Create NGINX configuration
NGINX_CONF_PATH="/etc/nginx/sites-available/smartelectric"

echo "Configuring NGINX server block..."
sudo tee "$NGINX_CONF_PATH" > /dev/null <<EOF
server {
    listen 80;
    server_name _; # Respond to any IP/hostname

    # Route /api to the FastAPI backend running on localhost:8000
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_addrs;
    }

    # Serve the static frontend (HTML/JS/CSS)
    location / {
        root $FRONTEND_STATIC_DIR;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

# Enable the configuration by linking to sites-enabled
if [ -L /etc/nginx/sites-enabled/smartelectric ]; then
    sudo rm /etc/nginx/sites-enabled/smartelectric
fi
sudo ln -s "$NGINX_CONF_PATH" /etc/nginx/sites-enabled/

# Remove default NGINX configuration if it exists
if [ -L /etc/nginx/sites-enabled/default ]; then
    sudo rm /etc/nginx/sites-enabled/default
fi

# Test NGINX configuration
sudo nginx -t

# Restart NGINX to apply changes
echo "Restarting NGINX..."
sudo systemctl restart nginx
sudo systemctl enable nginx

echo "=== NGINX setup complete! ==="
echo "You can now access the SmartElectric application via the Jetson Nano's IP address on port 80."
