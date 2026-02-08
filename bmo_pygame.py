import os
import sys
import time
import socket
import urllib.request
import random
import pygame
import threading
import math
from evdev import InputDevice, ecodes
from PIL import Image
import json
import shutil
import subprocess
from games.snake import SnakeGame

# --- CONFIGURATION ---
WIDTH, HEIGHT = 480, 320
FB_DEVICE = "/dev/fb1"
TOUCH_DEVICE = "/dev/input/event4" # SPI-connected touch panel on CS1
NEXTCLOUD_PATH = "/home/pi/mnt/nextcloud/shr/BMO_Agnes"
CONFIG_FILE = "/home/pi/bmo/bmo_config.json"
BMO_FACES_ROOT = "/home/pi/bmo/bmo_faces"
IDLE_THOUGHT_DIR = "/home/pi/bmo/bmo_assets/idle/thought"

def load_config():
    """Load configuration from file"""
    defaults = {"brightness": 1.0, "default_mode": "FACE"}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return {**defaults, **config}
        except:
            return defaults
    return defaults

def save_config():
    """Save configuration to file"""
    config = {
        "brightness": state.get("brightness", 1.0),
        "default_mode": state.get("default_mode", "FACE")
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")

# Initialize Pygame Headless
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

# Create Surface matching Framebuffer format (RGB565)
screen = pygame.Surface((WIDTH, HEIGHT), depth=16, masks=(0xF800, 0x07E0, 0x001F, 0))

# Colors
BLACK = (20, 24, 28)
WHITE = (245, 247, 250)
TEAL = (165, 215, 185) # Paler, minty teal for the screen face
PINK = (255, 148, 178)
YELLOW = (241, 196, 15)
RED = (231, 76, 60)
BLUE = (52, 152, 219)
GREEN = (46, 204, 113)
GREEN_MOUTH = (39, 174, 96) # For the big smile
GRAY = (127, 140, 141)

# Fonts
try:
    FONT_LARGE = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    FONT_MEDIUM = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 35)
    FONT_SMALL = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    # Smaller font for timer
    FONT_TINY = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
except:
    FONT_LARGE = pygame.font.SysFont(None, 60)
    FONT_MEDIUM = pygame.font.SysFont(None, 35)
    FONT_SMALL = pygame.font.SysFont(None, 20)
    FONT_TINY = pygame.font.SysFont(None, 15)



stats = {"cpu_temp": 0, "ram_usage": 0, "last_update": 0}

LOVE_NOTES = [
    "You are amazing!",
    "BMO loves you! <3",
    "Have a great day!",
    "You're my favorite!",
    "I'm happy to be yours!",
    "You look great today!",
]

