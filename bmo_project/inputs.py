import threading
import time
import pygame
from . import config
# Only import evdev on Linux if possible, or handle import error
try:
    from evdev import InputDevice, ecodes
    HAS_EVDEV = True
except ImportError:
    HAS_EVDEV = False

from . import utils

def touch_thread(running_event):
    """
    Background thread to read touch events and post them to Pygame event queue.
    running_event: threading.Event to signal when to stop.
    """
    if config.IS_WINDOWS or not HAS_EVDEV:
        # On Windows, Pygame handles mouse events as touch events in the main loop
        # We don't need a separate thread for input
        print("🖱️ Running in Desktop Mode: Using Mouse for Touch Input")
        while running_event.is_set():
            time.sleep(1)
        return

    touch_path = utils.find_touch_device()
    try:
        dev = InputDevice(touch_path)
        print(f"👋 Touch thread started on {touch_path}")
        
        raw_x, raw_y = 0, 0
        last_finger_state = False
        finger_down = False
        
        for event in dev.read_loop():
            if not running_event.is_set():
                break
                
            if event.type == ecodes.EV_ABS:
                if event.code == ecodes.ABS_X: raw_x = event.value
                if event.code == ecodes.ABS_Y: raw_y = event.value
            
            elif event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH:
                finger_down = (event.value == 1)
            
            elif event.type == ecodes.EV_SYN and event.code == ecodes.SYN_REPORT:
                if finger_down and not last_finger_state:
                    # New Touch Detected!
                    # Calibration (from bmo_pygame.py)
                    
                    sx = config.WIDTH - ((raw_y / 4095.0) * config.WIDTH)
                    sy = (raw_x / 4095.0) * config.HEIGHT
                    
                    # Clamp
                    sx = max(0, min(config.WIDTH, sx))
                    sy = max(0, min(config.HEIGHT, sy))
                    
                    # Post to Pygame
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(sx), int(sy)), 'button': 1}))
                
                last_finger_state = finger_down
                
    except Exception as e:
        print(f"Touch Error: {e}")
