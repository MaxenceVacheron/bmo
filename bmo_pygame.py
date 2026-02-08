import os
import sys
import time
import socket
import random
import pygame
import threading
import math
from evdev import InputDevice, ecodes
from PIL import Image
from games.snake import SnakeGame

# --- CONFIGURATION ---
WIDTH, HEIGHT = 480, 320
FB_DEVICE = "/dev/fb0"
TOUCH_DEVICE = "/dev/input/event6" # Ensure this matches detected device
NEXTCLOUD_PATH = "/home/pi/mnt/nextcloud/shr/BMO_Agnes"

# Initialize Pygame Headless
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

# Create Surface matching Framebuffer format (RGB565)
screen = pygame.Surface((WIDTH, HEIGHT), depth=16, masks=(0xF800, 0x07E0, 0x001F, 0))

# Colors
BLACK = (20, 24, 28)
WHITE = (245, 247, 250)
TEAL = (100, 220, 200)
PINK = (255, 148, 178)
YELLOW = (241, 196, 15)
RED = (231, 76, 60)
BLUE = (52, 152, 219)
GREEN = (46, 204, 113)
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
        {"label": "STATS", "action": "MODE:STATS", "color": YELLOW},
        {"label": "CLOCK", "action": "MODE:CLOCK", "color": BLUE},
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
    "last_interaction": 0,
    "love_note": "You are amazing!",
    "menu_stack": ["MAIN"],
    "menu_page": 0,
    "brightness": 1.0, # 1.0 = Max, 0.0 = Black
    "blink_timer": 0, # Time until next blink
    "is_blinking": False,
    "blink_end_time": 0,
    "middle_finger_timer": 0,
    "show_middle_finger": False,
    "middle_finger_end_time": 0,
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
    "snake": None  # Will hold SnakeGame instance
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
        # Animation complete, wait 2 seconds then go to FACE
        if elapsed > len(state["startup"]["message"]) * state["startup"]["char_delay"] + 2.0:
            print("Startup complete, moving to FACE")
            state["mode"] = "FACE"
    else:
        if target_chars != state["startup"]["char_index"]:
            state["startup"]["char_index"] = target_chars
            print(f"Startup progress: {state['startup']['char_index']}/{len(state['startup']['message'])}")

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
    """Update BMO's face state (blinking and occasional middle finger)"""
    now = time.time()
    
    # Blinking logic
    if state["is_blinking"]:
        if now > state["blink_end_time"]:
            state["is_blinking"] = False
            state["blink_timer"] = now + random.uniform(2.0, 6.0)
    else:
        if now > state["blink_timer"]:
            state["is_blinking"] = True
            state["blink_end_time"] = now + 0.15 # Blink duration
    
    # Middle finger easter egg (rare)
    if state["show_middle_finger"]:
        if now > state["middle_finger_end_time"]:
            state["show_middle_finger"] = False
            state["middle_finger_timer"] = now + random.uniform(10.0, 20.0)
    else:
        if state["middle_finger_timer"] == 0:
            state["middle_finger_timer"] = now + random.uniform(5.0, 10.0)
        elif now > state["middle_finger_timer"]:
            # 20% chance to show middle finger
            if random.random() < 0.8:
                state["show_middle_finger"] = True
                state["middle_finger_end_time"] = now + 2.0  # Show for 2 seconds
            state["middle_finger_timer"] = now + random.uniform(5.0, 10.0)

