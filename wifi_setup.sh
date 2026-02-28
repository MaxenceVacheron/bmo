#!/bin/bash
# WiFi Hotspot Setup for BMO/AMO Configuration Portal
# Usage: sudo wifi_setup.sh start|stop
# Creates a WiFi hotspot so a phone can connect and configure the device.

INTERFACE="wlan0"
HOTSPOT_IP="192.168.4.1"
DHCP_RANGE_START="192.168.4.10"
DHCP_RANGE_END="192.168.4.50"
LOG="/tmp/bmo_wifi_setup.log"

# Read device name for SSID
DEVICE_NAME="BMO"
if [ -f /home/pi/bmo/.name ]; then
    DEVICE_NAME=$(cat /home/pi/bmo/.name | tr '[:lower:]' '[:upper:]')
fi
SSID="${DEVICE_NAME}-Setup"

HOSTAPD_CONF="/tmp/bmo_hostapd.conf"
DNSMASQ_CONF="/tmp/bmo_dnsmasq.conf"

start_hotspot() {
    echo "📡 Starting WiFi hotspot: $SSID ..." | tee "$LOG"

    # 1. Unblock WiFi radio (critical on many Pis)
    echo "  [1/7] Unblocking WiFi radio..." | tee -a "$LOG"
    rfkill unblock wlan 2>>"$LOG" || true
    rfkill unblock wifi 2>>"$LOG" || true
    rfkill unblock all 2>>"$LOG" || true

    # 2. Stop ALL conflicting services
    echo "  [2/7] Stopping conflicting services..." | tee -a "$LOG"
    systemctl stop wpa_supplicant 2>>"$LOG" || true
    systemctl stop dhcpcd 2>>"$LOG" || true
    systemctl stop NetworkManager 2>>"$LOG" || true
    nmcli device set $INTERFACE managed no 2>>"$LOG" || true
    
    # Stop Docker to free port 80 (common cause of "C ki ?" prompt)
    echo "  Stopping Docker to free port 80..." | tee -a "$LOG"
    systemctl stop docker 2>>"$LOG" || true
    systemctl stop docker.socket 2>>"$LOG" || true
    
    systemctl stop dnsmasq 2>>"$LOG" || true
    systemctl stop hostapd 2>>"$LOG" || true
    # Unmask hostapd in case systemd masked it
    systemctl unmask hostapd 2>>"$LOG" || true
    killall wpa_supplicant 2>>"$LOG" || true
    killall hostapd 2>>"$LOG" || true
    killall dnsmasq 2>>"$LOG" || true
    rm -f /var/run/wpa_supplicant/$INTERFACE

    # 3. Wait for processes to die
    sleep 1

    # 4. Configure interface with static IP
    echo "  [3/7] Setting static IP $HOTSPOT_IP..." | tee -a "$LOG"
    ip link set $INTERFACE down 2>>"$LOG" || true
    ip addr flush dev $INTERFACE 2>>"$LOG"
    ip link set $INTERFACE up 2>>"$LOG"
    ip addr add ${HOTSPOT_IP}/24 dev $INTERFACE 2>>"$LOG"

    # Verify IP was set
    echo "  Interface status:" >> "$LOG"
    ip addr show $INTERFACE >> "$LOG" 2>&1

    # 5. Write hostapd config
    echo "  [4/7] Writing hostapd config..." | tee -a "$LOG"
    cat > "$HOSTAPD_CONF" <<EOF
interface=$INTERFACE
driver=nl80211
ssid=$SSID
country_code=FR
hw_mode=g
channel=7
ieee80211n=1
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
# Open network (no password for easy setup)
EOF

    # 6. Write dnsmasq config (DHCP + DNS redirect)
    echo "  [5/7] Writing dnsmasq config..." | tee -a "$LOG"
    cat > "$DNSMASQ_CONF" <<EOF
interface=$INTERFACE
bind-interfaces
dhcp-range=${DHCP_RANGE_START},${DHCP_RANGE_END},255.255.255.0,24h

# Redirect specific captive portal detection domains (OS native triggers)
address=/connectivitycheck.gstatic.com/${HOTSPOT_IP}
address=/clients3.google.com/${HOTSPOT_IP}
address=/connectivitycheck.android.com/${HOTSPOT_IP}
address=/connectivity-check.ubuntu.com/${HOTSPOT_IP}
address=/detectportal.firefox.com/${HOTSPOT_IP}
address=/www.apple.com/${HOTSPOT_IP}
address=/apple.com/${HOTSPOT_IP}
address=/itools.info/${HOTSPOT_IP}
address=/ibook.info/${HOTSPOT_IP}
address=/airport.us/${HOTSPOT_IP}
address=/thinkdifferent.us/${HOTSPOT_IP}
address=/www.msftncsi.com/${HOTSPOT_IP}
address=/www.msftconnecttest.com/${HOTSPOT_IP}

# Blanket redirect is REMOVED to avoid SSL/HSTS errors on HTTPS domains.
# Instruct users to visit http://192.168.4.1 manually.
EOF

    # 7. Start hostapd
    echo "  [6/7] Starting hostapd..." | tee -a "$LOG"
    hostapd -B "$HOSTAPD_CONF" >> "$LOG" 2>&1
    HOSTAPD_EXIT=$?
    if [ $HOSTAPD_EXIT -ne 0 ]; then
        echo "  ❌ hostapd failed (exit $HOSTAPD_EXIT)! Trying without driver line..." | tee -a "$LOG"
        # Some Pi WiFi chips work better without explicit driver
        sed -i '/^driver=/d' "$HOSTAPD_CONF"
        hostapd -B "$HOSTAPD_CONF" >> "$LOG" 2>&1
        HOSTAPD_EXIT=$?
        if [ $HOSTAPD_EXIT -ne 0 ]; then
            echo "  ❌ hostapd still failed! Check $LOG for details." | tee -a "$LOG"
            echo "  Attempting hostapd debug run (5s)..." | tee -a "$LOG"
            timeout 5 hostapd -d "$HOSTAPD_CONF" >> "$LOG" 2>&1 || true
            exit 1
        fi
    fi
    echo "  ✅ hostapd started successfully" | tee -a "$LOG"

    # Wait for AP to be ready
    sleep 2

    # 8. Start dnsmasq
    echo "  [7/7] Starting dnsmasq..." | tee -a "$LOG"
    dnsmasq -C "$DNSMASQ_CONF" -x /tmp/bmo_dnsmasq.pid >> "$LOG" 2>&1
    DNSMASQ_EXIT=$?
    if [ $DNSMASQ_EXIT -ne 0 ]; then
        echo "  ❌ dnsmasq failed (exit $DNSMASQ_EXIT)!" | tee -a "$LOG"
        # Try killing any stale dnsmasq and retry
        killall dnsmasq 2>/dev/null || true
        sleep 1
        dnsmasq -C "$DNSMASQ_CONF" -x /tmp/bmo_dnsmasq.pid >> "$LOG" 2>&1 || true
    fi

    echo "✅ Hotspot '$SSID' is running!" | tee -a "$LOG"
    echo "   IP: $HOTSPOT_IP" | tee -a "$LOG"
    echo "   Web: http://$HOTSPOT_IP" | tee -a "$LOG"
    echo "   Log: $LOG" | tee -a "$LOG"
}

