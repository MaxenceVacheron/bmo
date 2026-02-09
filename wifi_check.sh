#!/bin/bash

# Configuration
PING_TARGET="8.8.8.8"
INTERFACE="wlan0"
LOG_FILE="/var/log/wifi_check.log"

# Check connection
if ! ping -c 1 -W 5 $PING_TARGET > /dev/null; then
    echo "$(date): Network is unreachable. Attempting recovery..." >> $LOG_FILE
    
    # Level 1: Quick reconfigure
    wpa_cli -i $INTERFACE reconfigure
    sleep 5
    
    if ! ping -c 1 -W 5 $PING_TARGET > /dev/null; then
        echo "$(date): Level 1 failed. Level 2: Nuke & Restart Service..." >> $LOG_FILE
        killall wpa_supplicant 2>/dev/null || true
        rm -f /var/run/wpa_supplicant/$INTERFACE
        ip link set $INTERFACE down
        sleep 2
        ip link set $INTERFACE up
        sleep 2
        systemctl restart wpa_supplicant
        sleep 10
    fi
    
    if ! ping -c 1 -W 5 $PING_TARGET > /dev/null; then
        echo "$(date): Level 2 failed. Level 3: Manual wpa_supplicant fallback..." >> $LOG_FILE
        killall wpa_supplicant 2>/dev/null || true
        rm -f /var/run/wpa_supplicant/$INTERFACE
        wpa_supplicant -B -i $INTERFACE -c /etc/wpa_supplicant/wpa_supplicant.conf
        sleep 10
    fi
    
    # Final check
    if ping -c 1 -W 5 $PING_TARGET > /dev/null; then
        echo "$(date): SUCCESS - Connection restored!" >> $LOG_FILE
    else
        echo "$(date): CRITICAL - All recovery levels failed." >> $LOG_FILE
    fi
fi
