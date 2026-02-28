#!/usr/bin/env python3
"""
Hub — Personal Dashboard & App Launcher for AMO's Pi
Runs on the same SPI TFT framebuffer. Switch back to AMO via menu.
"""
import os
import sys
import time
import socket
import subprocess
import json
import shutil
import pygame
import threading
import math
import urllib.request

# --- FRAMEBUFFER & SCREEN ---
WIDTH, HEIGHT = 480, 320
FB_DEVICE = "/dev/fb1" if os.path.exists("/dev/fb1") else "/dev/fb0"

# --- COLORS (Purple theme) ---
BG_DARK = (18, 12, 28)
BG_CARD = (32, 22, 48)
PURPLE = (178, 132, 220)
PURPLE_DIM = (120, 80, 160)
PURPLE_BRIGHT = (210, 170, 255)
WHITE = (245, 247, 250)
GRAY = (140, 140, 160)
GRAY_DIM = (80, 80, 100)
RED = (231, 76, 60)
GREEN = (46, 204, 113)
YELLOW = (241, 196, 15)
ORANGE = (230, 126, 34)
BLUE = (52, 152, 219)
TEAL = (26, 188, 156)
PINK = (255, 105, 180)

# --- PYGAME INIT ---
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
screen = pygame.Surface((WIDTH, HEIGHT), depth=16, masks=(0xF800, 0x07E0, 0x001F, 0))

# Fonts
try:
    FONT_TIME = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
    FONT_LARGE = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    FONT_MED = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    FONT_SMALL = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    FONT_TINY = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
except:
    FONT_TIME = pygame.font.SysFont(None, 72)
    FONT_LARGE = pygame.font.SysFont(None, 36)
    FONT_MED = pygame.font.SysFont(None, 22)
    FONT_SMALL = pygame.font.SysFont(None, 16)
    FONT_TINY = pygame.font.SysFont(None, 12)

# --- STATE ---
state = {
    "mode": "DASHBOARD",  # DASHBOARD, APPS
    "needs_redraw": True,
    "tap_debug": {"pos": None, "time": 0},  # Crosshair debug
    "weather": {
        "temp": "--",
        "city": "...",
        "desc": "Loading...",
        "icon": "cloud",
        "last_update": 0
    },
    "stats_cache": {
        "cpu_temp": 0,
        "ram_pct": 0,
        "ram_free": 0,
        "disk_pct": 0,
        "disk_free": 0,
        "ip": "...",
        "wifi": 0,
        "last_update": 0
    }
}

# --- SYSTEM FUNCTIONS ---
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except:
        return 0

def get_ram_usage():
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        total = free = 0
        for line in lines:
            if "MemTotal" in line: total = int(line.split()[1])
            if "MemAvailable" in line: free = int(line.split()[1])
        used = total - free
        return (used / total) * 100, free / 1024.0 / 1024.0
    except:
        return 0, 0

def get_disk_usage():
    try:
        total, used, free = shutil.disk_usage("/")
        return (used / total) * 100, free / (1024**3)
    except:
        return 0, 0

def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "No Network"

def get_wifi_strength():
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

def update_stats():
    """Update cached stats (call periodically)"""
    now = time.time()
    if now - state["stats_cache"]["last_update"] < 2:
        return
    state["stats_cache"]["cpu_temp"] = get_cpu_temp()
    state["stats_cache"]["ram_pct"], state["stats_cache"]["ram_free"] = get_ram_usage()
    state["stats_cache"]["disk_pct"], state["stats_cache"]["disk_free"] = get_disk_usage()
    state["stats_cache"]["ip"] = get_ip_address()
    state["stats_cache"]["wifi"] = get_wifi_strength()
    state["stats_cache"]["last_update"] = now

def fetch_weather():
    """Fetch weather in background"""
    try:
        url = "http://wttr.in/?format=j1"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            current = data['current_condition'][0]
            area = data['nearest_area'][0]
            state["weather"] = {
                "temp": f"{current['temp_C']}°",
                "city": area['areaName'][0]['value'],
                "desc": current['weatherDesc'][0]['value'],
                "icon": "cloud",
                "last_update": time.time()
            }
            state["needs_redraw"] = True
    except Exception as e:
        print(f"Weather Error: {e}")

