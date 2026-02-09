import pygame
import time
from .. import config
from .. import ui_core
from .. import network

# T9 Key mapping
T9_KEYS = {
    pygame.K_1: ".,?!1",
    pygame.K_2: "abc2",
    pygame.K_3: "def3",
    pygame.K_4: "ghi4",
    pygame.K_5: "jkl5",
    pygame.K_6: "mno6",
    pygame.K_7: "pqrs7",
    pygame.K_8: "tuv8",
    pygame.K_9: "wxyz9",
    pygame.K_0: " 0",
}

# Key coordinates for touch UI (approximate grid)
# 1 2 3
# 4 5 6
# 7 8 9
# * 0 #
KEYS_LAYOUT = [
    ("1", ".,?!", (50, 180)), ("2", "ABC", (160, 180)), ("3", "DEF", (270, 180)),
    ("4", "GHI", (50, 220)), ("5", "JKL", (160, 220)), ("6", "MNO", (270, 220)),
    ("7", "PQRS", (50, 260)), ("8", "TUV", (160, 260)), ("9", "WXYZ", (270, 260)),
    ("*", "DEL", (50, 300)), ("0", "_", (160, 300)), ("#", "SEND", (270, 300))
]

class T9Keyboard:
    def __init__(self):
        self.text = ""
        self.last_key = None
        self.last_press_time = 0
        self.cycle_index = 0
        self.cursor_visible = True
        self.cursor_timer = 0
        self.recipient = "" # Target bot name (e.g. "AMO" or "BMO")

    def handle_input(self, key_val):
        now = time.time()
        
        # Check if we are cycling the same key
        if key_val == self.last_key and (now - self.last_press_time < 1.0):
            # cycle
            self.cycle_index += 1
            # Remove last char
            self.text = self.text[:-1]
        else:
            # new key
            self.cycle_index = 0
            self.last_key = key_val
        
        self.last_press_time = now
        
        # Get char
        chars = T9_KEYS.get(key_val, "")
        if chars:
            char = chars[self.cycle_index % len(chars)]
            self.text += char

    def handle_touch(self, pos):
        # Map touch to keys
        x, y = pos
        # Simple grid collision detection
        # Logic to match KEYS_LAYOUT positions
        # Assuming button size ~80x35
        w, h = 80, 35
        
        for k, label, (kx, ky) in KEYS_LAYOUT:
            if kx <= x <= kx + w and ky <= y <= ky + h:
                self.process_key(k)
                return

    def process_key(self, k):
        if k in "1234567890":
            # Map str to pygame key const for reusable logic if wanted, 
            # but simpler to just use specific logic here
            mapping = {
                "1": ".,?!1", "2": "abc2", "3": "def3",
                "4": "ghi4", "5": "jkl5", "6": "mno6",
                "7": "pqrs7", "8": "tuv8", "9": "wxyz9",
                "0": " 0"
            }
            fake_key = ord(k) # Use ascii as key
            now = time.time()
            
            if fake_key == self.last_key and (now - self.last_press_time < 0.8):
                self.cycle_index += 1
                self.text = self.text[:-1]
            else:
                self.cycle_index = 0
                self.last_key = fake_key
                
            self.last_press_time = now
            chars = mapping.get(k, "")
            char = chars[self.cycle_index % len(chars)]
            self.text += char
            
        elif k == "*": # DEL
            self.text = self.text[:-1]
        elif k == "#": # SEND
            if self.text:
                network.send_message(self.recipient, self.text)
                self.text = "" # Clear after send
                return "SENT"

    def draw(self, screen):
        # Draw Input Field
        pygame.draw.rect(screen, (255, 255, 255), (20, 20, 440, 140))
        pygame.draw.rect(screen, (0, 0, 0), (20, 20, 440, 140), 2)
        
        font = config.FONT_MEDIUM
        if font:
            # Render text
            txt_surf = font.render(self.text + ("|" if (time.time() % 1 > 0.5) else ""), True, (0, 0, 0))
            # Wrap is hard, just clip for now
            screen.blit(txt_surf, (30, 30))
            
        # Draw Keys
        for k, label, (x, y) in KEYS_LAYOUT:
            color = (200, 200, 200)
            if k == "#": color = (100, 200, 100) # Green for Send
            if k == "*": color = (200, 100, 100) # Red for Del
            
            pygame.draw.rect(screen, color, (x, y, 80, 35))
            pygame.draw.rect(screen, (0, 0, 0), (x, y, 80, 35), 2)
            
            lbl = config.FONT_SMALL.render(f"{k} {label}", True, (0, 0, 0))
            screen.blit(lbl, (x + 40 - lbl.get_width()//2, y + 17 - lbl.get_height()//2))


def draw_messages(screen, state):
    if state.get("composing", False):
        res = state["keyboard"].draw(screen)
        # Handle touch logic is in main loop or separate function?
        # We need to detect touch events here or in input handler.
        pass
    else:
        # View Messages List
        screen.fill(config.WHITE)
        
        # Header
        pygame.draw.rect(screen, config.MAIN_COLOR, (0, 0, config.WIDTH, 50))
        title = config.FONT_MEDIUM.render("MESSAGES", True, config.WHITE)
        screen.blit(title, (20, 10))
        
        # Compose Button
        pygame.draw.rect(screen, config.GREEN, (350, 10, 100, 30))
        lbl = config.FONT_SMALL.render("COMPOSE", True, config.WHITE)
        screen.blit(lbl, (360, 15))
        
        y = 60
        msgs = state["messages"]["list"]
        start_idx = state.get("scroll_y", 0) # Just index for now
        
        if not msgs:
            lbl = config.FONT_SMALL.render("No messages.", True, config.GRAY)
            screen.blit(lbl, (150, 150))
        
        for i in range(start_idx, min(len(msgs), start_idx + 4)):
            m = msgs[i]
            # Draw message item
            color = (240, 240, 240) if m.get("read") else (255, 230, 230)
            pygame.draw.rect(screen, color, (20, y, 440, 50))
            pygame.draw.rect(screen, config.GRAY, (20, y, 440, 50), 1)
            
            sender = m.get("sender", "Unknown")
            txt = m.get("content", "")
            if len(txt) > 30: txt = txt[:27] + "..."
            
            name_lbl = config.FONT_SMALL.render(sender, True, config.BLACK)
            txt_lbl = config.FONT_TINY.render(txt, True, config.GRAY)
            
            screen.blit(name_lbl, (30, y + 5))
            screen.blit(txt_lbl, (30, y + 25))
            
            # Read indicator
            if not m.get("read"):
                pygame.draw.circle(screen, config.RED, (450, y+25), 5)
                
            y += 60

def handle_touch(state, pos):
    x, y = pos
    if state.get("composing", False):
        if state.get("keyboard"):
            res = state["keyboard"].handle_touch(pos)
            if res == "SENT":
                state["composing"] = False
        
        # Exit compose if touch outside?
        if x > 400 and y < 50: # Top right corner cancel
             state["composing"] = False
             
    else:
        # List view touches
        if 350 <= x <= 450 and 10 <= y <= 40:
            # Compose button
            state["composing"] = True
            state["keyboard"] = T9Keyboard()
            state["keyboard"].recipient = "AMO" if config.IDENTITY == "BMO" else "BMO"
            
        # Message click logic...
        # For now simple scrolling or selecting could be implemented
