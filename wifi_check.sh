#!/bin/bash

# Configuration
PING_TARGET="8.8.8.8"
INTERFACE="wlan0"
LOG_FILE="/var/log/wifi_check.log"

# Check connection
if ! ping -c 1 -W 5 $PING_TARGET > /dev/null; then
    echo "$(date): Network is unreachable. Attempting to reconnect $INTERFACE..." >> $LOG_FILE
    
    # Method 1: Reconfigure wpa_supplicant
    wpa_cli -i $INTERFACE reconfigure
    
    # Wait and check again
    sleep 10
    if ! ping -c 1 -W 5 $PING_TARGET > /dev/null; then
        echo "$(date): Still unreachable. Hard resetting interface..." >> $LOG_FILE
        ip link set $INTERFACE down
        sleep 5
        ip link set $INTERFACE up
        sleep 10
        # Ensure dhcpcd picks it up if needed, or just wait for wpa_supplicant
    fi
    
    echo "$(date): Reconnection attempt finished." >> $LOG_FILE
fi
