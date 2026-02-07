#!/bin/bash
# Install the BMO service on the Raspberry Pi

set -e

echo "🔧 Installing BMO service on device..."

ssh bmo << 'EOF'
sudo cp /home/pi/bmo/bmo.service /etc/systemd/system/bmo.service
sudo systemctl daemon-reload
sudo systemctl enable bmo.service
sudo systemctl restart bmo.service
echo "✅ BMO service installed and started!"
EOF

echo "🤖 BMO will now launch automatically on boot!"
