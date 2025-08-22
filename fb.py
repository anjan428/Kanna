import pygame
import random
import sys
import math
from pathlib import Path

# ---------------------------
# Flappy Bird — Pygame (no assets)
# Single file. Run:  python flappy.py
# Controls: SPACE / UP to flap, P to pause, R to restart, ESC to quit
# ---------------------------

# --- Config ---
WIDTH, HEIGHT = 420, 680
FPS = 60
GROUND_H = 90
PIPE_W = 70
PIPE_GAP = 170
PIPE_SPEED = 3.2
SPAWN_EVERY = 1500  # ms

BIRD_X = 90
BIRD_SIZE = 26
GRAVITY = 0.42
FLAP_V = -8.5
MAX_FALL = 10

BG_TOP = (120, 200, 255)
BG_BOTTOM = (70, 170, 245)
GREEN = (70, 200, 120)
DARK_GREEN = (40, 120, 70)
WHITE = (255, 255, 255)
BLACK = (20, 26, 34)
SAND = (232, 219, 182)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird — Pygame")
clock = pygame.time.Clock()
font_big = pygame.font.SysFont("arialroundedmt", 48)
font_med = pygame.font.SysFont("arialroundedmt", 28)
font_small = pygame.font.SysFont("arial", 20)

# Persist high score
HS_FILE = Path("flappy_highscore.txt")
def load_hs():
    try:
        return int(HS_FILE.read_text().strip())
    except Exception:
        return 0

def save_hs(v):
    try:
        HS_FILE.write_text(str(int(v)))
    except Exception:
        pass

HIGH_SCORE = load_hs()


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_bg():
    # vertical gradient background
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        pygame.draw.line(screen, lerp_color(BG_TOP, BG_BOTTOM, t), (0, y), (WIDTH, y))

    # ground
    pygame.draw.rect(screen, SAND, (0, HEIGHT - GROUND_H, WIDTH, GROUND_H))
    # subtle ground stripes
    for x in range(0, WIDTH, 20):
        pygame.draw.line(screen, (220, 210, 175), (x, HEIGHT - GROUND_H + 6), (x + 10, HEIGHT - 4), 2)


class Bird:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = BIRD_X
        self.y = HEIGHT * 0.45
        self.vy = 0.0
        self.alive = True
        self.angle = 0.0  # for tilt animation
        self.anim_t = 0.0

    def flap(self):
        self.vy = FLAP_V

    def update(self, dt):
        if not self.alive:
            return
        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        self.y += self.vy
        # tilt based on velocity
        self.angle = max(-25, min(60, -self.vy * 3))
        self.anim_t += dt

    def draw(self):
        # Draw a stylized bird (circle + beak + wing) rotated slightly
        surf = pygame.Surface((BIRD_SIZE * 2, BIRD_SIZE * 2), pygame.SRCALPHA)
        cx, cy = BIRD_SIZE, BIRD_SIZE
        body_col = (255, 235, 120)
        wing_col = (245, 210, 90)
        eye_col = BLACK
        beak_col = (255, 140, 0)
        # body
        pygame.draw.circle(surf, body_col, (cx, cy), BIRD_SIZE - 2)
        # wing flaps subtly with time
        wing_offset = int(3 * math.sin(self.anim_t * 8))
        pygame.draw.ellipse(surf, wing_col, (cx - 10, cy + wing_offset, 20, 10))
        # eye
        pygame.draw.circle(surf, WHITE, (cx + 8, cy - 6), 5)
        pygame.draw.circle(surf, eye_col, (cx + 9, cy - 6), 2)
        # beak
        pygame.draw.polygon(surf, beak_col, [(cx + 18, cy), (cx + 6, cy + 4), (cx + 6, cy - 4)])

        rotated = pygame.transform.rotate(surf, self.angle)
        rect = rotated.get_rect(center=(self.x, self.y))
        screen.blit(rotated, rect)

    @property
    def rect(self):
        return pygame.Rect(self.x - (BIRD_SIZE - 6), self.y - (BIRD_SIZE - 6), (BIRD_SIZE - 6) * 2, (BIRD_SIZE - 6) * 2)


class Pipe:
    def __init__(self, x):
        self.x = x
        self.gap_y = random.randint(int(HEIGHT * 0.25), int(HEIGHT * 0.65))
        self.passed = False

    def update(self, dt):
        self.x -= PIPE_SPEED

    def offscreen(self):
        return self.x + PIPE_W < -4

    def draw(self):
        top_h = self.gap_y - PIPE_GAP // 2
        bot_y = self.gap_y + PIPE_GAP // 2
        # pipes
        pygame.draw.rect(screen, GREEN, (self.x, 0, PIPE_W, top_h))
        pygame.draw.rect(screen, DARK_GREEN, (self.x, top_h - 20, PIPE_W, 20))  # cap
        pygame.draw.rect(screen, GREEN, (self.x, bot_y, PIPE_W, HEIGHT - bot_y - GROUND_H))
        pygame.draw.rect(screen, DARK_GREEN, (self.x, bot_y, PIPE_W, 20))  # cap

    def collides(self, rect):
        top_h = self.gap_y - PIPE_GAP // 2
        bot_y = self.gap_y + PIPE_GAP // 2
        pipe_top = pygame.Rect(self.x, 0, PIPE_W, top_h)
        pipe_bottom = pygame.Rect(self.x, bot_y, PIPE_W, HEIGHT - bot_y - GROUND_H)
        return rect.colliderect(pipe_top) or rect.colliderect(pipe_bottom)


