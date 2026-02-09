import pygame
import time
from .. import config

def draw_face(screen, state):
    screen.fill(config.FACE_COLOR)
    
    expr = state.get("expression", "happy")
    
    # Eyes
    eye_color = config.BLACK
    left_eye_pos = (130, 120)
    right_eye_pos = (350, 120)
    eye_size = (30, 60) # Oval
    
    if expr == "happy":
        pygame.draw.ellipse(screen, eye_color, (*left_eye_pos, *eye_size))
        pygame.draw.ellipse(screen, eye_color, (*right_eye_pos, *eye_size))
        # Smile
        pygame.draw.arc(screen, eye_color, (190, 180, 100, 60), 3.14, 6.28, 5)

    elif expr == "sleepy":
        pygame.draw.line(screen, eye_color, (110, 150), (160, 150), 5)
        pygame.draw.line(screen, eye_color, (320, 150), (370, 150), 5)
        pygame.draw.line(screen, eye_color, (220, 220), (260, 220), 3)

def draw_menu(screen, state):
    screen.fill(config.WHITE)
    
    # Draw Menu Items
    menu_name = state.get("current_menu", "MAIN")
    items = config.MENUS.get(menu_name, [])
    
    y = 20
    for item in items:
        color = item.get("color", config.GRAY)
        label = item.get("label", "???")
        
        pygame.draw.rect(screen, color, (40, y, 400, 40), border_radius=5)
        
        lbl = config.FONT_SMALL.render(label, True, config.WHITE)
        screen.blit(lbl, (config.WIDTH//2 - lbl.get_width()//2, y + 10))
        
        y += 50

def handle_menu_touch(state, pos):
    x, y = pos
    menu_name = state.get("current_menu", "MAIN")
    items = config.MENUS.get(menu_name, [])
    
    # Simple hit testing
    # y starts at 20, increments by 50
    # items are at 20, 70, 120, 170...
    # height 40
    
    idx = (y - 20) // 50
    if 0 <= idx < len(items):
        # Touched item idx
        # Check if touch is within x bounds (40 to 440)
        if 40 <= x <= 440:
             # Trigger action
             action = items[idx]["action"]
             return action
    return None

def draw_clock(screen, state):
    screen.fill(config.BLUE)
    t = time.strftime("%H:%M")
    font = config.FONT_LARGE
    lbl = font.render(t, True, config.WHITE)
    screen.blit(lbl, (config.WIDTH//2 - lbl.get_width()//2, config.HEIGHT//2 - 30))

def draw_stats(screen, state):
    screen.fill(config.GRAY)
    # Simple list of stats
    pass 