def weather_thread():
    """Periodically fetch weather"""
    while True:
        fetch_weather()
        time.sleep(600)  # Every 10 min

# --- DRAWING ---
def draw_rounded_rect(surface, color, rect, radius=8):
    """Draw a rounded rectangle"""
    x, y, w, h = rect
    pygame.draw.rect(surface, color, (x + radius, y, w - 2*radius, h))
    pygame.draw.rect(surface, color, (x, y + radius, w, h - 2*radius))
    pygame.draw.circle(surface, color, (x + radius, y + radius), radius)
    pygame.draw.circle(surface, color, (x + w - radius, y + radius), radius)
    pygame.draw.circle(surface, color, (x + radius, y + h - radius), radius)
    pygame.draw.circle(surface, color, (x + w - radius, y + h - radius), radius)

def draw_progress_bar(surface, x, y, w, h, pct, color, bg_color=GRAY_DIM):
    """Draw a slick progress bar"""
    draw_rounded_rect(surface, bg_color, (x, y, w, h), h//2)
    bar_w = max(h, int(w * (pct / 100.0)))
    if pct > 0:
        draw_rounded_rect(surface, color, (x, y, bar_w, h), h//2)

def draw_dashboard(surface):
    """Main dashboard screen"""
    surface.fill(BG_DARK)
    now = time.time()
    update_stats()
    s = state["stats_cache"]

    # --- Top bar ---
    pygame.draw.rect(surface, BG_CARD, (0, 0, WIDTH, 36))
    # IP
    ip_lbl = FONT_TINY.render(f"IP: {s['ip']}", True, GRAY)
    surface.blit(ip_lbl, (8, 10))
    # WiFi
    wifi_lbl = FONT_TINY.render(f"WiFi: {s['wifi']:.0f}%", True, GRAY)
    surface.blit(wifi_lbl, (WIDTH//2 - wifi_lbl.get_width()//2, 10))
    # Weather
    w = state["weather"]
    weather_lbl = FONT_TINY.render(f"{w['city']} {w['temp']}", True, PURPLE_BRIGHT)
    surface.blit(weather_lbl, (WIDTH - weather_lbl.get_width() - 8, 10))

    # --- Clock (centered, prominent) ---
    t = time.localtime()
    time_str = time.strftime("%H:%M", t)
    time_surf = FONT_TIME.render(time_str, True, WHITE)
    surface.blit(time_surf, (WIDTH//2 - time_surf.get_width()//2, 44))

    # Seconds (smaller, to the right of clock)
    sec_str = time.strftime(":%S", t)
    sec_surf = FONT_MED.render(sec_str, True, PURPLE_DIM)
    sec_x = WIDTH//2 + time_surf.get_width()//2 + 2
    surface.blit(sec_surf, (sec_x, 80))

    # Date
    date_str = time.strftime("%A %d %B %Y", t)
    date_surf = FONT_SMALL.render(date_str, True, GRAY)
    surface.blit(date_surf, (WIDTH//2 - date_surf.get_width()//2, 120))

    # --- Stats Cards ---
    card_y = 150
    card_h = 38
    card_gap = 6
    card_margin = 12
    card_w = WIDTH - 2 * card_margin

    # CPU Temp
    temp = s["cpu_temp"]
    temp_color = GREEN if temp < 55 else (YELLOW if temp < 70 else RED)
    draw_rounded_rect(surface, BG_CARD, (card_margin, card_y, card_w, card_h), 6)
    lbl = FONT_SMALL.render(f"CPU  {temp:.0f}°C", True, WHITE)
    surface.blit(lbl, (card_margin + 10, card_y + 4))
    draw_progress_bar(surface, card_margin + 10, card_y + 24, card_w - 20, 8, min(temp / 85 * 100, 100), temp_color)

    # RAM
    card_y += card_h + card_gap
    draw_rounded_rect(surface, BG_CARD, (card_margin, card_y, card_w, card_h), 6)
    lbl = FONT_SMALL.render(f"RAM  {s['ram_pct']:.0f}%  ({s['ram_free']:.1f} GB free)", True, WHITE)
    surface.blit(lbl, (card_margin + 10, card_y + 4))
    ram_color = GREEN if s['ram_pct'] < 60 else (YELLOW if s['ram_pct'] < 85 else RED)
    draw_progress_bar(surface, card_margin + 10, card_y + 24, card_w - 20, 8, s['ram_pct'], ram_color)

    # Disk
    card_y += card_h + card_gap
    draw_rounded_rect(surface, BG_CARD, (card_margin, card_y, card_w, card_h), 6)
    lbl = FONT_SMALL.render(f"DISK  {s['disk_pct']:.0f}%  ({s['disk_free']:.1f} GB free)", True, WHITE)
    surface.blit(lbl, (card_margin + 10, card_y + 4))
    disk_color = GREEN if s['disk_pct'] < 60 else (YELLOW if s['disk_pct'] < 85 else RED)
    draw_progress_bar(surface, card_margin + 10, card_y + 24, card_w - 20, 8, s['disk_pct'], disk_color)

    # --- Bottom bar: buttons ---
    btn_y = HEIGHT - 40
    btn_h = 32

    # ← AMO button (bottom left)
    draw_rounded_rect(surface, PURPLE, (card_margin, btn_y, 90, btn_h), 6)
    lbl = FONT_SMALL.render("← AMO", True, WHITE)
    surface.blit(lbl, (card_margin + 45 - lbl.get_width()//2, btn_y + 7))

    # BTOP button (bottom center)
    btop_x = WIDTH//2 - 50
    draw_rounded_rect(surface, TEAL, (btop_x, btn_y, 100, btn_h), 6)
    lbl = FONT_SMALL.render("BTOP", True, WHITE)
    surface.blit(lbl, (btop_x + 50 - lbl.get_width()//2, btn_y + 7))

    # Weather desc (bottom right)
    desc_lbl = FONT_TINY.render(state["weather"]["desc"], True, GRAY_DIM)
    surface.blit(desc_lbl, (WIDTH - desc_lbl.get_width() - card_margin, btn_y + 10))

    # --- Tap crosshair debug ---
    tap = state["tap_debug"]
    if tap["pos"] and time.time() - tap["time"] < 2.0:
        tx, ty = tap["pos"]
        pygame.draw.line(surface, RED, (tx - 15, ty), (tx + 15, ty), 2)
        pygame.draw.line(surface, RED, (tx, ty - 15), (tx, ty + 15), 2)
        pygame.draw.circle(surface, RED, (tx, ty), 8, 1)
        coord_lbl = FONT_TINY.render(f"({tx},{ty})", True, RED)
        surface.blit(coord_lbl, (tx + 12, ty - 16))


# --- TOUCH ---
def find_touch_device():
    """Dynamically find the touchscreen device"""
    try:
        from evdev import list_devices, InputDevice
        print("🔍 Hub: Searching for touchscreen...")
        devices = [InputDevice(path) for path in list_devices()]
        for device in devices:
            name_lower = device.name.lower()
            if any(key in name_lower for key in ["gt911", "goodix", "tsc2007", "touchscreen", "ads7846", "input"]):
                print(f"🎯 Hub: Touch found: {device.name} at {device.path}")
                sys.stdout.flush()
                return device.path
    except Exception as e:
        print(f"Touch Discovery Error: {e}")
    return "/dev/input/event0"

def touch_thread():
    """Touch input handler with retry logic for post-execv recovery"""
    time.sleep(0.5)  # Give evdev a moment after process switch
    for attempt in range(5):
        try:
            from evdev import InputDevice, ecodes
            active_dev = find_touch_device()
            print(f"👆 Hub: Opening touch device {active_dev} (attempt {attempt+1})")
            sys.stdout.flush()
            dev = InputDevice(active_dev)
            raw_x, raw_y = 0, 0
            finger_down = False
            last_finger_state = False

            for event in dev.read_loop():
                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_X: raw_x = event.value
                    if event.code == ecodes.ABS_Y: raw_y = event.value
                elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                    finger_down = (event.value == 1)
                elif event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                    if finger_down and not last_finger_state:
                        sx = WIDTH - ((raw_y / 4095.0) * WIDTH)
                        sy = (raw_x / 4095.0) * HEIGHT
                        pygame.event.post(pygame.event.Event(
                            pygame.MOUSEBUTTONDOWN,
                            {'pos': (int(sx), int(sy)), 'button': 1}
                        ))
                    last_finger_state = finger_down
        except Exception as e:
            print(f"Hub Touch Error (attempt {attempt+1}): {e}")
            sys.stdout.flush()
            time.sleep(1)
    print("❌ Hub: Touch thread gave up after 5 attempts")
    sys.stdout.flush()

# --- APP SWITCHING ---
def switch_to_amo():
    """Replace this process with AMO (bmo_pygame.py)"""
    print("🔄 Hub → AMO")
    sys.stdout.flush()
    os.execv(sys.executable, [sys.executable, "/home/pi/bmo/bmo_pygame.py"])

def launch_btop():
    """Launch btop on the framebuffer console, return to hub when done"""
    print("🖥️ Launching btop...")
    sys.stdout.flush()
    # Write a launcher script that runs btop and then returns to hub
    launcher = "/tmp/hub_btop_launcher.sh"
    with open(launcher, 'w') as f:
        f.write("#!/bin/bash\n")
        f.write("clear > /dev/tty1\n")
        f.write("TERM=linux openvt -c 1 -w -- btop 2>/dev/null || openvt -c 1 -w -- htop 2>/dev/null || openvt -c 1 -w -- top\n")
        f.write(f"exec {sys.executable} /home/pi/bmo/hub.py\n")
    os.chmod(launcher, 0o755)
    os.execv("/bin/bash", ["/bin/bash", launcher])

# --- MAIN ---
def main():
    # Singleton
    try:
        lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        lock_socket.bind('\0hub_instance_lock')
    except socket.error:
        print("Hub is already running!")
        sys.exit(0)

    print(f"🚀 Hub starting on {FB_DEVICE}")
    sys.stdout.flush()

    # Start background threads
    threading.Thread(target=touch_thread, daemon=True).start()
    threading.Thread(target=weather_thread, daemon=True).start()

    # Open framebuffer
    try:
        fb_fd = os.open(FB_DEVICE, os.O_RDWR)
    except FileNotFoundError:
        print(f"❌ Framebuffer {FB_DEVICE} not found!")
        sys.exit(1)

    # Main loop
    last_redraw = 0
    try:
        while True:
            now = time.time()

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = event.pos
                    print(f"🔘 Hub tap: ({x}, {y})")
                    sys.stdout.flush()
                    state["tap_debug"] = {"pos": (x, y), "time": time.time()}
                    state["needs_redraw"] = True

                    if state["mode"] == "DASHBOARD":
                        btn_y = HEIGHT - 40
                        # ← AMO button
                        if 12 < x < 102 and btn_y < y < btn_y + 32:
                            switch_to_amo()
                        # BTOP button
                        elif WIDTH//2 - 50 < x < WIDTH//2 + 50 and btn_y < y < btn_y + 32:
                            launch_btop()

            # Redraw at ~2 FPS for dashboard (low CPU), faster if interaction
            if now - last_redraw > 0.5 or state["needs_redraw"]:
                if state["mode"] == "DASHBOARD":
                    draw_dashboard(screen)

                # Write to framebuffer
                try:
                    os.lseek(fb_fd, 0, os.SEEK_SET)
                    os.write(fb_fd, screen.get_buffer())
                except Exception as e:
                    print(f"FB Write Error: {e}")

                last_redraw = now
                state["needs_redraw"] = False

            # Sleep to avoid busy loop
            time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        os.close(fb_fd)
        pygame.quit()

if __name__ == "__main__":
    main()
