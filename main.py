import json
import math
import random
import sys
from pathlib import Path

import pygame

from routes import ROUTES

W, H = 900, 640
FPS = 60
ROAD_WIDTH = 220
PLAYER_Y = 460
PLAYER_W, PLAYER_H = 26, 48
PX_PER_M = 25
MIN_SPEED = 8
MAX_SPEED_BASE = 64
EMPTY_ENERGY_SPEED = 20
BASE_MAX_ENERGY = 100
DRINK_AMOUNT = 32
WATER_BOTTLES_BASE = 3
STEER_SPEED = 240

GRASS = (60, 110, 60)
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
PINK = (235, 120, 180)
CYAN = (80, 220, 220)

SAVE_FILE = Path(__file__).parent / "save.json"

SHOP_ITEMS = [
    {"id": "jersey_red",    "type": "jersey", "name": "Klassik Rot",       "color": (220, 50, 50),   "cost": 0,   "default": True},
    {"id": "jersey_blue",   "type": "jersey", "name": "Sky Blau",          "color": (60, 130, 220),  "cost": 60},
    {"id": "jersey_polka",  "type": "jersey", "name": "Bergtrikot Polka",  "color": (240, 240, 240), "secondary": (220, 60, 60), "cost": 180},
    {"id": "jersey_yellow", "type": "jersey", "name": "Maillot Jaune",     "color": (240, 210, 60),  "cost": 320},
    {"id": "jersey_pink",   "type": "jersey", "name": "Maglia Rosa",       "color": (235, 120, 180), "cost": 380},
    {"id": "jersey_rainbow","type": "jersey", "name": "Regenbogentrikot",  "color": (240, 240, 240), "secondary": (90, 150, 230), "cost": 700},

    {"id": "helmet_std",    "type": "helmet", "name": "Standard Helm",     "color": (40, 90, 200),   "cost": 0,   "default": True},
    {"id": "helmet_aero",   "type": "helmet", "name": "Aero-Helm",         "color": (180, 30, 30),   "stat": {"wind_resist": 0.3}, "cost": 220},
    {"id": "helmet_tt",     "type": "helmet", "name": "Zeitfahr-Helm",     "color": (235, 180, 30),  "stat": {"wind_resist": 0.5, "max_speed_bonus": 2}, "cost": 550},

    {"id": "wheels_std",    "type": "wheels", "name": "Standard Räder",    "cost": 0,   "default": True},
    {"id": "wheels_carbon", "type": "wheels", "name": "Carbon Räder",      "stat": {"drain_mult": 0.88, "accel_mult": 1.1},  "cost": 380},
    {"id": "wheels_aero",   "type": "wheels", "name": "Aero Räder",        "stat": {"drain_mult": 0.92, "max_speed_bonus": 4}, "cost": 540},

    {"id": "frame_std",     "type": "frame",  "name": "Aluminium Rahmen",  "cost": 0,   "default": True},
    {"id": "frame_carbon",  "type": "frame",  "name": "Carbon Rahmen",     "stat": {"drain_mult": 0.92, "max_speed_bonus": 3}, "cost": 500},
    {"id": "frame_climber", "type": "frame",  "name": "Climber Rahmen",    "stat": {"accel_mult": 1.25, "drain_mult": 0.9},   "cost": 750},
    {"id": "frame_aero",    "type": "frame",  "name": "Aero Rahmen",       "stat": {"max_speed_bonus": 7, "wind_resist": 0.2}, "cost": 950},

    {"id": "bottles_std",   "type": "bottles","name": "2 Trinkflaschen",   "stat": {"bottles": 3}, "cost": 0,   "default": True},
    {"id": "bottles_extra", "type": "bottles","name": "3 Trinkflaschen",   "stat": {"bottles": 4}, "cost": 260},
    {"id": "bottles_pro",   "type": "bottles","name": "Hydration Pack",    "stat": {"bottles": 5}, "cost": 520},
]

ITEM_TYPES = ["jersey", "helmet", "wheels", "frame", "bottles"]
ITEM_TYPE_LABELS = {
    "jersey":  "Trikot",
    "helmet":  "Helm",
    "wheels":  "Räder",
    "frame":   "Rahmen",
    "bottles": "Flaschen",
}


def find_item(item_id):
    return next((x for x in SHOP_ITEMS if x["id"] == item_id), None)


def items_of_type(t):
    return [x for x in SHOP_ITEMS if x["type"] == t]


def default_item_id(t):
    for x in SHOP_ITEMS:
        if x["type"] == t and x.get("default"):
            return x["id"]
    return items_of_type(t)[0]["id"]


def default_equipped():
    return {t: default_item_id(t) for t in ITEM_TYPES}


def default_owned():
    return [x["id"] for x in SHOP_ITEMS if x.get("default")]


