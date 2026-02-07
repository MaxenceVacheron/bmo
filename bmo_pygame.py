import os
import sys
import time
import random
import pygame
import threading
from evdev import InputDevice, ecodes

# --- CONFIGURATION ---
WIDTH, HEIGHT = 480, 320
FB_DEVICE = "/dev/fb0"
TOUCH_DEVICE = "/dev/input/event6" # Ensure this matches detected device

# Initialize Pygame Headless
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()

# Create Surface matching Framebuffer format (RGB565)
# Create Surface matching Framebuffer format (BGR565) explicitly
# R mask: 0000000000011111 (0x001F)
# G mask: 0000011111100000 (0x07E0)
# B mask: 1111100000000000 (0xF800)
screen = pygame.Surface((WIDTH, HEIGHT), depth=16, masks=(0x001F, 0x07E0, 0xF800, 0))

# Colors
BLACK = (20, 24, 28)
WHITE = (245, 247, 250)
TEAL = (100, 220, 200)
PINK = (255, 148, 178)
YELLOW = (241, 196, 15)
RED = (231, 76, 60)
BLUE = (52, 152, 219)
GREEN = (46, 204, 113)

# Fonts
try:
    FONT_LARGE = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
    FONT_MEDIUM = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 35)
    FONT_SMALL = pygame.font.Font("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
except:
    FONT_LARGE = pygame.font.SysFont(None, 60)
    FONT_MEDIUM = pygame.font.SysFont(None, 35)
    FONT_SMALL = pygame.font.SysFont(None, 20)

# State
state = {
    "mode": "FACE",
    "expression": "happy",
    "last_interaction": 0,
    "love_note": "You are amazing!",
}

stats = {"cpu_temp": 0, "ram_usage": 0, "last_update": 0}

LOVE_NOTES = [
    "You are amazing!",
    "BMO loves you! <3",
    "Have a great day!",
    "You're my favorite!",
    "I'm happy to be yours!",
    "You look great today!",
]

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
        current_touch_id = None
        
        for event in dev.read_loop():
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_X: raw_x = event.value
                if event.code == ecodes.ABS_Y: raw_y = event.value
            
            elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                if event.value == 1: # Touch Down
                    # Calibrate coordinates (Swap X/Y + Invert Y logic matches current bmo.py)
                    # From bmo.py: sx = WIDTH - ((raw_y / 4095) * WIDTH)
                    #              sy = (raw_x / 4095) * HEIGHT 
                    sx = WIDTH - ((raw_y / 4095.0) * WIDTH)
                    sy = (raw_x / 4095.0) * HEIGHT
                    
                    # Post Pygame Event
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(sx), int(sy)), 'button': 1}))
                    
    except Exception as e:
        print(f"Touch Input Error: {e}")

# --- DRAWING FUNCTIONS ---
def draw_face(screen):
    screen.fill(TEAL)
    pygame.draw.circle(screen, BLACK, (140, 120), 15)
    pygame.draw.circle(screen, BLACK, (340, 120), 15)
    
    if state["expression"] == "happy":
        pygame.draw.lines(screen, BLACK, False, [(200, 180), (200, 195), (280, 195), (280, 180)], 5)
    
    pygame.draw.circle(screen, PINK, (110, 150), 15)
    pygame.draw.circle(screen, PINK, (370, 150), 15)

def draw_menu(screen):
    screen.fill(WHITE)
    pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, 50))
    title = FONT_MEDIUM.render("BMO MENU", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 10))
    
    options = ["FACE", "STATS", "CLOCK", "NOTES", "HEART"]
    colors = [TEAL, YELLOW, BLUE, RED, PINK]
    
    y = 60
    for i, opt in enumerate(options):
        btn_rect = (40, y + i*50, 400, 40)
        pygame.draw.rect(screen, colors[i % len(colors)], btn_rect)
        lbl = FONT_SMALL.render(opt, True, BLACK)
        screen.blit(lbl, (WIDTH//2 - lbl.get_width()//2, y + i*50 + 10))

def draw_stats(screen):
    screen.fill(YELLOW)
    temp = get_cpu_temp()
    ram = get_ram_usage()
    
    y = 40
    lbl = FONT_MEDIUM.render(f"CPU: {temp:.1f}C", True, BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, BLACK, (40, y+40, 400, 30), 2)
    w = int(396 * (temp / 85.0))
    pygame.draw.rect(screen, RED if temp > 60 else GREEN, (42, y+42, w, 26))
    
    y += 100
    lbl = FONT_MEDIUM.render(f"RAM: {ram:.1f}%", True, BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, BLACK, (40, y+40, 400, 30), 2)
    w = int(396 * (ram / 100.0))
    pygame.draw.rect(screen, BLUE, (42, y+42, w, 26))

def draw_clock(screen):
    screen.fill(BLUE)
    t = time.strftime("%H:%M:%S")
    d = time.strftime("%A, %b %d")
    lbl_t = FONT_LARGE.render(t, True, WHITE)
    lbl_d = FONT_MEDIUM.render(d, True, WHITE)
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
        surf = FONT_MEDIUM.render(l, True, WHITE)
        screen.blit(surf, (WIDTH//2 - surf.get_width()//2, y))
        y += 40

def draw_heart(screen):
    screen.fill(PINK)
    pulse = (time.time() * 3) % 1.5
    scale = 1.0 + (pulse if pulse < 0.5 else 0)
    
    center = (WIDTH//2, HEIGHT//2)
    # Simple polygon heart
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

def main():
    # Start Touch Thread
    t = threading.Thread(target=touch_thread, daemon=True)
    t.start()
    
    clock = pygame.time.Clock()
    
    # Open FB0 for raw write
    fb_fd = os.open(FB_DEVICE, os.O_RDWR)
    
    running = True
    while running:
        # Event Loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                state["last_interaction"] = time.time()
                
                if state["mode"] == "FACE":
                    state["mode"] = "MENU"
                elif state["mode"] == "MENU":
                    clicked_idx = (y - 60) // 50
                    if 0 <= clicked_idx < 5:
                        options = ["FACE", "STATS", "CLOCK", "NOTES", "HEART"]
                        state["mode"] = options[int(clicked_idx)]
                        if state["mode"] == "NOTES":
                            state["love_note"] = random.choice(LOVE_NOTES)
                else:
                    state["mode"] = "MENU"
        
        # Draw Logic
        if state["mode"] == "FACE": draw_face(screen)
        elif state["mode"] == "MENU": draw_menu(screen)
        elif state["mode"] == "STATS": draw_stats(screen)
        elif state["mode"] == "CLOCK": draw_clock(screen)
        elif state["mode"] == "NOTES": draw_notes(screen)
        elif state["mode"] == "HEART": draw_heart(screen)
        
        # Blit to Framebuffer (Zero Copy optimization possible?)
        # Pygame surface buffer is memory view.
        # We need byte string.
        # Check if surface is locked? Usually not unless manual lock.
        # For RGB565 surface, get_buffer returns raw pixel data.
        
        try:
            # Write entire buffer to FB0
            os.lseek(fb_fd, 0, os.SEEK_SET)
            os.write(fb_fd, screen.get_buffer())
        except Exception as e:
            print(f"FB Write Error: {e}")
            
        clock.tick(30) # 30 FPS cap
    
    os.close(fb_fd)
    pygame.quit()

if __name__ == "__main__":
    main()
