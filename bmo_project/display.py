import os
import pygame
from . import config

def init_display():
    """Initialize Pygame and the display surface"""
    
    if config.IS_WINDOWS:
        # Windowed mode for local dev with scaling
        pygame.init()
        # Create a window that is scaled up
        window_width = config.WIDTH * config.SCALE_FACTOR
        window_height = config.HEIGHT * config.SCALE_FACTOR
        window = pygame.display.set_mode((window_width, window_height))
        pygame.display.set_caption(f"{config.IDENTITY} - BMO Project (Scaled {config.SCALE_FACTOR}x)")
        
        # We still return a "virtual" screen at the original resolution (480x320)
        # We will scale this surface to the window in update_framebuffer
        screen = pygame.Surface((config.WIDTH, config.HEIGHT))
        
    else:
        # Headless/Framebuffer mode for Raspberry Pi
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        # Create Surface matching Framebuffer format (RGB565)
        # 16-bit depth with specific masks for 5-6-5 format
        screen = pygame.Surface((config.WIDTH, config.HEIGHT), depth=16, masks=(0xF800, 0x07E0, 0x001F, 0))
    
    # Initialize fonts
    config.init_fonts()
    
    return screen

def update_framebuffer(screen, fb_path=config.FB_DEVICE):
    """Write the current screen content to the framebuffer device or window"""
    try:
        if config.IS_WINDOWS:
            # Scale the internal screen to the window size
            window = pygame.display.get_surface()
            pygame.transform.scale(screen, window.get_size(), window)
            pygame.display.flip()
        elif fb_path:
            with open(fb_path, "wb") as fb:
                fb.write(screen.get_buffer())
    except IOError as e:
        # print(f"Error writing to framebuffer: {e}") # Reduce spam for dev on PC
        pass
    except Exception as e:
        print(f"Framebuffer error: {e}")

def cleanup():
    pygame.quit()
