#!/bin/bash
# Install the BMO service on the Raspberry Pi

set -e

echo "🔧 Installing BMO service on device..."

ssh bmo << 'EOF'
cd /home/pi/bmo
echo "📥 Mise à jour du code sur le BMO..."
git fetch origin main
git reset --hard origin/main

echo "⚙️ Installation du service..."
sudo cp /home/pi/bmo/bmo.service /etc/systemd/system/bmo.service
sudo systemctl daemon-reload
sudo systemctl enable bmo.service
sudo systemctl restart bmo.service
echo "✅ Service BMO installé et démarré !"
EOF

echo "🤖 BMO will now launch automatically on boot!"
