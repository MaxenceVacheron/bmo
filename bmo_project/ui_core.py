import pygame
from PIL import Image, ImageDraw, ImageFont
from . import config

def render_text_with_emoji(text, size, color, font_path=None):
    """
    Render text including emojis using PIL and convert to Pygame Surface.
    Returns a Pygame Surface.
    """
    # Use config font path if not provided
    # Note: Default PIL font might not support emojis well without a color emoji font.
    # We will try to use the best available font.
    
    if font_path is None:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    
    try:
        pil_font = ImageFont.truetype(font_path, size)
    except:
        pil_font = ImageFont.load_default()

    # Calculate text size (dummy)
    dummy_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)
    
    # helper to get text bounding box
    bbox = draw.textbbox((0, 0), text, font=pil_font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    
    # Add some padding
    width += 10
    height += 10
    
    # Create actual image
    img = Image.new('RGBA', (int(width), int(height)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw text
    # Note: 'embedded_color=True' requires libraqm and a color font (like NotoColorEmoji)
    # If not present, it will render monochrome outlines if the font supports the glyphs.
    draw.text((5, 5), text, font=pil_font, fill=color, embedded_color=True)
    
    # Convert to Pygame Surface
    raw_str = img.tobytes("raw", "RGBA")
    surface = pygame.image.fromstring(raw_str, img.size, 'RGBA')
    
    return surface

def draw_text_centered(screen, text, font, color, y_pos):
    """Draw centered text using Pygame font (faster, no emoji support)"""
    lbl = font.render(text, True, color)
    x = (config.WIDTH - lbl.get_width()) // 2
    screen.blit(lbl, (x, y_pos))

def draw_multiline_text(screen, text, font, color, rect):
    """Draw multiline text within a rectangle"""
    # Simple wrap logic could be added here
    # For now, just split by newline
    lines = text.split('\n')
    y = rect[1]
    line_h = font.get_height()
    
    for line in lines:
        if y + line_h > rect[1] + rect[3]: break
        lbl = font.render(line, True, color)
        screen.blit(lbl, (rect[0], y))
        y += line_h
