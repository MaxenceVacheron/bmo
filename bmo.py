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
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# BMO Palettes (Randomized on start)
PALETTES = [
    (145, 201, 178), # Original Green
    (255, 200, 200), # Pale Red
    (200, 220, 255), # Soft Blue
    (240, 230, 140), # BMO Yellow
    (220, 180, 255), # Lumpy Purple
]
BMO_COLOR = random.choice(PALETTES)


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
    "last_time_update": "", # Track time change
}

# --- TOUCH LOGIC (Y-INVERSION FIXED) ---
def touch_thread():
    from evdev import InputDevice, ecodes
    try:
        dev = InputDevice(TOUCH_DEVICE)
        raw_x, raw_y = 0, 0
        finger_down = False
        for event in dev.read_loop():
            # Coordinate tracking
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_X: raw_x = event.value
                if event.code == ecodes.ABS_Y: raw_y = event.value
            
            # Touch tracking
            if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                finger_down = (event.value == 1)
            
            # SYN_REPORT means the packet (coordinations + touch state) is complete
            if event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                if finger_down:
                    # CALCULATE with the synchronized coordinates
                    sx = WIDTH - ((raw_y / 4095) * WIDTH)
                    sy = (raw_x / 4095) * HEIGHT 
                    
                    # If this is the start of a touch (pos was None)
                    if state["touch_pos"] is None:
                        state["touch_pos"] = (sx, sy)
                        state["touch_time"] = time.time()
                        state["needs_redraw"] = True
                        
                        # HITBOXES
                        if sx > 380 and sy < 80:
                            new_mode = "MENU" if state["current_mode"] != "MENU" else "FACE"
                            state["current_mode"] = new_mode
                            state["needs_redraw"] = True
                        
                        elif state["current_mode"] == "MENU":
                            new_mode = None
                            if 100 < sy < 140: new_mode = "FACE"
                            elif 140 < sy < 180: new_mode = "STATS"
                            elif 180 < sy < 220: new_mode = "MESSAGE"
                            elif 220 < sy < 260: new_mode = "CLOCK"
                            
                            if new_mode:
                                state["current_mode"] = new_mode
                                state["needs_redraw"] = True
                else:
                    # Finger released
                    pass

    except Exception as e: print(f"Touch Error: {e}")

# --- DRAWING MODES ---
def draw_face(draw, expr):
    if expr == "happy":
        draw.ellipse([110, 90, 150, 150], fill=BLACK)
        draw.ellipse([330, 90, 370, 150], fill=BLACK)
        draw.line([(220, 210), (240, 230), (260, 210)], fill=BLACK, width=6)
    elif expr == "surprised":
        draw.ellipse([100, 70, 160, 170], fill=BLACK)
        draw.ellipse([320, 70, 380, 170], fill=BLACK)
        draw.ellipse([210, 200, 270, 260], outline=BLACK, width=5)
    elif expr == "sleepy":
        # Closed slanted eyes
        draw.line([(100, 110), (160, 130)], fill=BLACK, width=8)
        draw.line([(320, 130), (380, 110)], fill=BLACK, width=8)
        draw.arc([210, 210, 270, 230], start=0, end=180, fill=BLACK, width=4)

def draw_stats(draw):
    """Draw BMO Internal Health screen with CPU temp and RAM usage"""
    # Title
    draw.text((70, 20), "BMO INTERNAL HEALTH", fill=BLACK, font=FONT_MEDIUM)
    
    # CPU Temperature Bar
    cpu_temp = get_cpu_temp()
    draw.text((50, 80), "CORE TEMPERATURE", fill=BLACK, font=FONT_SMALL)
    
    # Temperature bar (0-80°C range)
    bar_x, bar_y, bar_w, bar_h = 50, 110, 320, 30
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], outline=BLACK, width=2)
    
    # Color coding: green (0-50), yellow (50-65), red (65+)
    temp_ratio = min(cpu_temp / 80.0, 1.0)
    fill_width = int(bar_w * temp_ratio)
    if cpu_temp < 50:
        temp_color = (50, 200, 100)
    elif cpu_temp < 65:
        temp_color = (255, 200, 50)
    else:
        temp_color = (255, 80, 80)
    
    if fill_width > 0:
        draw.rectangle([bar_x + 2, bar_y + 2, bar_x + fill_width - 2, bar_y + bar_h - 2], fill=temp_color)
    
    draw.text((bar_x + bar_w + 10, bar_y + 5), f"{cpu_temp:.1f}°C", fill=BLACK, font=FONT_SMALL)
    
    # RAM Usage Bar
    ram_usage = get_ram_usage()
    draw.text((50, 170), "MEMORY ENERGY", fill=BLACK, font=FONT_SMALL)
    
    bar_y = 200
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], outline=BLACK, width=2)
    
    # Energy bar style - darker BMO green for used portion
    ram_ratio = min(ram_usage / 100.0, 1.0)
    fill_width = int(bar_w * ram_ratio)
    if fill_width > 0:
        draw.rectangle([bar_x + 2, bar_y + 2, bar_x + fill_width - 2, bar_y + bar_h - 2], fill=(80, 140, 120))
    
    draw.text((bar_x + bar_w + 10, bar_y + 5), f"{ram_usage:.1f}%", fill=BLACK, font=FONT_SMALL)

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
    """Draw a large digital clock with a sleepy face"""
    draw_face(draw, "sleepy")
    current_time = time.strftime("%H:%M")
    # Draw time in middle
    draw.text((160, 150), current_time, fill=BLACK, font=FONT_LARGE)
    draw.text((170, 30), "BMO SLEEPY TIME", fill=BLACK, font=FONT_SMALL)

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
            
            # Only render if something changed
            if should_render:
                # 1. Create Frame
                img = Image.new('RGB', (WIDTH, HEIGHT), BMO_COLOR)
                draw = ImageDraw.Draw(img)
                
                # 2. Render content based on mode
                if state["current_mode"] == "FACE":
                    draw_face(draw, state["expression"])
                elif state["current_mode"] == "MENU":
                    draw.rectangle([50, 50, 430, 270], fill=(60, 80, 75), outline=WHITE, width=2)
                    draw.text((80, 105), "> 1. BACK TO FACE", fill=WHITE, font=FONT_SMALL)
                    draw.text((80, 145), "> 2. SYSTEM STATS", fill=WHITE, font=FONT_SMALL)
                    draw.text((80, 185), "> 3. MESSAGE CENTER", fill=WHITE, font=FONT_SMALL)
                    draw.text((80, 225), "> 4. BMO CLOCK", fill=WHITE, font=FONT_SMALL)
                elif state["current_mode"] == "STATS":
                    draw_stats(draw)
                elif state["current_mode"] == "MESSAGE":
                    draw_message(draw)
                elif state["current_mode"] == "CLOCK":
                    draw_clock(draw)
                
                # Menu button indicator for all non-menu modes
                if state["current_mode"] != "MENU":
                    draw.rectangle([380, 10, 470, 70], outline=BLACK, width=2)
                    draw.text((395, 30), "MENU", fill=BLACK, font=FONT_SMALL)

                # 3. Animation Overlay
                if state["touch_pos"]:
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
	