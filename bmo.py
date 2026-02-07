import os, time, socket, random, threading
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- FONT SETUP ---
try:
    FONT_LARGE = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    FONT_MEDIUM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    FONT_SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
except:
    FONT_LARGE = FONT_MEDIUM = FONT_SMALL = None  # Fallback to default


# --- CONFIG ---
WIDTH, HEIGHT = 480, 320
FB_DEVICE = "/dev/fb1"
TOUCH_DEVICE = "/dev/input/event4" 
BLACK = (20, 24, 28)    # Deep Slate instead of pure black
WHITE = (245, 247, 250)  # Off-white for better contrast
PINK = (255, 148, 178)   # Signature blush / heart color

# Premium Themes
THEMES = [
    {"bg": (145, 201, 178), "accent": (115, 171, 148)}, # Original Mint
    {"bg": (255, 190, 190), "accent": (235, 160, 160)}, # Sakura
    {"bg": (178, 212, 255), "accent": (148, 182, 225)}, # Sky
    {"bg": (250, 230, 170), "accent": (220, 200, 140)}, # Honey
    {"bg": (210, 190, 255), "accent": (180, 160, 225)}, # Lavender
]
active_theme = random.choice(THEMES)
BMO_COLOR = active_theme["bg"]
ACCENT_COLOR = active_theme["accent"]



# --- SYSTEM MONITORING ---
_stats_cache = {"cpu_temp": 0, "ram_usage": 0, "last_update": 0}

def get_cpu_temp():
    """Read CPU temperature from thermal zone (cached for 1 second)"""
    now = time.time()
    if now - _stats_cache["last_update"] > 1.0:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                _stats_cache["cpu_temp"] = int(f.read().strip()) / 1000.0
        except:
            _stats_cache["cpu_temp"] = 0
    return _stats_cache["cpu_temp"]

def get_ram_usage():
    """Get RAM usage percentage (cached for 1 second)"""
    now = time.time()
    if now - _stats_cache["last_update"] > 1.0:
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                mem_total = int(lines[0].split()[1])
                mem_available = int(lines[2].split()[1])
                mem_used = mem_total - mem_available
                _stats_cache["ram_usage"] = (mem_used / mem_total) * 100
        except:
            _stats_cache["ram_usage"] = 0
        _stats_cache["last_update"] = now
    return _stats_cache["ram_usage"]

# --- SYSTEM STATE ---
state = {
    "current_mode": "FACE", 
    "expression": "happy",
    "touch_pos": None,
    "touch_time": 0,
    "last_rendered_data": None,
    "needs_redraw": True,
    "last_mode": None,
    "last_stats_update": 0,
    "last_time_update": "",
    "raw_coords": (0, 0),
    "love_note": "You are amazing!",
    "debug_info": "", # New field for performance logs
}


LOVE_NOTES = [
    "You are amazing!",
    "BMO loves you! ♥",
    "Have a great day, cutie!",
    "You're my favorite human!",
    "I'm so happy to be yours!",
    "You look beautiful today!",
]


# --- TOUCH LOGIC (Y-INVERSION FIXED) ---
def touch_thread():
    from evdev import InputDevice, ecodes
    try:
        dev = InputDevice(TOUCH_DEVICE)
        raw_x, raw_y = 0, 0
        finger_down = False
        for event in dev.read_loop():
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_X: raw_x = event.value
                if event.code == ecodes.ABS_Y: raw_y = event.value
            
            if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                finger_down = (event.value == 1)
            
            if event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                if finger_down:
                    sx = WIDTH - ((raw_y / 4095) * WIDTH)
                    sy = (raw_x / 4095) * HEIGHT 
                    
                    # Only process if this is the START of a touch
                    if state["touch_pos"] is None:
                        state["touch_pos"] = (sx, sy)
                        state["touch_time"] = time.time()
                        state["needs_redraw"] = True
                        
                        # Hitbox Menu Button
                        if sx > 380 and sy < 80:
                            state["current_mode"] = "MENU" if state["current_mode"] != "MENU" else "FACE"
                            state["needs_redraw"] = True
                        
                        # Hitbox Menu Options
                        elif state["current_mode"] == "MENU":
                            item_h = 35
                            if 80 < sy < 80 + item_h: state["current_mode"] = "FACE"
                            elif 80 + item_h < sy < 80 + 2*item_h: state["current_mode"] = "STATS"
                            elif 80 + 2*item_h < sy < 80 + 3*item_h: state["current_mode"] = "MESSAGE"
                            elif 80 + 3*item_h < sy < 80 + 4*item_h: state["current_mode"] = "CLOCK"
                            elif 80 + 4*item_h < sy < 80 + 5*item_h: 
                                state["current_mode"] = "NOTES"
                                state["love_note"] = random.choice(LOVE_NOTES)
                            elif 80 + 5*item_h < sy < 80 + 6*item_h: state["current_mode"] = "HEART"
                            state["needs_redraw"] = True
                else:
                    state["touch_pos"] = None # Reset on release
                    state["needs_redraw"] = True

    except Exception as e: print(f"Touch Error: {e}")

