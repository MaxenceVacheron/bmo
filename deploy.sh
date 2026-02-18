#!/bin/bash
# Deploy BMO code to GitHub and Raspberry Pi
set -e

# Configuration
# Set to specific IP if needed (e.g. "172.24.13.4"), or leave empty to use "bmo" alias from ssh config
# BMO_IP="172.24.13.4"
BMO_IP=""

if [ -n "$BMO_IP" ]; then
    SSH_TARGET="pi@$BMO_IP"
    GIT_REMOTE_URL="pi@$BMO_IP:/home/pi/bmo"
else
    SSH_TARGET="bmo"
    GIT_REMOTE_URL="pi@bmo:/home/pi/bmo"
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "🚀 Starting Deployment of branch [$CURRENT_BRANCH] to $SSH_TARGET..."

# 1. Push to GitHub (Source of Truth)
echo "☁️ Pushing to GitHub (origin $CURRENT_BRANCH)..."
git push origin $CURRENT_BRANCH

# 2. Prepare Raspberry Pi (Force Clean)
echo "🧹 Configuring Raspberry Pi environment..."
ssh $SSH_TARGET "sudo git config --global --add safe.directory /home/pi/bmo && echo \"pi ALL=(ALL) NOPASSWD: ALL\" | sudo tee /etc/sudoers.d/010_pi-nopasswd && cd /home/pi/bmo && git reset --hard HEAD && git clean -fd"

# 3. Push to Raspberry Pi
echo "📲 Pushing to BMO Device..."
# Ensure remote exists
if ! git remote | grep -q "^bmo-device$"; then
    git remote add bmo-device "$GIT_REMOTE_URL"
else
    git remote set-url bmo-device "$GIT_REMOTE_URL"
fi
git push bmo-device $CURRENT_BRANCH:main -f

# 4. Restart Service
echo "🔄 Restarting BMO Service..."
ssh $SSH_TARGET << 'EOF'
sudo systemctl stop bmo.service 2>/dev/null || true
cd /home/pi/bmo
# Ensure we are on main and up to date (redundant but safe)
# We push our local branch to remote main for simplicity on the device
git checkout -f main
git reset --hard HEAD
sudo systemctl daemon-reload
# Sync service files
sudo cp /home/pi/bmo/bmo.service /etc/systemd/system/bmo.service
# sudo cp /home/pi/bmo/bmo-mirror.service /etc/systemd/system/bmo-mirror.service
sudo systemctl daemon-reload
sudo systemctl restart bmo.service
echo "✅ Service restarted!"

# Update WiFi Config if present
if [ -f "/home/pi/bmo/wpa_supplicant.conf" ]; then
    echo "📶 Checking internet connectivity before WiFi update..."
    if ping -c 1 1.1.1.1 > /dev/null 2>&1; then
        echo "✅ Internet is already active. Skipping WiFi restart to avoid disconnection."
    else
        echo "📶 Updating WiFi configuration..."
        sudo cp /home/pi/bmo/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf
        sudo chmod 600 /etc/wpa_supplicant/wpa_supplicant.conf
        
        # Pre-emptive cleanup to avoid "FAIL"
        sudo killall wpa_supplicant 2>/dev/null || true
        sudo rm -f /var/run/wpa_supplicant/wlan0
        
        sudo wpa_cli -i wlan0 reconfigure || (echo "⚠️ wpa_cli failed, trying manual restart..." && sudo systemctl restart wpa_supplicant)
        echo "✅ WiFi configuration updated!"
    fi
fi

# Setup WiFi Check Cron Job
echo "🕒 Setting up WiFi check cron job..."
chmod +x /home/pi/bmo/wifi_check.sh
# Remove old entry if it exists and add new ones (every minute + on boot)
(sudo crontab -l 2>/dev/null | grep -v "wifi_check.sh"; echo "* * * * * /home/pi/bmo/wifi_check.sh >> /var/log/wifi_check.cron.log 2>&1"; echo "@reboot /home/pi/bmo/wifi_check.sh >> /var/log/wifi_check.cron.log 2>&1") | sudo crontab -
echo "✅ Cron jobs installed (Every minute + On Boot)!"

EOF

echo "🎉 Deployment Complete!"
echo "📋 Tailing logs (Ctrl+C to stop)..."
ssh $SSH_TARGET "sudo journalctl -u bmo.service -f -n 50"
