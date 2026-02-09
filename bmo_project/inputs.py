import threading
import time
import pygame
from evdev import InputDevice, ecodes
from . import config
from . import utils

def touch_thread(running_event):
    """
    Background thread to read touch events and post them to Pygame event queue.
    running_event: threading.Event to signal when to stop.
    """
    touch_path = utils.find_touch_device()
    try:
        dev = InputDevice(touch_path)
        print(f"👋 Touch thread started on {touch_path}")
        
        raw_x, raw_y = 0, 0
        last_finger_state = False
        finger_down = False
        
        # Non-blocking read loop ideally, or blocking with timeout
        # standard read_loop is blocking. We can use select or just rely on daemon thread.
        
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
                    # sx = WIDTH - ((raw_y / 4095.0) * WIDTH)
                    # sy = (raw_x / 4095.0) * HEIGHT
                    
                    # Note: raw_y mapped to X, inverted? 
                    # This depends on screen orientation. 
                    # Assuming bmo_pygame.py calibration was correct for the hardware.
                    
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
