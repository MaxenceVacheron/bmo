import pygame
import time
from .. import config

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
    # (Simplified for core mode, full logic is in main/idle modules usually)
    pass

def draw_menu(screen, state):
    screen.fill(config.WHITE)
    
    current_menu_id = state.get("current_menu", "MAIN")
    items = config.MENUS.get(current_menu_id, config.MENUS["MAIN"])
    
    # Header
    pygame.draw.rect(screen, config.BLACK, (0, 0, config.WIDTH, 50))
    title = config.FONT_MEDIUM.render(f"BMO MENU: {current_menu_id}", False, config.WHITE)
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
            l1 = config.FONT_TINY.render(" ".join(words[:mid]), False, config.BLACK)
            l2 = config.FONT_TINY.render(" ".join(words[mid:]), False, config.BLACK)
            screen.blit(l1, (bx + (btn_w - l1.get_width())//2, by + 15))
            screen.blit(l2, (bx + (btn_w - l2.get_width())//2, by + 40))
        else:
            lbl = config.FONT_SMALL.render(label, False, config.BLACK)
            screen.blit(lbl, (bx + (btn_w - lbl.get_width())//2, by + (btn_h - lbl.get_height())//2))

    # Draw Navigation Buttons (Centered at Bottom)
    nav_y = 250
    nav_h = 45
    
    if page > 0:
        # PREV Button
        prev_rect = (start_x, nav_y, btn_w, nav_h)
        pygame.draw.rect(screen, config.GRAY, prev_rect, border_radius=5)
        lbl = config.FONT_SMALL.render("< PREV", False, config.BLACK)
        screen.blit(lbl, (prev_rect[0] + (btn_w - lbl.get_width())//2, nav_y + 10))
        
    if page < total_pages - 1:
        # NEXT Button
        next_rect = (start_x + btn_w + gap, nav_y, btn_w, nav_h)
        pygame.draw.rect(screen, config.GRAY, next_rect, border_radius=5)
        lbl = config.FONT_SMALL.render("NEXT >", False, config.BLACK)
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
    lbl_t = config.FONT_LARGE.render(t, False, config.WHITE)
    lbl_d = config.FONT_MEDIUM.render(d, False, config.WHITE)
    screen.blit(lbl_t, (config.WIDTH//2 - lbl_t.get_width()//2, 100))
    screen.blit(lbl_d, (config.WIDTH//2 - lbl_d.get_width()//2, 180))

def draw_stats(screen, state):
    # This requires utils imports in main or passing data
    # For now, minimal placeholder or better yet, move logic here if simple
    from .. import utils
    
    screen.fill(config.YELLOW)
    temp = utils.get_cpu_temp()
    ram_p, _ = utils.get_ram_usage()
    
    y = 40
    lbl = config.FONT_MEDIUM.render(f"CPU: {temp:.1f}C", False, config.BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, config.BLACK, (40, y+40, 400, 30), 2)
    w = int(396 * (temp / 85.0))
    pygame.draw.rect(screen, config.RED if temp > 60 else config.GREEN, (42, y+42, w, 26))
    
    y += 100
    lbl = config.FONT_MEDIUM.render(f"RAM: {ram_p:.1f}%", False, config.BLACK)
    screen.blit(lbl, (40, y))
    pygame.draw.rect(screen, config.BLACK, (40, y+40, 400, 30), 2)
    w = int(396 * (ram_p / 100.0))
    pygame.draw.rect(screen, config.BLUE, (42, y+42, w, 26))
