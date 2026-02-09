#!/bin/bash

# Configuration
PING_TARGET="8.8.8.8"
INTERFACE="wlan0"
LOG_FILE="/var/log/wifi_check.log"

# Environment safety
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Check connection
if ! /bin/ping -c 1 -W 5 $PING_TARGET > /dev/null; then
    echo "------------------------------------------" >> $LOG_FILE
    echo "$(date): [CHECK] Network unreachable. Starting AGGRESSIVE recovery..." >> $LOG_FILE
    
    # Log current status
    echo "$(date): [DEBUG] IP: $(/sbin/ip -4 addr show $INTERFACE | /usr/bin/grep inet | /usr/bin/awk '{print $2}')" >> $LOG_FILE
    
    # AGGRESSIVE RECOVERY
    echo "$(date): [FORCE] Killing wpa_supplicant and removing stale socket..." >> $LOG_FILE
    /usr/bin/killall -9 wpa_supplicant >> $LOG_FILE 2>&1 || true
    /bin/rm -v -f /var/run/wpa_supplicant/$INTERFACE >> $LOG_FILE 2>&1
    
    echo "$(date): [FORCE] Starting wpa_supplicant manually..." >> $LOG_FILE
    /usr/sbin/wpa_supplicant -B -i $INTERFACE -c /etc/wpa_supplicant/wpa_supplicant.conf >> $LOG_FILE 2>&1
    
    # Wait for association and DHCP
    /bin/sleep 10
    
    # Final check
    if /bin/ping -c 1 -W 5 $PING_TARGET > /dev/null; then
        echo "$(date): [SUCCESS] Connection restored via force!" >> $LOG_FILE
    else
        echo "$(date): [CRITICAL] Recovery failed. Attempting level 2 (restart service)..." >> $LOG_FILE
        /usr/bin/killall -9 wpa_supplicant >> $LOG_FILE 2>&1 || true
        /bin/rm -v -f /var/run/wpa_supplicant/$INTERFACE >> $LOG_FILE 2>&1
        /usr/bin/systemctl restart wpa_supplicant >> $LOG_FILE 2>&1
        /bin/sleep 10
        
        if /bin/ping -c 1 -W 5 $PING_TARGET > /dev/null; then
            echo "$(date): [SUCCESS] Connection restored via service restart!" >> $LOG_FILE
        else
            echo "$(date): [ERROR] Persistent failure." >> $LOG_FILE
        fi
    fi
    echo "------------------------------------------" >> $LOG_FILE
fi
