#!/bin/bash
# Enable maximal power saving
echo "🔋 Enabling Power Save Mode..."

# 1. Disable HDMI output
echo "📺 Keeping HDMI active (Power save modified)..."
# sudo vcgencmd display_power 0 || true

# 2. Disable LEDs (ACT and PWR)
echo "💡 Disabling LEDs..."
# ACT LED
if [ -e /sys/class/leds/ACT ]; then
    echo 0 | sudo tee /sys/class/leds/ACT/brightness > /dev/null
    echo "none" | sudo tee /sys/class/leds/ACT/trigger > /dev/null
elif [ -e /sys/class/leds/led0 ]; then
    echo 0 | sudo tee /sys/class/leds/led0/brightness > /dev/null
    echo "none" | sudo tee /sys/class/leds/led0/trigger > /dev/null
fi
# PWR LED
if [ -e /sys/class/leds/PWR ]; then
    echo 0 | sudo tee /sys/class/leds/PWR/brightness > /dev/null
    echo "none" | sudo tee /sys/class/leds/PWR/trigger > /dev/null
elif [ -e /sys/class/leds/led1 ]; then
    echo 0 | sudo tee /sys/class/leds/led1/brightness > /dev/null
    echo "none" | sudo tee /sys/class/leds/led1/trigger > /dev/null
fi

# 3. Disable Bluetooth
echo "📡 Disabling Bluetooth..."
sudo systemctl stop bluetooth.service || true
sudo systemctl disable bluetooth.service || true

echo "✅ Power Save Mode Active."
