import os, time, socket, random, threading
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- FONTS (Native 480x320 sizing) ---
try:
    FONT_LARGE = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
    FONT_MEDIUM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    FONT_SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 25)
except:
    FONT_LARGE = FONT_MEDIUM = FONT_SMALL = ImageFont.load_default() # Fallback to default


# --- CONFIG ---
WIDTH, HEIGHT = 480, 320
FB_DEVICE = "/dev/fb0" # Swapped after GPU activation
TOUCH_DEVICE = "/dev/input/event6" # Changed after reboot (Check dmesg)
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
                        
                        # Hitbox Menu Button (NOW ANYWHERE ON FACE)
                        if state["current_mode"] == "FACE":
                            state["current_mode"] = "MENU"
                            state["needs_redraw"] = True
                        
                        # Hitbox Menu Options
                        elif state["current_mode"] == "MENU":
                            item_h = 32
                            if 80 < sy < 80 + item_h: state["current_mode"] = "FACE"
                            elif 80 + item_h < sy < 80 + 2*item_h: state["current_mode"] = "STATS"
                            elif 80 + 2*item_h < sy < 80 + 3*item_h: state["current_mode"] = "MESSAGE"
                            elif 80 + 3*item_h < sy < 80 + 4*item_h: state["current_mode"] = "CLOCK"
                            elif 80 + 4*item_h < sy < 80 + 5*item_h: 
                                state["current_mode"] = "NOTES"
                                state["love_note"] = random.choice(LOVE_NOTES)
                            elif 80 + 5*item_h < sy < 80 + 6*item_h: state["current_mode"] = "HEART"
                            # Removed DESKTOP mode
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
    """Neo-Retro High Contrast Stats"""
    draw.text((40, 30), "SYSTEM STATUS", fill=BLACK, font=FONT_MEDIUM)
    
    # CPU Gauge (HEAVY)
    temp = get_cpu_temp()
    draw.text((40, 90), f"TEMP: {int(temp)}C", fill=BLACK, font=FONT_SMALL)
    draw.rectangle([40, 125, 440, 165], outline=BLACK, width=6)
    w = int(390 * min(temp/80, 1))
    color = (50, 220, 100) if temp < 55 else (255, 80, 80)
    if w > 0: draw.rectangle([45, 130, 40+w, 160], fill=color)

    # RAM Gauge (HEAVY)
    ram = get_ram_usage()
    draw.text((40, 190), f"ENERGY: {int(ram)}%", fill=BLACK, font=FONT_SMALL)
    draw.rectangle([40, 225, 440, 265], outline=BLACK, width=6)
    w = int(390 * (ram/100))
    if w > 0: draw.rectangle([45, 230, 40+w, 260], fill=(100, 180, 255))
    
    # Personal note area
    draw.text((120, 180), "From your friend,", fill=BLACK, font=FONT_SMALL)
    draw.text((140, 210), "with love ♥", fill=(200, 50, 100), font=FONT_MEDIUM)

def draw_clock(draw):
    """Bold Modern Clock"""
    current_time = time.strftime("%H:%M")
    draw.text((80, 100), current_time, fill=BLACK, font=FONT_LARGE)
    draw.text((80, 180), time.strftime("%A").upper(), fill=BLACK, font=FONT_MEDIUM)

def draw_notes(draw):
    """Heavy Border Note"""
    draw_face(draw, "happy")
    draw.rectangle([30, 180, 450, 300], fill=WHITE, outline=BLACK, width=6)
    draw.text((60, 220), state["love_note"], fill=BLACK, font=FONT_SMALL)

def draw_heart(draw, pulse):
    """Massive Stylized Heart"""
    cx, cy = 240, 160
    size = int(100 + pulse * 30)
    # Drawing heart with thick outlines
    draw.ellipse([cx-size, cy-size, cx, cy], fill=PINK, outline=BLACK, width=4)
    draw.ellipse([cx, cy-size, cx+size, cy], fill=PINK, outline=BLACK, width=4)
    draw.polygon([(cx-size, cy-size//4), (cx+size, cy-size//4), (cx, cy+size)], fill=PINK, outline=BLACK, width=4)
    draw.text((180, 135), "MINE", fill=WHITE, font=FONT_MEDIUM)






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
                # 1. Back to Native Resolution (480x320)
                img = Image.new('RGB', (WIDTH, HEIGHT), BMO_COLOR)
                draw = ImageDraw.Draw(img)
                
                # 2. Render content
                if state["current_mode"] == "FACE":
                    draw_face(draw, state["expression"])
                elif state["current_mode"] == "MENU":
                    draw.rectangle([40, 20, 440, 310], fill=WHITE, outline=BLACK, width=6)
                    draw.text((70, 35), "SELECT MODE", fill=BLACK, font=FONT_MEDIUM)
                    options = ["1. FACE", "2. STATS", "3. WISH", "4. CLOCK", "5. NOTES", "6. HEART"]
                    for i, opt in enumerate(options):
                        draw.text((80, 90 + i*30), opt, fill=BLACK, font=FONT_SMALL)
                elif state["current_mode"] == "STATS":
                    draw_stats(draw)
                elif state["current_mode"] == "MESSAGE":
                    draw.rectangle([30, 30, 450, 290], outline=BLACK, width=8)
                    draw.text((70, 80), "HAPPY", fill=BLACK, font=FONT_LARGE)
                    draw.text((70, 160), "BIRTHDAY!", fill=BLACK, font=FONT_LARGE)
                elif state["current_mode"] == "CLOCK":
                    draw_clock(draw)
                elif state["current_mode"] == "NOTES":
                    draw_notes(draw)
                elif state["current_mode"] == "HEART":
                    t = now * 1.5
                    pulse = (abs(np.sin(t * np.pi)) ** 30) * 0.5 + (abs(np.sin(t * np.pi - 1.5)) ** 30) * 1.0
                    draw_heart(draw, min(pulse, 1.2))
                # Global Menu Button (Arcade Style) REMOVED


                # 3. Filter and Write
                if img:
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
	