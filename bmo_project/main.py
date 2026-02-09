import time
import threading
import pygame
import sys
import subprocess
from . import config
from . import display
from . import inputs
from . import network
from .modes import core_modes, messages

def main():
    print(f"🤖 Starting {config.IDENTITY}...")
    
    # Init Display
    screen = display.init_display()
    
    # Init Fonts
    config.init_fonts()

    # Init State
    state = {
        "current_mode": config.load_config().get("default_mode", "FACE"),
        "expression": "happy",
        "menu_stack": ["MAIN"],
        "current_menu": "MAIN",
        "menu_page": 0,
        "loop_running": True,
        "needs_redraw": True,
        "last_interaction": time.time(),
        
        # Identity / Face
        "emotion": "positive",
        "face_images": [],
        "current_face_open": None,
        "current_face_closed": None,
        "last_face_switch": 0,
        "is_blinking": False,
        "blink_timer": 0,
        "blink_end_time": 0,
        
        # Sub-states
        "messages": {
            "list": [],
            "unread": False,
            "viewing_id": None
        },
        "keyboard": None,
        "composing": False,
        
        "idle": {
            "thought": {
                "is_active": False,
                "end_time": 0,
                "next_time": time.time() + 10, 
                "current_image": None
            },
            "humming": {
                "is_active": False,
                "end_time": 0,
                "next_time": time.time() + 20,
                "notes": []
            }
        },
        
        "needs": {
            "hunger": 80.0,
            "energy": 90.0,
            "play": 70.0,
            "last_decay": time.time(),
            "hearts": [],
            "show_interaction": False
        },
        
        "click_feedback": {
            "pos": (0, 0),
            "time": 0
        },
        
        "weather": {
             "temp": "--",
             "city": "Unknown",
             "desc": "Loading...",
             "icon": "cloud",
             "last_update": 0
        },
        
        "tap_times": []
    }
    
    # Load Initial Face
    core_modes.load_random_face(state)
    
    # Load Data
    network.load_messages(state)
    
    # Start separate threads
    running_event = threading.Event()
    running_event.set()
    
    t_touch = threading.Thread(target=inputs.touch_thread, args=(running_event,), daemon=True)
    t_touch.start()
    
    t_net = threading.Thread(target=network.fetch_remote_messages, args=(state,), daemon=True)
    t_net.start()
    
    clock = pygame.time.Clock()
    
    try:
        while state["loop_running"]:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    state["loop_running"] = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    state["last_interaction"] = time.time()
                    pos = event.pos
                    
                    # --- 5-Tap Reset Logic ---
                    now = time.time()
                    state["tap_times"].append(now)
                    # Keep only taps within last 2 seconds
                    state["tap_times"] = [t for t in state["tap_times"] if now - t < 2.0]
                    
                    if len(state["tap_times"]) >= 5:
                        print("🔄 5-Tap Reset Triggered! Updating...")
                        # Draw Updating Screen
                        screen.fill(config.BLACK)
                        lbl = config.FONT_MEDIUM.render("UPDATING...", True, config.WHITE)
                        screen.blit(lbl, (config.WIDTH//2 - lbl.get_width()//2, config.HEIGHT//2))
                        display.update_framebuffer(screen)
                        
                        try:
                            # Pull latest code
                            subprocess.call(["git", "pull", "origin", "main"])
                        except Exception as e:
                            print(f"Update failed: {e}")
                        
                        # Exit to let systemd restart
                        sys.exit(0)
                    
                    # Handle Mode Specific Input
                    mode = state["current_mode"]
                    
                    if mode == "FACE":
                        # Tap face to go to menu
                        state["current_mode"] = "MENU"
                        state["needs_redraw"] = True
                        
                    elif mode == "MENU":
                        action = core_modes.handle_menu_touch(state, pos)
                        if action:
                            if action.startswith("MODE:"):
                                new_mode = action.split(":")[1]
                                state["current_mode"] = new_mode
                            elif action.startswith("MENU:"):
                                new_menu = action.split(":")[1]
                                state["current_menu"] = new_menu
                            elif action == "BACK":
                                # Simple back logic (go to MAIN or Face)
                                if state["current_menu"] == "MAIN":
                                    state["current_mode"] = "FACE"
                                else:
                                    state["current_menu"] = "MAIN"
                            state["needs_redraw"] = True
                            
                    elif mode == "MESSAGES":
                        messages.handle_touch(state, pos)
                        state["needs_redraw"] = True
            
            # Update Logic (Face Animation & Behaviors)
            if state["current_mode"] == "FACE":
                core_modes.update_face(state)
            
            # Redraw if needed
            current_time = time.time()
            
            # Redraw if needed
            if state["needs_redraw"] or (current_time % 1.0 < 0.1): # Force redraw occasionally or on logic
                # Actually, for clock we need per-minute, for animations per-frame
                # Let's just redraw on event or logic trigger.
                # But Clock needs auto update.
                if state["current_mode"] == "CLOCK":
                     state["needs_redraw"] = True # Force redraw for clock
                
                # Input cursor blink
                if state.get("composing"):
                     state["needs_redraw"] = True
                
                # Clear
                screen.fill(config.BLACK)
                
                # Draw Mode
                mode = state["current_mode"]
                
                if mode == "FACE":
                    core_modes.draw_face(screen, state)
                elif mode == "MENU":
                    core_modes.draw_menu(screen, state)
                elif mode == "CLOCK":
                    core_modes.draw_clock(screen, state)
                elif mode == "MESSAGES":
                    messages.draw_messages(screen, state)
                elif mode == "STATS": # ADVANCED_STATS
                     # Not implemented fully yet, fallback
                     core_modes.draw_stats(screen, state)
                elif mode == "NOTES":
                     # TODO
                     pass
                
                # Push to Framebuffer
                display.update_framebuffer(screen)
                state["needs_redraw"] = False
            
            # Cap FPS
            clock.tick(30)
            
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        running_event.clear()
        display.cleanup()

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except: pass
    main()
