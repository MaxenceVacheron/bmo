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
        return

    # Original BMO Style
    screen.fill(config.PINK) # PINK background
    
    # Header styling
    pygame.draw.rect(screen, config.BLACK, (0, 0, config.WIDTH, 50))
    title = config.FONT_MEDIUM.render("BMO INBOX", True, config.WHITE)
    screen.blit(title, (config.WIDTH//2 - title.get_width()//2, 10))
    
    # FETCH Button (Top Right) - RESTORED
    pygame.draw.rect(screen, config.BLUE, (config.WIDTH - 90, 10, 80, 30), border_radius=5)
    lbl = config.FONT_TINY.render("FETCH", True, config.WHITE)
    screen.blit(lbl, (config.WIDTH - 50 - lbl.get_width()//2, 17))

    # WRITE/COMPOSE Button (Top Left) - NEW LOCATION
    pygame.draw.rect(screen, config.GREEN, (10, 10, 80, 30), border_radius=5)
    lbl = config.FONT_TINY.render("WRITE", True, config.WHITE)
    screen.blit(lbl, (50 - lbl.get_width()//2, 17))
    
    msgs = state["messages"]["list"]
    if not msgs:
        lbl = config.FONT_SMALL.render("No messages yet!", True, config.BLACK)
        screen.blit(lbl, (config.WIDTH//2 - lbl.get_width()//2, config.HEIGHT//2))
    else:
        # Pagination
        items_per_page = 4
        page = state.get("menu_page", 0)
        start_idx = page * items_per_page
        visible = msgs[start_idx:start_idx + items_per_page]
        
        for i, m in enumerate(visible):
            y = 60 + i * 55
            rect = (20, y, 440, 50)
            pygame.draw.rect(screen, config.WHITE, rect, border_radius=10)
            pygame.draw.rect(screen, config.BLACK, rect, 2, border_radius=10)
            
            sender = m.get("sender", "Unknown")
            content = m.get("content", "")
            if len(content) > 30: content = content[:27] + "..."
            
            ts = m.get("timestamp", 0)
            formatted_time = time.strftime("%d/%m %H:%M", time.localtime(ts)) if ts else ""
            
            lbl_s = config.FONT_TINY.render(f"From: {sender}", True, config.BLACK)
            lbl_t = config.FONT_TINY.render(formatted_time, True, config.GRAY)
            lbl_c = config.FONT_SMALL.render(content, True, config.BLACK)
            
            screen.blit(lbl_s, (40, y + 5))
            screen.blit(lbl_t, (config.WIDTH - 40 - lbl_t.get_width(), y + 5))
            screen.blit(lbl_c, (40, y + 22))
            
            # Unread indicator
            if not m.get("read"):
                 pygame.draw.circle(screen, config.RED, (450, y+25), 5)

        # Navigation
        nav_y = 280
        if page > 0:
            lbl = config.FONT_TINY.render("< PREV", True, config.BLACK)
            screen.blit(lbl, (20, nav_y))
        if len(msgs) > (page + 1) * items_per_page:
            lbl = config.FONT_TINY.render("NEXT >", True, config.BLACK)
            screen.blit(lbl, (config.WIDTH - 80, nav_y))

    # EXIT Button (Center Bottom)
    pygame.draw.rect(screen, config.GRAY, (config.WIDTH//2 - 40, 280, 80, 30), border_radius=5)
    lbl = config.FONT_TINY.render("EXIT", True, config.WHITE)
    screen.blit(lbl, (config.WIDTH//2 - lbl.get_width()//2, 287))

def handle_touch(state, pos):
    x, y = pos
    if state.get("composing", False):
        if state.get("keyboard"):
            res = state["keyboard"].handle_touch(pos)
            if res == "SENT":
                state["composing"] = False
        
        # Exit compose if touch outside keyboard area?
        # Keyboard is roughly bottom half, allow specific cancel button if needed
        # Or just tap top area
        if y < 50: 
             state["composing"] = False
        return

    # List View Touches
    # FETCH (Top Right)
    if x > config.WIDTH - 90 and y < 40:
        network.sync_messages(state)
        return

    # WRITE (Top Left)
    if x < 90 and y < 40:
        state["composing"] = True
        state["keyboard"] = T9Keyboard()
        # Auto-recipient based on identity
        state["keyboard"].recipient = "BMO" if config.IDENTITY == "AMO" else "AMO"
        return

    # EXIT (Bottom Center)
    if config.WIDTH//2 - 40 <= x <= config.WIDTH//2 + 40 and y > 280:
        state["current_mode"] = "MENU" # Go back to menu
        return

    # PREV/NEXT
    page = state.get("menu_page", 0)
    items_per_page = 4
    msgs = state["messages"]["list"]
    
    if y > 280:
        if x < 100 and page > 0:
            state["menu_page"] = page - 1
        elif x > config.WIDTH - 100 and len(msgs) > (page + 1) * items_per_page:
            state["menu_page"] = page + 1
        return

    # Message Click
    # Rows start at 60, height 55 (50 + 5 gap?)
    # y = 60 + i * 55
    # i = (y - 60) // 55
    if 60 <= y <= 280:
        idx = (y - 60) // 55
        start_idx = page * items_per_page
        real_idx = start_idx + idx
        if 0 <= idx < 4 and real_idx < len(msgs):
            # View Message
            # state["mode"] = "MESSAGE_VIEW" # Need to ensure this mode exists or handle view here
            # For now just toggle read
            msgs[real_idx]["read"] = True
            # In original code, it goes to specific view. 
            # We haven't implemented MESSAGE_VIEW in this file yet? 
            # It was in bmo_pygame.py draw_message_view.
            pass
