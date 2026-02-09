import os
import sys
import json
import pygame

# --- CONFIGURATION ---
WIDTH, HEIGHT = 480, 320

# Detect Environment
IS_RASPBERRY_PI = os.uname().sysname == 'Linux' and 'arm' in os.uname().machine if hasattr(os, 'uname') else False
IS_WINDOWS = sys.platform.startswith('win')

if IS_WINDOWS:
    # Local Development Paths (Relative to project root or user home)
    # Using a local 'bmo_data' folder in the current directory or user home
    BASE_DIR = os.path.join(os.getcwd(), "bmo_data")
    os.makedirs(BASE_DIR, exist_ok=True)
    
    FB_DEVICE = None # No framebuffer on Windows
    TOUCH_DEVICE = None # Mouse simulation
    
    NEXTCLOUD_PATH = os.path.join(BASE_DIR, "nextcloud_mock")
    CONFIG_FILE = os.path.join(BASE_DIR, "bmo_config.json")
    BMO_FACES_ROOT = os.path.join(BASE_DIR, "bmo_faces")
    IDLE_THOUGHT_DIR = os.path.join(BASE_DIR, "idle_thought")
    MESSAGES_FILE = os.path.join(BASE_DIR, "messages.json")
    
    # Ensure dirs exist
    for d in [NEXTCLOUD_PATH, BMO_FACES_ROOT, IDLE_THOUGHT_DIR]:
        os.makedirs(d, exist_ok=True)
        
else:
    # Raspberry Pi Paths (Original)
    FB_DEVICE = "/dev/fb1"
    TOUCH_DEVICE = "/dev/input/event4" 
    NEXTCLOUD_PATH = "/home/pi/mnt/nextcloud/shr/BMO_Agnes"
    CONFIG_FILE = "/home/pi/bmo/bmo_config.json"
    BMO_FACES_ROOT = "/home/pi/bmo/bmo_faces"
    IDLE_THOUGHT_DIR = "/home/pi/bmo/bmo_assets/idle/thought"
    MESSAGES_FILE = "/home/pi/bmo/messages.json"

# API Configuration
SERVER_URL = "https://bmo.pg.maxencevacheron.fr" 
MESSAGES_URL = f"{SERVER_URL}" # GET / (?)
READ_RECEIPT_URL = f"{SERVER_URL}/read" # POST /read
SEND_MESSAGE_URL = f"{SERVER_URL}/send" # POST /send

# --- IDENTITY ---
IDENTITY = os.environ.get("BMO_IDENTITY", "BMO") 

# --- COLORS ---
BLACK = (20, 24, 28)
WHITE = (245, 247, 250)
GRAY = (127, 140, 141)

if IDENTITY == "AMO":
    MAIN_COLOR = (142, 68, 173) # Purple
    ACCENT_COLOR = (46, 204, 113) # Green
    HIGHLIGHT_COLOR = (155, 89, 182) # Lighter Purple
    ALERT_COLOR = (231, 76, 60) # Red
    FACE_COLOR = (155, 89, 182) # Purple Face
else:
    MAIN_COLOR = (165, 215, 185) # Teal
    ACCENT_COLOR = (255, 148, 178) # Pink
    HIGHLIGHT_COLOR = (241, 196, 15) # Yellow
    ALERT_COLOR = (231, 76, 60) # Red
    FACE_COLOR = (165, 215, 185) # Teal Face

# Standard palette aliases
TEAL = (165, 215, 185)
PINK = (255, 148, 178)
YELLOW = (241, 196, 15)
RED = (231, 76, 60)
BLUE = (52, 152, 219)
GREEN = (46, 204, 113)
GREEN_MOUTH = (39, 174, 96)
ORANGE = (230, 126, 34)

# --- FONTS ---
FONT_LARGE = None
FONT_MEDIUM = None
FONT_SMALL = None
FONT_TINY = None

def init_fonts():
    global FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_TINY
    try:
        if IS_WINDOWS:
             # Use generic system font or specific ttf if available
             FONT_LARGE = pygame.font.SysFont("arial", 60, bold=True)
             FONT_MEDIUM = pygame.font.SysFont("arial", 35, bold=True)
             FONT_SMALL = pygame.font.SysFont("arial", 20, bold=True)
             FONT_TINY = pygame.font.SysFont("arial", 15, bold=True)
        else:
            FONT_LARGE = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
            FONT_MEDIUM = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 35)
            FONT_SMALL = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            FONT_TINY = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except:
        FONT_LARGE = pygame.font.SysFont(None, 60)
        FONT_MEDIUM = pygame.font.SysFont(None, 35)
        FONT_SMALL = pygame.font.SysFont(None, 20)
        FONT_TINY = pygame.font.SysFont(None, 15)

# --- LOVE NOTES ---
LOVE_NOTES = [
    "You are amazing!",
    "BMO loves you! <3",
    "Have a great day!",
    "You're my favorite!",
    "I'm happy to be yours!",
    "You look great today!",
]

if IDENTITY == "AMO":
    LOVE_NOTES = [
        "System Operational.",
        "AMO online.",
        "Scanning...",
        "Target acquired: Cute.",
        "Processing affection...",
    ]