def load_save():
    data = {}
    if SAVE_FILE.exists():
        try:
            data = json.loads(SAVE_FILE.read_text())
        except Exception:
            data = {}
    data.setdefault("points", 0)
    data.setdefault("races", 0)
    data.setdefault("best", {})
    data.setdefault("owned", default_owned())
    data.setdefault("equipped", default_equipped())
    for t in ITEM_TYPES:
        if t not in data["equipped"] or data["equipped"][t] is None:
            data["equipped"][t] = default_item_id(t)
        if data["equipped"][t] not in data["owned"]:
            data["owned"].append(data["equipped"][t])
    for d_id in default_owned():
        if d_id not in data["owned"]:
            data["owned"].append(d_id)
    return data


def save_state(state):
    SAVE_FILE.write_text(json.dumps(state, indent=2))


def level_from_points(points):
    lvl = 1
    threshold = 200
    p = points
    while p >= threshold:
        p -= threshold
        lvl += 1
        threshold += 100
    return lvl, p, threshold


def max_energy_for_level(level):
    return BASE_MAX_ENERGY + (level - 1) * 8


def compute_stats(save_data):
    s = {
        "drain_mult": 1.0,
        "accel_mult": 1.0,
        "max_speed_bonus": 0,
        "wind_resist": 0.0,
        "bottles": WATER_BOTTLES_BASE,
        "jersey_color": (220, 60, 60),
        "jersey_secondary": None,
        "helmet_color": (40, 90, 200),
    }
    eq = save_data.get("equipped", {})
    for _slot, iid in eq.items():
        item = find_item(iid)
        if not item:
            continue
        if item["type"] == "jersey":
            s["jersey_color"] = item.get("color", s["jersey_color"])
            s["jersey_secondary"] = item.get("secondary")
        elif item["type"] == "helmet":
            s["helmet_color"] = item.get("color", s["helmet_color"])
        for k, v in item.get("stat", {}).items():
            if k == "bottles":
                s[k] = v
            elif k in ("drain_mult", "accel_mult"):
                s[k] *= v
            elif k in ("max_speed_bonus", "wind_resist"):
                s[k] += v
    return s


def road_curve(distance):
    """World x offset (pixels) of road centerline at given world distance (meters)."""
    return (math.sin(distance * 0.032) * 130
            + math.sin(distance * 0.010) * 70
            + math.sin(distance * 0.080) * 34)


def make_cyclist_sprite(jersey, helmet, secondary=None, w=PLAYER_W, h=PLAYER_H):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = w // 2
    pygame.draw.rect(s, BLACK, (cx - 1, 0, 3, 7))
    pygame.draw.rect(s, (60, 60, 70), (cx - 7, 7, 14, 2))
    pygame.draw.rect(s, jersey, (cx - 5, 9, 10, 3))
    pygame.draw.rect(s, jersey, (cx - 8, 12, 16, 4))
    pygame.draw.ellipse(s, helmet, (cx - 5, 16, 10, 8))
    pygame.draw.rect(s, jersey, (cx - 7, 22, 14, 13))
    if secondary:
        for py in range(23, 34, 3):
            pygame.draw.rect(s, secondary, (cx - 6 + (py % 4), py, 3, 2))
    pygame.draw.rect(s, (35, 35, 42), (cx - 2, 35, 4, 4))
    pygame.draw.rect(s, BLACK, (cx - 1, 39, 3, 9))
    return s


def make_pothole_sprite(w=32, h=14):
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


def make_goodie_sprite(kind):
    s = pygame.Surface((22, 24), pygame.SRCALPHA)
    if kind == "bottle":
        pygame.draw.rect(s, BLUE, (5, 5, 12, 16), border_radius=3)
        pygame.draw.rect(s, (50, 100, 200), (5, 5, 12, 4))
        pygame.draw.rect(s, WHITE, (7, 11, 8, 2))
    elif kind == "gel":
        pygame.draw.rect(s, ORANGE, (4, 6, 14, 14), border_radius=4)
        pygame.draw.rect(s, YELLOW, (6, 9, 10, 2))
        pygame.draw.rect(s, YELLOW, (6, 13, 10, 2))
    elif kind == "bar":
        pygame.draw.rect(s, BROWN, (3, 7, 16, 10), border_radius=2)
        pygame.draw.rect(s, (240, 200, 100), (5, 9, 12, 2))
        pygame.draw.rect(s, (240, 200, 100), (5, 13, 12, 2))
    return s


