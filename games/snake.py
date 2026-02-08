import pygame
import random
import time

class SnakeGame:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid_size = 20
        self.reset()
        
    def reset(self):
        self.snake = [(self.width // 2, self.height // 2)]
        self.direction = (self.grid_size, 0)
        self.food = self._spawn_food()
        self.score = 0
        self.game_over = False
        self.last_move = time.time()
        self.move_delay = 0.2  # Speed
        
    def _spawn_food(self):
        while True:
            x = random.randrange(0, self.width, self.grid_size)
            y = random.randrange(0, self.height, self.grid_size)
            if (x, y) not in self.snake:
                return (x, y)
                
    def handle_input(self, pos):
        # Divide screen into 4 triangles for direction
        x, y = pos
        # Calculate relative to center
        rx = x - self.width // 2
        ry = y - self.height // 2
        
        if abs(rx) > abs(ry):
            if rx > 0 and self.direction != (-self.grid_size, 0): # Right
                self.direction = (self.grid_size, 0)
            elif rx < 0 and self.direction != (self.grid_size, 0): # Left
                self.direction = (-self.grid_size, 0)
        else:
            if ry > 0 and self.direction != (0, -self.grid_size): # Down
                self.direction = (0, self.grid_size)
            elif ry < 0 and self.direction != (0, self.grid_size): # Up
                self.direction = (0, -self.grid_size)

    def update(self):
        if self.game_over:
            return
            
        if time.time() - self.last_move > self.move_delay:
            self.last_move = time.time()
            
            # New head
            head_x, head_y = self.snake[0]
            new_head = (head_x + self.direction[0], head_y + self.direction[1])
            
            # Collision with walls
            if (new_head[0] < 0 or new_head[0] >= self.width or 
                new_head[1] < 0 or new_head[1] >= self.height):
                self.game_over = True
                return
                
            # Collision with self
            if new_head in self.snake:
                self.game_over = True
                return
                
            self.snake.insert(0, new_head)
            
            # Eating food
            if new_head == self.food:
                self.score += 1
                self.food = self._spawn_food()
                # Increase speed slightly
                self.move_delay = max(0.08, self.move_delay * 0.98)
            else:
                self.snake.pop()

    def draw(self, screen):
        # Background
        screen.fill((46, 204, 113)) # Green background
        
        # Grid (subtle)
        for x in range(0, self.width, self.grid_size):
            pygame.draw.line(screen, (39, 174, 96), (x, 0), (x, self.height))
        for y in range(0, self.height, self.grid_size):
            pygame.draw.line(screen, (39, 174, 96), (0, y), (self.width, y))
            
        # Food
        pygame.draw.rect(screen, (231, 76, 60), (*self.food, self.grid_size, self.grid_size))
        
        # Snake
        for i, (x, y) in enumerate(self.snake):
            color = (44, 62, 80) if i == 0 else (52, 73, 94)
            pygame.draw.rect(screen, color, (x+1, y+1, self.grid_size-2, self.grid_size-2))
            
        # Score
        font = pygame.font.SysFont(None, 24)
        score_txt = font.render(f"PUNTOS: {self.score}", True, (255, 255, 255))
        screen.blit(score_txt, (10, 10))
        
        if self.game_over:
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            
            font_lg = pygame.font.SysFont(None, 48)
            msg = font_lg.render("GAME OVER", True, (255, 255, 255))
            hint = font.render("Tap to Exit", True, (200, 200, 200))
            screen.blit(msg, (self.width//2 - msg.get_width()//2, self.height//2 - 20))
            screen.blit(hint, (self.width//2 - hint.get_width()//2, self.height//2 + 30))