# --- MENUS DEFINITION ---
MENUS = {
    "MAIN": [
        {"label": "FACE", "action": "MODE:FACE", "color": TEAL},
        {"label": "FOCUS", "action": "MENU:FOCUS", "color": GREEN}, # New Focus Menu
        {"label": "NEXTCLOUD", "action": "MENU:NEXTCLOUD", "color": BLUE},
        {"label": "GAMES", "action": "MENU:GAMES", "color": YELLOW},
        {"label": "CLOCK", "action": "MODE:CLOCK", "color": BLUE},
        {"label": "WEATHER", "action": "MODE:WEATHER", "color": BLUE},
        {"label": "SYSTEM", "action": "MODE:ADVANCED_STATS", "color": GRAY},
        {"label": "NOTES", "action": "MODE:NOTES", "color": RED},
        {"label": "HEART", "action": "MODE:HEART", "color": PINK},
        {"label": "SETTINGS", "action": "MENU:SETTINGS", "color": GRAY},
    ],
    "GAMES": [
        {"label": "SNAKE", "action": "MODE:SNAKE", "color": GREEN},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "SETTINGS": [
        {"label": "BRIGHTNESS: 25%", "action": "BRIGHTNESS:0.25", "color": TEAL},
        {"label": "BRIGHTNESS: 50%", "action": "BRIGHTNESS:0.50", "color": TEAL},
        {"label": "BRIGHTNESS: 75%", "action": "BRIGHTNESS:0.75", "color": TEAL},
        {"label": "BRIGHTNESS: 100%", "action": "BRIGHTNESS:1.0", "color": TEAL},
        {"label": "BOOT MODE", "action": "MENU:DEFAULT_MODE", "color": BLUE},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "DEFAULT_MODE": [
        {"label": "FACE (Default)", "action": "SET_DEFAULT:FACE", "color": TEAL},
        {"label": "CLOCK", "action": "SET_DEFAULT:CLOCK", "color": BLUE},
        {"label": "STATS", "action": "SET_DEFAULT:STATS", "color": YELLOW},
        {"label": "HEART", "action": "SET_DEFAULT:HEART", "color": PINK},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "FOCUS": [
        {"label": "15 MIN", "action": "FOCUS:15", "color": GREEN},
        {"label": "25 MIN (Pomo)", "action": "FOCUS:25", "color": TEAL},
        {"label": "45 MIN", "action": "FOCUS:45", "color": YELLOW},
        {"label": "60 MIN", "action": "FOCUS:60", "color": RED},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "NEXTCLOUD": [
        {"label": "DEFAULT", "action": "MENU:NC_DEFAULT", "color": YELLOW},
        {"label": "PERSO", "action": "MENU:NC_PERSO", "color": GREEN},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "NC_DEFAULT": [
        {"label": "PHOTOS", "action": "MENU:DEFAULT_PHOTOS", "color": YELLOW},
        {"label": "TEXTES", "action": "TEXT:default", "color": GREEN},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "NC_PERSO": [
        {"label": "PHOTOS", "action": "MENU:PERSO_PHOTOS", "color": PINK},
        {"label": "TEXTES", "action": "TEXT:perso", "color": BLUE},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "DEFAULT_PHOTOS": [
        {"label": "GIFs", "action": "GIF:default", "color": GREEN},
        {"label": "Images", "action": "SLIDESHOW:default", "color": YELLOW},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "PERSO_PHOTOS": [
        {"label": "GIFs", "action": "GIF:perso", "color": GREEN},
        {"label": "Images", "action": "SLIDESHOW:perso", "color": PINK},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "TEXTES": [
        {"label": "PERSO", "action": "TEXT:Perso", "color": PINK},
        {"label": "REMOTE", "action": "TEXT:Remote", "color": BLUE},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ]
}

# State
state = {
    "mode": "STARTUP", # Back to startup for Agnès
    "expression": "happy",
    "last_interaction": time.time(),
    "love_note": "You are amazing!",
    "menu_stack": ["MAIN"],
    "menu_page": 0,
    "brightness": 1.0,
    "default_mode": "FACE",
    "blink_timer": 0, # Time until next blink
    "is_blinking": False,
    "blink_end_time": 0,
    "pop_face_timer": time.time() + 60,
    "is_showing_pop_face": False,
    "pop_face_end_time": 0,
    "emotion": "positive", # Default emotion
    "face_images": [],
    "current_face_open": None,
    "current_face_closed": None,
    "last_face_switch": 0,
    "needs_redraw": True,
    "idle": {
        "thought": {
            "is_active": False,
            "end_time": 0,
            "next_time": time.time(), # Force first one immediately
            "current_image": None
        },
        "humming": {
            "is_active": False,
            "end_time": 0,
            "next_time": time.time() + 20,
            "notes": []
        }
    },
    "startup": {
        "message": "Hello Agnès! I'm BMO. Maxence built my brain just for you.",
        "char_index": 0,
        "start_time": 0,
        "char_delay": 0.05  # 50ms per character
    },
    "slideshow": {
        "path": "",
        "images": [],
        "index": 0,
        "last_switch": 0,
        "current_surface": None,
        "last_touch_time": 0
    },
    "text_viewer": {
        "content": [],
        "scroll_y": 0,
        "path": ""
    },
    "focus": {
        "end_time": 0,
        "duration": 0,
        "active": False,
        "blink_timer": 0
    },
    "gif_player": {
        "path": "",
        "gifs": [],
        "current_gif_index": 0,
        "frames": [],
        "frame_index": 0,
        "last_frame_time": 0,
        "frame_duration": 0.1,
        "gif_switch_time": 0,
        "last_touch_time": 0,
        "next_frames": [],  # Preloaded next GIF
        "next_frame_duration": 0.1
    },
    "snake": None, # Will hold SnakeGame instance
    "cached_dim_surf": None,
    "last_brightness": -1.0,
    "tap_times": [], # For 5-tap shortcut
    "weather": {
        "temp": "--",
        "city": "Unknown",
        "desc": "Loading...",
        "icon": "cloud",
        "last_update": 0
    },
    "needs": {
        "hunger": 80.0,
        "energy": 90.0,
        "play": 70.0,
        "last_decay": time.time(),
        "hearts": [], # Floating hearts: {"pos": [x,y], "vel": [vx,vy], "life": t}
        "show_interaction": False # Whether to show feeding/playing buttons
    },
    "click_feedback": {
        "pos": (0, 0),
        "time": 0
    }
}

# --- SYSTEM STATS ---
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except: return 0

def get_ram_usage():
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            total = int(lines[0].split()[1])
            avail = int(lines[2].split()[1])
            return ((total - avail) / total) * 100
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

def draw_advanced_stats(screen):
    screen.fill(GRAY)
    
    title = FONT_MEDIUM.render("BMO SYSTEM STATUS", False, WHITE)
    pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, 50))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 10))
    
    y = 70
    ip = get_ip_address()
    lbl = FONT_SMALL.render(f"IP: {ip}", False, BLACK)
    screen.blit(lbl, (40, y))
    
    y += 40
    wifi = get_wifi_strength()
    lbl = FONT_SMALL.render(f"WIFI SIGNAL: {wifi:.0f}%", False, BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, BLACK, (40, y+30, 400, 20), 2)
    w = int(396 * (wifi / 100.0))
    if wifi > 0:
        color = GREEN if wifi > 50 else YELLOW
        pygame.draw.rect(screen, color, (42, y+32, w, 16))
    
    y += 70
    temp = get_cpu_temp()
    lbl = FONT_SMALL.render(f"CPU TEMP: {temp:.1f}C", False, BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, BLACK, (40, y+30, 400, 20), 2)
    w = int(396 * (min(temp, 85) / 85.0))
    color = RED if temp > 65 else GREEN
    pygame.draw.rect(screen, color, (42, y+32, w, 16))
    
    y += 70
    disk_p, disk_f = get_disk_usage()
    lbl = FONT_SMALL.render(f"DISK: {disk_p:.1f}% ({disk_f:.1f} GB Free)", False, BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, BLACK, (40, y+30, 400, 20), 2)
    w = int(396 * (disk_p / 100.0))
    pygame.draw.rect(screen, BLUE, (42, y+32, w, 16))

def auto_update_and_restart():
    """Pull latest changes from Git and restart the service"""
    print("🚀 BMO Auto-Update triggered!")
    screen.fill(BLACK)
    lbl = FONT_MEDIUM.render("UPDATING BMO...", False, WHITE)
    screen.blit(lbl, (WIDTH//2 - lbl.get_width()//2, HEIGHT//2 - 20))
    
    # Write to framebuffer directly for immediate feedback
    try:
        with open(FB_DEVICE, "wb") as f:
            f.write(screen.get_buffer())
    except: pass
    
    try:
        # Run git pull
        subprocess.run(["git", "pull"], cwd="/home/pi/bmo", timeout=30)
        # Restart the systemd service
        os.system("sudo systemctl restart bmo &")
        sys.exit(0)
    except Exception as e:
        print(f"Error during update: {e}")

def spawn_hearts(x, y):
    """Create a burst of floating hearts at position"""
    now = time.time()
    for _ in range(5):
        state["needs"]["hearts"].append({
            "pos": [float(x), float(y)],
            "vel": [random.uniform(-1.5, 1.5), random.uniform(-2, -4)],
            "end_time": now + random.uniform(1.5, 2.5)
        })
    state["needs_redraw"] = True

def get_weather():
    """Fetch current weather from wttr.in"""
    try:
        url = "http://wttr.in/?format=j1"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            current = data['current_condition'][0]
            area = data['nearest_area'][0]
            city = area['areaName'][0]['value']
            temp = current['temp_C']
            desc = current['weatherDesc'][0]['value']
            # Map description to icons
            desc_lower = desc.lower()
            icon = "cloud"
            if "sun" in desc_lower or "clear" in desc_lower: icon = "sun"
            elif "rain" in desc_lower or "drizzle" in desc_lower: icon = "rain"
            elif "snow" in desc_lower: icon = "snow"
            elif "storm" in desc_lower or "thunder" in desc_lower: icon = "storm"
            
            state["weather"] = {
                "temp": f"{temp}°C",
                "city": city,
                "desc": desc,
                "icon": icon,
                "last_update": time.time()
            }
            state["needs_redraw"] = True
            print(f"Weather updated for {city}: {temp}C, {desc}")
    except Exception as e:
        print(f"Error fetching weather: {e}")

def draw_weather(screen):
    screen.fill(TEAL) # Nice teal background for weather
    now = time.time()
    
    # Auto-refresh every 20 mins
    if now - state["weather"]["last_update"] > 1200:
        threading.Thread(target=get_weather, daemon=True).start()
    
    # Header area (City)
    pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, 40))
    city_lbl = FONT_SMALL.render(state["weather"]["city"].upper(), False, WHITE)
    screen.blit(city_lbl, (WIDTH//2 - city_lbl.get_width()//2, 10))

    # Icon
    icon_name = state["weather"]["icon"]
    icon_path = f"/home/pi/bmo/bmo_assets/weather/{icon_name}.png"
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path).convert('RGBA')
            img = img.resize((150, 150), Image.Resampling.LANCZOS)
            data = img.tobytes()
            pygame_img = pygame.image.fromstring(data, img.size, img.mode)
            screen.blit(pygame_img, (WIDTH//2 - 75, 50))
        except:
            pass
            
    # Temp
    temp_lbl = FONT_LARGE.render(state["weather"]["temp"], False, BLACK)
    screen.blit(temp_lbl, (WIDTH//2 - temp_lbl.get_width()//2, 210))
    
    # Description
    desc = state["weather"]["desc"]
    desc_lbl = FONT_SMALL.render(desc, False, BLACK)
    screen.blit(desc_lbl, (WIDTH//2 - desc_lbl.get_width()//2, 275))

# --- TOUCH INPUT THREAD ---
def touch_thread():
    try:
        dev = InputDevice(TOUCH_DEVICE)
        raw_x, raw_y = 0, 0
        last_finger_state = False
        finger_down = False
        
        for event in dev.read_loop():
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_X: raw_x = event.value
                if event.code == ecodes.ABS_Y: raw_y = event.value
            
            elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                finger_down = (event.value == 1)
            
            elif event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                if finger_down and not last_finger_state:
                    # New Touch Detected!
                    sx = WIDTH - ((raw_y / 4095.0) * WIDTH)
                    sy = (raw_x / 4095.0) * HEIGHT
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(sx), int(sy)), 'button': 1}))
                
                last_finger_state = finger_down
    except Exception as e:
        print(f"Touch Error: {e}")

# --- SLIDESHOW FUNCTIONS ---
def start_slideshow(subdir):
    # subdir is 'default' or 'perso'
    path = os.path.join(NEXTCLOUD_PATH, subdir, "Photos")
    state["slideshow"]["path"] = path
    state["slideshow"]["images"] = []
    
    if os.path.exists(path):
        for f in os.listdir(path):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                state["slideshow"]["images"].append(os.path.join(path, f))
    
    if not state["slideshow"]["images"]:
        state["slideshow"]["images"] = ["PLACEHOLDER_EMPTY"]
        
    state["slideshow"]["index"] = 0
    state["slideshow"]["last_switch"] = 0
    state["mode"] = "SLIDESHOW"

def update_slideshow():
    if time.time() - state["slideshow"]["last_switch"] > 5.0:
        state["slideshow"]["last_switch"] = time.time()
        
        imgs = state["slideshow"]["images"]
        if not imgs or imgs[0] == "PLACEHOLDER_EMPTY": return

        try:
            img_path = imgs[state["slideshow"]["index"]]
            
            # Load with PIL (better format handling)
            pil_img = Image.open(img_path)
            pil_img = pil_img.convert('RGB')  # Force RGB
            
            # Calculate scaling
            img_w, img_h = pil_img.size
            scale = min(WIDTH / img_w, HEIGHT / img_h)
            new_size = (int(img_w * scale), int(img_h * scale))
            
            # Resize with PIL (high quality)
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert PIL to Pygame surface
            mode = pil_img.mode
            size = pil_img.size
            data = pil_img.tobytes()
            
            pygame_img = pygame.image.fromstring(data, size, mode)
            
            # Convert to screen format
            converted = pygame.Surface(pygame_img.get_size(), depth=16, masks=(0xF800, 0x07E0, 0x001F, 0))
            converted.blit(pygame_img, (0, 0))
            
            state["slideshow"]["current_surface"] = converted
            state["slideshow"]["index"] = (state["slideshow"]["index"] + 1) % len(imgs)
        except Exception as e:
            print(f"Slideshow error: {e}")
            state["slideshow"]["index"] = (state["slideshow"]["index"] + 1) % len(imgs)

def draw_slideshow(screen):
    screen.fill(BLACK)
    if not state["slideshow"]["images"] or state["slideshow"]["images"][0] == "PLACEHOLDER_EMPTY":
        txt = FONT_MEDIUM.render("No Images Found", False, WHITE)
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2))
        return

    surf = state["slideshow"]["current_surface"]
    if surf:
        x = (WIDTH - surf.get_width()) // 2
        y = (HEIGHT - surf.get_height()) // 2
        screen.blit(surf, (x, y))
    
    # Navigation hints (show for 1 second after touch)
    if time.time() - state["slideshow"]["last_touch_time"] < 1.0:
        hint_left = FONT_SMALL.render("<", False, WHITE)
        hint_right = FONT_SMALL.render(">", False, WHITE)
        screen.blit(hint_left, (10, HEIGHT - 30))
        screen.blit(hint_right, (WIDTH - 30, HEIGHT - 30))

# --- GIF PLAYER FUNCTIONS ---
def start_gif_player(subdir):
    # subdir is 'default' or 'perso'
    path = os.path.join(NEXTCLOUD_PATH, subdir, "Photos", "GIFs")
    state["gif_player"]["path"] = path
    state["gif_player"]["gifs"] = []
    
    # Scan for GIFs
    if os.path.exists(path):
        for f in os.listdir(path):
            if f.lower().endswith('.gif'):
                state["gif_player"]["gifs"].append(os.path.join(path, f))
    
    if not state["gif_player"]["gifs"]:
        print(f"No GIFs found in {path}")
        state["mode"] = "MENU"
        return
    
    # Shuffle for random order
    random.shuffle(state["gif_player"]["gifs"])
        
    state["gif_player"]["current_gif_index"] = 0
    state["gif_player"]["gif_switch_time"] = time.time()
    load_next_gif()
    state["mode"] = "GIF_PLAYER"

def _load_gif_frames(gif_path):
    """Helper function to load GIF frames and duration"""
    frames = []
    duration = 0.1
    
    try:
        pil_gif = Image.open(gif_path)
        
        # Get frame duration (in milliseconds, convert to seconds)
        try:
            duration = pil_gif.info.get('duration', 100) / 1000.0
        except:
            duration = 0.1
        
        # Extract all frames
        frame_num = 0
        while True:
            try:
                pil_gif.seek(frame_num)
                frame = pil_gif.convert('RGB')
                
                # Scale to fit screen
                img_w, img_h = frame.size
                scale = min(WIDTH / img_w, HEIGHT / img_h)
                new_size = (int(img_w * scale), int(img_h * scale))
                frame = frame.resize(new_size, Image.Resampling.NEAREST)  # NEAREST for pixel art
                
                # Convert to Pygame
                mode = frame.mode
                size = frame.size
                data = frame.tobytes()
                pygame_frame = pygame.image.fromstring(data, size, mode)
                
                frames.append(pygame_frame)
                frame_num += 1
            except EOFError:
                break
        
        print(f"Loaded GIF with {len(frames)} frames")
    except Exception as e:
        print(f"Error loading GIF: {e}")
    
    return frames, duration

def load_next_gif():
    """Load all frames from current GIF (use preloaded if available)"""
    gifs = state["gif_player"]["gifs"]
    if not gifs:
        return
    
    # Use preloaded frames if available
    if state["gif_player"]["next_frames"]:
        state["gif_player"]["frames"] = state["gif_player"]["next_frames"]
        state["gif_player"]["frame_duration"] = state["gif_player"]["next_frame_duration"]
        state["gif_player"]["frame_index"] = 0
        state["gif_player"]["next_frames"] = []
        print("Using preloaded GIF")
    else:
        # Load current GIF
        gif_path = gifs[state["gif_player"]["current_gif_index"]]
        frames, duration = _load_gif_frames(gif_path)
        state["gif_player"]["frames"] = frames
        state["gif_player"]["frame_duration"] = duration
        state["gif_player"]["frame_index"] = 0
    
    # Preload next GIF
    preload_next_gif()

def preload_next_gif():
    """Preload the next GIF in background"""
    gifs = state["gif_player"]["gifs"]
    if not gifs or len(gifs) <= 1:
        return
    
    next_index = (state["gif_player"]["current_gif_index"] + 1) % len(gifs)
    next_gif_path = gifs[next_index]
    
    frames, duration = _load_gif_frames(next_gif_path)
    state["gif_player"]["next_frames"] = frames
    state["gif_player"]["next_frame_duration"] = duration
    print(f"Preloaded next GIF (index {next_index})")

def update_gif():
    """Update GIF animation"""
    # Check if time to switch to next GIF (every 15 seconds)
    if time.time() - state["gif_player"]["gif_switch_time"] > 15.0:
        gifs = state["gif_player"]["gifs"]
        state["gif_player"]["current_gif_index"] = (state["gif_player"]["current_gif_index"] + 1) % len(gifs)
        state["gif_player"]["gif_switch_time"] = time.time()
        load_next_gif()
    
    # Animate current GIF
    if time.time() - state["gif_player"]["last_frame_time"] > state["gif_player"]["frame_duration"]:
        state["gif_player"]["last_frame_time"] = time.time()
        frames = state["gif_player"]["frames"]
        if frames:
            state["gif_player"]["frame_index"] = (state["gif_player"]["frame_index"] + 1) % len(frames)

def draw_gif(screen):
    screen.fill(BLACK)
    
    frames = state["gif_player"]["frames"]
    if not frames:
        txt = FONT_MEDIUM.render("No GIF loaded", False, WHITE)
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2))
        return
    
    frame = frames[state["gif_player"]["frame_index"]]
    x = (WIDTH - frame.get_width()) // 2
    y = (HEIGHT - frame.get_height()) // 2
    screen.blit(frame, (x, y))
    
    # Navigation hints (show for 1 second after touch)
    if time.time() - state["gif_player"]["last_touch_time"] < 1.0:
        hint_left = FONT_SMALL.render("<", False, WHITE)
        hint_right = FONT_SMALL.render(">", False, WHITE)
        screen.blit(hint_left, (10, HEIGHT - 30))
        screen.blit(hint_right, (WIDTH - 30, HEIGHT - 30))

# --- TEXT VIEWER FUNCTIONS ---
def start_text_viewer(subdir):
    # subdir is 'default' or 'perso'
    path = os.path.join(NEXTCLOUD_PATH, subdir, "Textes")
    found_file = None
    if os.path.exists(path):
        for f in os.listdir(path):
            if f.lower().endswith('.txt'):
                found_file = os.path.join(path, f)
                break
    
    state["text_viewer"]["content"] = []
    if found_file:
        try:
            with open(found_file, 'r') as f:
                content = f.read()
                words = content.split(' ')
                line = []
                for w in words:
                    line.append(w)
                    if FONT_SMALL.size(' '.join(line))[0] > 440:
                        line.pop()
                        state["text_viewer"]["content"].append(' '.join(line))
                        line = [w]
                state["text_viewer"]["content"].append(' '.join(line))
        except:
            state["text_viewer"]["content"] = ["Error reading file."]
    else:
        state["text_viewer"]["content"] = ["No text file found.", f"Path: {path}"]
        
    state["mode"] = "TEXT_VIEWER"

def draw_text_viewer(screen):
    screen.fill(BLACK)
    y = 20
    for line in state["text_viewer"]["content"]:
        if y > HEIGHT - 20: break
        txt = FONT_SMALL.render(line, False, WHITE)
        screen.blit(txt, (20, y))
        y += 25
    hint = FONT_SMALL.render("Tap to Close", False, GRAY)
    screen.blit(hint, (WIDTH - hint.get_width() - 10, HEIGHT - 30))

# --- STARTUP ANIMATION ---
def update_startup():
    """Update typewriter animation"""
    if state["startup"]["start_time"] == 0:
        state["startup"]["start_time"] = time.time()
    
    elapsed = time.time() - state["startup"]["start_time"]
    target_chars = int(elapsed / state["startup"]["char_delay"])
    
    if target_chars > len(state["startup"]["message"]):
        # Animation complete, wait 2 seconds then go to default mode
        if elapsed > len(state["startup"]["message"]) * state["startup"]["char_delay"] + 2.0:
            print(f"Startup complete, moving to {state['default_mode']}")
            if state["default_mode"] == "FACE":
                switch_to_face_mode()
            else:
                state["mode"] = state["default_mode"]
    else:
        if target_chars != state["startup"]["char_index"]:
            state["startup"]["char_index"] = target_chars
            print(f"Startup progress: {state['startup']['char_index']}/{len(state['startup']['message'])}")
            sys.stdout.flush()

def draw_startup(screen):
    screen.fill(BLACK) # Using BLACK for startup contrast
    
    # Draw partial message (typewriter effect)
    message = state["startup"]["message"]
    visible_text = message[:state["startup"]["char_index"]]
    
    # Word wrap
    words = visible_text.split(' ')
    lines = []
    line = []
    for w in words:
        line.append(w)
        if FONT_MEDIUM.size(' '.join(line))[0] > WIDTH - 40:
            line.pop()
            lines.append(' '.join(line))
            line = [w]
    lines.append(' '.join(line))
    
    # Draw lines
    y = HEIGHT // 2 - (len(lines) * 30) // 2
    for l in lines:
        if l.strip():
            surf = FONT_MEDIUM.render(l, False, WHITE) # WHITE text on BLACK
            screen.blit(surf, (WIDTH//2 - surf.get_width()//2, y))
        y += 30
    
    # Blinking cursor
    if state["startup"]["char_index"] < len(message):
        if int(time.time() * 2) % 2 == 0:  # Blink every 0.5s
            cursor = FONT_MEDIUM.render("_", False, WHITE)
            # Position cursor at end of last line
            last_line_content = lines[-1] if lines else ""
            last_line_surf = FONT_MEDIUM.render(last_line_content, False, WHITE)
            cursor_x = WIDTH//2 - last_line_surf.get_width()//2 + last_line_surf.get_width()
            cursor_y = y - 30
            screen.blit(cursor, (cursor_x, cursor_y))

def switch_to_face_mode(emotion="positive"):
    """Switch to FACE mode and force an emotion (default: positive)"""
    state["mode"] = "FACE"
    load_random_face(emotion=emotion)

# --- FACE IMAGE MANAGEMENT ---
def load_random_face(emotion=None):
    """Load a random face pair. If emotion is None, uses 20% negative chance."""
    
    # 20% chance for negative if not forced
    if emotion is None:
        emotion = "negative" if random.random() < 0.2 else "positive"
    
    # Check if target emotion directory has images, fallback if needed
    open_dir = os.path.join(BMO_FACES_ROOT, emotion, "open")
    if not os.path.exists(open_dir) or not [f for f in os.listdir(open_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]:
        emotion = "positive" # Fallback to positive
        open_dir = os.path.join(BMO_FACES_ROOT, "positive", "open")

    state["emotion"] = emotion
    closed_dir = os.path.join(BMO_FACES_ROOT, emotion, "closed")
    
    # Always refresh list
    state["face_images"] = [f for f in os.listdir(open_dir) 
                           if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if state["face_images"]:
        try:
            filename = random.choice(state["face_images"])
            open_path = os.path.join(open_dir, filename)
            closed_path = os.path.join(closed_dir, filename)
            
            # Helper to load and format surface
            def _prep_surf(path):
                if not os.path.exists(path): return None
                img = Image.open(path).convert('RGB')
                img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
                data = img.tobytes()
                pygame_img = pygame.image.fromstring(data, img.size, img.mode)
                
                # Use EXACT masks from screen to prevent color shifts
                surf = pygame.Surface((WIDTH, HEIGHT), depth=16, masks=screen.get_masks())
                surf.blit(pygame_img, (0, 0))
                return surf

            state["current_face_open"] = _prep_surf(open_path)
            state["current_face_closed"] = _prep_surf(closed_path)
            
            # Fallback if closed version doesn't exist
            if state["current_face_closed"] is None:
                state["current_face_closed"] = state["current_face_open"]
                print(f"Loaded {emotion} face: {filename} (no closed version)")
            else:
                print(f"Loaded {emotion} face: {filename} (with blink version)")
                
            state["last_face_switch"] = time.time()
            state["needs_redraw"] = True
            sys.stdout.flush()
        except Exception as e:
            print(f"Error loading face images: {e}")
            sys.stdout.flush()

def load_thought_bubble():
    """Load a random thought bubble icon"""
    if not os.path.exists(IDLE_THOUGHT_DIR): return None
    files = [f for f in os.listdir(IDLE_THOUGHT_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not files: return None
    path = os.path.join(IDLE_THOUGHT_DIR, random.choice(files))
    try:
        img = Image.open(path).convert('RGBA')
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        # Convert to Pygame
        data = img.tobytes()
        pygame_img = pygame.image.fromstring(data, img.size, img.mode)
        return pygame_img
    except Exception as e:
        print(f"Error loading thought bubble: {e}")
        return None

# --- FOCUS MODE FUNCTIONS ---
def start_focus_timer(minutes):
    state["focus"]["duration"] = minutes * 60
    state["focus"]["end_time"] = time.time() + (minutes * 60)
    state["focus"]["active"] = True
    state["mode"] = "FOCUS"

def draw_focus_face(screen):
    screen.fill(TEAL)
    
    remaining = state["focus"]["end_time"] - time.time()
    
    if remaining <= 0:
        # Time's Up! Celebrate!
        state["focus"]["active"] = False
        
        # Happy Face (Eyes Closed >_< or Excitement)
        # Left Eye (>)
        pygame.draw.lines(screen, BLACK, False, [(125, 110), (140, 125), (125, 140)], 5)
        # Right Eye (<)
        pygame.draw.lines(screen, BLACK, False, [(355, 110), (340, 125), (355, 140)], 5)
        
        # Mouth (Open D)
        pygame.draw.circle(screen, BLACK, (240, 200), 40) # Filled mouth
        pygame.draw.rect(screen, TEAL, (200, 160, 80, 40)) # Cut top half
        
        # Text
        txt = FONT_MEDIUM.render("GOOD JOB!", False, BLACK)
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 50))
        
        hint = FONT_SMALL.render("Tap to finish", False, BLACK)
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, 280))
        
        return

    # Focus Mode (Glasses)
    # Glasses Frames (Squares)
    pygame.draw.rect(screen, BLACK, (110, 90, 60, 60), 4) # Left lens
    pygame.draw.rect(screen, BLACK, (310, 90, 60, 60), 4) # Right lens
    # Bridge
    pygame.draw.line(screen, BLACK, (170, 120), (310, 120), 4)
    # Sides
    pygame.draw.line(screen, BLACK, (110, 120), (60, 110), 4)
    pygame.draw.line(screen, BLACK, (370, 120), (420, 110), 4)
    
    # Eyes (Small dots focused)
    pygame.draw.circle(screen, BLACK, (140, 120), 5)
    pygame.draw.circle(screen, BLACK, (340, 120), 5)
    
    # Mouth (Concentrated line)
    pygame.draw.line(screen, BLACK, (220, 200), (260, 200), 4)
    
    # Timer Text
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    timer_txt = f"{mins:02d}:{secs:02d}"
    
    txt = FONT_MEDIUM.render(timer_txt, False, BLACK)
    # Background for timer text for readability
    # pygame.draw.rect(screen, WHITE, (WIDTH//2 - 50, 250, 100, 40))
    screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 260))
    
    # Progress Bar at bottom
    total = state["focus"]["duration"]
    progress = 1.0 - (remaining / total)
    pygame.draw.rect(screen, BLACK, (40, 300, 400, 10), 1)
    pygame.draw.rect(screen, GREEN, (41, 301, int(398 * progress), 8))


# --- COMMON DRAWING ---
def update_face():
    """Update BMO's face state (blinking, image rotation, and needs)"""
    now = time.time()
    
    # --- NEEDS DECAY ---
    # Decay every 30 seconds for performance
    if now - state["needs"]["last_decay"] > 30:
        elapsed_mins = (now - state["needs"]["last_decay"]) / 60.0
        # Decay rates (per minute)
        # Hunger: 100% in 15h -> 0.11% / min
        # Play: 100% in 10h -> 0.16% / min
        # Energy: 100% in 20h -> 0.08% / min
        state["needs"]["hunger"] = max(0, state["needs"]["hunger"] - (0.11 * elapsed_mins))
        state["needs"]["play"] = max(0, state["needs"]["play"] - (0.16 * elapsed_mins))
        state["needs"]["energy"] = max(0, state["needs"]["energy"] - (0.08 * elapsed_mins))
        state["needs"]["last_decay"] = now
        
        # Update Emotion based on needs
        avg = (state["needs"]["hunger"] + state["needs"]["play"] + state["needs"]["energy"]) / 3.0
        if avg < 40:
            if state["emotion"] != "negative":
                state["emotion"] = "negative"
                print("BMO feels sad/neglected...")
                load_random_face()
        elif avg > 60:
            if state["emotion"] != "positive":
                state["emotion"] = "positive"
                print("BMO feels happy and cared for!")
                load_random_face()

    # --- HEARTS ANIMATION ---
    still_alive = []
    for h in state["needs"]["hearts"]:
        if now < h["end_time"]:
            h["pos"][0] += h["vel"][0]
            h["pos"][1] += h["vel"][1]
            still_alive.append(h)
            state["needs_redraw"] = True
    state["needs"]["hearts"] = still_alive

    # Dynamic rotation interval (Original logic)
    interval = 22.5 if state.get("emotion") == "negative" else 45.0
    
    if now - state["last_face_switch"] > interval:
        print(f"Rotating face image (Emotion: {state.get('emotion')}, Interval: {interval}s)...")
        load_random_face()
    
    # Blinking logic (decreased frequency: 8-20 seconds)
    if state["is_blinking"]:
        if now > state["blink_end_time"]:
            state["is_blinking"] = False
            state["blink_timer"] = now + random.uniform(8.0, 20.0)
            state["needs_redraw"] = True
    else:
        if now > state["blink_timer"]:
            state["is_blinking"] = True
            state["blink_end_time"] = now + 0.15 # Blink duration
            state["needs_redraw"] = True
            print("BMO Blink!")
            sys.stdout.flush()
            
    # --- IDLE BEHAVIORS ---
    # 1. Thought Bubbles
    if not state["idle"]["thought"]["is_active"]:
        if now > state["idle"]["thought"]["next_time"]:
            surf = load_thought_bubble()
            if surf:
                state["idle"]["thought"]["is_active"] = True
                state["idle"]["thought"]["current_image"] = surf
                state["idle"]["thought"]["end_time"] = now + random.uniform(5, 10)
                state["needs_redraw"] = True
                print("BMO is thinking...")
                sys.stdout.flush()
    else:
        if now > state["idle"]["thought"]["end_time"]:
            state["idle"]["thought"]["is_active"] = False
            state["idle"]["thought"]["next_time"] = now + random.uniform(30, 120)
            state["needs_redraw"] = True

    # 2. Humming (Only when positive)
    if state["emotion"] == "positive":
        if not state["idle"]["humming"]["is_active"]:
            if now > state["idle"]["humming"]["next_time"]:
                state["idle"]["humming"]["is_active"] = True
                state["idle"]["humming"]["end_time"] = now + random.uniform(6, 12)
                state["idle"]["humming"]["notes"] = []
                state["needs_redraw"] = True
                print("BMO is humming...")
                sys.stdout.flush()
        else:
            if now > state["idle"]["humming"]["end_time"]:
                if not state["idle"]["humming"]["notes"]: # Wait for notes to vanish
                    state["idle"]["humming"]["is_active"] = False
                    state["idle"]["humming"]["next_time"] = now + random.uniform(20, 90)
                    state["needs_redraw"] = True
            
            # Spawn new notes
            if now < state["idle"]["humming"]["end_time"] and random.random() < 0.1:
                state["idle"]["humming"]["notes"].append({
                    "pos": [random.uniform(100, WIDTH-100), 280],
                    "vel": [random.uniform(-0.5, 0.5), random.uniform(-1.5, -2.5)],
                    "start": now,
                    "life": random.uniform(2, 4)
                })

            # Update notes
            still_alive = []
            for n in state["idle"]["humming"]["notes"]:
                if now - n["start"] < n["life"]:
                    n["pos"][0] += n["vel"][0]
                    n["pos"][1] += n["vel"][1]
                    still_alive.append(n)
                    state["needs_redraw"] = True
            state["idle"]["humming"]["notes"] = still_alive

def draw_music_note(screen, pos, alpha):
    """Draw a procedural music note"""
    x, y = int(pos[0]), int(pos[1])
    # Simple quaver
    pygame.draw.circle(screen, BLACK, (x, y), 6)
    pygame.draw.line(screen, BLACK, (x+4, y), (x+4, y-18), 2)
    pygame.draw.line(screen, BLACK, (x+4, y-18), (x+12, y-12), 3)

def draw_face(screen):
    # No need to fill with BLACK if we are blitting a full-screen image
    if state["is_blinking"]:
        target_surf = state["current_face_closed"]
    else:
        target_surf = state["current_face_open"]

    if target_surf:
        screen.blit(target_surf, (0, 0))
    else:
        # Emergency Fallback - only clear here
        screen.fill(TEAL)
        pygame.draw.circle(screen, BLACK, (140, 120), 9)
        pygame.draw.circle(screen, BLACK, (340, 120), 9)
        pygame.draw.arc(screen, BLACK, (210, 140, 60, 40), 3.14, 6.28, 4)
        
    # --- IDLE OVERLAYS ---
    # 1. Thought Bubble (Top Right)
    if state["idle"]["thought"]["is_active"] and state["idle"]["thought"]["current_image"]:
        # Cloud position
        bx, by = WIDTH - 100, 30
        # Draw actual bubble icon
        screen.blit(state["idle"]["thought"]["current_image"], (bx, by))
        # Draw small trail circles (comic book style)
        pygame.draw.circle(screen, WHITE, (bx - 10, by + 50), 8)
        pygame.draw.circle(screen, WHITE, (bx - 25, by + 65), 5)
        
    # 2. Humming Notes
    if state["idle"]["humming"]["is_active"] or state["idle"]["humming"]["notes"]:
        for n in state["idle"]["humming"]["notes"]:
            draw_music_note(screen, n["pos"], 1.0) # Procedural note

    # 3. Needs Interaction UI (Floating buttons on face)
    if state["needs"]["show_interaction"]:
        # Draw semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0,0))
        
        # Draw 3 buttons: FOOD, PLAY, SLEEP
        # Icons/Colors for buttons
        btns = [
            ("FOOD", PINK, (80, 240, 80, 40), "hunger"),
            ("PLAY", YELLOW, (200, 240, 80, 40), "play"),
            ("SLEEP", BLUE, (320, 240, 80, 40), "energy")
        ]
        for label, color, rect, key in btns:
            val = state["needs"][key]
            # Draw BG
            pygame.draw.rect(screen, color, rect, border_radius=8)
            # Draw level bar inside
            bar_w = int(76 * (val/100.0))
            pygame.draw.rect(screen, WHITE, (rect[0]+2, rect[1]+30, bar_w, 6))
            # Text
            txt = FONT_TINY.render(label, False, WHITE)
            screen.blit(txt, (rect[0] + (rect[2]-txt.get_width())//2, rect[1]+5))

        # Close instruction
        instr = FONT_TINY.render("Tap center to hide", False, WHITE)
        screen.blit(instr, (WIDTH//2 - instr.get_width()//2, 290))

    # 4. Floating Hearts
    for h in state["needs"]["hearts"]:
        # Draw a simple heart shape
        hx, hy = h["pos"]
        pygame.draw.circle(screen, PINK, (int(hx-4), int(hy)), 5)
        pygame.draw.circle(screen, PINK, (int(hx+4), int(hy)), 5)
        pygame.draw.polygon(screen, PINK, [(int(hx-9), int(hy+2)), (int(hx+9), int(hy+2)), (int(hx), int(hy+10))])

def draw_click_crosshair(screen):
    """Draw a visual crosshair feedback at the last click position"""
    now = time.time()
    diff = now - state["click_feedback"]["time"]
    if diff < 1.0:
        x, y = state["click_feedback"]["pos"]
        # Fade out effect
        alpha = int(255 * (1.0 - diff))
        # Use a temporary surface for alpha crosshair
        cross_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        color = (255, 255, 255, alpha)
        # Draw circle
        pygame.draw.circle(cross_surf, color, (20, 20), 10, 2)
        # Draw cross lines
        pygame.draw.line(cross_surf, color, (20, 5), (20, 15), 2)
        pygame.draw.line(cross_surf, color, (20, 25), (20, 35), 2)
        pygame.draw.line(cross_surf, color, (int(WIDTH/2-15+x-x), 20), (int(WIDTH/2-5+x-x), 20), 2) # Just kidding on the math
        # Real lines:
        pygame.draw.line(cross_surf, color, (5, 20), (15, 20), 2)
        pygame.draw.line(cross_surf, color, (25, 20), (35, 20), 2)
        
        screen.blit(cross_surf, (x - 20, y - 20))
        # Keep redraw active during the 1s window
        state["needs_redraw"] = True

def draw_menu(screen):
    screen.fill(WHITE)
    current_menu_id = state["menu_stack"][-1]
    items = MENUS.get(current_menu_id, MENUS["MAIN"])
    
    pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, 50))
    title = FONT_MEDIUM.render(f"BMO MENU: {current_menu_id}", False, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 10))
    
    # Pagination Logic
    items_per_page = 5
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    
    # Clamp page
    if state["menu_page"] >= total_pages: state["menu_page"] = total_pages - 1
    if state["menu_page"] < 0: state["menu_page"] = 0
    
    page = state["menu_page"]
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    visible_items = items[start_idx:end_idx]
    
    start_y = 60
    item_height = 40
    margin = 5
    
    # Draw Menu Items
    for i, item in enumerate(visible_items):
        y = start_y + i * (item_height + margin)
        btn_rect = (40, y, 400, item_height)
        pygame.draw.rect(screen, item.get("color", GRAY), btn_rect)
        lbl = FONT_SMALL.render(item["label"], False, BLACK)
        screen.blit(lbl, (WIDTH//2 - lbl.get_width()//2, y + 10))

    # Draw Navigation Buttons (Bottom Area)
    nav_y = start_y + 5 * (item_height + margin)
    
    if page > 0:
        # PREV Button
        prev_rect = (40, nav_y, 190, item_height)
        pygame.draw.rect(screen, GRAY, prev_rect)
        lbl = FONT_SMALL.render("< PREV", False, BLACK)
        screen.blit(lbl, (prev_rect[0] + prev_rect[2]//2 - lbl.get_width()//2, nav_y + 10))
        
    if page < total_pages - 1:
        # NEXT Button
        next_rect = (250, nav_y, 190, item_height)
        pygame.draw.rect(screen, GRAY, next_rect)
        lbl = FONT_SMALL.render("NEXT >", False, BLACK)
        screen.blit(lbl, (next_rect[0] + next_rect[2]//2 - lbl.get_width()//2, nav_y + 10))

def draw_stats(screen):
    screen.fill(YELLOW)
    temp = get_cpu_temp()
    ram = get_ram_usage()
    y = 40
    lbl = FONT_MEDIUM.render(f"CPU: {temp:.1f}C", False, BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, BLACK, (40, y+40, 400, 30), 2)
    w = int(396 * (temp / 85.0))
    pygame.draw.rect(screen, RED if temp > 60 else GREEN, (42, y+42, w, 26))
    y += 100
    lbl = FONT_MEDIUM.render(f"RAM: {ram:.1f}%", False, BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, BLACK, (40, y+40, 400, 30), 2)
    w = int(396 * (ram / 100.0))
    pygame.draw.rect(screen, BLUE, (42, y+42, w, 26))

def draw_clock(screen):
    screen.fill(BLUE)
    t = time.strftime("%H:%M:%S")
    d = time.strftime("%A, %b %d")
    lbl_t = FONT_LARGE.render(t, False, WHITE)
    lbl_d = FONT_MEDIUM.render(d, False, WHITE)
    screen.blit(lbl_t, (WIDTH//2 - lbl_t.get_width()//2, 100))
    screen.blit(lbl_d, (WIDTH//2 - lbl_d.get_width()//2, 180))

def draw_notes(screen):
    screen.fill(RED)
    msg = state["love_note"]
    words = msg.split(' ')
    lines = []
    line = []
    for w in words:
        line.append(w)
        if FONT_MEDIUM.size(' '.join(line))[0] > 400:
            line.pop()
            lines.append(' '.join(line))
            line = [w]
    lines.append(' '.join(line))
    y = 100
    for l in lines:
        surf = FONT_MEDIUM.render(l, False, WHITE)
        screen.blit(surf, (WIDTH//2 - surf.get_width()//2, y))
        y += 40

def draw_heart(screen):
    screen.fill(PINK)
    pulse = (time.time() * 3) % 1.5
    scale = 1.0 + (pulse if pulse < 0.5 else 0)
    center = (WIDTH//2, HEIGHT//2)
    size = 20 * scale
    pts = [
        (center[0], center[1] + 3*size),
        (center[0] - 4*size, center[1] - size),
        (center[0] - 2*size, center[1] - 3*size),
        (center[0], center[1] - size),
        (center[0] + 2*size, center[1] - 3*size),
        (center[0] + 4*size, center[1] - size)
    ]
    pygame.draw.polygon(screen, RED, pts)

# --- FOCUS MODE FUNCTIONS ---
def start_focus_timer(minutes):
    state["focus"]["duration"] = minutes * 60
    state["focus"]["end_time"] = time.time() + (minutes * 60)
    state["focus"]["active"] = True
    state["mode"] = "FOCUS"

def draw_focus_face(screen):
    screen.fill(TEAL)
    
    remaining = state["focus"]["end_time"] - time.time()
    
    if remaining <= 0:
        # Time's Up! Celebrate!
        state["focus"]["active"] = False
        
        # Happy Face (Eyes Closed >_< or Excitement)
        # Left Eye (>)
        pygame.draw.lines(screen, BLACK, False, [(125, 110), (140, 125), (125, 140)], 5)
        # Right Eye (<)
        pygame.draw.lines(screen, BLACK, False, [(355, 110), (340, 125), (355, 140)], 5)
        
        # Mouth (Open D)
        pygame.draw.circle(screen, BLACK, (240, 200), 40) # Filled mouth
        pygame.draw.rect(screen, TEAL, (200, 160, 80, 40)) # Cut top half
        
        # Text
        txt = FONT_MEDIUM.render("GOOD JOB!", False, BLACK)
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 50))
        
        hint = FONT_SMALL.render("Tap to finish", False, BLACK)
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, 280))
        
        return

    # Focus Mode (Glasses)
    # Glasses Frames (Squares)
    pygame.draw.rect(screen, BLACK, (110, 90, 60, 60), 4) # Left lens
    pygame.draw.rect(screen, BLACK, (310, 90, 60, 60), 4) # Right lens
    # Bridge
    pygame.draw.line(screen, BLACK, (170, 120), (310, 120), 4)
    # Sides
    pygame.draw.line(screen, BLACK, (110, 120), (60, 110), 4)
    pygame.draw.line(screen, BLACK, (370, 120), (420, 110), 4)
    
    # Eyes (Small dots focused)
    pygame.draw.circle(screen, BLACK, (140, 120), 5)
    pygame.draw.circle(screen, BLACK, (340, 120), 5)
    
    # Mouth (Concentrated line)
    pygame.draw.line(screen, BLACK, (220, 200), (260, 200), 4)
    
    # Timer Text
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    timer_txt = f"{mins:02d}:{secs:02d}"
    
    txt = FONT_MEDIUM.render(timer_txt, False, BLACK)
    # Background for timer text for readability
    # pygame.draw.rect(screen, WHITE, (WIDTH//2 - 50, 250, 100, 40))
    screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 260))
    
    # Progress Bar at bottom
    total = state["focus"]["duration"]
    progress = 1.0 - (remaining / total)
    pygame.draw.rect(screen, BLACK, (40, 300, 400, 10), 1)
    pygame.draw.rect(screen, GREEN, (41, 301, int(398 * progress), 8))

def main():
    # singleton check
    try:
        lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        lock_socket.bind('\0bmo_instance_lock')
    except socket.error:
        print("BMO is already running!")
        sys.exit(0)

    # Load Config
    config = load_config()
    state["brightness"] = config.get("brightness", 1.0)
    state["default_mode"] = config.get("default_mode", "FACE")

    # Load initial face
    load_random_face()

    t = threading.Thread(target=touch_thread, daemon=True)
    t.start()
    clock = pygame.time.Clock()
    fb_fd = os.open(FB_DEVICE, os.O_RDWR)
    
    start_time = time.time()
    frame_count = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                now = time.time()
                state["tap_times"].append(now)
                state["tap_times"] = state["tap_times"][-5:]
                
                if len(state["tap_times"]) == 5:
                    if state["tap_times"][-1] - state["tap_times"][0] < 2.0:
                        auto_update_and_restart()

                state["click_feedback"]["pos"] = (x, y)
                state["click_feedback"]["time"] = now

                state["last_touch_pos"] = (x, y)
                state["last_touch_pos_time"] = now
                state["last_interaction"] = now
                
                # If showing a pop-up face, any touch dismisses it
                if state["is_showing_pop_face"]:
                    state["is_showing_pop_face"] = False
                    state["pop_face_timer"] = time.time() + random.uniform(50, 70)
                    state["needs_redraw"] = True
                    continue # Ignore this touch for the underlying mode
                
                state["needs_redraw"] = True
                if state["mode"] == "STARTUP":
                    switch_to_face_mode()
                elif state["mode"] == "FACE":
                    # If tapping face, toggle interaction UI
                    if WIDTH/4 < x < 3*WIDTH/3 and HEIGHT/4 < y < 3*HEIGHT/4:
                        state["needs"]["show_interaction"] = not state["needs"]["show_interaction"]
                    
                    # Handle interaction buttons if they are shown
                    if state["needs"]["show_interaction"]:
                        if 80 < x < 160 and 240 < y < 280: # FOOD
                            state["needs"]["hunger"] = min(100, state["needs"]["hunger"] + 20)
                            spawn_hearts(x, y)
                        elif 200 < x < 280 and 240 < y < 280: # PLAY
                            state["needs"]["play"] = min(100, state["needs"]["play"] + 25)
                            spawn_hearts(x, y)
                        elif 320 < x < 400 and 240 < y < 280: # SLEEP
                            state["needs"]["energy"] = min(100, state["needs"]["energy"] + 30)
                            spawn_hearts(x, y)
                        else:
                            # Tapping outside buttons while UI is up hides it
                            state["needs"]["show_interaction"] = False
                    else:
                        # Normal face tap -> Menu
                        state["mode"] = "MENU"
                        state["menu_stack"] = ["MAIN"]
                        state["menu_page"] = 0 # Reset page when entering menu
                    
                    state["needs_redraw"] = True
                
                elif state["mode"] == "MENU":
                    current_menu_id = state["menu_stack"][-1]
                    items = MENUS.get(current_menu_id, MENUS["MAIN"])
                    
                    # Layout Params (same as draw)
                    start_y = 60
                    item_height = 40
                    margin = 5
                    nav_y = start_y + 5 * (item_height + margin)
                    
                    # Check Item Clicks
                    clicked_item_idx = -1
                    if start_y <= y < nav_y:
                        row = (y - start_y) // (item_height + margin)
                        if 0 <= row < 5:
                            # Map row to item index based on page
                            real_idx = (state["menu_page"] * 5) + int(row)
                            if real_idx < len(items):
                                clicked_item_idx = real_idx
                    
                    # Check Nav Clicks
                    elif nav_y <= y < nav_y + item_height:
                        # Left (Prev) or Right (Next)
                        if x < WIDTH // 2: # PREV
                            if state["menu_page"] > 0:
                                state["menu_page"] -= 1
                        else: # NEXT
                            total_pages = (len(items) + 5 - 1) // 5
                            if state["menu_page"] < total_pages - 1:
                                state["menu_page"] += 1
                                
                    if clicked_item_idx != -1:
                        action = items[clicked_item_idx]["action"]
                        if action == "BACK":
                            state["menu_stack"].pop()
                            state["menu_page"] = 0 # Reset page when going back
                            if not state["menu_stack"]: switch_to_face_mode()
                        elif action.startswith("MENU:"):
                            state["menu_stack"].append(action.split(":")[1])
                            state["menu_page"] = 0 # Reset page for new menu
                        elif action.startswith("MODE:"):
                            state["mode"] = action.split(":")[1]
                            state["menu_page"] = 0
                            if state["mode"] == "NOTES": state["love_note"] = random.choice(LOVE_NOTES)
                            if state["mode"] == "SNAKE": state["snake"] = None # Reset game
                        elif action.startswith("SLIDESHOW:"):
                            start_slideshow(action.split(":")[1])
                        elif action.startswith("GIF:"):
                            start_gif_player(action.split(":")[1])
                        elif action.startswith("TEXT:"):
                            start_text_viewer(action.split(":")[1])
                        elif action.startswith("FOCUS:"):
                            mins = int(action.split(":")[1])
                            start_focus_timer(mins)
                        elif action.startswith("BRIGHTNESS:"):
                            state["brightness"] = float(action.split(":")[1])
                            save_config()
                        elif action.startswith("SET_DEFAULT:"):
                            state["default_mode"] = action.split(":")[1]
                            save_config()
                            # Pop back to SETTINGS menu
                            if len(state["menu_stack"]) > 1:
                                state["menu_stack"].pop()
                            state["menu_page"] = 0
                            state["mode"] = "MENU"
                
                elif state["mode"] == "FOCUS":
                    # If active, ignore touches? Or allow double tap to cancel?
                    # For now: Any touch returns to menu (CANCEL)
                    # But if Timer Ended: Return to Face
                    remaining = state["focus"]["end_time"] - time.time()
                    if remaining <= 0:
                        switch_to_face_mode()
                    else:
                        # Cancel Timer?
                        state["mode"] = "MENU" # Or ask confirmation?
                
                
                elif state["mode"] in ["SLIDESHOW", "GIF_PLAYER", "TEXT_VIEWER"]:
                    # Touch navigation: Left = Previous, Center = Exit, Right = Next
                    # Update touch time to show arrows
                    if state["mode"] == "SLIDESHOW":
                        state["slideshow"]["last_touch_time"] = time.time()
                    elif state["mode"] == "GIF_PLAYER":
                        state["gif_player"]["last_touch_time"] = time.time()
                    
                    if x < WIDTH / 3:
                        # LEFT: Previous
                        if state["mode"] == "SLIDESHOW":
                            imgs = state["slideshow"]["images"]
                            if imgs and imgs[0] != "PLACEHOLDER_EMPTY":
                                state["slideshow"]["index"] = (state["slideshow"]["index"] - 2) % len(imgs)
                                state["slideshow"]["last_switch"] = 0  # Force immediate load
                        elif state["mode"] == "GIF_PLAYER":
                            gifs = state["gif_player"]["gifs"]
                            if gifs:
                                state["gif_player"]["current_gif_index"] = (state["gif_player"]["current_gif_index"] - 1) % len(gifs)
                                state["gif_player"]["gif_switch_time"] = time.time()
                                load_next_gif()
                        # TEXT_VIEWER: no previous/next for now
                    
                    elif x > 2 * WIDTH / 3:
                        # RIGHT: Next
                        if state["mode"] == "SLIDESHOW":
                            state["slideshow"]["last_switch"] = 0  # Force immediate switch
                        elif state["mode"] == "GIF_PLAYER":
                            gifs = state["gif_player"]["gifs"]
                            if gifs:
                                state["gif_player"]["current_gif_index"] = (state["gif_player"]["current_gif_index"] + 1) % len(gifs)
                                state["gif_player"]["gif_switch_time"] = time.time()
                                load_next_gif()
                    
                    else:
                        # CENTER: Exit to menu
                        state["mode"] = "MENU"
                
                elif state["mode"] == "SNAKE":
                    if state["snake"]:
                        if state["snake"].game_over:
                            state["mode"] = "MENU"
                        else:
                            state["snake"].handle_input((x, y))
                
                else: 
                    state["mode"] = "MENU"
        
        # --- UPDATE PHASE ---
        now = time.time()
        always_update = state["mode"] in ["SNAKE", "GIF_PLAYER", "STARTUP", "SLIDESHOW", "CLOCK"]
        
        # Inactivity Check
        if state["mode"] in ["MENU", "STATS", "CLOCK", "NOTES", "HEART", "SETTINGS", "GAMES"]:
            if now - state["last_interaction"] > 20:
                print("Inactivity timeout: Returning to FACE")
                switch_to_face_mode()
        
        # Pop-up Check
        if not state["is_showing_pop_face"] and state["mode"] not in ["FACE", "SNAKE", "STARTUP"]:
            if now > state["pop_face_timer"]:
                state["is_showing_pop_face"] = True
                state["pop_face_end_time"] = now + 5.0
                state["needs_redraw"] = True
                load_random_face()

        # State updates
        if state["is_showing_pop_face"] or state["mode"] == "FACE":
            update_face()
        elif state["mode"] == "STARTUP":
            update_startup()
        elif state["mode"] == "SLIDESHOW":
            update_slideshow()
        elif state["mode"] == "GIF_PLAYER":
            update_gif()
        elif state["mode"] == "SNAKE":
            if state["snake"] is None:
                state["snake"] = SnakeGame(WIDTH, HEIGHT)
            state["snake"].update()
        
        # --- DRAW & WRITE PHASE (Strictly lazy) ---
        if state["needs_redraw"] or always_update:
            # 1. Background / Core Mode Drawing
            if state["is_showing_pop_face"]:
                draw_face(screen)
                if now > state["pop_face_end_time"]:
                    state["is_showing_pop_face"] = False
                    state["pop_face_timer"] = now + random.uniform(50, 70)
                    state["needs_redraw"] = True
            elif state["mode"] == "STARTUP":
                draw_startup(screen)
            elif state["mode"] == "SLIDESHOW":
                draw_slideshow(screen)
            elif state["mode"] == "GIF_PLAYER":
                draw_gif(screen)
            elif state["mode"] == "TEXT_VIEWER":
                draw_text_viewer(screen)
            elif state["mode"] == "FOCUS":
                draw_focus_face(screen)
            elif state["mode"] == "FACE": 
                draw_face(screen)
            elif state["mode"] == "WEATHER":
                draw_weather(screen)
            elif state["mode"] == "ADVANCED_STATS":
                draw_advanced_stats(screen)
            elif state["mode"] == "MENU": draw_menu(screen)
            elif state["mode"] == "STATS": draw_stats(screen)
            elif state["mode"] == "CLOCK": draw_clock(screen)
            elif state["mode"] == "NOTES": draw_notes(screen)
            elif state["mode"] == "HEART": draw_heart(screen)
            elif state["mode"] == "SNAKE":
                state["snake"].draw(screen)

            # 2. Visual Feedback Layer (Crosshair)
            draw_click_crosshair(screen)

            # 3. Dimming (Apply directly before write)
            if state["brightness"] < 1.0:
                if state["cached_dim_surf"] is None or state["last_brightness"] != state["brightness"]:
                    dim_val = int(state["brightness"] * 255)
                    state["cached_dim_surf"] = pygame.Surface((WIDTH, HEIGHT), depth=16, masks=screen.get_masks())
                    state["cached_dim_surf"].fill((dim_val, dim_val, dim_val))
                    state["last_brightness"] = state["brightness"]
                screen.blit(state["cached_dim_surf"], (0, 0), special_flags=pygame.BLEND_MULT)

            # 3. Framebuffer Write (Contiguous)
            try:
                os.lseek(fb_fd, 0, os.SEEK_SET)
                os.write(fb_fd, screen.get_buffer())
                state["needs_redraw"] = False
            except Exception as e:
                print(f"Framebuffer Write Error: {e}")
                sys.stdout.flush()
                sys.exit(1)
            
        clock.tick(30)
        frame_count += 1
    
    os.close(fb_fd)
    pygame.quit()

if __name__ == "__main__":
    main()