stop_hotspot() {
    echo "📡 Stopping WiFi hotspot..." | tee -a "$LOG"

    # Kill hotspot services
    killall hostapd 2>/dev/null || true
    if [ -f /tmp/bmo_dnsmasq.pid ]; then
        kill $(cat /tmp/bmo_dnsmasq.pid) 2>/dev/null || true
        rm -f /tmp/bmo_dnsmasq.pid
    fi
    killall dnsmasq 2>/dev/null || true

    # Clean up temp configs
    rm -f "$HOSTAPD_CONF" "$DNSMASQ_CONF"

    # Restore normal WiFi
    echo "  Restoring normal WiFi..." | tee -a "$LOG"
    ip link set $INTERFACE down 2>/dev/null || true
    ip addr flush dev $INTERFACE 2>/dev/null || true
    ip link set $INTERFACE up 2>/dev/null || true

    # Restart networking services
    killall wpa_supplicant 2>/dev/null || true
    rm -f /var/run/wpa_supplicant/$INTERFACE
    
    nmcli device set $INTERFACE managed yes 2>>"$LOG" || true
    systemctl start NetworkManager 2>>"$LOG" || true
    systemctl start dhcpcd 2>>"$LOG" || true
    
    # Restart Docker
    echo "  Restarting Docker..." | tee -a "$LOG"
    systemctl start docker 2>>"$LOG" || true
    
    wpa_supplicant -B -i $INTERFACE -c /etc/wpa_supplicant/wpa_supplicant.conf 2>>"$LOG" || true
    
    # Request DHCP
    dhclient $INTERFACE 2>>"$LOG" || true

    echo "✅ Normal WiFi restored." | tee -a "$LOG"
}

case "${1:-}" in
    start)
        start_hotspot
        ;;
    stop)
        stop_hotspot
        ;;
    *)
        echo "Usage: sudo $0 start|stop"
        exit 1
        ;;
esac
