import pygame
import time
import os
from PIL import Image
from .. import config

# --- SLIDESHOW ---
def start_slideshow(state, subdir):
    # subdir is 'default' or 'perso'
    path = os.path.join(config.NEXTCLOUD_PATH, subdir, "Photos")
    if "slideshow" not in state: state["slideshow"] = {}
    
    state["slideshow"]["path"] = path
    state["slideshow"]["images"] = []
    
    if os.path.exists(path):
        try:
            for f in os.listdir(path):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    state["slideshow"]["images"].append(os.path.join(path, f))
        except (OSError, IOError) as e:
            print(f"Error accessing slideshow path {path}: {e}")
            state["slideshow"]["images"] = []
    
    if not state["slideshow"]["images"]:
        state["slideshow"]["images"] = ["PLACEHOLDER_EMPTY"]
        
    state["slideshow"]["index"] = 0
    state["slideshow"]["last_switch"] = 0
    state["slideshow"]["current_surface"] = None
    state["slideshow"]["last_touch_time"] = 0
    
    state["current_mode"] = "SLIDESHOW"

def update_slideshow(state):
    # Determine slide
    if "slideshow" not in state: return
    
    now = time.time()
    if now - state["slideshow"].get("last_switch", 0) > 5.0:
        state["slideshow"]["last_switch"] = now
        
        imgs = state["slideshow"]["images"]
        if not imgs or imgs[0] == "PLACEHOLDER_EMPTY": return

        try:
            # Cycle index
            state["slideshow"]["index"] = (state["slideshow"].get("index", 0) + 1) % len(imgs)
            idx = state["slideshow"]["index"]
            img_path = imgs[idx]
            
            # Load with PIL (better format handling)
            pil_img = Image.open(img_path)
            pil_img = pil_img.convert('RGB')
            
            # Calculate scaling
            img_w, img_h = pil_img.size
            scale = min(config.WIDTH / img_w, config.HEIGHT / img_h)
            new_size = (int(img_w * scale), int(img_h * scale))
            
            # Resize with PIL (high quality)
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to Pygame
            mode = pil_img.mode
            size = pil_img.size
            data = pil_img.tobytes()
            pygame_img = pygame.image.fromstring(data, size, mode)
            
            # Create centered surface
            converted = pygame.Surface((config.WIDTH, config.HEIGHT))
            converted.fill(config.BLACK)
            
            x = (config.WIDTH - new_size[0]) // 2
            y = (config.HEIGHT - new_size[1]) // 2
            converted.blit(pygame_img, (x, y))
            
            state["slideshow"]["current_surface"] = converted
            state["needs_redraw"] = True
            
        except Exception as e:
            print(f"Slideshow error: {e}")
            state["slideshow"]["index"] = (state["slideshow"].get("index", 0) + 1) % len(imgs)

def draw_slideshow(screen, state):
    if not state.get("slideshow"): return
    
    surf = state["slideshow"].get("current_surface")
    
    if not surf:
        screen.fill(config.BLACK)
        if not state["slideshow"]["images"] or state["slideshow"]["images"][0] == "PLACEHOLDER_EMPTY":
            txt = config.FONT_MEDIUM.render("No Images Found", True, config.WHITE)
            screen.blit(txt, (config.WIDTH//2 - txt.get_width()//2, config.HEIGHT//2))
    else:
        screen.blit(surf, (0, 0))
    
    # Navigation hints (show for 1 second after touch)
    if time.time() - state["slideshow"].get("last_touch_time", 0) < 1.0:
        hint_left = config.FONT_SMALL.render("<", True, config.WHITE)
        hint_right = config.FONT_SMALL.render(">", True, config.WHITE)
        screen.blit(hint_left, (10, config.HEIGHT - 30))
        screen.blit(hint_right, (config.WIDTH - 30, config.HEIGHT - 30))
