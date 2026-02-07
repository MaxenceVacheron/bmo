#!/bin/bash
# Deploy BMO code to the Raspberry Pi device

set -e

echo "🤖 Deploying BMO code to device..."

# SSH into the BMO device and pull latest changes
ssh bmo << 'EOF'
cd /home/pi/bmo
echo "📥 Resetting to latest code..."
git reset --hard origin/main
echo "🚀 Starting BMO..."
sudo python3 /home/pi/bmo/bmo.py
EOF

echo "🎮 BMO is running!"
