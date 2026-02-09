import os
import shutil
import socket
import subprocess
import sys
try:
    from evdev import list_devices, InputDevice
    HAS_EVDEV = True
except ImportError:
    HAS_EVDEV = False

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except: return 0

def get_ip_address():
    """Get the IP address of the device"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Not Connected"

def get_disk_usage():
    """Get disk usage percentage"""
    try:
        total, used, free = shutil.disk_usage("/")
        return (used / total) * 100, free / (1024**3) # Percent, Free GB
    except:
        return 0, 0

def get_ram_usage():
    """Get RAM usage percentage and free GB"""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        total = 0
        free = 0
        for line in lines:
            if "MemTotal" in line:
                total = int(line.split()[1])
            if "MemAvailable" in line:
                free = int(line.split()[1])
        used = total - free
        p = (used / total) * 100
        f_gb = free / 1024.0 / 1024.0
        return p, f_gb
    except:
        return 0, 0

def get_wifi_strength():
    """Get Wi-Fi signal strength (percentage)"""
    try:
        res = subprocess.check_output(['iwconfig', 'wlan0']).decode('utf-8')
        for line in res.split('\n'):
            if "Link Quality" in line:
                part = line.split("Link Quality=")[1].split()[0]
                q, t = map(int, part.split('/'))
                return (q / t) * 100
    except:
        pass
    return 0

def find_touch_device():
    """Dynamically find the touchscreen device"""
    if not HAS_EVDEV:
        return "/dev/null" # Dummy path for non-Linux systems

    print("🔍 Searching for touchscreen devices...")
    try:
        devices = [InputDevice(path) for path in list_devices()]
        for device in devices:
            print(f"  - Found: {device.name} at {device.path}")
            # Broad search for common touch controllers
            name_lower = device.name.lower()
            if any(key in name_lower for key in ["gt911", "goodix", "tsc2007", "touchscreen", "ads7846", "input"]):
                print(f"🎯 MATCH FOUND: {device.name} at {device.path}")
                sys.stdout.flush()
                return device.path
    except Exception as e:
        print(f"❌ Device Discovery Error: {e}")
    
    print("⚠️ No touch device matched. Falling back to /dev/input/event4")
    sys.stdout.flush()
    # Fallback to the known default if detection fails
    return "/dev/input/event4"
