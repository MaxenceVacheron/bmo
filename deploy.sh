#!/bin/bash
# Deploy BMO code to GitHub and Raspberry Pi
set -e

# Configuration
# Set to specific IP if needed (e.g. "172.24.13.4"), or leave empty to use "bmo" alias from ssh config
BMO_IP="172.24.13.4"

if [ -n "$BMO_IP" ]; then
    SSH_TARGET="pi@$BMO_IP"
    GIT_REMOTE_URL="pi@$BMO_IP:/home/pi/bmo"
else
    SSH_TARGET="bmo"
    GIT_REMOTE_URL="pi@bmo:/home/pi/bmo"
fi

echo "🚀 Starting Deployment to $SSH_TARGET..."

# 1. Push to GitHub (Source of Truth)
echo "☁️ Pushing to GitHub (origin main)..."
git push origin main

# 2. Prepare Raspberry Pi (Force Clean)
echo "🧹 Cleaning Raspberry Pi workspace..."
ssh $SSH_TARGET "cd /home/pi/bmo && git reset --hard HEAD && git clean -fd"

# 3. Push to Raspberry Pi
echo "📲 Pushing to BMO Device..."
# Ensure remote exists
if ! git remote | grep -q "^bmo-device$"; then
    git remote add bmo-device "$GIT_REMOTE_URL"
else
    git remote set-url bmo-device "$GIT_REMOTE_URL"
fi
git push bmo-device main:main -f

# 4. Restart Service
echo "🔄 Restarting BMO Service..."
ssh $SSH_TARGET << 'EOF'
sudo systemctl stop bmo.service 2>/dev/null || true
cd /home/pi/bmo
# Ensure we are on main and up to date (redundant but safe)
git checkout -f main
git reset --hard HEAD
sudo systemctl daemon-reload
sudo systemctl restart bmo.service
echo "✅ Service restarted!"

# Update WiFi Config if present
if [ -f "/home/pi/bmo/wpa_supplicant.conf" ]; then
    echo "📶 Updating WiFi configuration..."
    sudo cp /home/pi/bmo/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf
    sudo chmod 600 /etc/wpa_supplicant/wpa_supplicant.conf
    sudo wpa_cli -i wlan0 reconfigure
    echo "✅ WiFi configuration updated!"
fi

# Setup WiFi Check Cron Job
echo "🕒 Setting up WiFi check cron job..."
chmod +x /home/pi/bmo/wifi_check.sh
if ! sudo crontab -l 2>/dev/null | grep -F "wifi_check.sh"; then
    (sudo crontab -l 2>/dev/null; echo "* * * * * /home/pi/bmo/wifi_check.sh >> /var/log/wifi_check.cron.log 2>&1") | sudo crontab -
    echo "✅ Cron job installed!"
else
    echo "ℹ️ Cron job already exists."
fi

EOF

echo "🎉 Deployment Complete!"
echo "📋 Tailing logs (Ctrl+C to stop)..."
ssh $SSH_TARGET "sudo journalctl -u bmo.service -f -n 50"
