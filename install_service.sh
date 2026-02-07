#!/bin/bash
# Install the BMO service on the Raspberry Pi

set -e

echo "🔧 Installing BMO service on device..."

ssh bmo << 'EOF'
cd /home/pi/bmo
echo "📥 Mise à jour du code sur le BMO..."
git fetch origin main
git reset --hard origin/main

echo "⚙️ Installation des services..."
sudo cp /home/pi/bmo/bmo.service /etc/systemd/system/bmo.service
sudo cp /home/pi/bmo/bmo-mirror.service /etc/systemd/system/bmo-mirror.service
sudo systemctl daemon-reload
sudo systemctl enable bmo.service
sudo systemctl enable bmo-mirror.service
sudo systemctl restart bmo.service
# Don't restart mirror yet as we need to reboot for GPU
echo "✅ Services BMO installés !"
EOF

echo "🤖 BMO will now launch automatically on boot!"
