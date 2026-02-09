import os
import pygame
from . import config

def init_display():
    """Initialize Pygame and the display surface"""
    # Initialize Pygame Headless if needed (or minimal video driver)
    # The original code used "dummy" driver, we should probably keep that
    # unless we want to try directfb or fbcon.
    
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    
    # Create Surface matching Framebuffer format (RGB565)
    # 16-bit depth with specific masks for 5-6-5 format
    screen = pygame.Surface((config.WIDTH, config.HEIGHT), depth=16, masks=(0xF800, 0x07E0, 0x001F, 0))
    
    # Initialize fonts
    config.init_fonts()
    
    return screen

def update_framebuffer(screen, fb_path=config.FB_DEVICE):
    """Write the current screen content to the framebuffer device"""
    try:
        with open(fb_path, "wb") as fb:
            fb.write(screen.get_buffer())
    except IOError as e:
        # print(f"Error writing to framebuffer: {e}") # Reduce spam for dev on PC
        pass
    except Exception as e:
        print(f"Framebuffer error: {e}")

def cleanup():
    pygame.quit()
