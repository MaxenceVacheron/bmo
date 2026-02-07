#!/bin/bash
# Deploy BMO code to the Raspberry Pi device

set -e

echo "🤖 Deploying BMO code to device..."

# SSH into the BMO device and pull latest changes
ssh bmo << 'EOF'
cd /home/pi/bmo
echo "📥 Resetting to latest code..."
git fetch
git reset --hard origin/main

if systemctl is-enabled --quiet bmo.service 2>/dev/null; then
    echo "🔄 Restarting BMO service..."
    sudo systemctl restart bmo.service
else
    echo "🚀 Service not active, starting BMO manually..."
    sudo python3 /home/pi/bmo/bmo.py
fi
EOF

echo "🎮 BMO is running!"