# --- DRAWING MODES ---
def draw_face(draw, expr):
    # Rosy Cheeks (Blush) - ALWAYS THERE BUT FADES
    draw.ellipse([80, 150, 110, 170], fill=(255, 180, 200))
    draw.ellipse([370, 150, 400, 170], fill=(255, 180, 200))
    
    if expr == "happy":
        draw.ellipse([115, 90, 145, 150], fill=BLACK)
        draw.ellipse([335, 90, 365, 150], fill=BLACK)
        # Small cute smile
        draw.arc([220, 200, 260, 230], start=0, end=180, fill=BLACK, width=4)
    elif expr == "surprised":
        draw.ellipse([110, 80, 150, 160], fill=BLACK)
        draw.ellipse([330, 80, 370, 160], fill=BLACK)
        draw.ellipse([220, 200, 260, 240], outline=BLACK, width=4)
    elif expr == "sleepy":
        # Zen slanted eyes
        draw.line([(110, 120), (160, 115)], fill=BLACK, width=6)
        draw.line([(320, 115), (370, 120)], fill=BLACK, width=6)
        draw.line([(220, 210), (260, 210)], fill=BLACK, width=3)

def draw_stats(draw):
    """Modern Dashboard style stats"""
    draw.text((60, 40), "SYSTEM VITALS", fill=BLACK, font=FONT_MEDIUM)
    
    # CPU Gauge
    temp = get_cpu_temp()
    draw.text((60, 90), "CORE TEMP", fill=ACCENT_COLOR, font=FONT_SMALL)
    # Background pill
    draw.rounded_rectangle([60, 115, 420, 135], radius=10, fill=(255, 255, 255, 100), outline=BLACK, width=1)
    # Fill pill
    w = int(360 * min(temp/80, 1))
    color = (80, 200, 120) if temp < 55 else (255, 150, 50)
    if w > 4: draw.rounded_rectangle([62, 117, 60+w, 133], radius=8, fill=color)
    draw.text((360, 90), f"{temp:.1f}°C", fill=BLACK, font=FONT_SMALL)

    # RAM Gauge
    ram = get_ram_usage()
    draw.text((60, 170), "MEMORY LOAD", fill=ACCENT_COLOR, font=FONT_SMALL)
    draw.rounded_rectangle([60, 195, 420, 215], radius=10, fill=(255, 255, 255, 100), outline=BLACK, width=1)
    w = int(360 * (ram/100))
    if w > 4: draw.rounded_rectangle([62, 197, 60+w, 213], radius=8, fill=(100, 150, 255))
    draw.text((360, 170), f"{ram:.1f}%", fill=BLACK, font=FONT_SMALL)


