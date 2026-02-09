import time
import threading
import pygame
import sys
import subprocess
from . import config
from . import display
from . import inputs
from . import network
from .modes import core_modes, messages, apps, media
from .games import snake

def main():
    # Singleton Check (Linux/Pi only)
    if not config.IS_WINDOWS:
        try:
            import socket
            lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            lock_socket.bind('\0bmo_instance_lock')
        except Exception:
            print("BMO is already running!")
            sys.exit(0)

    print(f"🤖 Starting {config.IDENTITY}...")
    
    # Init Display
    screen = display.init_display()
    
    # Init Fonts
    config.init_fonts()

    # Init State
    state = {
        "current_mode": "STARTUP", # Start with typewriter effect
        "default_mode": config.load_config().get("default_mode", "FACE"),
        "expression": "happy",
        "menu_stack": ["MAIN"],
        "current_menu": "MAIN",
        "menu_page": 0,
        "loop_running": True,
        "needs_redraw": True,
        "last_interaction": time.time(),
        
        "startup": {
            "message": "Hello Agnès! I'm BMO. Maxence built my brain just for you.",
            "char_index": 0,
            "start_time": 0,
            "char_delay": 0.05
        },
        
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
        
        "random_gif": {
            "last_trigger": time.time(),
            "active": False
        },
        
        "is_showing_pop_face": False,
        "pop_face_timer": time.time() + 60,
        "pop_face_end_time": 0,
        
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
                    # Only if NOT composing (typing on T9 triggers this easily)
                    if not state.get("composing"):
                        now = time.time()
                        state["tap_times"].append(now)
                    # Keep only taps within last 2 seconds
                    state["tap_times"] = [t for t in state["tap_times"] if now - t < 2.0]
                    
                    if len(state["tap_times"]) >= 5:
                        print("🚀 BMO Auto-Update triggered!")
                        # Draw Updating Screen
                        screen.fill(config.BLACK)
                        lbl = config.FONT_MEDIUM.render("UPDATING...", True, config.WHITE)
                        screen.blit(lbl, (config.WIDTH//2 - lbl.get_width()//2, config.HEIGHT//2))
                        display.update_framebuffer(screen)
                        
                        try:
                            # Pull latest code
                            subprocess.call(["git", "pull", "origin", "main"])
                        except Exception as e:
                            print(f"Error during update: {e}")
                        
                        # Exit to let systemd restart
                        sys.exit(0)

                    # Pop-up Face Dismissal
                    if state.get("is_showing_pop_face"):
                        state["is_showing_pop_face"] = False
                        state["pop_face_timer"] = time.time() + 60 + (time.time() % 30) # Random delay
                        state["needs_redraw"] = True
                        continue

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
                                # Snake Init
                                if new_mode == "SNAKE":
                                    state["snake"] = snake.SnakeGame(config.WIDTH, config.HEIGHT)
                                    
                            elif action.startswith("MENU:"):
                                menu_name = action.split(":")[1]
                                state["menu_stack"].append(menu_name)
                                state["current_menu"] = menu_name
                                state["menu_page"] = 0
                                
                            elif action == "BACK":
                                if len(state["menu_stack"]) > 1:
                                    state["menu_stack"].pop()
                                    state["current_menu"] = state["menu_stack"][-1]
                                    state["menu_page"] = 0
                                else:
                                    state["current_mode"] = "FACE"
                                    
                            # --- APP ACTIONS ---
                            elif action.startswith("FOCUS:"):
                                mins = int(action.split(":")[1])
                                apps.start_focus_timer(state, mins)
                                
                            elif action.startswith("SLIDESHOW:"):
                                subdir = action.split(":")[1]
                                media.start_slideshow(state, subdir)
                            
                            elif action.startswith("GIF:"):
                                subdir = action.split(":")[1]
                                media.start_gif_player(state, subdir)
                                 
                            elif action.startswith("SYSTEM:"):
                                cmd = action.split(":")[1]
                                if cmd == "REBOOT":
                                    os.system("sudo reboot")
                                    
                            elif action.startswith("BRIGHTNESS:"):
                                try:
                                    val = float(action.split(":")[1])
                                    with open("/sys/class/backlight/rpi_backlight/brightness", "w") as f:
                                        f.write(str(int(val * 255)))
                                    state["brightness"] = val
                                    config.save_config(state)
                                except: pass
                                    
                            elif action.startswith("SET_POWER:"):
                                val = action.split(":")[1]
                                state["power_save"] = (val == "ON")
                                config.save_config(state)
                                script = "power_save_on.sh" if state["power_save"] else "power_save_off.sh"
                                path = os.path.join(config.BASE_DIR, script)
                                if os.path.exists(path):
                                    subprocess.run([path], shell=True)

                            state["needs_redraw"] = True
                            
                    elif mode == "MESSAGES":
                        messages.handle_touch(state, pos)
                        state["needs_redraw"] = True
                        
                    elif mode == "MESSAGE_VIEW":
                        messages.handle_message_view_touch(state, pos)
                        state["needs_redraw"] = True
                        
                    elif mode == "SNAKE":
                        if state.get("snake"):
                            res = state["snake"].handle_input(pos)
                            if res == "EXIT":
                                state["current_mode"] = "MENU"
                        state["needs_redraw"] = True
                    elif mode == "SLIDESHOW":
                         # Exit slideshow on tap
                         state["current_mode"] = "MENU"
                    elif mode == "GIF_PLAYER":
                        media.handle_gif_touch(state, pos)
                    elif mode == "FOCUS":
                         # Exit focus on tap (if finished)
                         if state["focus"].get("active") == False:
                             state["current_mode"] = "MENU"
                    elif mode == "WEATHER" or mode == "ADVANCED_STATS" or mode == "NOTES":
                         # Simple back on tap
                         state["current_mode"] = "MENU"
            
            # Update Logic (Face Animation & Behaviors)
            # Update Logic (Face Animation & Behaviors)
            # Update Logic (Face Animation & Behaviors)
            if state["current_mode"] == "STARTUP":
                core_modes.update_startup(state)
            elif state["current_mode"] == "FACE":
                core_modes.update_face(state)
                # Random GIF Trigger
                if time.time() - state["random_gif"].get("last_trigger", 0) > 60:
                     # 10% chance? Or just trigger? Original logic was just time check + trigger
                     # But let's add some randomness so it's not exactly every 60s
                     if int(time.time()) % 10 == 0: 
                         media.trigger_random_gif(state)
                         state["random_gif"]["last_trigger"] = time.time()
                         
            elif state["current_mode"] == "SLIDESHOW":
                media.update_slideshow(state)
            elif state["current_mode"] == "GIF_PLAYER":
                media.update_gif(state)
            elif state["current_mode"] == "RANDOM_GIF":
                media.update_gif(state)
                # Check Duration
                if time.time() - state["random_gif"]["start_time"] > state["random_gif"]["duration"]:
                    state["current_mode"] = "FACE"
                    state["random_gif"]["active"] = False
                    state["needs_redraw"] = True
                    
            elif state["current_mode"] == "SNAKE":
                 if state.get("snake"):
                     state["snake"].update()
                     state["needs_redraw"] = True
            elif state["current_mode"] == "FOCUS":
                if state.get("focus") and state["focus"]["active"]:
                     if time.time() > state["focus"]["end_time"]:
                         state["needs_redraw"] = True
                     elif int(time.time()) % 1 == 0:
                         state["needs_redraw"] = True

            # Pop-up Face Logic
            # Only if not in attention-demanding modes
            if not state.get("is_showing_pop_face") and state["current_mode"] not in ["FACE", "SNAKE", "STARTUP", "GIF_PLAYER", "SLIDESHOW", "RANDOM_GIF", "FOCUS", "MESSAGE_VIEW"]:
                # Inactivity Timeout (return to FACE)
                if time.time() - state["last_interaction"] > 60:
                     print("Inactivity timeout: Returning to FACE")
                     state["current_mode"] = "FACE"
                     state["needs_redraw"] = True
                
                elif time.time() > state.get("pop_face_timer", 0):
                    state["is_showing_pop_face"] = True
                    state["pop_face_end_time"] = time.time() + 5.0
                    state["needs_redraw"] = True
                    core_modes.load_random_face(state)
            
            # Update Pop-up Face
            if state.get("is_showing_pop_face"):
                core_modes.update_face(state) # Animate the pop-up face
                if time.time() > state.get("pop_face_end_time", 0):
                    state["is_showing_pop_face"] = False
                    state["pop_face_timer"] = time.time() + 60 + (time.time() % 30)
                    state["needs_redraw"] = True
            
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
                
                if state.get("is_showing_pop_face"):
                    core_modes.draw_face(screen, state)
                elif state["current_mode"] == "STARTUP":
                    core_modes.draw_startup(screen, state)
                elif state["current_mode"] == "FACE":
                    core_modes.draw_face(screen, state)
                elif state["current_mode"] == "MENU":
                    core_modes.draw_menu(screen, state)
                elif state["current_mode"] == "CLOCK":
                    core_modes.draw_clock(screen, state)
                elif state["current_mode"] == "MESSAGES":
                    messages.draw_messages(screen, state)
                elif state["current_mode"] == "MESSAGE_VIEW":
                    messages.draw_message_view(screen, state)
                elif state["current_mode"] == "RANDOM_GIF":
                    media.draw_gif(screen, state)
                
                # --- NEW APPS ---
                elif state["current_mode"] == "ADVANCED_STATS":
                    apps.draw_advanced_stats(screen, state)
                elif state["current_mode"] == "WEATHER":
                    apps.draw_weather(screen, state)
                elif state["current_mode"] == "NOTES":
                    apps.draw_notes(screen, state)
                elif state["current_mode"] == "FOCUS":
                    apps.draw_focus(screen, state)
                elif state["current_mode"] == "SLIDESHOW":
                    media.draw_slideshow(screen, state)
                elif state["current_mode"] == "GIF_PLAYER":
                    media.draw_gif(screen, state)
                elif state["current_mode"] == "SNAKE":
                    if state.get("snake"):
                        state["snake"].draw(screen)
                
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
