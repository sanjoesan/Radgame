import json
import math
import random
import sys
from pathlib import Path

import pygame

from routes import ROUTES

W, H = 900, 640
FPS = 60
ROAD_LEFT = 260
ROAD_RIGHT = 640
ROAD_WIDTH = ROAD_RIGHT - ROAD_LEFT
PLAYER_Y = 460
PLAYER_W, PLAYER_H = 26, 48
PX_PER_M = 25
MIN_SPEED = 8
MAX_SPEED = 58
MAX_ENERGY = 100
DRINK_AMOUNT = 32
WATER_BOTTLES = 3

GRASS = (60, 110, 60)
GRASS_DARK = (40, 80, 45)
ROAD = (72, 72, 82)
ROAD_EDGE = (220, 220, 220)
LANE_LINE = (240, 230, 110)
HUD_BG = (15, 20, 30)
HUD_TEXT = (220, 225, 235)
HUD_DIM = (130, 140, 160)
WHITE = (250, 250, 255)
BLACK = (15, 18, 24)
RED = (220, 60, 60)
GREEN = (80, 200, 100)
BLUE = (90, 150, 230)
YELLOW = (250, 210, 80)
ORANGE = (240, 140, 50)
BROWN = (110, 75, 40)
BROWN_DARK = (75, 50, 25)

SAVE_FILE = Path(__file__).parent / "save.json"


def load_save():
    if SAVE_FILE.exists():
        try:
            return json.loads(SAVE_FILE.read_text())
        except Exception:
            pass
    return {"points": 0, "races": 0, "best": {}}


def save_state(state):
    SAVE_FILE.write_text(json.dumps(state, indent=2))


def make_cyclist_sprite(jersey, helmet, w=PLAYER_W, h=PLAYER_H):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = w // 2
    pygame.draw.rect(s, BLACK, (cx - 1, 0, 3, 7))
    pygame.draw.rect(s, (60, 60, 70), (cx - 7, 7, 14, 2))
    pygame.draw.rect(s, jersey, (cx - 5, 9, 10, 3))
    pygame.draw.rect(s, jersey, (cx - 8, 12, 16, 4))
    pygame.draw.ellipse(s, helmet, (cx - 5, 16, 10, 8))
    pygame.draw.rect(s, jersey, (cx - 7, 22, 14, 13))
    pygame.draw.rect(s, (35, 35, 42), (cx - 2, 35, 4, 4))
    pygame.draw.rect(s, BLACK, (cx - 1, 39, 3, 9))
    return s


def make_pothole_sprite(w=30, h=14):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (18, 18, 22), (0, 0, w, h))
    pygame.draw.ellipse(s, (38, 38, 48), (3, 2, w - 6, h - 4))
    return s


