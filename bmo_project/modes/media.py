import pygame
import time
import os
import sys
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
            pil_img = pil_img.resize(new_size, Image.Resampling.BILINEAR)
            
            # Convert to Pygame
            mode = pil_img.mode
            size = pil_img.size
            data = pil_img.tobytes()
            pygame_img = pygame.image.fromstring(data, size, mode)
            
            # OPTIMIZATION: Convert immediately
            if config.SURFACE_DEPTH == 16:
                converted = pygame.Surface((config.WIDTH, config.HEIGHT), depth=16, masks=config.SURFACE_MASKS)
            else:
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

# --- GIF PLAYER ---
import random

def start_gif_player(state, subdir):
    path = os.path.join(config.NEXTCLOUD_PATH, subdir, "Photos", "GIFs")
    print(f"🎞️ Starting GIF Player. Searching in: {path}")

    if "gif_player" not in state: state["gif_player"] = {}
    
    state["gif_player"]["path"] = path
    state["gif_player"]["gifs"] = []
    
    if os.path.exists(path):
        try:
            for f in os.listdir(path):
                if f.lower().endswith('.gif'):
                    full_path = os.path.join(path, f)
                    state["gif_player"]["gifs"].append(full_path)
        except (OSError, IOError) as e:
            print(f"❌ Error accessing GIF path {path}: {e}")
    else:
        print(f"❌ Path not found: {path}")
    
    print(f"🎞️ Found {len(state['gif_player']['gifs'])} GIFs")

    if not state["gif_player"]["gifs"]:
        print(f"⚠️ No GIFs found in {path}")
        state["current_mode"] = "MENU"
        return

    random.shuffle(state["gif_player"]["gifs"])
    state["gif_player"]["current_gif_index"] = 0
    state["gif_player"]["gif_switch_time"] = time.time()
    state["gif_player"]["next_frames"] = [] # Clear preload
    
    load_next_gif(state)
    state["current_mode"] = "GIF_PLAYER"

def _load_gif_frames(gif_path):
    print(f"🎞️ Loading GIF: {gif_path}")
    frames = []
    duration = 0.1
    try:
        pil_gif = Image.open(gif_path)
        try:
            duration = pil_gif.info.get('duration', 100) / 1000.0
        except:
            duration = 0.1
        
        frame_num = 0
        while True:
            try:
                pil_gif.seek(frame_num)
                frame = pil_gif.convert('RGB')
                
                img_w, img_h = frame.size
                scale = min(config.WIDTH / img_w, config.HEIGHT / img_h)
                new_size = (int(img_w * scale), int(img_h * scale))
                frame = frame.resize(new_size, Image.Resampling.NEAREST) # Nearest neighbor is fastest and retro for GIFs
                
                mode = frame.mode
                size = frame.size
                data = frame.tobytes()
                pygame_frame = pygame.image.fromstring(data, size, mode)
                
                # OPTIMIZATION: Convert immediately
                if config.SURFACE_DEPTH == 16:
                   surf = pygame.Surface((new_size[0], new_size[1]), depth=16, masks=config.SURFACE_MASKS)
                   surf.blit(pygame_frame, (0,0))
                   frames.append(surf)
                else:
                   frames.append(pygame_frame.convert())
                   
                frame_num += 1
            except EOFError:
                break
        print(f"✅ Loaded {len(frames)} frames. Duration: {duration}s")
    except Exception as e:
        print(f"❌ Error loading GIF {gif_path}: {e}")
    return frames, duration

def load_next_gif(state):
    gifs = state["gif_player"].get("gifs")
    if not gifs: return
    
    if state["gif_player"].get("next_frames"):
        state["gif_player"]["frames"] = state["gif_player"]["next_frames"]
        state["gif_player"]["frame_duration"] = state["gif_player"]["next_frame_duration"]
        state["gif_player"]["frame_index"] = 0
        state["gif_player"]["next_frames"] = []
    else:
        gif_path = gifs[state["gif_player"]["current_gif_index"]]
        frames, duration = _load_gif_frames(gif_path)
        state["gif_player"]["frames"] = frames
        state["gif_player"]["frame_duration"] = duration
        state["gif_player"]["frame_index"] = 0
        state["gif_player"]["last_frame_time"] = time.time()
    
    preload_next_gif(state)

def preload_next_gif(state):
    gifs = state["gif_player"].get("gifs")
    if not gifs or len(gifs) <= 1: return
    
    next_index = (state["gif_player"]["current_gif_index"] + 1) % len(gifs)
    next_gif_path = gifs[next_index]
    frames, duration = _load_gif_frames(next_gif_path)
    state["gif_player"]["next_frames"] = frames
    state["gif_player"]["next_frame_duration"] = duration

