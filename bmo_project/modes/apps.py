import pygame
import time
import threading
import json
import urllib.request
import os
from PIL import Image
from .. import config
from .. import utils

# --- WEATHER ---
def get_weather(state):
    """Fetch current weather from wttr.in"""
    try:
        print("Fetching weather...")
        # Add User-Agent to avoid some blocking
        req = urllib.request.Request(
            "http://wttr.in/?format=j1", 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
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
            
            state["weather"].update({
                "temp": f"{temp}°C",
                "city": city,
                "desc": desc,
                "icon": icon,
                "last_update": time.time(),
                "fetching": False
            })
            state["needs_redraw"] = True
            print(f"Weather updated: {city}, {temp}C")
            
    except Exception as e:
        print(f"Error fetching weather: {e}")
        # On failure, wait 1 minute before retry (set last_update so it doesn't retry immediately if we cleared fetching)
        # Actually, just set fetching to False. Main loop checks time.
        # To prevent immediate retry if 20 mins passed, we should fake a last_update to "now - 19 mins"
        # so it retries in 1 min.
        state["weather"]["last_update"] = time.time() - 1140 
        state["weather"]["fetching"] = False
        state["weather"]["desc"] = "Connection Error"

def draw_weather(screen, state):
    screen.fill(config.BLUE) # Nice blue background for weather
    now = time.time()
    
    # Auto-refresh every 20 mins
    # Ensure nested keys exist
    if "fetching" not in state["weather"]: state["weather"]["fetching"] = False
    
    if (now - state["weather"]["last_update"] > 1200) and not state["weather"]["fetching"]:
        state["weather"]["fetching"] = True # Lock
        state["weather"]["desc"] = "Updating..."
        threading.Thread(target=get_weather, args=(state,), daemon=True).start()
    
    # Header area (City)
    pygame.draw.rect(screen, config.BLACK, (0, 0, config.WIDTH, 40))
    city_lbl = config.FONT_SMALL.render(state["weather"]["city"].upper(), True, config.WHITE)
    screen.blit(city_lbl, (config.WIDTH//2 - city_lbl.get_width()//2, 10))

    # Icon
    icon_name = state["weather"]["icon"]
    # Fallback to simple drawing if no image
    # For now, we just draw text if no icon, or simple shapes
    # (Assuming assets might be missing on clean install, we use shapes)
    
    if icon_name == "sun":
        pygame.draw.circle(screen, config.YELLOW, (config.WIDTH//2, 120), 40)
    elif icon_name == "rain":
        pygame.draw.circle(screen, config.GRAY, (config.WIDTH//2, 120), 40)
        pygame.draw.line(screen, config.BLUE, (config.WIDTH//2-10, 150), (config.WIDTH//2-20, 180), 3)
        pygame.draw.line(screen, config.BLUE, (config.WIDTH//2+10, 150), (config.WIDTH//2+20, 180), 3)
    else:
        # Cloud
        pygame.draw.circle(screen, config.WHITE, (config.WIDTH//2 - 20, 120), 30)
        pygame.draw.circle(screen, config.WHITE, (config.WIDTH//2 + 20, 120), 30)

    # Temp
    temp_lbl = config.FONT_LARGE.render(state["weather"]["temp"], True, config.BLACK)
    screen.blit(temp_lbl, (config.WIDTH//2 - temp_lbl.get_width()//2, 210))
    
    # Description
    desc = state["weather"]["desc"]
    desc_lbl = config.FONT_SMALL.render(desc, True, config.BLACK)
    screen.blit(desc_lbl, (config.WIDTH//2 - desc_lbl.get_width()//2, 275))
    
    # Back Hint
    hint = config.FONT_TINY.render("< TAP TO BACK", True, config.WHITE)
    screen.blit(hint, (20, config.HEIGHT - 20))

# --- FOCUS ---
def start_focus_timer(state, minutes):
    # Ensure nested dict exists
    if "focus" not in state:
        state["focus"] = {}
        
    state["focus"]["duration"] = minutes * 60
    state["focus"]["end_time"] = time.time() + (minutes * 60)
    state["focus"]["active"] = True
    state["current_mode"] = "FOCUS"

def draw_focus(screen, state):
    screen.fill(config.TEAL)
    
    if "focus" not in state: state["focus"] = {"end_time": 0, "duration": 1, "active": False}
    
    remaining = state["focus"]["end_time"] - time.time()
    
    if remaining <= 0:
        # Time's Up! Celebrate!
        state["focus"]["active"] = False
        
        # Happy Face (Eyes Closed >_< or Excitement)
        # Left Eye (>)
        pygame.draw.lines(screen, config.BLACK, False, [(125, 110), (140, 125), (125, 140)], 5)
        # Right Eye (<)
        pygame.draw.lines(screen, config.BLACK, False, [(355, 110), (340, 125), (355, 140)], 5)
        
        # Mouth (Open D)
        pygame.draw.circle(screen, config.BLACK, (240, 200), 40) # Filled mouth
        pygame.draw.rect(screen, config.TEAL, (200, 160, 80, 40)) # Cut top half
        
        # Text
        txt = config.FONT_MEDIUM.render("GOOD JOB!", True, config.BLACK)
        screen.blit(txt, (config.WIDTH//2 - txt.get_width()//2, 50))
        
        hint = config.FONT_SMALL.render("Tap to finish", True, config.BLACK)
        screen.blit(hint, (config.WIDTH//2 - hint.get_width()//2, 280))
        
        return

    # Focus Mode (Glasses)
    # Glasses Frames (Squares)
    pygame.draw.rect(screen, config.BLACK, (110, 90, 60, 60), 4) # Left lens
    pygame.draw.rect(screen, config.BLACK, (310, 90, 60, 60), 4) # Right lens
    # Bridge
    pygame.draw.line(screen, config.BLACK, (170, 120), (310, 120), 4)
    # Sides
    pygame.draw.line(screen, config.BLACK, (110, 120), (60, 110), 4)
    pygame.draw.line(screen, config.BLACK, (370, 120), (420, 110), 4)
    
    # Eyes (Small dots focused)
    pygame.draw.circle(screen, config.BLACK, (140, 120), 5)
    pygame.draw.circle(screen, config.BLACK, (340, 120), 5)
    
    # Mouth (Concentrated line)
    pygame.draw.line(screen, config.BLACK, (220, 200), (260, 200), 4)
    
    # Timer Text
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    timer_txt = f"{mins:02d}:{secs:02d}"
    
    txt = config.FONT_MEDIUM.render(timer_txt, True, config.BLACK)
    screen.blit(txt, (config.WIDTH//2 - txt.get_width()//2, 260))
    
    # Progress Bar at bottom
    total = state["focus"]["duration"]
    progress = 1.0 - (remaining / total)
    pygame.draw.rect(screen, config.BLACK, (40, 300, 400, 10), 1)
    pygame.draw.rect(screen, config.GREEN, (41, 301, int(398 * progress), 8))

# --- STATS ---
def draw_advanced_stats(screen, state):
    screen.fill(config.GRAY)
    
    title = config.FONT_MEDIUM.render("BMO SYSTEM STATUS", True, config.WHITE)
    pygame.draw.rect(screen, config.BLACK, (0, 0, config.WIDTH, 50))
    screen.blit(title, (config.WIDTH//2 - title.get_width()//2, 10))
    
    y = 70
    ip = utils.get_ip_address()
    lbl = config.FONT_SMALL.render(f"IP: {ip}", True, config.BLACK)
    screen.blit(lbl, (40, y))
    
    y += 40
    wifi = utils.get_wifi_strength()
    lbl = config.FONT_SMALL.render(f"WIFI SIGNAL: {wifi:.0f}%", True, config.BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, config.BLACK, (40, y+30, 400, 20), 2)
    w = int(396 * (wifi / 100.0))
    if wifi > 0:
        color = config.GREEN if wifi > 50 else config.YELLOW
        pygame.draw.rect(screen, color, (42, y+32, w, 16))
    
    y += 70
    temp = utils.get_cpu_temp()
    lbl = config.FONT_SMALL.render(f"CPU TEMP: {temp:.1f}C", True, config.BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, config.BLACK, (40, y+30, 400, 20), 2)
    w = int(396 * (min(temp, 85) / 85.0))
    color = config.RED if temp > 65 else config.GREEN
    pygame.draw.rect(screen, color, (42, y+32, w, 16))
    
    y += 70
    ram_p, ram_f = utils.get_ram_usage()
    lbl = config.FONT_SMALL.render(f"RAM: {ram_p:.1f}% ({ram_f:.1f} GB Free)", True, config.BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, config.BLACK, (40, y+30, 400, 20), 2)
    w = int(396 * (ram_p / 100.0))
    pygame.draw.rect(screen, config.ORANGE, (42, y+32, w, 16))
    
    # Back Hint
    hint = config.FONT_TINY.render("< TAP TO BACK", True, config.WHITE)
    screen.blit(hint, (20, config.HEIGHT - 20))

# --- NOTES ---
def draw_notes(screen, state):
    screen.fill(config.RED)
    msg = state.get("love_note", "BMO LOVES YOU!")
    words = msg.split(' ')
    lines = []
    line = []
    
    # Word Wrap
    for w in words:
        line.append(w)
        if config.FONT_MEDIUM.size(' '.join(line))[0] > 400:
            line.pop()
            lines.append(' '.join(line))
            line = [w]
    lines.append(' '.join(line))
    
    y = 100
    for l in lines:
        surf = config.FONT_MEDIUM.render(l, True, config.WHITE)
        screen.blit(surf, (config.WIDTH//2 - surf.get_width()//2, y))
        y += 40
        
    # Back Hint
    hint = config.FONT_TINY.render("< TAP TO BACK", True, config.WHITE)
    screen.blit(hint, (20, config.HEIGHT - 20))
