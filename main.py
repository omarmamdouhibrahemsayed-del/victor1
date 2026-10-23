import pygame
import sys
import random
import math

# -----------------------------------------------------------------------------
# 1. INITIALIZATION & SETUP
# -----------------------------------------------------------------------------
pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 900, 500
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Vector Style Parkour - Eng. Omar Mamdouh")
clock = pygame.time.Clock()

# Colors (Vector Aesthetic)
COLOR_BG_TOP = (15, 23, 42)       # Dark Cyber Blue
COLOR_BG_BOTTOM = (30, 58, 138)   # Neon Navy
COLOR_SILHOUETTE = (10, 10, 12)   # Pitch Black for Character & Buildings
COLOR_CYAN = (6, 182, 212)        # Accent Cyan
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (100, 116, 139)

# Fonts
font_title = pygame.font.SysFont("Arial", 42, bold=True)
font_subtitle = pygame.font.SysFont("Arial", 20, bold=True)
font_ui = pygame.font.SysFont("Consolas", 18, bold=True)

# -----------------------------------------------------------------------------
# 2. GENERATIVE PROCEDURAL AUDIO (No external MP3 files needed)
# -----------------------------------------------------------------------------
def create_tone(frequency, duration, volume=0.3, wave_type="sine"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buf = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        if wave_type == "sine":
            val = math.sin(2 * math.pi * frequency * t)
        elif wave_type == "square":
            val = 1.0 if math.sin(2 * math.pi * frequency * t) > 0 else -1.0
        elif wave_type == "noise":
            val = random.uniform(-1.0, 1.0)
        else:
            val = 0
            
        # Envelope decay
        decay = (1.0 - (i / n_samples))
        sample_val = int(val * volume * decay * 32767)
        sample_val = max(-32768, min(32767, sample_val))
        buf.extend(sample_val.to_bytes(2, byteorder='little', signed=True))
    return pygame.mixer.Sound(buffer=bytes(buf))

snd_jump = create_tone(450, 0.15, volume=0.2, wave_type="sine")
snd_slide = create_tone(150, 0.25, volume=0.25, wave_type="noise")
snd_land = create_tone(80, 0.1, volume=0.4, wave_type="square")

# -----------------------------------------------------------------------------
# 3. VFX & PARTICLES SYSTEM
# -----------------------------------------------------------------------------
particles = []
ghost_trails = []

def add_particles(x, y, color, count=10):
    for _ in range(count):
        particles.append({
            'x': x,
            'y': y,
            'vx': random.uniform(-3, 3),
            'vy': random.uniform(-2, 1),
            'size': random.uniform(2, 5),
            'color': color,
            'life': random.randint(15, 30)
        })

def update_particles():
    for p in particles[:]:
        p['x'] += p['vx']
        p['y'] += p['vy']
        p['size'] = max(0, p['size'] - 0.15)
        p['life'] -= 1
        if p['life'] <= 0 or p['size'] <= 0:
            particles.remove(p)

def draw_particles(surface):
    for p in particles:
        pygame.draw.circle(surface, p['color'], (int(p['x']), int(p['y'])), int(p['size']))

# -----------------------------------------------------------------------------
# 4. GAME OBJECTS (Player, Buildings, Obstacles)
# -----------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.x = 150
        self.y = 300
        self.width = 24
        self.height = 54
        self.vy = 0
        self.gravity = 0.75
        self.is_grounded = True
        self.is_sliding = False
        self.slide_timer = 0
        self.anim_frame = 0

    def jump(self):
        if self.is_grounded:
            self.vy = -14.5
            self.is_grounded = False
            self.is_sliding = False
            snd_jump.play()
            add_particles(self.x + self.width // 2, self.y + self.height, COLOR_CYAN, 12)

    def slide(self):
        if self.is_grounded and not self.is_sliding:
            self.is_sliding = True
            self.slide_timer = 30
            snd_slide.play()
            add_particles(self.x, self.y + self.height, COLOR_WHITE, 8)

    def update(self, ground_y):
        # Apply Gravity
        self.vy += self.gravity
        self.y += self.vy

        # Check Ground Collision
        if self.y + self.height >= ground_y:
            if not self.is_grounded:
                snd_land.play()
                add_particles(self.x + self.width // 2, ground_y, COLOR_CYAN, 10)
            self.y = ground_y - self.height
            self.vy = 0
            self.is_grounded = True

        # Handle Sliding State
        if self.is_sliding:
            self.height = 26
            self.slide_timer -= 1
            if self.slide_timer <= 0:
                self.is_sliding = False
                self.height = 54
                self.y -= 28  # Restore height smoothly

        # Add Ghost Trail for Vector Motion Blur Effect
        if random.random() < 0.4:
            ghost_trails.append({
                'rect': pygame.Rect(self.x, self.y, self.width, self.height),
                'alpha': 120
            })

        self.anim_frame += 1

    def draw(self, surface):
        # Render Motion Ghost Trails
        for gt in ghost_trails[:]:
            s = pygame.Surface((gt['rect'].width, gt['rect'].height))
            s.set_alpha(gt['alpha'])
            s.fill(COLOR_CYAN)
            surface.blit(s, (gt['rect'].x - 10, gt['rect'].y))
            gt['alpha'] -= 12
            if gt['alpha'] <= 0:
                ghost_trails.remove(gt)

        # Draw Player Silhouette
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, COLOR_SILHOUETTE, rect, border_radius=4)
        
        # Add Vector-Style Cyan Headvisor Accent
        head_y = self.y + 4 if not self.is_sliding else self.y + 2
        pygame.draw.rect(surface, COLOR_CYAN, (self.x + 12, head_y, 8, 4))


class Building:
    def __init__(self, x, width, height):
        self.rect = pygame.Rect(x, HEIGHT - height, width, height)

class Obstacle:
    def __init__(self, x, y, width, height, is_high=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.is_high = is_high  # High obstacles require slide, low require jump

# -----------------------------------------------------------------------------
# 5. MAIN GAME LOOP & STATE MANAGEMENT
# -----------------------------------------------------------------------------
def run_game():
    player = Player()
    speed = 7
    score = 0
    screen_shake = 0

    ground_level = 380
    buildings = [
        Building(0, 400, 120),
        Building(420, 500, 120),
        Building(940, 600, 120)
    ]
    obstacles = [
        Obstacle(600, ground_level - 35, 25, 35, is_high=False),
        Obstacle(1000, ground_level - 70, 30, 40, is_high=True)
    ]

    game_state = "MENU"  # MENU, PLAYING, GAMEOVER

    while True:
        # Gradient Background
        for i in range(HEIGHT):
            ratio = i / HEIGHT
            r = int(COLOR_BG_TOP[0] * (1 - ratio) + COLOR_BG_BOTTOM[0] * ratio)
            g = int(COLOR_BG_TOP[1] * (1 - ratio) + COLOR_BG_BOTTOM[1] * ratio)
            b = int(COLOR_BG_TOP[2] * (1 - ratio) + COLOR_BG_BOTTOM[2] * ratio)
            pygame.draw.line(screen, (r, g, b), (0, i), (WIDTH, i))

        # Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if game_state == "MENU" and event.key == pygame.K_SPACE:
                    game_state = "PLAYING"
                    player = Player()
                    score = 0
                    speed = 7
                    obstacles.clear()
                    obstacles.append(Obstacle(700, ground_level - 35, 25, 35, is_high=False))

                elif game_state == "PLAYING":
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        player.jump()
                    elif event.key == pygame.K_DOWN:
                        player.slide()

                elif game_state == "GAMEOVER" and event.key == pygame.K_SPACE:
                    game_state = "MENU"

        # ---------------------------------------------------------------------
        # STATE: MENU
        # ---------------------------------------------------------------------
        if game_state == "MENU":
            # Title
            t_surf = font_title.render("VECTOR RUNNER 2D", True, COLOR_WHITE)
            screen.blit(t_surf, (WIDTH // 2 - t_surf.get_width() // 2, 130))

            # Developer Name Tag
            dev_surf = font_subtitle.render("Developed by: Eng. Omar Mamdouh", True, COLOR_CYAN)
            screen.blit(dev_surf, (WIDTH // 2 - dev_surf.get_width() // 2, 190))

            # Instruction
            i_surf = font_ui.render("Press [SPACE] to Start | [UP] Jump | [DOWN] Slide", True, COLOR_GRAY)
            screen.blit(i_surf, (WIDTH // 2 - i_surf.get_width() // 2, 300))

        # ---------------------------------------------------------------------
        # STATE: PLAYING
        # ---------------------------------------------------------------------
        elif game_state == "PLAYING":
            score += 1
            speed = 7 + (score // 500) * 0.5  # Progressive difficulty

            # Move World Elements
            for b in buildings:
                b.rect.x -= int(speed * 0.5)
            if buildings[0].rect.right < 0:
                buildings.pop(0)
                new_x = buildings[-1].rect.right
                buildings.append(Building(new_x, random.randint(400, 700), 120))

            for obs in obstacles:
                obs.rect.x -= int(speed)
            if obstacles and obstacles[0].rect.right < 0:
                obstacles.pop(0)

            # Spawn Obstacles
            if len(obstacles) == 0 or obstacles[-1].rect.x < WIDTH - random.randint(300, 500):
                is_hi = random.choice([True, False])
                obs_y = ground_level - 75 if is_hi else ground_level - 35
                obstacles.append(Obstacle(WIDTH + 100, obs_y, 30, 40, is_high=is_hi))

            # Update Player & Particles
            player.update(ground_level)
            update_particles()

            # Collision Detection
            p_rect = pygame.Rect(player.x, player.y, player.width, player.height)
            for obs in obstacles:
                if p_rect.colliderect(obs.rect):
                    screen_shake = 15
                    snd_land.play()
                    game_state = "GAMEOVER"

            # Render Buildings (City Silhouette)
            for b in buildings:
                pygame.draw.rect(screen, COLOR_SILHOUETTE, b.rect)
                pygame.draw.line(screen, COLOR_CYAN, (b.rect.left, b.rect.top), (b.rect.right, b.rect.top), 2)

            # Render Obstacles
            for obs in obstacles:
                pygame.draw.rect(screen, COLOR_SILHOUETTE, obs.rect, border_radius=3)
                pygame.draw.rect(screen, COLOR_CYAN, obs.rect, width=2, border_radius=3)

            # Render Player & VFX
            draw_particles(screen)
            player.draw(screen)

            # Draw HUD Score & Author Tag
            score_txt = font_ui.render(f"SCORE: {score}", True, COLOR_WHITE)
            author_txt = font_ui.render("Eng. Omar Mamdouh", True, COLOR_CYAN)
            screen.blit(score_txt, (20, 20))
            screen.blit(author_txt, (WIDTH - author_txt.get_width() - 20, 20))

        # ---------------------------------------------------------------------
        # STATE: GAME OVER
        # ---------------------------------------------------------------------
        elif game_state == "GAMEOVER":
            go_surf = font_title.render("GAME OVER", True, (239, 68, 68))
            screen.blit(go_surf, (WIDTH // 2 - go_surf.get_width() // 2, 160))

            sc_surf = font_subtitle.render(f"Final Score: {score}", True, COLOR_WHITE)
            screen.blit(sc_surf, (WIDTH // 2 - sc_surf.get_width() // 2, 230))

            r_surf = font_ui.render("Press [SPACE] for Main Menu", True, COLOR_GRAY)
            screen.blit(r_surf, (WIDTH // 2 - r_surf.get_width() // 2, 300))

        # Screen Shake Effect on Impact
        render_surface = screen
        if screen_shake > 0:
            screen_shake -= 1
            shake_x = random.randint(-4, 4)
            shake_y = random.randint(-4, 4)
            screen.blit(render_surface, (shake_x, shake_y))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    run_game()