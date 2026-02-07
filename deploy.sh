#!/bin/bash
# Deploy BMO code to the Raspberry Pi device

set -e

echo "🤖 Deploying BMO code to device..."

# SSH into the BMO device and pull latest changes
ssh bmo << 'EOF'
echo "🧹 Nettoyage des anciens processus..."
sudo systemctl stop bmo.service 2>/dev/null || true
sudo pkill -9 -f bmo.py || true

cd /home/pi/bmo
echo "📥 Mise à jour du code..."
git fetch
git reset --hard origin/main

if systemctl is-enabled --quiet bmo.service 2>/dev/null; then
    echo "🔄 Redémarrage du service BMO..."
    sudo systemctl start bmo.service
else
    echo "🚀 Service non actif, lancement manuel..."
    sudo python3 /home/pi/bmo/bmo.py
fi
EOF

echo "🎮 BMO is running!"
