import pygame
import time
import random
import os
import sys
from PIL import Image
from .. import config

# --- HELPER FUNCTIONS ---

def load_random_face(state, emotion=None):
    """Load a random face pair. If emotion is None, uses 20% negative chance."""
    
    # 20% chance for negative if not forced
    if emotion is None:
        emotion = "negative" if random.random() < 0.2 else "positive"
    
    # Check if target emotion directory has images, fallback if needed
    open_dir = os.path.join(config.BMO_FACES_ROOT, emotion, "open")
    if not os.path.exists(open_dir) or not [f for f in os.listdir(open_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]:
        emotion = "positive" # Fallback to positive
        open_dir = os.path.join(config.BMO_FACES_ROOT, "positive", "open")

    state["emotion"] = emotion
    closed_dir = os.path.join(config.BMO_FACES_ROOT, emotion, "closed")
    
    # Always refresh list
    if os.path.exists(open_dir):
        state["face_images"] = [f for f in os.listdir(open_dir) 
                                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    else:
        state["face_images"] = []
    
    if state["face_images"]:
        try:
            filename = random.choice(state["face_images"])
            open_path = os.path.join(open_dir, filename)
            closed_path = os.path.join(closed_dir, filename)
            
            # Helper to load and format surface
            def _prep_surf(path):
                if not os.path.exists(path): return None
                img = Image.open(path).convert('RGB')
                img = img.resize((config.WIDTH, config.HEIGHT), Image.Resampling.LANCZOS)
                data = img.tobytes()
                pygame_img = pygame.image.fromstring(data, img.size, img.mode)
                return pygame_img

            state["current_face_open"] = _prep_surf(open_path)
            state["current_face_closed"] = _prep_surf(closed_path)
            
            # Fallback if closed version doesn't exist
            if state["current_face_closed"] is None:
                state["current_face_closed"] = state["current_face_open"]
                
            state["last_face_switch"] = time.time()
            state["needs_redraw"] = True
        except Exception as e:
            print(f"Error loading face images: {e}")

def load_thought_bubble():
    """Load a random thought bubble icon"""
    if not os.path.exists(config.IDLE_THOUGHT_DIR): return None
    files = [f for f in os.listdir(config.IDLE_THOUGHT_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not files: return None
    path = os.path.join(config.IDLE_THOUGHT_DIR, random.choice(files))
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

def draw_music_note(screen, pos, alpha):
    """Draw a procedural music note"""
    x, y = int(pos[0]), int(pos[1])
    # Simple quaver
    pygame.draw.circle(screen, config.BLACK, (x, y), 6)
    pygame.draw.line(screen, config.BLACK, (x+4, y), (x+4, y-18), 2)
    pygame.draw.line(screen, config.BLACK, (x+4, y-18), (x+12, y-12), 3)

def draw_click_crosshair(screen, state):
    """Draw a simple visual crosshair feedback at the last click position"""
    now = time.time()
    diff = now - state["click_feedback"]["time"]
    if diff < 1.0:
        x, y = state["click_feedback"]["pos"]
        alpha = int(255 * (1.0 - diff))
        cross_surf = pygame.Surface((30, 30), pygame.SRCALPHA)
        color = (255, 255, 255, alpha)
        
        # Simple cross: horizontal and vertical lines
        pygame.draw.line(cross_surf, color, (0, 15), (30, 15), 2)
        pygame.draw.line(cross_surf, color, (15, 0), (15, 30), 2)
        
        screen.blit(cross_surf, (x - 15, y - 15))
        state["needs_redraw"] = True

# --- MAIN FUNCTIONS ---

def update_face(state):
    """Update BMO's face state (blinking, image rotation, and needs)"""
    now = time.time()
    
    # --- NEEDS DECAY ---
    # Decay every 30 seconds for performance
    if now - state["needs"]["last_decay"] > 30:
        elapsed_mins = (now - state["needs"]["last_decay"]) / 60.0
        # Decay rates (per minute)
        state["needs"]["hunger"] = max(0, state["needs"]["hunger"] - (0.11 * elapsed_mins))
        state["needs"]["play"] = max(0, state["needs"]["play"] - (0.16 * elapsed_mins))
        state["needs"]["energy"] = max(0, state["needs"]["energy"] - (0.08 * elapsed_mins))
        state["needs"]["last_decay"] = now
        
        # Update Emotion based on needs
        avg = (state["needs"]["hunger"] + state["needs"]["play"] + state["needs"]["energy"]) / 3.0
        if avg < 40:
            if state["emotion"] != "negative":
                state["emotion"] = "negative"
                load_random_face(state)
        elif avg > 60:
            if state["emotion"] != "positive":
                state["emotion"] = "positive"
                load_random_face(state)

    # --- HEARTS ANIMATION ---
    still_alive = []
    for h in state["needs"]["hearts"]:
        if now < h["end_time"]:
            h["pos"][0] += h["vel"][0]
            h["pos"][1] += h["vel"][1]
            still_alive.append(h)
            state["needs_redraw"] = True
    state["needs"]["hearts"] = still_alive

    # Dynamic rotation interval 
    interval = 22.5 if state.get("emotion") == "negative" else 45.0
    
    if now - state["last_face_switch"] > interval:
        load_random_face(state)
    
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
        else:
            if now > state["idle"]["humming"]["end_time"]:
                if not state["idle"]["humming"]["notes"]: # Wait for notes to vanish
                    state["idle"]["humming"]["is_active"] = False
                    state["idle"]["humming"]["next_time"] = now + random.uniform(20, 90)
                    state["needs_redraw"] = True
            
            # Spawn new notes
            if now < state["idle"]["humming"]["end_time"] and random.random() < 0.1:
                state["idle"]["humming"]["notes"].append({
                    "pos": [random.uniform(100, config.WIDTH-100), 280],
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

def draw_face(screen, state):
    # No need to fill with BLACK if we are blitting a full-screen image
    if state.get("is_blinking", False):
        target_surf = state.get("current_face_closed")
    else:
        target_surf = state.get("current_face_open")

    if target_surf:
        screen.blit(target_surf, (0, 0))
    else:
        # Emergency Fallback - only clear here
        screen.fill(config.FACE_COLOR)
        pygame.draw.circle(screen, config.BLACK, (140, 120), 9)
        pygame.draw.circle(screen, config.BLACK, (340, 120), 9)
        pygame.draw.arc(screen, config.BLACK, (210, 140, 60, 40), 3.14, 6.28, 4)
        
    # --- IDLE OVERLAYS ---
    # 1. Thought Bubble (Top Right)
    if state["idle"]["thought"]["is_active"] and state["idle"]["thought"]["current_image"]:
        # Cloud position
        bx, by = config.WIDTH - 100, 30
        # Draw actual bubble icon
        screen.blit(state["idle"]["thought"]["current_image"], (bx, by))
        # Draw small trail circles (comic book style)
        pygame.draw.circle(screen, config.WHITE, (bx - 10, by + 50), 8)
        pygame.draw.circle(screen, config.WHITE, (bx - 25, by + 65), 5)
        
    # 2. Humming Notes
    if state["idle"]["humming"]["is_active"] or state["idle"]["humming"]["notes"]:
        for n in state["idle"]["humming"]["notes"]:
            draw_music_note(screen, n["pos"], 1.0) # Procedural note

    # 3. Needs Interaction UI (Floating buttons on face)
    if state["needs"]["show_interaction"]:
        # Draw semi-transparent overlay
        overlay = pygame.Surface((config.WIDTH, config.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0,0))
        
        # Draw 3 buttons: FOOD, PLAY, SLEEP
        # Icons/Colors for buttons
        btns = [
            ("FOOD", config.PINK, (80, 240, 80, 40), "hunger"),
            ("PLAY", config.YELLOW, (200, 240, 80, 40), "play"),
            ("SLEEP", config.BLUE, (320, 240, 80, 40), "energy")
        ]
        for label, color, rect, key in btns:
            val = state["needs"][key]
            # Draw BG
            pygame.draw.rect(screen, color, rect, border_radius=8)
            # Draw level bar inside
            bar_w = int(76 * (val/100.0))
            pygame.draw.rect(screen, config.WHITE, (rect[0]+2, rect[1]+30, bar_w, 6))
            # Text
            txt = config.FONT_TINY.render(label, True, config.WHITE)
            screen.blit(txt, (rect[0] + (rect[2]-txt.get_width())//2, rect[1]+5))

        # Close instruction
        instr = config.FONT_TINY.render("Tap center to hide", True, config.WHITE)
        screen.blit(instr, (config.WIDTH//2 - instr.get_width()//2, 290))

    # 4. Floating Hearts
    for h in state["needs"]["hearts"]:
        # Draw a simple heart shape
        hx, hy = h["pos"]
        pygame.draw.circle(screen, config.PINK, (int(hx-4), int(hy)), 5)
        pygame.draw.circle(screen, config.PINK, (int(hx+4), int(hy)), 5)
        pygame.draw.polygon(screen, config.PINK, [(int(hx-9), int(hy+2)), (int(hx+9), int(hy+2)), (int(hx), int(hy+10))])

    # Visual Feedback Layer (Crosshair)
    draw_click_crosshair(screen, state)
    
    # Draw Message Notification if on Face
    if state["messages"]["unread"]:
        pygame.draw.circle(screen, config.RED, (config.WIDTH - 30, config.HEIGHT - 30), 12)
        txt = config.FONT_TINY.render("!", True, config.WHITE)
        screen.blit(txt, (config.WIDTH - 30 - txt.get_width()//2, config.HEIGHT - 30 - txt.get_height()//2))

def draw_menu(screen, state):
    screen.fill(config.WHITE)
    
    current_menu_id = state.get("current_menu", "MAIN")
    items = config.MENUS.get(current_menu_id, config.MENUS["MAIN"])
    
    # Header
    pygame.draw.rect(screen, config.BLACK, (0, 0, config.WIDTH, 50))
    title = config.FONT_MEDIUM.render(f"BMO MENU: {current_menu_id}", True, config.WHITE)
    screen.blit(title, (config.WIDTH//2 - title.get_width()//2, 10))
    
    # Pagination Logic (2x2 Grid = 4 items per page)
    items_per_page = 4
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    
    # Clamp page
    page = state.get("menu_page", 0)
    if page >= total_pages: page = total_pages - 1
    if page < 0: page = 0
    state["menu_page"] = page
    
    start_idx = page * items_per_page
    visible_items = items[start_idx:start_idx + items_per_page]
    
    # Layout Params
    cols, rows = 2, 2
    btn_w, btn_h = 190, 70
    gap = 20
    start_x = (config.WIDTH - (cols * btn_w + (cols-1) * gap)) // 2
    start_y = 70
    
    # Draw Menu Items in Grid
    for i, item in enumerate(visible_items):
        r = i // cols
        c = i % cols
        bx = start_x + c * (btn_w + gap)
        by = start_y + r * (btn_h + gap)
        
        btn_rect = (bx, by, btn_w, btn_h)
        pygame.draw.rect(screen, item.get("color", config.GRAY), btn_rect, border_radius=10)
        
        # Two-line text wrapping if too long
        label = item["label"]
        if " " in label and config.FONT_SMALL.size(label)[0] > btn_w - 10:
            words = label.split(" ")
            mid = len(words) // 2
            l1 = config.FONT_TINY.render(" ".join(words[:mid]), True, config.BLACK)
            l2 = config.FONT_TINY.render(" ".join(words[mid:]), True, config.BLACK)
            screen.blit(l1, (bx + (btn_w - l1.get_width())//2, by + 15))
            screen.blit(l2, (bx + (btn_w - l2.get_width())//2, by + 40))
        else:
            lbl = config.FONT_SMALL.render(label, True, config.BLACK)
            screen.blit(lbl, (bx + (btn_w - lbl.get_width())//2, by + (btn_h - lbl.get_height())//2))

    # Draw Navigation Buttons (Centered at Bottom)
    nav_y = 250
    nav_h = 45
    
    if page > 0:
        # PREV Button
        prev_rect = (start_x, nav_y, btn_w, nav_h)
        pygame.draw.rect(screen, config.GRAY, prev_rect, border_radius=5)
        lbl = config.FONT_SMALL.render("< PREV", True, config.BLACK)
        screen.blit(lbl, (prev_rect[0] + (btn_w - lbl.get_width())//2, nav_y + 10))
        
    if page < total_pages - 1:
        # NEXT Button
        next_rect = (start_x + btn_w + gap, nav_y, btn_w, nav_h)
        pygame.draw.rect(screen, config.GRAY, next_rect, border_radius=5)
        lbl = config.FONT_SMALL.render("NEXT >", True, config.BLACK)
        screen.blit(lbl, (next_rect[0] + (btn_w - lbl.get_width())//2, nav_y + 10))

def handle_menu_touch(state, pos):
    x, y = pos
    current_menu_id = state.get("current_menu", "MAIN")
    items = config.MENUS.get(current_menu_id, config.MENUS["MAIN"])
    
    # Pagination Logic
    items_per_page = 4
    total_pages = (len(items) + items_per_page - 1) // items_per_page
    page = state.get("menu_page", 0)
    
    start_idx = page * items_per_page
    visible_items = items[start_idx:start_idx + items_per_page]
    
    # Layout Params (Same as draw)
    cols, rows = 2, 2
    btn_w, btn_h = 190, 70
    gap = 20
    start_x = (config.WIDTH - (cols * btn_w + (cols-1) * gap)) // 2
    start_y = 70
    
    # Check Item Clicks
    for i, item in enumerate(visible_items):
        r = i // cols
        c = i % cols
        bx = start_x + c * (btn_w + gap)
        by = start_y + r * (btn_h + gap)
        
        if bx <= x <= bx + btn_w and by <= y <= by + btn_h:
            return item["action"]
            
    # Check Nav Buttons
    nav_y = 250
    nav_h = 45
    
    if page > 0:
        prev_rect = (start_x, nav_y, btn_w, nav_h)
        if prev_rect[0] <= x <= prev_rect[0] + btn_w and prev_rect[1] <= y <= prev_rect[1] + nav_h:
            state["menu_page"] = page - 1
            return None
            
    if page < total_pages - 1:
        next_rect = (start_x + btn_w + gap, nav_y, btn_w, nav_h)
        if next_rect[0] <= x <= next_rect[0] + btn_w and next_rect[1] <= y <= next_rect[1] + nav_h:
            state["menu_page"] = page + 1
            return None
            
    return None

def draw_clock(screen, state):
    screen.fill(config.BLUE)
    t = time.strftime("%H:%M:%S")
    d = time.strftime("%A, %b %d")
    lbl_t = config.FONT_LARGE.render(t, True, config.WHITE)
    lbl_d = config.FONT_MEDIUM.render(d, True, config.WHITE)
    screen.blit(lbl_t, (config.WIDTH//2 - lbl_t.get_width()//2, 100))
    screen.blit(lbl_d, (config.WIDTH//2 - lbl_d.get_width()//2, 180))

def draw_stats(screen, state):
    # Placeholder for system stats
    screen.fill(config.YELLOW)
    lbl = config.FONT_MEDIUM.render("SYSTEM STATS", True, config.BLACK)
    screen.blit(lbl, (config.WIDTH//2 - lbl.get_width()//2, 20))

