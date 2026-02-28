#!/bin/bash
# WiFi Hotspot Setup for BMO/AMO Configuration Portal
# Usage: sudo wifi_setup.sh start|stop
# Creates a WiFi hotspot so a phone can connect and configure the device.
set -e

INTERFACE="wlan0"
HOTSPOT_IP="192.168.4.1"
DHCP_RANGE_START="192.168.4.10"
DHCP_RANGE_END="192.168.4.50"

# Read device name for SSID
DEVICE_NAME="BMO"
if [ -f /home/pi/bmo/.name ]; then
    DEVICE_NAME=$(cat /home/pi/bmo/.name | tr '[:lower:]' '[:upper:]')
fi
SSID="${DEVICE_NAME}-Setup"

HOSTAPD_CONF="/tmp/bmo_hostapd.conf"
DNSMASQ_CONF="/tmp/bmo_dnsmasq.conf"

start_hotspot() {
    echo "📡 Starting WiFi hotspot: $SSID ..."

    # Stop normal WiFi
    echo "  [1/5] Stopping wpa_supplicant..."
    systemctl stop wpa_supplicant 2>/dev/null || true
    killall wpa_supplicant 2>/dev/null || true
    rm -f /var/run/wpa_supplicant/$INTERFACE

    # Stop any existing hotspot processes
    killall hostapd 2>/dev/null || true
    killall dnsmasq 2>/dev/null || true

    # Configure static IP
    echo "  [2/5] Setting static IP $HOTSPOT_IP..."
    ip addr flush dev $INTERFACE
    ip addr add ${HOTSPOT_IP}/24 dev $INTERFACE
    ip link set $INTERFACE up

    # Write hostapd config
    echo "  [3/5] Writing hostapd config..."
    cat > "$HOSTAPD_CONF" <<EOF
interface=$INTERFACE
driver=nl80211
ssid=$SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
# Open network (no password for easy setup)
EOF

    # Write dnsmasq config (DHCP + DNS redirect)
    echo "  [4/5] Writing dnsmasq config..."
    cat > "$DNSMASQ_CONF" <<EOF
interface=$INTERFACE
dhcp-range=${DHCP_RANGE_START},${DHCP_RANGE_END},255.255.255.0,24h
# Redirect all DNS queries to the hotspot IP (captive portal)
address=/#/${HOTSPOT_IP}
EOF

    # Start hostapd and dnsmasq
    echo "  [5/5] Starting hostapd and dnsmasq..."
    hostapd -B "$HOSTAPD_CONF"
    dnsmasq -C "$DNSMASQ_CONF" --no-daemon &
    DNSMASQ_PID=$!
    echo $DNSMASQ_PID > /tmp/bmo_dnsmasq.pid

    echo "✅ Hotspot '$SSID' is running!"
    echo "   IP: $HOTSPOT_IP"
    echo "   Web: http://$HOTSPOT_IP"
}

stop_hotspot() {
    echo "📡 Stopping WiFi hotspot..."

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
    echo "  Restoring normal WiFi..."
    ip addr flush dev $INTERFACE
    ip link set $INTERFACE up

    # Restart wpa_supplicant
    killall wpa_supplicant 2>/dev/null || true
    rm -f /var/run/wpa_supplicant/$INTERFACE
    wpa_supplicant -B -i $INTERFACE -c /etc/wpa_supplicant/wpa_supplicant.conf
    
    # Request DHCP
    dhclient $INTERFACE 2>/dev/null || true

    echo "✅ Normal WiFi restored."
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