class Player:
    def __init__(self, save_data):
        self.stats = compute_stats(save_data)
        lvl, _, _ = level_from_points(save_data.get("points", 0))
        self.level = lvl
        self.max_energy = max_energy_for_level(lvl)
        self.max_bottles = self.stats["bottles"]
        self.max_speed = MAX_SPEED_BASE + self.stats["max_speed_bonus"]
        self.distance = 0.0
        self.world_x = road_curve(0.0)
        self.speed = 26.0
        self.target_speed = 26.0
        self.energy = self.max_energy
        self.water = self.max_bottles
        self.crashed_timer = 0.0
        self.flash_timer = 0.0
        self.on_grass = False

    def drink(self):
        if self.water > 0 and self.energy < self.max_energy:
            self.water -= 1
            self.energy = min(self.max_energy, self.energy + DRINK_AMOUNT)
            return True
        return False

    def pick_up(self, kind):
        if kind == "bottle":
            if self.water < self.max_bottles:
                self.water += 1
                return True
            return False
        if kind == "gel":
            if self.energy < self.max_energy:
                self.energy = min(self.max_energy, self.energy + 30)
                return True
            return False
        if kind == "bar":
            self.energy = min(self.max_energy, self.energy + 15)
            self.target_speed = min(self.max_speed, self.target_speed + 3)
            return True
        return False

    def update(self, dt, keys, route, wind_phase):
        accel = keys[pygame.K_UP] or keys[pygame.K_w]
        brake = keys[pygame.K_DOWN] or keys[pygame.K_s]
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]

        if self.crashed_timer > 0:
            self.crashed_timer -= dt
            self.target_speed = max(MIN_SPEED, self.target_speed - 26 * dt)
        elif accel and self.energy > 0:
            self.target_speed = min(self.max_speed,
                                    self.target_speed + 14 * dt * self.stats["accel_mult"])
        elif brake:
            self.target_speed = max(MIN_SPEED, self.target_speed - 16 * dt)
        else:
            self.target_speed += (28 - self.target_speed) * 0.4 * dt

        if self.energy <= 0:
            self.target_speed = min(self.target_speed, EMPTY_ENERGY_SPEED)
        if self.on_grass:
            self.target_speed = min(self.target_speed, 24)
            self.target_speed *= 1 - 0.6 * dt

        self.speed += (self.target_speed - self.speed) * 2.8 * dt
        self.speed = max(MIN_SPEED, min(self.max_speed, self.speed))
        self.distance += self.speed / 3.6 * dt

        steer = STEER_SPEED * dt
        if left:
            self.world_x -= steer
        if right:
            self.world_x += steer

        wind_factor = max(0.0, 1.0 - self.stats["wind_resist"])
        wind = route.get("wind", 0) * wind_factor
        if wind > 0:
            gust = math.sin(wind_phase) * wind
            self.world_x += gust * 55 * dt

        road_c = road_curve(self.distance)
        max_drift = ROAD_WIDTH * 1.3
        if self.world_x < road_c - max_drift:
            self.world_x = road_c - max_drift
        elif self.world_x > road_c + max_drift:
            self.world_x = road_c + max_drift
        off = self.world_x - road_c
        self.on_grass = abs(off) > ROAD_WIDTH // 2 - PLAYER_W // 2

        base_drain = 0.30
        over = max(0.0, (self.speed - 26) / 20)
        drain = base_drain + over ** 2 * 3.0
        drain *= 1.0 + route.get("heat", 0) * 0.6
        drain *= self.stats["drain_mult"]
        self.energy = max(0.0, self.energy - drain * dt)

        if not accel and not self.on_grass:
            regen_rate = 1.6 * max(0.1, (1 - self.speed / 50))
            self.energy = min(self.max_energy, self.energy + regen_rate * dt)

        if self.flash_timer > 0:
            self.flash_timer -= dt