def draw_message(draw):
    """Draw personalized message center"""
    # Background accent
    draw.rectangle([30, 30, 450, 290], outline=WHITE, width=3)
    draw.rectangle([40, 40, 440, 280], outline=BLACK, width=2)
    
    # Main message - large text
    draw.text((90, 100), "Happy Birthday!", fill=BLACK, font=FONT_LARGE)
    
    # Decorative hearts
    for x, y in [(60, 60), (400, 60), (60, 250), (400, 250)]:
        draw.polygon([
            (x, y + 8), (x - 8, y), (x - 4, y - 4),
            (x, y - 2), (x + 4, y - 4), (x + 8, y)
        ], fill=(255, 100, 150))
    
    # Personal note area
    draw.text((120, 180), "From your friend,", fill=BLACK, font=FONT_SMALL)
    draw.text((140, 210), "with love ♥", fill=(200, 50, 100), font=FONT_MEDIUM)

def draw_clock(draw):
    """Minimal Modern Clock"""
    current_time = time.strftime("%H:%M")
    # Centered High-impact time
    draw.text((120, 110), current_time, fill=BLACK, font=FONT_LARGE)
    draw.text((125, 160), time.strftime("%A, %b %d"), fill=ACCENT_COLOR, font=FONT_SMALL)

def draw_notes(draw):
    """Premium Card Note"""
    draw_face(draw, "happy")
    # Floating Glass Card
    draw.rounded_rectangle([40, 180, 440, 280], radius=20, fill=(255, 255, 255, 180), outline=BLACK, width=2)
    draw.text((70, 215), state["love_note"], fill=BLACK, font=FONT_MEDIUM)

