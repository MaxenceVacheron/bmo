#!/bin/bash
# Deploy BMO/AMO code to GitHub and Raspberry Pi
set -e

# --- TARGET SELECTION ---
TARGET="${1:-bmo}"

case "$TARGET" in
    bmo)
        DEVICE_IP="10.208.104.4"
        DEVICE_NAME="BMO"
        ;;
    amo)
        DEVICE_IP="10.208.104.104"
        DEVICE_NAME="AMO"
        ;;
    *)
        echo "❌ Unknown target: $TARGET"
        echo "Usage: ./deploy.sh [bmo|amo]"
        exit 1
        ;;
esac

SSH_TARGET="pi@$DEVICE_IP"
GIT_REMOTE_URL="pi@$DEVICE_IP:/home/pi/bmo"
GIT_REMOTE_NAME="${TARGET}-device"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "🚀 Starting Deployment of branch [$CURRENT_BRANCH] to $DEVICE_NAME ($SSH_TARGET)..."

# 1. Push to GitHub (Source of Truth)
echo "☁️ Pushing to GitHub (origin $CURRENT_BRANCH)..."
git push origin $CURRENT_BRANCH

# 2. Prepare Raspberry Pi (Force Clean)
echo "🧹 Configuring Raspberry Pi environment..."
ssh $SSH_TARGET "sudo git config --global --add safe.directory /home/pi/bmo && echo \"pi ALL=(ALL) NOPASSWD: ALL\" | sudo tee /etc/sudoers.d/010_pi-nopasswd && if [ ! -d /home/pi/bmo/.git ]; then mkdir -p /home/pi/bmo && cd /home/pi/bmo && git init && git config receive.denyCurrentBranch updateInstead; else cd /home/pi/bmo && git reset --hard HEAD 2>/dev/null; git clean -fd; fi"

# 3. Push to Raspberry Pi
echo "📲 Pushing to $DEVICE_NAME Device..."
# Ensure remote exists
if ! git remote | grep -q "^${GIT_REMOTE_NAME}$"; then
    git remote add "$GIT_REMOTE_NAME" "$GIT_REMOTE_URL"
else
    git remote set-url "$GIT_REMOTE_NAME" "$GIT_REMOTE_URL"
fi
git push "$GIT_REMOTE_NAME" $CURRENT_BRANCH:main -f

# 4. Write device identity file, install deps & Restart Service
echo "🔄 Configuring $DEVICE_NAME identity and restarting service..."
ssh $SSH_TARGET << EOF
# Write identity file
echo "$DEVICE_NAME" > /home/pi/bmo/.name

sudo systemctl stop bmo.service 2>/dev/null || true
cd /home/pi/bmo
# Ensure we are on main and up to date
git checkout -f main
git reset --hard HEAD

# Install Python dependencies if missing
if ! python3 -c "import pygame" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    sudo pip3 install pygame Pillow evdev --break-system-packages 2>/dev/null || sudo pip3 install pygame Pillow evdev
fi

# Install hostapd and dnsmasq for WiFi Setup mode
if ! dpkg -s hostapd dnsmasq > /dev/null 2>&1; then
    echo "📦 Installing hostapd and dnsmasq for WiFi Setup..."
    sudo apt-get install -y hostapd dnsmasq
    sudo systemctl disable hostapd 2>/dev/null || true
    sudo systemctl stop hostapd 2>/dev/null || true
    sudo systemctl disable dnsmasq 2>/dev/null || true
    sudo systemctl stop dnsmasq 2>/dev/null || true
fi

# Make WiFi setup script executable
chmod +x /home/pi/bmo/wifi_setup.sh

sudo systemctl daemon-reload
# Sync service files
sudo cp /home/pi/bmo/bmo.service /etc/systemd/system/bmo.service
sudo systemctl daemon-reload
sudo systemctl restart bmo.service
echo "✅ $DEVICE_NAME Service restarted!"

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

echo "🎉 $DEVICE_NAME Deployment Complete!"
echo "📋 Tailing logs (Ctrl+C to stop)..."
ssh $SSH_TARGET "sudo journalctl -u bmo.service -f -n 50"
