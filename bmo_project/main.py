import time
import threading
import pygame
import sys
from . import config
from . import display
from . import inputs
from . import network
from .modes import core_modes, messages

def main():
    print(f"🤖 Starting {config.IDENTITY}...")
    
    # Init Display
    screen = display.init_display()
    
    # Init State
    state = {
        "current_mode": config.load_config().get("default_mode", "FACE"),
        "expression": "happy",
        "menu_stack": ["MAIN"],
        "current_menu": "MAIN",
        "loop_running": True,
        "needs_redraw": True,
        "last_interaction": time.time(),
        
        # Sub-states
        "messages": {
            "list": [],
            "unread": False
        },
        "keyboard": None,
        "composing": False
    }
    
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
            
            # Update Logic
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
