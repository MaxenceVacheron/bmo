#!/bin/bash

# Configuration
PING_TARGET="8.8.8.8"
INTERFACE="wlan0"
LOG_FILE="/var/log/wifi_check.log"

# Check connection
if ! ping -c 1 -W 5 $PING_TARGET > /dev/null; then
    echo "------------------------------------------" >> $LOG_FILE
    echo "$(date): [CHECK] Network is unreachable. Starting recovery..." >> $LOG_FILE
    
    # Log current status for debugging
    echo "$(date): [DEBUG] Current IP: $(ip -4 addr show $INTERFACE | grep inet | awk '{print $2}')" >> $LOG_FILE
    echo "$(date): [DEBUG] WiFi Status: $(iwconfig $INTERFACE | grep ESSID)" >> $LOG_FILE
    
    # Level 1: Quick reconfigure
    echo "$(date): [LEVEL 1] Attempting wpa_cli reconfigure..." >> $LOG_FILE
    wpa_cli -i $INTERFACE reconfigure >> $LOG_FILE 2>&1
    sleep 5
    
    if ! ping -c 1 -W 5 $PING_TARGET > /dev/null; then
        echo "$(date): [LEVEL 1] FAILED. Level 2: Nuke & Restart Service..." >> $LOG_FILE
        killall wpa_supplicant >> $LOG_FILE 2>&1 || true
        rm -v -f /var/run/wpa_supplicant/$INTERFACE >> $LOG_FILE 2>&1
        ip link set $INTERFACE down >> $LOG_FILE 2>&1
        sleep 2
        ip link set $INTERFACE up >> $LOG_FILE 2>&1
        sleep 2
        systemctl restart wpa_supplicant >> $LOG_FILE 2>&1
        sleep 10
    fi
    
    if ! ping -c 1 -W 5 $PING_TARGET > /dev/null; then
        echo "$(date): [LEVEL 2] FAILED. Level 3: Manual wpa_supplicant fallback..." >> $LOG_FILE
        killall wpa_supplicant >> $LOG_FILE 2>&1 || true
        rm -v -f /var/run/wpa_supplicant/$INTERFACE >> $LOG_FILE 2>&1
        wpa_supplicant -B -i $INTERFACE -c /etc/wpa_supplicant/wpa_supplicant.conf >> $LOG_FILE 2>&1
        sleep 10
    fi
    
    # Final check
    if ping -c 1 -W 5 $PING_TARGET > /dev/null; then
        echo "$(date): [SUCCESS] Connection restored!" >> $LOG_FILE
    else
        echo "$(date): [CRITICAL] All recovery levels failed. Is the hotspot on?" >> $LOG_FILE
        # Final debug dump
        echo "$(date): [DEBUG] Final check: $(ip addr show $INTERFACE)" >> $LOG_FILE
    fi
    echo "------------------------------------------" >> $LOG_FILE
fi