def make_branch_sprite(w=34, h=10):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, BROWN_DARK, (0, h // 2 - 2, w, 4))
    pygame.draw.rect(s, BROWN, (0, h // 2 - 1, w, 2))
    pygame.draw.rect(s, BROWN, (w - 6, 1, 4, 3))
    pygame.draw.rect(s, BROWN, (4, h - 4, 4, 3))
    return s


class Player:
    def __init__(self):
        self.x = (ROAD_LEFT + ROAD_RIGHT) / 2
        self.distance = 0.0
        self.speed = 22.0
        self.target_speed = 22.0
        self.energy = MAX_ENERGY
        self.water = WATER_BOTTLES
        self.crashed_timer = 0.0
        self.flash_timer = 0.0

    def drink(self):
        if self.water > 0 and self.energy < MAX_ENERGY:
            self.water -= 1
            self.energy = min(MAX_ENERGY, self.energy + DRINK_AMOUNT)
            return True
        return False

    def update(self, dt, keys, route, wind_phase):
        accel = keys[pygame.K_UP] or keys[pygame.K_w]
        brake = keys[pygame.K_DOWN] or keys[pygame.K_s]
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        if self.crashed_timer > 0:
            self.crashed_timer -= dt
            self.target_speed = max(MIN_SPEED, self.target_speed - 25 * dt)
        elif accel and self.energy > 0:
            self.target_speed = min(MAX_SPEED, self.target_speed + 10 * dt)
        elif brake:
            self.target_speed = max(MIN_SPEED, self.target_speed - 14 * dt)
        else:
            self.target_speed += (24 - self.target_speed) * 0.4 * dt

        if self.energy <= 0:
            self.target_speed = min(self.target_speed, 14)

        self.speed += (self.target_speed - self.speed) * 2.8 * dt
        self.speed = max(MIN_SPEED, min(MAX_SPEED, self.speed))

        self.distance += self.speed / 3.6 * dt

        steer = 230 * dt
        if left:
            self.x -= steer
        if right:
            self.x += steer

        wind = route.get("wind", 0)
        if wind > 0:
            gust = math.sin(wind_phase) * wind
            self.x += gust * 45 * dt

        self.x = max(ROAD_LEFT + PLAYER_W // 2, min(ROAD_RIGHT - PLAYER_W // 2, self.x))

        base_drain = 0.35
        over = max(0.0, (self.speed - 22) / 18)
        drain = base_drain + over ** 2 * 3.4
        drain *= 1.0 + route.get("heat", 0) * 0.6
        self.energy = max(0.0, self.energy - drain * dt)

        if self.flash_timer > 0:
            self.flash_timer -= dt


class Opponent:
    def __init__(self, start_distance, base_speed):
        self.x = random.uniform(ROAD_LEFT + 22, ROAD_RIGHT - 22)
        self.distance = start_distance
        self.speed = base_speed
        self.target_speed = base_speed
        self.jersey = (random.randint(60, 230), random.randint(60, 230), random.randint(60, 230))
        self.helmet = (random.randint(40, 220), random.randint(40, 220), random.randint(40, 220))
        self.sprite = make_cyclist_sprite(self.jersey, self.helmet)
        self.wobble_phase = random.uniform(0, math.tau)

    def update(self, dt):
        self.target_speed += random.gauss(0, 1.5) * dt
        self.target_speed = max(16, min(46, self.target_speed))
        self.speed += (self.target_speed - self.speed) * 1.2 * dt
        self.distance += self.speed / 3.6 * dt
        self.wobble_phase += dt * 2
        self.x += math.sin(self.wobble_phase) * 12 * dt
        self.x = max(ROAD_LEFT + 16, min(ROAD_RIGHT - 16, self.x))


class Obstacle:
    def __init__(self, distance, x, kind):
        self.distance = distance
        self.x = x
        self.kind = kind
        self.hit = False


def player_position(player, opponents):
    ahead = sum(1 for o in opponents if o.distance > player.distance)
    return ahead + 1


def spawn_obstacles_ahead(player, obstacles, density, next_distance):
    horizon = player.distance + 220
    while next_distance < horizon:
        x = random.uniform(ROAD_LEFT + 18, ROAD_RIGHT - 18)
        kind = random.choice(["pothole", "branch", "branch", "pothole"])
        obstacles.append(Obstacle(next_distance, x, kind))
        gap = random.uniform(16, 38) / max(density, 0.15)
        next_distance += gap
    return next_distance


def check_collisions(player, obstacles):
    half_w = PLAYER_W // 2
    for o in obstacles:
        if o.hit:
            continue
        dd = o.distance - player.distance
        if -0.4 < dd < 0.9:
            reach = 16 if o.kind == "pothole" else 18
            if abs(o.x - player.x) < half_w + reach - 6:
                o.hit = True
                if o.kind == "pothole":
                    player.target_speed *= 0.45
                    player.speed *= 0.55
                    player.crashed_timer = 0.5
                    player.energy = max(0, player.energy - 3)
                else:
                    player.target_speed *= 0.75
                    player.speed *= 0.8
                    player.energy = max(0, player.energy - 8)
                    player.crashed_timer = 0.3
                player.flash_timer = 0.25


def draw_road(screen, scroll):
    screen.fill(GRASS)
    for i in range(0, H, 40):
        y_off = (int(scroll * 0.3) + i) % 80
        if y_off < 40:
            pygame.draw.rect(screen, GRASS_DARK, (0, i, ROAD_LEFT - 8, 22))
            pygame.draw.rect(screen, GRASS_DARK, (ROAD_RIGHT + 8, i, W - ROAD_RIGHT - 8, 22))
    pygame.draw.rect(screen, ROAD, (ROAD_LEFT, 0, ROAD_WIDTH, H))
    pygame.draw.rect(screen, ROAD_EDGE, (ROAD_LEFT - 3, 0, 4, H))
    pygame.draw.rect(screen, ROAD_EDGE, (ROAD_RIGHT - 1, 0, 4, H))
    cycle = 70
    offset = int(scroll) % cycle
    y = -offset
    while y < H:
        pygame.draw.rect(screen, LANE_LINE, (W // 2 - 3, y, 6, 36))
        y += cycle


def draw_finish_line(screen, player, distance_target):
    rem = distance_target - player.distance
    if rem > 30:
        return
    y = PLAYER_Y - rem * PX_PER_M
    for col in range(8):
        x = ROAD_LEFT + col * (ROAD_WIDTH / 8)
        color = WHITE if (col % 2 == 0) else BLACK
        pygame.draw.rect(screen, color, (x, y - 8, ROAD_WIDTH / 8 + 1, 8))
        color2 = BLACK if (col % 2 == 0) else WHITE
        pygame.draw.rect(screen, color2, (x, y, ROAD_WIDTH / 8 + 1, 8))


def draw_obstacle(screen, obs, player, pothole_spr, branch_spr):
    y = PLAYER_Y - (obs.distance - player.distance) * PX_PER_M
    if y < -30 or y > H + 30:
        return
    spr = pothole_spr if obs.kind == "pothole" else branch_spr
    screen.blit(spr, (obs.x - spr.get_width() // 2, y - spr.get_height() // 2))


def draw_player(screen, player, sprite):
    x = int(player.x - PLAYER_W // 2)
    y = int(PLAYER_Y - PLAYER_H // 2)
    if player.flash_timer > 0 and int(player.flash_timer * 20) % 2 == 0:
        flash = sprite.copy()
        flash.fill((255, 100, 100, 0), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(flash, (x, y))
    else:
        screen.blit(sprite, (x, y))


def draw_hud(screen, player, position, total, distance_remaining, fonts, route):
    h = 110
    pygame.draw.rect(screen, HUD_BG, (0, H - h, W, h))
    pygame.draw.rect(screen, (40, 50, 70), (0, H - h, W, 2))

    speed_int = int(round(player.speed))
    speed_text = fonts["big"].render(f"{speed_int}", True, WHITE)
    screen.blit(speed_text, (24, H - h + 18))
    unit = fonts["small"].render("km/h", True, HUD_DIM)
    screen.blit(unit, (24 + speed_text.get_width() + 6, H - h + 42))

    bar_x, bar_y, bar_w, bar_h = 24, H - 30, 220, 14
    pygame.draw.rect(screen, (30, 35, 48), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    pct = player.energy / MAX_ENERGY
    color = GREEN if pct > 0.5 else (YELLOW if pct > 0.2 else RED)
    pygame.draw.rect(screen, color, (bar_x, bar_y, int(bar_w * pct), bar_h), border_radius=4)
    label = fonts["small"].render(f"Energie {int(player.energy)}", True, HUD_TEXT)
    screen.blit(label, (bar_x, bar_y - 18))

    bx = 280
    for i in range(WATER_BOTTLES):
        color = BLUE if i < player.water else (50, 60, 80)
        pygame.draw.rect(screen, color, (bx + i * 24, H - 30, 18, 14), border_radius=3)
    label = fonts["small"].render("Wasser (Leertaste)", True, HUD_TEXT)
    screen.blit(label, (bx, H - 48))

    pos_text = fonts["mid"].render(f"Platz {position}/{total}", True, WHITE)
    screen.blit(pos_text, (W - pos_text.get_width() - 24, H - h + 22))
    d_text = fonts["small"].render(f"{int(distance_remaining)} m bis Ziel", True, HUD_DIM)
    screen.blit(d_text, (W - d_text.get_width() - 24, H - h + 56))

    cond_x = W // 2 - 60
    if route.get("wind", 0) > 0.4:
        screen.blit(fonts["small"].render("🌬 Wind", True, HUD_DIM), (cond_x, H - h + 22))
    if route.get("heat", 0) > 0.5:
        screen.blit(fonts["small"].render("🔥 Hitze", True, HUD_DIM), (cond_x, H - h + 44))


def run_menu(screen, save_data, fonts):
    clock = pygame.time.Clock()
    cursor = 0
    visible = 7
    row_h = 58
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    cursor = (cursor - 1) % len(ROUTES)
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    cursor = (cursor + 1) % len(ROUTES)
                if event.key == pygame.K_PAGEUP:
                    cursor = max(0, cursor - visible)
                if event.key == pygame.K_PAGEDOWN:
                    cursor = min(len(ROUTES) - 1, cursor + visible)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return ROUTES[cursor]
                if event.key == pygame.K_ESCAPE:
                    return None

        screen.fill((22, 26, 40))
        title = fonts["huge"].render("RADGAME", True, WHITE)
        screen.blit(title, (W // 2 - title.get_width() // 2, 24))
        sub = fonts["small"].render("Vom Noob zum Sieger — Strecke wählen", True, HUD_DIM)
        screen.blit(sub, (W // 2 - sub.get_width() // 2, 80))

        pts = fonts["mid"].render(f"Punkte: {save_data.get('points', 0)}", True, YELLOW)
        screen.blit(pts, (W - pts.get_width() - 30, 24))
        races = fonts["small"].render(f"Rennen: {save_data.get('races', 0)}", True, HUD_DIM)
        screen.blit(races, (W - races.get_width() - 30, 56))

        scroll_start = max(0, min(len(ROUTES) - visible, cursor - visible // 2))
        list_x = 70
        list_w = W - 140
        list_y0 = 120
        for slot in range(min(visible, len(ROUTES))):
            i = scroll_start + slot
            if i >= len(ROUTES):
                break
            r = ROUTES[i]
            y = list_y0 + slot * row_h
            sel = (i == cursor)
            bg = (40, 52, 80) if sel else (28, 32, 48)
            pygame.draw.rect(screen, bg, (list_x, y, list_w, row_h - 6), border_radius=10)
            if sel:
                pygame.draw.rect(screen, BLUE, (list_x, y, list_w, row_h - 6), 2, border_radius=10)
            name = fonts["mid"].render(r["name"], True, WHITE)
            screen.blit(name, (list_x + 18, y + 6))
            stars = "★" * r["difficulty"] + "☆" * (5 - r["difficulty"])
            meta = fonts["small"].render(
                f"{r['race']} · {r['region']} · {r['distance_m']} m · {stars}", True, HUD_DIM
            )
            screen.blit(meta, (list_x + 18, y + 30))
            best = save_data.get("best", {}).get(r["id"])
            if best:
                b = fonts["small"].render(f"Best: P{best}", True, YELLOW)
                screen.blit(b, (list_x + list_w - b.get_width() - 18, y + 14))

        # scroll indicators
        if scroll_start > 0:
            up = fonts["small"].render("▲", True, HUD_DIM)
            screen.blit(up, (W // 2 - 6, list_y0 - 14))
        if scroll_start + visible < len(ROUTES):
            dn = fonts["small"].render("▼", True, HUD_DIM)
            screen.blit(dn, (W // 2 - 6, list_y0 + visible * row_h - 4))

        hint = fonts["small"].render(
            "↑/↓ wählen · PgUp/PgDn springen · Enter starten · Esc beenden", True, HUD_DIM
        )
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 26))

        pygame.display.flip()


def run_race(screen, route, save_data, fonts):
    clock = pygame.time.Clock()
    player = Player()
    opponents = []
    base = 32 - route["difficulty"] * 1.0
    for _ in range(route["opponents"]):
        opponents.append(Opponent(random.uniform(18, 55), base + random.uniform(-3, 6)))
    obstacles = []
    next_obs_distance = 60.0
    spawn_density = route["obstacle_density"]
    distance_target = route["distance_m"]

    player_sprite = make_cyclist_sprite((220, 50, 50), (30, 80, 200))
    pothole_spr = make_pothole_sprite()
    branch_spr = make_branch_sprite()

    scroll = 0.0
    elapsed = 0.0
    wind_phase = 0.0
    state = "racing"
    final_position = None
    final_time = None
    awarded = 0

    while True:
        dt = clock.tick(FPS) / 1000.0
        if dt > 1 / 20:
            dt = 1 / 20

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_SPACE and state == "racing":
                    player.drink()
                if event.key == pygame.K_RETURN and state == "finished":
                    return

        keys = pygame.key.get_pressed()

        if state == "racing":
            elapsed += dt
            wind_phase += dt * 1.3
            player.update(dt, keys, route, wind_phase)
            for o in opponents:
                o.update(dt)
            next_obs_distance = spawn_obstacles_ahead(player, obstacles, spawn_density, next_obs_distance)
            check_collisions(player, obstacles)
            obstacles[:] = [o for o in obstacles if o.distance > player.distance - 8]
            scroll += player.speed * PX_PER_M / 3.6 * dt
            if player.distance >= distance_target:
                state = "finished"
                final_position = player_position(player, opponents)
                final_time = elapsed
                total = len(opponents) + 1
                placement_score = max(0, (total - final_position + 1) * 22)
                diff_bonus = route["difficulty"] * 18
                awarded = placement_score + diff_bonus
                save_data["points"] = save_data.get("points", 0) + awarded
                save_data["races"] = save_data.get("races", 0) + 1
                best = save_data.setdefault("best", {})
                rid = route["id"]
                if rid not in best or final_position < best[rid]:
                    best[rid] = final_position
                save_state(save_data)

        draw_road(screen, scroll)
        for o in sorted(opponents, key=lambda x: x.distance):
            y = PLAYER_Y - (o.distance - player.distance) * PX_PER_M
            if -60 < y < H + 60:
                screen.blit(o.sprite, (o.x - PLAYER_W // 2, y - PLAYER_H // 2))
        for o in obstacles:
            draw_obstacle(screen, o, player, pothole_spr, branch_spr)
        draw_finish_line(screen, player, distance_target)
        draw_player(screen, player, player_sprite)

        pos = player_position(player, opponents)
        remaining = max(0, distance_target - player.distance)
        draw_hud(screen, player, pos, len(opponents) + 1, remaining, fonts, route)

        if state == "finished":
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 190))
            screen.blit(overlay, (0, 0))
            total = len(opponents) + 1
            title = fonts["huge"].render(f"Platz {final_position} / {total}", True, WHITE)
            screen.blit(title, (W // 2 - title.get_width() // 2, 160))
            mins = int(final_time // 60)
            secs = int(final_time % 60)
            time_s = fonts["mid"].render(f"Zeit: {mins}:{secs:02d}", True, WHITE)
            screen.blit(time_s, (W // 2 - time_s.get_width() // 2, 240))
            pts = fonts["mid"].render(f"+{awarded} Punkte", True, YELLOW)
            screen.blit(pts, (W // 2 - pts.get_width() // 2, 280))
            hint = fonts["small"].render("Enter: zurück zum Menü", True, HUD_DIM)
            screen.blit(hint, (W // 2 - hint.get_width() // 2, 360))

        pygame.display.flip()


def main():
    pygame.init()
    pygame.display.set_caption("Radgame")
    screen = pygame.display.set_mode((W, H))
    fonts = {
        "huge": pygame.font.Font(None, 64),
        "big": pygame.font.Font(None, 48),
        "mid": pygame.font.Font(None, 28),
        "small": pygame.font.Font(None, 20),
    }
    while True:
        save_data = load_save()
        route = run_menu(screen, save_data, fonts)
        if route is None:
            break
        run_race(screen, route, save_data, fonts)
    pygame.quit()


if __name__ == "__main__":
    main()
