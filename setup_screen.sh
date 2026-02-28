#!/bin/bash
# Setup SPI TFT 3.5" screen on a fresh Raspberry Pi
# Usage: ./setup_screen.sh [ip_address]
# Example: ./setup_screen.sh 10.208.104.104
set -e

PI_IP="${1:-10.208.104.104}"
SSH_TARGET="pi@$PI_IP"

echo "🖥️  Setting up SPI TFT screen on $SSH_TARGET..."

ssh $SSH_TARGET << 'SETUP_EOF'
CONFIG="/boot/firmware/config.txt"

echo "📋 Current config.txt dtoverlays:"
grep -i dtoverlay "$CONFIG" || true

# 1. Switch from vc4-kms-v3d to vc4-fkms-v3d (required for fb1)
if grep -q "dtoverlay=vc4-kms-v3d" "$CONFIG"; then
    echo "🔧 Switching vc4-kms-v3d → vc4-fkms-v3d..."
    sudo sed -i 's/dtoverlay=vc4-kms-v3d/dtoverlay=vc4-fkms-v3d/' "$CONFIG"
else
    echo "✅ Already using vc4-fkms-v3d (or not set)"
fi

# 2. Add tft35a overlay if not present
if ! grep -q "dtoverlay=tft35a" "$CONFIG"; then
    echo "🔧 Adding TFT 3.5\" overlay..."
    echo "" | sudo tee -a "$CONFIG" > /dev/null
    echo "# SPI TFT 3.5\" Screen" | sudo tee -a "$CONFIG" > /dev/null
    echo "dtoverlay=tft35a:rotate=90,speed=42000000,fps=30" | sudo tee -a "$CONFIG" > /dev/null
else
    echo "✅ tft35a overlay already present"
fi

# 3. Enable SPI if not already
if ! grep -q "^dtparam=spi=on" "$CONFIG"; then
    echo "🔧 Enabling SPI..."
    # Check if it's commented out
    if grep -q "#dtparam=spi=on" "$CONFIG"; then
        sudo sed -i 's/#dtparam=spi=on/dtparam=spi=on/' "$CONFIG"
    else
        echo "dtparam=spi=on" | sudo tee -a "$CONFIG" > /dev/null
    fi
else
    echo "✅ SPI already enabled"
fi

echo ""
echo "📋 Updated config.txt dtoverlays:"
grep -i "dtoverlay\|dtparam=spi" "$CONFIG" || true

echo ""
echo "⚠️  A reboot is required for changes to take effect."
SETUP_EOF

echo ""
read -p "🔄 Reboot $SSH_TARGET now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Rebooting..."
    ssh $SSH_TARGET "sudo reboot" || true
    echo "⏳ Waiting 30s for Pi to come back..."
    sleep 30
    echo "🔍 Checking if Pi is back..."
    if ssh -o ConnectTimeout=10 $SSH_TARGET "echo '✅ Pi is back! Checking /dev/fb1...' && ls -la /dev/fb1 2>/dev/null && echo '✅ /dev/fb1 found!' || echo '❌ /dev/fb1 not found yet (may need more time)'"; then
        echo "🎉 Screen setup complete!"
    else
        echo "⏳ Pi might still be booting. Try: ssh $SSH_TARGET 'ls /dev/fb1'"
    fi
else
    echo "⚠️  Remember to reboot the Pi manually: ssh $SSH_TARGET 'sudo reboot'"
fi
