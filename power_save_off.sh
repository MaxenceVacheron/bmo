#!/bin/bash
# Restore default power settings
echo "🏠 Restoring Default Power Mode..."

# 1. Enable HDMI output
echo "📺 Enabling HDMI..."
sudo tvservice -p || true

# 2. Re-enable LEDs (ACT and PWR)
echo "💡 Enabling LEDs..."
# ACT LED
if [ -e /sys/class/leds/led0 ]; then
    echo "mmc0" | sudo tee /sys/class/leds/led0/trigger > /dev/null
fi
# PWR LED
if [ -e /sys/class/leds/led1 ]; then
    echo "default-on" | sudo tee /sys/class/leds/led1/trigger > /dev/null
fi

# 3. Enable Bluetooth
echo "📡 Enabling Bluetooth..."
sudo systemctl start bluetooth.service || true
sudo systemctl enable bluetooth.service || true

echo "✅ Default Power Mode Restored."