def draw_face(screen):
    screen.fill(TEAL)
    
    if state["is_blinking"]:
        # Draw closed eyes
        pygame.draw.line(screen, BLACK, (125, 120), (155, 120), 5)
        pygame.draw.line(screen, BLACK, (325, 120), (355, 120), 5)
    else:
        # Draw open eyes
        pygame.draw.circle(screen, BLACK, (140, 120), 15)
        pygame.draw.circle(screen, BLACK, (340, 120), 15)
    
    if state["expression"] == "happy":
        pygame.draw.arc(screen, BLACK, (190, 170, 100, 50), 3.14, 6.28, 4)
    
    # Easter egg: middle finger
    if state["show_middle_finger"]:
        # Draw hand/fist at bottom center
        pygame.draw.rect(screen, BLACK, (220, 240, 40, 30))  # Palm
        # Draw middle finger extended upward
        pygame.draw.rect(screen, BLACK, (232, 200, 16, 45))  # Finger

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

    t = threading.Thread(target=touch_thread, daemon=True)
    t.start()
    clock = pygame.time.Clock()
    fb_fd = os.open(FB_DEVICE, os.O_RDWR)
    
    start_time = time.time()
    # Removed old splash loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                state["last_touch_pos"] = (x, y)
                state["last_touch_pos_time"] = time.time()
                state["last_interaction"] = time.time()
                
                if state["mode"] == "STARTUP":
                    state["mode"] = "FACE"
                elif state["mode"] == "FACE":
                    state["mode"] = "MENU"
                    state["menu_stack"] = ["MAIN"]
                    state["menu_page"] = 0 # Reset page when entering menu
                
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
                            if not state["menu_stack"]: state["mode"] = "FACE"
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
                
                elif state["mode"] == "FOCUS":
                    # If active, ignore touches? Or allow double tap to cancel?
                    # For now: Any touch returns to menu (CANCEL)
                    # But if Timer Ended: Return to Face
                    remaining = state["focus"]["end_time"] - time.time()
                    if remaining <= 0:
                        state["mode"] = "FACE"
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
        
        # --- INACTIVITY CHECK ---
        # Return to FACE after 60s of inactivity, unless in a "focus" mode
        if state["mode"] in ["MENU", "STATS", "CLOCK", "NOTES", "HEART", "SETTINGS", "GAMES"]:
            if time.time() - state["last_interaction"] > 60:
                print("Inactivity timeout: Returning to FACE")
                state["mode"] = "FACE"

        # --- UPDATE & DRAW ---
        if state["mode"] == "STARTUP":
            update_startup()
            draw_startup(screen)
        elif state["mode"] == "SLIDESHOW":
            update_slideshow()
            draw_slideshow(screen)
        elif state["mode"] == "GIF_PLAYER":
            update_gif()
            draw_gif(screen)
        elif state["mode"] == "TEXT_VIEWER":
            draw_text_viewer(screen)
        elif state["mode"] == "FOCUS":
            draw_focus_face(screen) # New Draw Function
        elif state["mode"] == "FACE": 
            update_face()
            draw_face(screen)
        elif state["mode"] == "MENU": draw_menu(screen)
        elif state["mode"] == "STATS": draw_stats(screen)
        elif state["mode"] == "CLOCK": draw_clock(screen)
        elif state["mode"] == "NOTES": draw_notes(screen)
        elif state["mode"] == "HEART": draw_heart(screen)
        elif state["mode"] == "SNAKE":
            if state["snake"] is None:
                state["snake"] = SnakeGame(WIDTH, HEIGHT)
            state["snake"].update()
            state["snake"].draw(screen)
        
        # Crosshair Debug (show for 1 second after touch)
        if "last_touch_pos" in state and "last_touch_pos_time" in state:
            if time.time() - state["last_touch_pos_time"] < 1.0:
                tx, ty = state["last_touch_pos"]
                pygame.draw.line(screen, WHITE, (tx-10, ty), (tx+10, ty), 3)
                pygame.draw.line(screen, WHITE, (tx, ty-10), (tx, ty+10), 3)
                pygame.draw.line(screen, BLACK, (tx-10, ty), (tx+10, ty), 1)
                pygame.draw.line(screen, BLACK, (tx, ty-10), (tx, ty+10), 1)
        
        # Apply Software Brightness
        if state["brightness"] < 1.0:
            # Using BLEND_MULT preserves color ratios better than alpha blending
            dim_val = int(state["brightness"] * 255)
            dim_surf = pygame.Surface((WIDTH, HEIGHT))
            dim_surf.fill((dim_val, dim_val, dim_val))
            screen.blit(dim_surf, (0, 0), special_flags=pygame.BLEND_MULT)
        
        try:
            os.lseek(fb_fd, 0, os.SEEK_SET)
            os.write(fb_fd, screen.get_buffer())
        except Exception as e: pass
        clock.tick(30)
    
    os.close(fb_fd)
    pygame.quit()

if __name__ == "__main__":
    main()
