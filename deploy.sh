#!/bin/bash
# Deploy BMO code to the Raspberry Pi device

set -e

echo "🤖 Deploying BMO code to device..."

# SSH into the BMO device and pull latest changes
ssh bmo << 'EOF'
sudo systemctl stop bmo.service 2>/dev/null || true
# Kill both old and new python scripts
sudo pkill -9 -f bmo.py || true
sudo pkill -9 -f bmo_pygame.py || true

cd /home/pi/bmo
echo "📥 Mise à jour du code..."
git fetch
git reset --hard origin/main

echo "🔄 Redémarrage du service BMO..."
sudo systemctl daemon-reload
sudo systemctl restart bmo.service

# Check status briefly
sleep 2
systemctl status bmo.service --no-pager
EOF

echo "🎮 BMO is updated and running!"