def update_gif(state):
    if "gif_player" not in state: return
    
    # Switch GIF every 15s
    if time.time() - state["gif_player"].get("gif_switch_time", 0) > 15.0:
        gifs = state["gif_player"].get("gifs")
        if gifs:
            state["gif_player"]["current_gif_index"] = (state["gif_player"]["current_gif_index"] + 1) % len(gifs)
            state["gif_player"]["gif_switch_time"] = time.time()
            load_next_gif(state)
            
    # Animate
    if time.time() - state["gif_player"].get("last_frame_time", 0) > state["gif_player"].get("frame_duration", 0.1):
        state["gif_player"]["last_frame_time"] = time.time()
        frames = state["gif_player"].get("frames")
        if frames:
            state["gif_player"]["frame_index"] = (state["gif_player"]["frame_index"] + 1) % len(frames)
            state["needs_redraw"] = True

def draw_gif(screen, state):
    if not state.get("gif_player"): return
    screen.fill(config.BLACK)
    
    frames = state["gif_player"].get("frames")
    if not frames:
        txt = config.FONT_MEDIUM.render("No GIF loaded", True, config.WHITE)
        screen.blit(txt, (config.WIDTH//2 - txt.get_width()//2, config.HEIGHT//2))
        return

    idx = state["gif_player"]["frame_index"] % len(frames)
    frame = frames[idx]
    x = (config.WIDTH - frame.get_width()) // 2
    y = (config.HEIGHT - frame.get_height()) // 2
    screen.blit(frame, (x, y))

    # Hints
    if time.time() - state["gif_player"].get("last_touch_time", 0) < 1.0:
        hint_left = config.FONT_SMALL.render("<", True, config.WHITE)
        hint_right = config.FONT_SMALL.render(">", True, config.WHITE)
        screen.blit(hint_left, (10, config.HEIGHT - 30))
        screen.blit(hint_right, (config.WIDTH - 30, config.HEIGHT - 30))

        screen.blit(hint_right, (config.WIDTH - 30, config.HEIGHT - 30))

def handle_gif_touch(state, pos):
    if "gif_player" not in state: return
    
    x, y = pos
    width = config.WIDTH
    
    state["gif_player"]["last_touch_time"] = time.time()
    
    # Navigation
    if x < width // 3:
        # Prev
        gifs = state["gif_player"].get("gifs")
        if gifs:
            state["gif_player"]["current_gif_index"] = (state["gif_player"]["current_gif_index"] - 1) % len(gifs)
            state["gif_player"]["gif_switch_time"] = time.time() # Reset auto-switch timer
            load_next_gif(state)
            
    elif x > 2 * width // 3:
        # Next
        gifs = state["gif_player"].get("gifs")
        if gifs:
            state["gif_player"]["current_gif_index"] = (state["gif_player"]["current_gif_index"] + 1) % len(gifs)
            state["gif_player"]["gif_switch_time"] = time.time()
            load_next_gif(state)
            
    else:
        # Center -> Exit
        state["current_mode"] = "MENU"

def trigger_random_gif(state):
    print("🎲 Triggering Random GIF...")
    # Search in both default and perso
    candidates = []
    for subdir in ["default", "perso"]:
        path = os.path.join(config.NEXTCLOUD_PATH, subdir, "Photos", "GIFs")
        if os.path.exists(path):
            try:
                for f in os.listdir(path):
                    if f.lower().endswith('.gif'):
                        candidates.append(os.path.join(path, f))
            except: pass
            
    if not candidates:
        print("❌ No GIF candidates found for random trigger.")
        return

    # Pick one
    gif_path = random.choice(candidates)
    print(f"🎲 Selected random GIF: {gif_path}")
    
    # Init GIF Player State specifically for random play
    if "gif_player" not in state: state["gif_player"] = {}
    
    # We manually set the GIF check this
    frames, duration = _load_gif_frames(gif_path)
    if not frames:
        print("❌ Failed to load random GIF frames.")
        return
    
    state["gif_player"]["frames"] = frames
    state["gif_player"]["frame_duration"] = duration
    state["gif_player"]["frame_index"] = 0
    state["gif_player"]["last_frame_time"] = time.time()
    
    print(f"🎬 Starting Random GIF Mode with {len(state['gif_player']['frames'])} frames")
    
    state["random_gif"]["active"] = True
    state["random_gif"]["active"] = True
    state["random_gif"]["start_time"] = time.time()
    
    # Calculate total duration of one loop
    gif_duration = len(frames) * duration
    # Play at least 5 seconds, or 2 loops, whichever is appropriate
    # If GIF is short (e.g. 1s), play 5s.
    # If GIF is long (e.g. 10s), play 10s (1 loop).
    state["random_gif"]["duration"] = max(5.0, gif_duration * 2) if gif_duration < 2.5 else max(5.0, gif_duration)
    
    print(f"⏱️ Random GIF Duration set to: {state['random_gif']['duration']:.1f}s (GIF len: {gif_duration:.1f}s)")
    
    state["current_mode"] = "RANDOM_GIF"
    sys.stdout.flush()
