#!/bin/bash
# Deploy BMO code to GitHub and Raspberry Pi
set -e

echo "🚀 Starting Deployment..."

# 1. Push to GitHub (Source of Truth)
echo "☁️ Pushing to GitHub (origin main)..."
git push origin main

# 2. Prepare Raspberry Pi (Force Clean)
echo "🧹 Cleaning Raspberry Pi workspace..."
ssh bmo "cd /home/pi/bmo && git reset --hard HEAD && git clean -fd"

# 3. Push to Raspberry Pi
echo "📲 Pushing to BMO Device..."
# Ensure remote exists
if ! git remote | grep -q "^bmo-device$"; then
    git remote add bmo-device pi@bmo:/home/pi/bmo
fi
git push bmo-device main:main -f

# 4. Restart Service
echo "🔄 Restarting BMO Service..."
ssh bmo << 'EOF'
sudo systemctl stop bmo.service 2>/dev/null || true
cd /home/pi/bmo
# Ensure we are on main and up to date (redundant but safe)
git checkout -f main
git reset --hard HEAD
sudo systemctl daemon-reload
sudo systemctl restart bmo.service
echo "✅ Service restarted!"
EOF

echo "🎉 Deployment Complete!"
echo "📋 Tailing logs (Ctrl+C to stop)..."
ssh bmo "sudo journalctl -u bmo.service -f -n 50"