# --- MENUS DEFINITION ---
MENUS = {
    "MAIN": [
        {"label": "HOME", "action": "MODE:FACE", "color": MAIN_COLOR},
        {"label": "MESSAGES", "action": "MODE:MESSAGES", "color": ACCENT_COLOR},
        {"label": "WEATHER", "action": "MODE:WEATHER", "color": BLUE},
        {"label": "CLOCK", "action": "MODE:CLOCK", "color": BLUE},
        # Page 2
        {"label": "FOCUS", "action": "MENU:FOCUS", "color": GREEN},
        {"label": "GAMES", "action": "MENU:GAMES", "color": HIGHLIGHT_COLOR},
        {"label": "SYSTEM", "action": "MODE:ADVANCED_STATS", "color": GRAY},
        {"label": "NOTES", "action": "MODE:NOTES", "color": ALERT_COLOR},
        # Page 3
        {"label": "HEART", "action": "MODE:HEART", "color": ACCENT_COLOR},
        {"label": "NEXTCLOUD", "action": "MENU:NEXTCLOUD", "color": BLUE},
        {"label": "SETTINGS", "action": "MENU:SETTINGS", "color": GRAY},
    ],
    "GAMES": [
        {"label": "SNAKE", "action": "MODE:SNAKE", "color": GREEN},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "SETTINGS": [
        {"label": "BRIGHTNESS", "action": "MENU:BRIGHTNESS", "color": MAIN_COLOR},
        {"label": "POWER MGMT", "action": "MENU:POWER", "color": ORANGE},
        {"label": "BOOT MODE", "action": "MENU:DEFAULT_MODE", "color": BLUE},
        {"label": "REBOOT", "action": "SYSTEM:REBOOT", "color": RED},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "BRIGHTNESS": [
        {"label": "25%", "action": "BRIGHTNESS:0.25", "color": MAIN_COLOR},
        {"label": "50%", "action": "BRIGHTNESS:0.50", "color": MAIN_COLOR},
        {"label": "75%", "action": "BRIGHTNESS:0.75", "color": MAIN_COLOR},
        {"label": "100%", "action": "BRIGHTNESS:1.0", "color": MAIN_COLOR},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "POWER": [
        {"label": "ENABLE ECO", "action": "SET_POWER:ON", "color": GREEN},
        {"label": "DISABLE ECO", "action": "SET_POWER:OFF", "color": RED},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "DEFAULT_MODE": [
        {"label": "FACE (Default)", "action": "SET_DEFAULT:FACE", "color": MAIN_COLOR},
        {"label": "CLOCK", "action": "SET_DEFAULT:CLOCK", "color": BLUE},
        {"label": "STATS", "action": "SET_DEFAULT:STATS", "color": HIGHLIGHT_COLOR},
        {"label": "HEART", "action": "SET_DEFAULT:HEART", "color": ACCENT_COLOR},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "FOCUS": [
        {"label": "15 MIN", "action": "FOCUS:15", "color": GREEN},
        {"label": "25 MIN (Pomo)", "action": "FOCUS:25", "color": MAIN_COLOR},
        {"label": "45 MIN", "action": "FOCUS:45", "color": HIGHLIGHT_COLOR},
        {"label": "60 MIN", "action": "FOCUS:60", "color": RED},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "NEXTCLOUD": [
        {"label": "DEFAULT", "action": "MENU:NC_DEFAULT", "color": HIGHLIGHT_COLOR},
        {"label": "PERSO", "action": "MENU:NC_PERSO", "color": GREEN},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "NC_DEFAULT": [
        {"label": "PHOTOS", "action": "MENU:DEFAULT_PHOTOS", "color": HIGHLIGHT_COLOR},
        {"label": "TEXTES", "action": "TEXT:default", "color": GREEN},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "NC_PERSO": [
        {"label": "PHOTOS", "action": "MENU:PERSO_PHOTOS", "color": ACCENT_COLOR},
        {"label": "TEXTES", "action": "TEXT:perso", "color": BLUE},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "DEFAULT_PHOTOS": [
        {"label": "GIFs", "action": "GIF:default", "color": GREEN},
        {"label": "Images", "action": "SLIDESHOW:default", "color": HIGHLIGHT_COLOR},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "PERSO_PHOTOS": [
        {"label": "GIFs", "action": "GIF:perso", "color": GREEN},
        {"label": "Images", "action": "SLIDESHOW:perso", "color": ACCENT_COLOR},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ],
    "TEXTES": [
        {"label": "PERSO", "action": "TEXT:Perso", "color": ACCENT_COLOR},
        {"label": "REMOTE", "action": "TEXT:Remote", "color": BLUE},
        {"label": "< BACK", "action": "BACK", "color": GRAY},
    ]
}

def load_config():
    """Load configuration from file"""
    defaults = {"brightness": 1.0, "default_mode": "FACE", "power_save": False}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return {**defaults, **config}
        except:
            return defaults
    return defaults

def save_config(state):
    """Save configuration to file"""
    config = {
        "brightness": state.get("brightness", 1.0),
        "default_mode": state.get("default_mode", "FACE"),
        "power_save": state.get("power_save", False)
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")
