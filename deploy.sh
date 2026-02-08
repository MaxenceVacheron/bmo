#!/bin/bash
# Deploy BMO code to the Raspberry Pi device

set -e

echo "🤖 Deploying BMO code to device..."

# Check if bmo-device remote exists
if ! git remote | grep -q "^bmo-device$"; then
    echo "🔗 Adding bmo-device remote..."
    git remote add bmo-device pi@bmo:/home/pi/bmo
fi

# Ensure Pi is ready to receive
ssh bmo "cd /home/pi/bmo && git init && git config receive.denyCurrentBranch updateInstead"

echo "📤 Pushing code to BMO..."
git push bmo-device main:main -f

# Finalize on device
ssh bmo << 'EOF'
sudo systemctl stop bmo.service 2>/dev/null || true
cd /home/pi/bmo
git checkout -f main
echo "🔄 Redémarrage du service BMO..."
sudo systemctl daemon-reload
sudo systemctl restart bmo.service
echo "📋 Affichage des logs (Ctrl+C pour arrêter)..."
sudo journalctl -u bmo.service -f -n 20
EOF

echo "🎮 BMO is updated and running!"