def draw_heart(draw, pulse):
    """Artistic Pulsing Heart with Glow"""
    cx, cy = 240, 160
    # Use a more organic pulse rhythm (double beat)
    base_size = int(80 + pulse * 25)
    
    # Draw Inner Glow (only at peak pulse)
    if pulse > 0.6:
        for i in range(2):
            gs = base_size + (i * 15)
            draw.ellipse([cx-gs, cy-gs, cx+gs, cy+gs], outline=(255, 180, 200, 40), width=2)

    # Simplified Vector Heart
    draw.ellipse([cx-base_size, cy-base_size, cx, cy], fill=PINK)
    draw.ellipse([cx, cy-base_size, cx+base_size, cy], fill=PINK)
    draw.polygon([(cx-base_size, cy-base_size//2), (cx+base_size, cy-base_size//2), (cx, cy+base_size)], fill=PINK)
    
    # Minimalist text
    draw.text((195, 145), "MINE", fill=WHITE, font=FONT_MEDIUM)




def convert_to_rgb565(pil_img):
    im_array = np.array(pil_img).astype(np.uint16)
    r, g, b = (im_array[:,:,0] >> 3) << 11, (im_array[:,:,1] >> 2) << 5, (im_array[:,:,2] >> 3)
    return (r | g | b).tobytes()

# --- MAIN LOOP ---
def main():
    threading.Thread(target=touch_thread, daemon=True).start()
    
    with open(FB_DEVICE, "wb") as fb:
        # --- STARTUP ANIMATION: BMO SAYS HELLO ---
        for frame in range(40):
            img = Image.new('RGB', (WIDTH, HEIGHT), BMO_COLOR)
            draw = ImageDraw.Draw(img)
            draw_face(draw, "happy")
            bounce = int(np.sin(frame * 0.4) * 5)
            draw.text((180, 50 + bounce), "HELLO!", fill=BLACK, font=FONT_LARGE)
            fb.write(convert_to_rgb565(img))
            fb.seek(0)
            fb.flush()
            time.sleep(0.05)
        
        while True:

            now = time.time()
            should_render = False
            
            # Check if we need to redraw
            # 1. Mode changed
            if state["current_mode"] != state["last_mode"]:
                should_render = True
                state["last_mode"] = state["current_mode"]
            
            # 2. Touch animation is active
            if state["touch_pos"]:
                elapsed = now - state["touch_time"]
                if elapsed < 0.4:
                    should_render = True
                else:
                    state["touch_pos"] = None
                    should_render = True  # One final draw to clear animation
            
            # 3. Face expression change (surprised -> happy)
            if state["current_mode"] == "FACE":
                current_expr = "surprised" if (now - state["touch_time"] < 1.0) else "happy"
                if current_expr != state["expression"]:
                    state["expression"] = current_expr
                    should_render = True
            
            # 4. Stats mode needs periodic updates (every 2 seconds)
            if state["current_mode"] == "STATS":
                if now - state["last_stats_update"] > 2.0:
                    state["last_stats_update"] = now
                    should_render = True
            
            # 5. Clock mode updates every minute
            if state["current_mode"] == "CLOCK":
                t_str = time.strftime("%H:%M")
                if t_str != state["last_time_update"]:
                    state["last_time_update"] = t_str
                    should_render = True
            
            # 6. Manual redraw flag
            if state["needs_redraw"]:
                should_render = True
                state["needs_redraw"] = False
            
            # 6. Heart animation (pulses every frame)
            if state["current_mode"] == "HEART":
                # Lower FPS for the heart (12 FPS = ~0.083s) 
                # Very stable for SPI screens and looks more like a real heartbeat
                if now - state["touch_time"] > 0.08: 
                    should_render = True
                    state["touch_time"] = now


            
            # 7. Manual redraw flag
            if state["needs_redraw"]:
                should_render = True
                state["needs_redraw"] = False
            
            # Only render if something changed
            if should_render:
                # 1. Create Frame
                img = Image.new('RGB', (WIDTH, HEIGHT), BMO_COLOR)
                draw = ImageDraw.Draw(img)
                
                # 2. Render content based on mode
                if state["current_mode"] == "FACE":
                    draw_face(draw, state["expression"])
                elif state["current_mode"] == "MENU":
                    # Glassmorphism Card
                    draw.rounded_rectangle([40, 30, 440, 300], radius=25, fill=(255, 255, 255, 220), outline=BLACK, width=2)
                    draw.text((170, 45), "BMO DASH", fill=ACCENT_COLOR, font=FONT_SMALL)
                    
                    item_h = 40
                    y_start = 85
                    options = ["DASHBOARD", "HEALTH", "BIRTHDAY", "CLOCK", "NOTES", "HEART"]
                    for i, opt in enumerate(options):
                        # Selector dot
                        draw.ellipse([70, y_start + i*item_h + 10, 80, y_start + i*item_h + 20], fill=ACCENT_COLOR)
                        draw.text((100, y_start + i*item_h), opt, fill=BLACK, font=FONT_SMALL)

                elif state["current_mode"] == "STATS":
                    draw_stats(draw)
                elif state["current_mode"] == "MESSAGE":
                    draw_message(draw)
                elif state["current_mode"] == "CLOCK":
                    draw_clock(draw)
                elif state["current_mode"] == "NOTES":
                    draw_notes(draw)
                if state["current_mode"] == "HEART":
                    # Beating heart effect (Organic double-thump Lub-Dub)
                    t = now * 1.5 # Speed adjustment
                    pulse = (abs(np.sin(t * np.pi)) ** 30) * 0.5 + (abs(np.sin(t * np.pi - 1.5)) ** 30) * 1.0
                    draw_heart(draw, min(pulse, 1.2))

                
                # 3. Menu Button (Global Floating Design)
                if state["current_mode"] != "MENU":
                    draw.rounded_rectangle([390, 15, 465, 65], radius=15, outline=BLACK, width=2, fill=(255, 255, 255, 150))
                    draw.text((405, 30), "•••", fill=BLACK, font=FONT_SMALL)

                # 3. Animation Overlay
                if state["touch_pos"] and state["current_mode"] != "HEART":
                    elapsed = now - state["touch_time"]
                    if elapsed < 0.4:
                        tx, ty = state["touch_pos"]
                        rad = int(elapsed * 80)
                        draw.ellipse([tx-rad, ty-rad, tx+rad, ty+rad], outline=WHITE, width=2)

                # 4. Write to framebuffer ONLY IF data changed
                new_data = convert_to_rgb565(img)
                if new_data != state["last_rendered_data"]:
                    fb.write(new_data)
                    fb.seek(0)
                    fb.flush()
                    state["last_rendered_data"] = new_data



            
            # Sleep longer when idle to reduce CPU and prevent any flicker
            if should_render:
                time.sleep(0.02)  # Short sleep after render
            else:
                time.sleep(0.1)  # Longer sleep when idle (no changes)

if __name__ == "__main__":
    main()
	