class Game:
    def __init__(self):
        self.state = "ready"  # ready | playing | gameover | paused
        self.bird = Bird()
        self.pipes = []
        self.score = 0
        self.time_since_spawn = 0

        # For a simple parallax ground scroll
        self.ground_x = 0

    def reset(self):
        global HIGH_SCORE
        if self.score > HIGH_SCORE:
            HIGH_SCORE = self.score
            save_hs(HIGH_SCORE)
        self.state = "ready"
        self.bird.reset()
        self.pipes.clear()
        self.score = 0
        self.time_since_spawn = 0
        self.ground_x = 0

    def start(self):
        if self.state in ("ready", "gameover"):
            self.state = "playing"
            self.bird.reset()
            self.pipes.clear()
            self.score = 0
            self.time_since_spawn = 0

    def flap(self):
        if self.state == "ready":
            self.start()
        if self.state == "playing":
            self.bird.flap()

    def toggle_pause(self):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def update(self, dt):
        if self.state != "playing":
            return
        self.time_since_spawn += dt
        if self.time_since_spawn >= SPAWN_EVERY:
            self.time_since_spawn = 0
            self.pipes.append(Pipe(WIDTH + 10))

        # update bird & pipes
        self.bird.update(dt / 1000.0)
        for p in self.pipes:
            p.update(dt)

        # remove offscreen pipes
        self.pipes = [p for p in self.pipes if not p.offscreen()]

        # scoring
        for p in self.pipes:
            if not p.passed and p.x + PIPE_W < self.bird.x:
                p.passed = True
                self.score += 1

        # collisions with pipes
        for p in self.pipes:
            if p.collides(self.bird.rect):
                self.state = "gameover"
                self.bird.alive = False
                break

        # ground / ceiling
        if self.bird.y + (BIRD_SIZE - 6) >= HEIGHT - GROUND_H or self.bird.y - (BIRD_SIZE - 6) <= 0:
            self.state = "gameover"
            self.bird.alive = False

        # ground scroll
        self.ground_x = (self.ground_x - PIPE_SPEED) % 40

    def draw_ui(self):
        if self.state in ("ready", "playing"):
            score_surf = font_big.render(str(self.score), True, WHITE)
            screen.blit(score_surf, score_surf.get_rect(center=(WIDTH//2, 80)))

        # Top HUD
        hs_text = font_small.render(f"HI {HIGH_SCORE}", True, WHITE)
        screen.blit(hs_text, (12, 10))

        if self.state == "ready":
            title = font_big.render("FLAPPY", True, WHITE)
            title2 = font_big.render("BIRD", True, WHITE)
            tip = font_med.render("Press SPACE to flap", True, WHITE)
            sub = font_small.render("P: pause  R: restart  ESC: quit", True, WHITE)
            screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//2 - 90)))
            screen.blit(title2, title2.get_rect(center=(WIDTH//2, HEIGHT//2 - 50)))
            screen.blit(tip, tip.get_rect(center=(WIDTH//2, HEIGHT//2 + 10)))
            screen.blit(sub, sub.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))

        if self.state == "paused":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,120))
            screen.blit(overlay, (0,0))
            txt = font_big.render("PAUSED", True, WHITE)
            screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2)))

        if self.state == "gameover":
            over = font_big.render("GAME OVER", True, WHITE)
            score_t = font_med.render(f"Score: {self.score}", True, WHITE)
            best_t = font_small.render("Press R to restart", True, WHITE)
            screen.blit(over, over.get_rect(center=(WIDTH//2, HEIGHT//2 - 40)))
            screen.blit(score_t, score_t.get_rect(center=(WIDTH//2, HEIGHT//2 + 10)))
            screen.blit(best_t, best_t.get_rect(center=(WIDTH//2, HEIGHT//2 + 40)))

    def draw(self):
        draw_bg()
        # pipes
        for p in self.pipes:
            p.draw()
        # bird
        self.bird.draw()

        # draw repeating ground bumps for motion
        for x in range(-40, WIDTH + 40, 40):
            pygame.draw.rect(screen, (210, 200, 165), (x + int(self.ground_x), HEIGHT - GROUND_H + 18, 30, 10), border_radius=3)
        self.draw_ui()


def handle_events(game):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE,):
                pygame.quit(); sys.exit()
            if event.key in (pygame.K_SPACE, pygame.K_UP):
                game.flap()
            if event.key == pygame.K_p:
                game.toggle_pause()
            if event.key == pygame.K_r:
                game.reset()


def main():
    game = Game()
    # spawn a couple starter pipes for aesthetics
    game.pipes = [Pipe(WIDTH + 120), Pipe(WIDTH + 120 + 200)]

    last_tick = pygame.time.get_ticks()
    while True:
        handle_events(game)
        now = pygame.time.get_ticks()
        dt = now - last_tick
        last_tick = now

        game.update(dt)
        game.draw()

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