class Opponent:
    def __init__(self, start_distance, base_speed):
        self.distance = start_distance
        self.target_speed = base_speed
        self.speed = base_speed
        self.lane_pref = random.uniform(-ROAD_WIDTH // 2 + 22, ROAD_WIDTH // 2 - 22)
        self.world_x = road_curve(start_distance) + self.lane_pref
        self.jersey = (random.randint(40, 230), random.randint(40, 230), random.randint(40, 230))
        self.helmet = (random.randint(30, 220), random.randint(30, 220), random.randint(30, 220))
        self.sprite = make_cyclist_sprite(self.jersey, self.helmet)
        self.wobble_phase = random.uniform(0, math.tau)

    def update(self, dt):
        self.target_speed += random.gauss(0, 1.4) * dt
        self.target_speed = max(20, min(56, self.target_speed))
        self.speed += (self.target_speed - self.speed) * 1.2 * dt
        self.distance += self.speed / 3.6 * dt
        target = road_curve(self.distance) + self.lane_pref
        self.world_x += (target - self.world_x) * 2.2 * dt
        self.wobble_phase += dt * 2
        self.world_x += math.sin(self.wobble_phase) * 9 * dt


class Obstacle:
    def __init__(self, distance, world_x, kind):
        self.distance = distance
        self.world_x = world_x
        self.kind = kind
        self.hit = False


class Goodie:
    def __init__(self, distance, world_x, kind):
        self.distance = distance
        self.world_x = world_x
        self.kind = kind
        self.collected = False


def player_position(player, opponents):
    ahead = sum(1 for o in opponents if o.distance > player.distance)
    return ahead + 1


def spawn_obstacles_ahead(player, obstacles, density, next_distance):
    horizon = player.distance + 240
    while next_distance < horizon:
        rc = road_curve(next_distance)
        x = rc + random.uniform(-ROAD_WIDTH // 2 + 18, ROAD_WIDTH // 2 - 18)
        kind = random.choice(["pothole", "branch", "branch", "pothole"])
        obstacles.append(Obstacle(next_distance, x, kind))
        gap = random.uniform(14, 32) / max(density, 0.15)
        next_distance += gap
    return next_distance


def spawn_goodies_ahead(player, goodies, next_distance):
    horizon = player.distance + 240
    while next_distance < horizon:
        rc = road_curve(next_distance)
        x = rc + random.uniform(-ROAD_WIDTH // 2 + 16, ROAD_WIDTH // 2 - 16)
        kind = random.choices(["bottle", "gel", "bar"], weights=[2, 2, 3])[0]
        goodies.append(Goodie(next_distance, x, kind))
        gap = random.uniform(55, 130)
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
            if abs(o.world_x - player.world_x) < half_w + reach - 6:
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


def check_goodies(player, goodies):
    half_w = PLAYER_W // 2
    picked = []
    for g in goodies:
        if g.collected:
            continue
        dd = g.distance - player.distance
        if -0.4 < dd < 0.9:
            if abs(g.world_x - player.world_x) < half_w + 12:
                if player.pick_up(g.kind):
                    g.collected = True
                    picked.append(g.kind)
    return picked


def draw_road(screen, player):
    screen.fill(GRASS)
    step = 6
    left_pts = []
    right_pts = []
    for y in range(-step, H + step, step):
        dist_y = player.distance + (PLAYER_Y - y) / PX_PER_M
        rc = road_curve(dist_y)
        cx = W // 2 + (rc - player.world_x)
        left_pts.append((cx - ROAD_WIDTH // 2, y))
        right_pts.append((cx + ROAD_WIDTH // 2, y))
    poly = left_pts + list(reversed(right_pts))
    pygame.draw.polygon(screen, ROAD, poly)
    if len(left_pts) >= 2:
        pygame.draw.lines(screen, ROAD_EDGE, False, left_pts, 3)
        pygame.draw.lines(screen, ROAD_EDGE, False, right_pts, 3)

    spacing_m = 3.0
    dash_len_m = 1.4
    bottom_dist = player.distance + (PLAYER_Y - H - 20) / PX_PER_M
    top_dist = player.distance + (PLAYER_Y + 30) / PX_PER_M
    first_idx = int(math.floor(bottom_dist / spacing_m))
    last_idx = int(math.ceil(top_dist / spacing_m))
    for i in range(first_idx, last_idx + 1):
        d_start = i * spacing_m
        d_mid = d_start + dash_len_m / 2
        y_top = PLAYER_Y - (d_start + dash_len_m - player.distance) * PX_PER_M
        cx = W // 2 + (road_curve(d_mid) - player.world_x)
        pygame.draw.rect(screen, LANE_LINE, (cx - 3, y_top, 6, max(2, int(dash_len_m * PX_PER_M))))


def draw_finish_line(screen, player, distance_target):
    rem = distance_target - player.distance
    if rem > 30:
        return
    y = PLAYER_Y - rem * PX_PER_M
    rc = road_curve(distance_target)
    cx = W // 2 + (rc - player.world_x)
    left = cx - ROAD_WIDTH // 2
    for col in range(8):
        x = left + col * (ROAD_WIDTH / 8)
        color = WHITE if (col % 2 == 0) else BLACK
        pygame.draw.rect(screen, color, (x, y - 8, ROAD_WIDTH / 8 + 1, 8))
        color2 = BLACK if (col % 2 == 0) else WHITE
        pygame.draw.rect(screen, color2, (x, y, ROAD_WIDTH / 8 + 1, 8))


def draw_world_obj(screen, distance, world_x, sprite, player, y_jitter=0):
    y = PLAYER_Y - (distance - player.distance) * PX_PER_M + y_jitter
    if y < -40 or y > H + 40:
        return
    x = W // 2 + (world_x - player.world_x)
    screen.blit(sprite, (x - sprite.get_width() // 2, y - sprite.get_height() // 2))


def draw_player(screen, player, sprite):
    x = int(W // 2 - PLAYER_W // 2)
    y = int(PLAYER_Y - PLAYER_H // 2)
    if player.flash_timer > 0 and int(player.flash_timer * 20) % 2 == 0:
        flash = sprite.copy()
        flash.fill((255, 100, 100, 0), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(flash, (x, y))
    else:
        screen.blit(sprite, (x, y))


def draw_hud(screen, player, position, total, distance_remaining, fonts, route, recent_pickup):
    h = 116
    pygame.draw.rect(screen, HUD_BG, (0, H - h, W, h))
    pygame.draw.rect(screen, (40, 50, 70), (0, H - h, W, 2))

    speed_int = int(round(player.speed))
    speed_text = fonts["big"].render(f"{speed_int}", True, WHITE)
    screen.blit(speed_text, (20, H - h + 18))
    unit = fonts["small"].render("km/h", True, HUD_DIM)
    screen.blit(unit, (20 + speed_text.get_width() + 6, H - h + 42))

    bar_x, bar_y, bar_w, bar_h_ = 20, H - 30, 240, 14
    pygame.draw.rect(screen, (30, 35, 48), (bar_x, bar_y, bar_w, bar_h_), border_radius=4)
    pct = player.energy / player.max_energy
    color = GREEN if pct > 0.5 else (YELLOW if pct > 0.2 else RED)
    pygame.draw.rect(screen, color, (bar_x, bar_y, int(bar_w * pct), bar_h_), border_radius=4)
    label = fonts["small"].render(f"Energie {int(player.energy)}/{player.max_energy}", True, HUD_TEXT)
    screen.blit(label, (bar_x, bar_y - 18))

    bx = 300
    for i in range(player.max_bottles):
        c = BLUE if i < player.water else (50, 60, 80)
        pygame.draw.rect(screen, c, (bx + i * 22, H - 30, 18, 14), border_radius=3)
    screen.blit(fonts["small"].render("Wasser (Leertaste)", True, HUD_TEXT), (bx, H - 48))

    pos_text = fonts["mid"].render(f"Platz {position}/{total}", True, WHITE)
    screen.blit(pos_text, (W - pos_text.get_width() - 20, H - h + 16))
    d_text = fonts["small"].render(f"{int(distance_remaining)} m bis Ziel", True, HUD_DIM)
    screen.blit(d_text, (W - d_text.get_width() - 20, H - h + 50))
    lvl_text = fonts["small"].render(f"Lvl {player.level}", True, YELLOW)
    screen.blit(lvl_text, (W - lvl_text.get_width() - 20, H - h + 74))

    cond_x = W // 2 - 80
    if route.get("wind", 0) > 0.4:
        screen.blit(fonts["small"].render("Wind", True, HUD_DIM), (cond_x, H - h + 18))
    if route.get("heat", 0) > 0.5:
        screen.blit(fonts["small"].render("Hitze", True, HUD_DIM), (cond_x, H - h + 40))
    if player.on_grass:
        screen.blit(fonts["small"].render("WIESE!", True, ORANGE), (cond_x, H - h + 62))

    if recent_pickup:
        kind, t = recent_pickup
        if t > 0:
            text_map = {
                "bottle": "+1 Flasche",
                "gel":    "+30 Energie",
                "bar":    "+15 Energie / +Speed",
            }
            txt = text_map.get(kind, "+")
            surf = fonts["mid"].render(txt, True, YELLOW)
            alpha = max(60, min(255, int(t * 200)))
            surf.set_alpha(alpha)
            screen.blit(surf, (W // 2 - surf.get_width() // 2, H - h - 36))


def run_menu(screen, save_data, fonts):
    clock = pygame.time.Clock()
    cursor = 0
    visible = 6
    row_h = 56
    options_count = len(ROUTES) + 1  # shop is index 0
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    cursor = (cursor - 1) % options_count
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    cursor = (cursor + 1) % options_count
                if event.key == pygame.K_PAGEUP:
                    cursor = max(0, cursor - visible)
                if event.key == pygame.K_PAGEDOWN:
                    cursor = min(options_count - 1, cursor + visible)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if cursor == 0:
                        return ("shop", None)
                    return ("race", ROUTES[cursor - 1])
                if event.key == pygame.K_ESCAPE:
                    return None

        screen.fill((22, 26, 40))
        title = fonts["huge"].render("RADGAME", True, WHITE)
        screen.blit(title, (W // 2 - title.get_width() // 2, 20))
        level, xp, need = level_from_points(save_data.get("points", 0))
        sub = fonts["small"].render(
            f"Level {level} · {xp}/{need} XP · max. Energie {max_energy_for_level(level)}",
            True, HUD_DIM,
        )
        screen.blit(sub, (W // 2 - sub.get_width() // 2, 76))

        pts = fonts["mid"].render(f"{save_data.get('points', 0)} Punkte", True, YELLOW)
        screen.blit(pts, (W - pts.get_width() - 30, 24))
        races = fonts["small"].render(f"Rennen: {save_data.get('races', 0)}", True, HUD_DIM)
        screen.blit(races, (W - races.get_width() - 30, 56))

        bar_w = 240
        bar_x = W // 2 - bar_w // 2
        bar_y = 102
        pygame.draw.rect(screen, (30, 35, 48), (bar_x, bar_y, bar_w, 6), border_radius=3)
        pct = xp / need if need > 0 else 0
        pygame.draw.rect(screen, YELLOW, (bar_x, bar_y, int(bar_w * pct), 6), border_radius=3)

        scroll_start = max(0, min(options_count - visible, cursor - visible // 2))
        list_x = 70
        list_w = W - 140
        list_y0 = 130
        for slot in range(min(visible, options_count)):
            i = scroll_start + slot
            if i >= options_count:
                break
            y = list_y0 + slot * row_h
            sel = (i == cursor)
            if i == 0:
                bg = (60, 50, 30) if sel else (40, 35, 25)
                pygame.draw.rect(screen, bg, (list_x, y, list_w, row_h - 6), border_radius=10)
                if sel:
                    pygame.draw.rect(screen, YELLOW, (list_x, y, list_w, row_h - 6), 2, border_radius=10)
                name = fonts["mid"].render("SHOP — Upgrades & Trikots", True, YELLOW)
                screen.blit(name, (list_x + 18, y + 8))
                desc = fonts["small"].render("Punkte ausgeben, Rad aufmotzen", True, HUD_DIM)
                screen.blit(desc, (list_x + 18, y + 32))
            else:
                r = ROUTES[i - 1]
                bg = (40, 52, 80) if sel else (28, 32, 48)
                pygame.draw.rect(screen, bg, (list_x, y, list_w, row_h - 6), border_radius=10)
                if sel:
                    pygame.draw.rect(screen, BLUE, (list_x, y, list_w, row_h - 6), 2, border_radius=10)
                name = fonts["mid"].render(r["name"], True, WHITE)
                screen.blit(name, (list_x + 18, y + 6))
                stars = "★" * r["difficulty"] + "☆" * (5 - r["difficulty"])
                meta = fonts["small"].render(
                    f"{r['race']} · {r['region']} · {r['distance_m']} m · {stars}",
                    True, HUD_DIM,
                )
                screen.blit(meta, (list_x + 18, y + 30))
                best = save_data.get("best", {}).get(r["id"])
                if best:
                    b = fonts["small"].render(f"Best: P{best}", True, YELLOW)
                    screen.blit(b, (list_x + list_w - b.get_width() - 18, y + 14))

        if scroll_start > 0:
            screen.blit(fonts["small"].render("▲", True, HUD_DIM), (W // 2 - 6, list_y0 - 14))
        if scroll_start + visible < options_count:
            screen.blit(fonts["small"].render("▼", True, HUD_DIM),
                        (W // 2 - 6, list_y0 + visible * row_h - 4))

        hint = fonts["small"].render(
            "↑/↓ wählen · PgUp/PgDn springen · Enter starten · Esc beenden",
            True, HUD_DIM,
        )
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 26))

        pygame.display.flip()


def run_shop(screen, save_data, fonts):
    clock = pygame.time.Clock()
    items_list = []
    for t in ITEM_TYPES:
        items_list.append(("header", t))
        for it in items_of_type(t):
            items_list.append(("item", it))
    selectable = [i for i, x in enumerate(items_list) if x[0] == "item"]
    cur = 0
    msg = ""
    msg_t = 0.0

    while True:
        dt = clock.tick(FPS) / 1000.0
        msg_t = max(0.0, msg_t - dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key in (pygame.K_UP, pygame.K_w):
                    cur = (cur - 1) % len(selectable)
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    cur = (cur + 1) % len(selectable)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    item = items_list[selectable[cur]][1]
                    if item["id"] in save_data["owned"]:
                        if save_data["equipped"][item["type"]] != item["id"]:
                            save_data["equipped"][item["type"]] = item["id"]
                            save_state(save_data)
                            msg = f"Angelegt: {item['name']}"
                            msg_t = 1.6
                    else:
                        if save_data["points"] >= item["cost"]:
                            save_data["points"] -= item["cost"]
                            save_data["owned"].append(item["id"])
                            save_data["equipped"][item["type"]] = item["id"]
                            save_state(save_data)
                            msg = f"Gekauft & angelegt: {item['name']}"
                            msg_t = 2.0
                        else:
                            msg = f"Zu wenig Punkte für {item['name']}"
                            msg_t = 1.5

        screen.fill((20, 24, 36))
        title = fonts["huge"].render("SHOP", True, YELLOW)
        screen.blit(title, (40, 20))
        pts = fonts["mid"].render(f"{save_data['points']} Punkte", True, WHITE)
        screen.blit(pts, (W - pts.get_width() - 40, 30))
        level, _, _ = level_from_points(save_data["points"])
        lvl = fonts["small"].render(
            f"Level {level} · max Energie {max_energy_for_level(level)}",
            True, HUD_DIM,
        )
        screen.blit(lvl, (W - lvl.get_width() - 40, 62))

        list_y0 = 100
        row_h = 30
        visible_rows = 16
        cursor_row = selectable[cur]
        scroll_start = max(0, min(len(items_list) - visible_rows, cursor_row - visible_rows // 2))
        for slot in range(min(visible_rows, len(items_list))):
            i = scroll_start + slot
            if i >= len(items_list):
                break
            kind, data = items_list[i]
            y = list_y0 + slot * row_h
            if kind == "header":
                lbl = ITEM_TYPE_LABELS.get(data, data).upper()
                t = fonts["mid"].render(lbl, True, CYAN)
                screen.blit(t, (60, y))
            else:
                item = data
                owned = item["id"] in save_data["owned"]
                equipped = save_data["equipped"].get(item["type"]) == item["id"]
                sel = (i == cursor_row)
                if sel:
                    pygame.draw.rect(screen, (40, 50, 75), (80, y - 2, W - 160, row_h - 2), border_radius=6)
                    pygame.draw.rect(screen, BLUE, (80, y - 2, W - 160, row_h - 2), 2, border_radius=6)
                name_c = WHITE if owned else HUD_TEXT
                if equipped:
                    name_c = GREEN
                if item.get("color") and item["type"] in ("jersey", "helmet"):
                    pygame.draw.rect(screen, item["color"], (90, y + 4, 16, 16), border_radius=3)
                    if item.get("secondary"):
                        pygame.draw.rect(screen, item["secondary"], (98, y + 6, 6, 12), border_radius=2)
                name = fonts["small"].render(item["name"], True, name_c)
                screen.blit(name, (114, y + 6))
                ss = []
                for k, v in item.get("stat", {}).items():
                    if k == "drain_mult":
                        ss.append(f"Verbrauch ×{v}")
                    elif k == "accel_mult":
                        ss.append(f"Beschl. ×{v}")
                    elif k == "max_speed_bonus":
                        ss.append(f"+{v} km/h")
                    elif k == "wind_resist":
                        ss.append(f"Wind -{int(v*100)}%")
                    elif k == "bottles":
                        ss.append(f"{v} Flaschen")
                if ss:
                    s_text = fonts["small"].render(" · ".join(ss), True, HUD_DIM)
                    screen.blit(s_text, (360, y + 6))
                if equipped:
                    r = fonts["small"].render("Angelegt", True, GREEN)
                elif owned:
                    r = fonts["small"].render("Im Besitz · Enter anlegen", True, YELLOW)
                else:
                    can = save_data["points"] >= item["cost"]
                    color = YELLOW if can else (140, 80, 80)
                    r = fonts["small"].render(
                        f"{item['cost']} pt · Enter kaufen" if can else f"{item['cost']} pt · zu teuer",
                        True, color,
                    )
                screen.blit(r, (W - r.get_width() - 100, y + 6))

        if scroll_start > 0:
            screen.blit(fonts["small"].render("▲", True, HUD_DIM), (W // 2 - 6, list_y0 - 14))
        if scroll_start + visible_rows < len(items_list):
            screen.blit(fonts["small"].render("▼", True, HUD_DIM),
                        (W // 2 - 6, list_y0 + visible_rows * row_h - 2))

        if msg_t > 0:
            t = fonts["mid"].render(msg, True, WHITE)
            screen.blit(t, (W // 2 - t.get_width() // 2, H - 60))

        hint = fonts["small"].render(
            "↑/↓ wählen · Enter kaufen/anlegen · Esc zurück",
            True, HUD_DIM,
        )
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 26))

        pygame.display.flip()


def run_race(screen, route, save_data, fonts):
    clock = pygame.time.Clock()
    player = Player(save_data)
    opp_count = max(10, route.get("opponents", 10))
    base = 38 - route["difficulty"] * 1.0
    opponents = [Opponent(random.uniform(15, 90), base + random.uniform(-4, 8))
                 for _ in range(opp_count)]
    obstacles = []
    goodies = []
    next_obs_d = 50.0
    next_goodie_d = 60.0
    spawn_density = route["obstacle_density"]
    distance_target = route["distance_m"]

    player_sprite = make_cyclist_sprite(
        player.stats["jersey_color"],
        player.stats["helmet_color"],
        player.stats["jersey_secondary"],
    )
    pothole_spr = make_pothole_sprite()
    branch_spr = make_branch_sprite()
    goodie_sprites = {k: make_goodie_sprite(k) for k in ("bottle", "gel", "bar")}

    elapsed = 0.0
    wind_phase = 0.0
    state = "racing"
    final_position = None
    final_time = None
    awarded = 0
    recent_pickup = None
    recent_pickup_t = 0.0
    level_up = False
    prev_level = player.level

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
            next_obs_d = spawn_obstacles_ahead(player, obstacles, spawn_density, next_obs_d)
            next_goodie_d = spawn_goodies_ahead(player, goodies, next_goodie_d)
            check_collisions(player, obstacles)
            picked = check_goodies(player, goodies)
            if picked:
                recent_pickup = picked[-1]
                recent_pickup_t = 1.5
            obstacles[:] = [o for o in obstacles if o.distance > player.distance - 8]
            goodies[:] = [g for g in goodies
                          if not g.collected and g.distance > player.distance - 8]
            if player.distance >= distance_target:
                state = "finished"
                final_position = player_position(player, opponents)
                final_time = elapsed
                total = len(opponents) + 1
                placement = max(0, (total - final_position + 1) * 18)
                diff_bonus = route["difficulty"] * 22
                awarded = placement + diff_bonus
                save_data["points"] = save_data.get("points", 0) + awarded
                save_data["races"] = save_data.get("races", 0) + 1
                best = save_data.setdefault("best", {})
                rid = route["id"]
                if rid not in best or final_position < best[rid]:
                    best[rid] = final_position
                new_lvl, _, _ = level_from_points(save_data["points"])
                if new_lvl > prev_level:
                    level_up = True
                save_state(save_data)

        recent_pickup_t = max(0.0, recent_pickup_t - dt)

        draw_road(screen, player)
        for o in sorted(opponents, key=lambda x: x.distance):
            draw_world_obj(screen, o.distance, o.world_x, o.sprite, player)
        for o in obstacles:
            draw_world_obj(screen, o.distance, o.world_x,
                           pothole_spr if o.kind == "pothole" else branch_spr, player)
        for g in goodies:
            if not g.collected:
                bob = math.sin(pygame.time.get_ticks() / 200 + g.distance) * 2
                draw_world_obj(screen, g.distance, g.world_x, goodie_sprites[g.kind],
                               player, y_jitter=bob)
        draw_finish_line(screen, player, distance_target)
        draw_player(screen, player, player_sprite)

        pos = player_position(player, opponents)
        remaining = max(0, distance_target - player.distance)
        rp = (recent_pickup, recent_pickup_t) if recent_pickup else None
        draw_hud(screen, player, pos, len(opponents) + 1, remaining, fonts, route, rp)

        if state == "finished":
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 190))
            screen.blit(overlay, (0, 0))
            total = len(opponents) + 1
            title = fonts["huge"].render(f"Platz {final_position} / {total}", True, WHITE)
            screen.blit(title, (W // 2 - title.get_width() // 2, 130))
            mins = int(final_time // 60)
            secs = int(final_time % 60)
            time_s = fonts["mid"].render(f"Zeit: {mins}:{secs:02d}", True, WHITE)
            screen.blit(time_s, (W // 2 - time_s.get_width() // 2, 210))
            pts = fonts["mid"].render(f"+{awarded} Punkte", True, YELLOW)
            screen.blit(pts, (W // 2 - pts.get_width() // 2, 250))
            new_lvl, xp, need = level_from_points(save_data["points"])
            lvl = fonts["small"].render(f"Level {new_lvl} · {xp}/{need} XP", True, HUD_DIM)
            screen.blit(lvl, (W // 2 - lvl.get_width() // 2, 290))
            if level_up:
                lup = fonts["mid"].render(f"LEVEL UP! Max-Energie jetzt {max_energy_for_level(new_lvl)}", True, GREEN)
                screen.blit(lup, (W // 2 - lup.get_width() // 2, 322))
            hint = fonts["small"].render("Enter: zurück zum Menü", True, HUD_DIM)
            screen.blit(hint, (W // 2 - hint.get_width() // 2, 380))

        pygame.display.flip()


def main():
    pygame.init()
    pygame.display.set_caption("Radgame")
    screen = pygame.display.set_mode((W, H))
    fonts = {
        "huge":  pygame.font.Font(None, 64),
        "big":   pygame.font.Font(None, 48),
        "mid":   pygame.font.Font(None, 28),
        "small": pygame.font.Font(None, 20),
    }
    while True:
        save_data = load_save()
        choice = run_menu(screen, save_data, fonts)
        if choice is None:
            break
        kind, payload = choice
        if kind == "shop":
            run_shop(screen, save_data, fonts)
        elif kind == "race":
            run_race(screen, payload, save_data, fonts)
    pygame.quit()


if __name__ == "__main__":
    main()
