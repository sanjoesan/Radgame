import asyncio
import json
import math
import random
import sys
from pathlib import Path

import pygame

from routes import ROUTES

IS_WEB = sys.platform == "emscripten"

# Wird bei JEDEM Push hochgezaehlt — siehe CLAUDE.md (Versionsnummer-Konvention).
# Damit man im Browser sieht, ob noch eine alte Version aus dem Cache laeuft.
VERSION = "v2"


def _detect_touch():
    """True nur auf echten Touch-Geräten (Smartphone/Tablet im Browser).
    Steuerkreuz/Trink-Button blenden wir am Desktop-Browser aus, weil sie
    sonst nur Platz wegnehmen und keinen Nutzen haben."""
    if not IS_WEB:
        return False
    try:
        from js import navigator  # type: ignore
        try:
            if int(navigator.maxTouchPoints) > 0:
                return True
        except Exception:
            pass
        try:
            ua = str(navigator.userAgent).lower()
            return any(kw in ua for kw in ("mobile", "android", "iphone", "ipad", "ipod"))
        except Exception:
            return False
    except Exception:
        return False


IS_TOUCH = _detect_touch()


def _query_viewport():
    """Aktuelle Browser-Viewport-Größe (für mobile Reloads, wenn die URL-Bar
    auf-/zugeht und sich H ändert). Auf Native None."""
    if not IS_WEB:
        return None
    try:
        from js import window  # type: ignore
        return int(window.innerWidth), int(window.innerHeight)
    except Exception:
        return None


def _clamp_size(w, h):
    return max(320, min(w, 1200)), max(480, min(h, 2400))


def _initial_size():
    """Bevorzugt das echte Browser-Viewport, damit es aufm Handy nicht
    quadratisch ausschaut. Auf dem Desktop ein vernünftiges Portrait."""
    if IS_WEB:
        v = _query_viewport()
        if v:
            return _clamp_size(*v)
    return 540, 960


W, H = _initial_size()
FPS = 60
ROAD_WIDTH = max(150, min(220, W // 3))
PLAYER_Y = H // 2
PLAYER_W, PLAYER_H = 26, 48
HUD_H = max(96, min(H // 7, 140))
FONT_SCALE = max(0.7, min(H / 960.0, 1.6))


def _apply_window_size(w, h):
    """Aktualisiert die globalen Layout-Werte. Wird beim Resize gerufen."""
    global W, H, ROAD_WIDTH, PLAYER_Y, HUD_H, FONT_SCALE
    W, H = _clamp_size(w, h)
    ROAD_WIDTH = max(150, min(220, W // 3))
    PLAYER_Y = H // 2
    HUD_H = max(96, min(H // 7, 140))
    FONT_SCALE = max(0.7, min(H / 960.0, 1.6))


def _rebuild_fonts(fonts):
    fonts["huge"]  = pygame.font.Font(None, max(28, int(64 * FONT_SCALE)))
    fonts["big"]   = pygame.font.Font(None, max(22, int(48 * FONT_SCALE)))
    fonts["mid"]   = pygame.font.Font(None, max(16, int(28 * FONT_SCALE)))
    fonts["small"] = pygame.font.Font(None, max(12, int(20 * FONT_SCALE)))


def make_fonts():
    f = {}
    _rebuild_fonts(f)
    return f


def _display_flags():
    return 0 if IS_WEB else pygame.RESIZABLE


def maybe_resize(screen, fonts):
    """Falls sich Browser-Viewport oder Native-Fenster geändert haben:
    set_mode neu, Layout-Globals und Fonts aktualisieren. Touch-Layouts
    bauen die Szenen selbst neu."""
    target = _query_viewport()
    if target is None:
        target = screen.get_size()
    nw, nh = _clamp_size(*target)
    if nw == W and nh == H:
        return screen, False
    _apply_window_size(nw, nh)
    screen = pygame.display.set_mode((W, H), _display_flags())
    _rebuild_fonts(fonts)
    return screen, True
PX_PER_M = 25
MIN_SPEED = 8
MAX_SPEED_BASE = 58
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
WEB_SAVE_KEY = "radgame_save_v1"

DIFFICULTY_ORDER = ["easy", "medium", "hard"]
DIFFICULTY_PRESETS = {
    "easy":   {"label": "Leicht", "opp_speed_mult": 0.92, "drain_mult": 0.82, "obstacle_mult": 0.7},
    "medium": {"label": "Mittel", "opp_speed_mult": 1.00, "drain_mult": 1.00, "obstacle_mult": 1.0},
    "hard":   {"label": "Schwer", "opp_speed_mult": 1.08, "drain_mult": 1.18, "obstacle_mult": 1.3},
}


def difficulty_preset(save_data):
    key = save_data.get("difficulty", "medium")
    return DIFFICULTY_PRESETS.get(key, DIFFICULTY_PRESETS["medium"])


def cycle_difficulty(save_data):
    cur = save_data.get("difficulty", "medium")
    if cur not in DIFFICULTY_ORDER:
        cur = "medium"
    nxt = DIFFICULTY_ORDER[(DIFFICULTY_ORDER.index(cur) + 1) % len(DIFFICULTY_ORDER)]
    save_data["difficulty"] = nxt
    save_state(save_data)
    return nxt


def _web_storage_get():
    try:
        from js import localStorage  # type: ignore
        raw = localStorage.getItem(WEB_SAVE_KEY)
        return None if raw is None else str(raw)
    except Exception:
        return None


def _web_storage_set(payload):
    try:
        from js import localStorage  # type: ignore
        localStorage.setItem(WEB_SAVE_KEY, payload)
    except Exception:
        pass

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
    raw = None
    if IS_WEB:
        raw = _web_storage_get()
    elif SAVE_FILE.exists():
        try:
            raw = SAVE_FILE.read_text()
        except Exception:
            raw = None
    if raw:
        try:
            data = json.loads(raw)
        except Exception:
            data = {}
    data.setdefault("points", 0)
    data.setdefault("races", 0)
    data.setdefault("best", {})
    data.setdefault("difficulty", "medium")
    if data["difficulty"] not in DIFFICULTY_ORDER:
        data["difficulty"] = "medium"
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
    if "xp" not in data:
        spent = 0
        for iid in data["owned"]:
            it = find_item(iid)
            if it:
                spent += it.get("cost", 0)
        data["xp"] = data["points"] + spent
    return data


def save_state(state):
    payload = json.dumps(state, indent=2)
    if IS_WEB:
        _web_storage_set(payload)
    else:
        SAVE_FILE.write_text(payload)


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


THEMES = {
    "coast": {
        "grass":   (110, 160, 90),
        "road":    (75, 75, 85),
        "edge":    (230, 225, 200),
        "decor":   ["palm", "palm", "palm", "palm", "bush", "bush",
                    "beach_hut", "beach_hut", "boat", "oak", "rock_small"],
        "decor_density": 1.6,
        "clutter": ["grass_coast", "grass_coast", "grass_coast", "rock_tiny",
                    "flower_yellow", "flower_white"],
        "clutter_density": 1.2,
        "obstacles": [("pothole", 3), ("branch", 2)],
        "curve_mult": 0.5,
    },
    "classic": {
        "grass":   (60, 110, 60),
        "road":    (72, 72, 82),
        "edge":    (220, 220, 220),
        "decor":   ["oak", "oak", "oak", "pine", "pine", "bush", "bush", "rock_small"],
        "decor_density": 2.4,
        "clutter": ["grass_green", "grass_green", "grass_green", "grass_green",
                    "rock_tiny", "flower_pink", "flower_yellow", "flower_white"],
        "clutter_density": 1.4,
        "obstacles": [("pothole", 3), ("branch", 3)],
        "curve_mult": 0.85,
    },
    "cobbles": {
        "grass":   (95, 120, 75),
        "road":    (130, 115, 95),
        "edge":    (190, 175, 150),
        "decor":   ["oak", "oak", "oak", "bush", "bush", "rock_small", "pine",
                    "belgian_flag", "belgian_flag", "frittenbude", "brick_church"],
        "decor_density": 1.9,
        "clutter": ["grass_green", "grass_green", "rock_tiny", "rock_tiny",
                    "flower_yellow", "flower_white"],
        "clutter_density": 1.2,
        "obstacles": [("pothole", 4), ("branch", 2)],
        "curve_mult": 0.75,
    },
    "gravel": {
        "grass":   (135, 145, 80),
        "road":    (180, 160, 110),
        "edge":    (210, 190, 140),
        "decor":   ["cypress", "cypress", "cypress", "cypress", "bush",
                    "vineyard", "vineyard", "vineyard", "sunflower", "sunflower",
                    "stone_house", "rock_small", "rock_big"],
        "decor_density": 2.0,
        "clutter": ["grass_dry", "grass_dry", "grass_dry", "rock_tiny", "rock_tiny",
                    "flower_yellow", "sunflower"],
        "clutter_density": 1.4,
        "obstacles": [("pothole", 3), ("rock", 2), ("branch", 2)],
        "curve_mult": 0.95,
    },
    "mountain": {
        "grass":   (95, 100, 85),
        "road":    (65, 65, 75),
        "edge":    (180, 180, 190),
        "decor":   ["pine", "pine", "pine", "pine", "rock_big", "rock_big",
                    "rock_small", "rock_small", "rock_small",
                    "tornante", "tornante", "goat"],
        "decor_density": 3.0,
        "clutter": ["grass_rocky", "grass_rocky", "rock_tiny", "rock_tiny", "rock_tiny",
                    "flower_white"],
        "clutter_density": 1.5,
        "obstacles": [("pothole", 2), ("rock", 3), ("branch", 1)],
        "curve_mult": 1.4,
    },
    "alpine": {
        "grass":   (225, 230, 235),
        "road":    (80, 80, 90),
        "edge":    (240, 240, 245),
        "decor":   ["pine_snow", "pine_snow", "pine_snow", "rock_big", "rock_big",
                    "rock_small", "rock_small", "chalet", "ski_lift", "goat", "tornante"],
        "decor_density": 2.6,
        "clutter": ["grass_snow", "grass_snow", "grass_alpine", "rock_tiny", "rock_tiny"],
        "clutter_density": 1.3,
        "obstacles": [("pothole", 2), ("rock", 3)],
        "curve_mult": 1.55,
    },
    "autumn": {
        "grass":   (130, 105, 60),
        "road":    (75, 70, 75),
        "edge":    (215, 210, 200),
        "decor":   ["oak_autumn", "oak_autumn", "oak_autumn", "bush_autumn", "bush_autumn",
                    "pine", "rock_small", "stone_wall", "stone_wall", "stone_house"],
        "decor_density": 2.2,
        "clutter": ["grass_autumn", "grass_autumn", "grass_autumn", "rock_tiny",
                    "flower_yellow"],
        "clutter_density": 1.3,
        "obstacles": [("pothole", 2), ("branch", 4)],
        "curve_mult": 0.95,
    },
}

_curve_amp_mult = 1.0


def set_curve_amp_mult(m):
    global _curve_amp_mult
    _curve_amp_mult = m


def road_curve(distance):
    """World x offset (pixels) of road centerline at given world distance (meters)."""
    m = _curve_amp_mult
    return (math.sin(distance * 0.032) * 130 * m
            + math.sin(distance * 0.010) * 70 * m
            + math.sin(distance * 0.080) * 34 * m)


def make_cyclist_sprite(jersey, helmet, secondary=None, w=PLAYER_W, h=PLAYER_H):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = w // 2
    tire = BLACK
    rim = (170, 170, 175)
    frame = (50, 50, 60)
    arm = (220, 195, 165)

    # Vorderrad: schmal, dünner Reifen mit hellem Felgenstreifen
    pygame.draw.rect(s, tire, (cx - 1, 0, 3, 9))
    pygame.draw.rect(s, rim, (cx, 1, 1, 7))

    # Lenker: schmaler Drop-Bar, an den Enden leicht abgewinkelt
    pygame.draw.rect(s, frame, (cx - 7, 7, 15, 2))
    pygame.draw.rect(s, frame, (cx - 7, 8, 2, 2))
    pygame.draw.rect(s, frame, (cx + 6, 8, 2, 2))

    # Arme zu den Bremsgriffen
    pygame.draw.rect(s, arm, (cx - 5, 10, 2, 4))
    pygame.draw.rect(s, arm, (cx + 4, 10, 2, 4))

    # Oberkörper Trikot — schmal (10 statt 16 breit), klar gegen Tank-Optik
    pygame.draw.rect(s, jersey, (cx - 4, 13, 9, 11))
    pygame.draw.rect(s, jersey, (cx - 3, 11, 7, 2))

    # Helm: oval, oben am Kopf, mit Lüftungsschlitz
    pygame.draw.ellipse(s, helmet, (cx - 4, 13, 9, 7))
    pygame.draw.rect(s, (25, 25, 30), (cx - 1, 14, 2, 4))

    # Trikot Po-Bereich
    pygame.draw.rect(s, jersey, (cx - 4, 24, 9, 6))
    if secondary:
        for py in (14, 17, 20, 23, 26):
            pygame.draw.rect(s, secondary, (cx - 3, py, 7, 1))

    # Sattel
    pygame.draw.rect(s, (30, 30, 38), (cx - 2, 30, 5, 3))

    # Sitzrohr / Sattelstütze
    pygame.draw.rect(s, frame, (cx, 33, 1, 5))

    # Hinterrad
    pygame.draw.rect(s, tire, (cx - 1, 38, 3, 10))
    pygame.draw.rect(s, rim, (cx, 39, 1, 8))
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


def make_pine_sprite(snow=False):
    s = pygame.Surface((22, 40), pygame.SRCALPHA)
    pygame.draw.rect(s, BROWN_DARK, (10, 32, 3, 8))
    green = (40, 100, 50)
    light = (70, 130, 65)
    tiers = [(2, 7), (10, 10), (18, 14)]
    for ty, w in tiers:
        pygame.draw.polygon(s, green, [(11, ty), (11 - w, ty + 10), (11 + w, ty + 10)])
        pygame.draw.polygon(s, light, [(11, ty + 1), (11 - w + 3, ty + 9), (11 + w - 3, ty + 9)])
    if snow:
        white = (240, 245, 250)
        for ty, w in tiers:
            pygame.draw.polygon(s, white, [(11, ty), (11 - w // 2, ty + 4), (11 + w // 2, ty + 4)])
    return s


def make_oak_sprite(autumn=False):
    s = pygame.Surface((26, 36), pygame.SRCALPHA)
    pygame.draw.rect(s, BROWN_DARK, (12, 24, 3, 12))
    if autumn:
        c1, c2 = (200, 100, 40), (240, 170, 70)
    else:
        c1, c2 = (45, 100, 55), (80, 150, 75)
    pygame.draw.ellipse(s, c1, (1, 2, 24, 26))
    pygame.draw.ellipse(s, c2, (4, 4, 16, 18))
    return s


def make_palm_sprite():
    s = pygame.Surface((26, 40), pygame.SRCALPHA)
    pygame.draw.rect(s, BROWN, (12, 10, 3, 30))
    pygame.draw.rect(s, BROWN_DARK, (12, 14, 3, 2))
    pygame.draw.rect(s, BROWN_DARK, (12, 22, 3, 2))
    green = (50, 130, 60)
    for ang in (200, 240, 290, 340, 30, 80):
        a = math.radians(ang)
        ex = 13 + int(math.cos(a) * 12)
        ey = 11 + int(math.sin(a) * 7)
        pygame.draw.line(s, green, (13, 11), (ex, ey), 3)
    return s


def make_cypress_sprite():
    s = pygame.Surface((14, 44), pygame.SRCALPHA)
    pygame.draw.rect(s, BROWN_DARK, (6, 38, 3, 6))
    pygame.draw.ellipse(s, (40, 90, 50), (3, 0, 9, 40))
    pygame.draw.ellipse(s, (65, 115, 65), (4, 4, 6, 34))
    return s


def make_bush_sprite(autumn=False):
    s = pygame.Surface((20, 14), pygame.SRCALPHA)
    if autumn:
        c1, c2 = (180, 90, 40), (220, 140, 60)
    else:
        c1, c2 = (50, 110, 55), (80, 150, 75)
    pygame.draw.ellipse(s, c1, (0, 2, 20, 12))
    pygame.draw.ellipse(s, c2, (3, 4, 14, 8))
    return s


def make_grass_tuft_sprite(variant="green"):
    palette = {
        "green":   ((45, 105, 45), (90, 160, 75)),
        "dry":     ((150, 140, 75), (200, 180, 100)),
        "snow":    ((215, 222, 232), (245, 248, 255)),
        "autumn":  ((140, 95, 50), (200, 150, 70)),
        "alpine":  ((175, 175, 165), (215, 215, 200)),
        "rocky":   ((100, 105, 75), (140, 150, 100)),
        "coast":   ((80, 140, 60), (120, 180, 90)),
    }
    c1, c2 = palette.get(variant, palette["green"])
    s = pygame.Surface((12, 11), pygame.SRCALPHA)
    pygame.draw.line(s, c1, (1, 10), (2, 1), 2)
    pygame.draw.line(s, c2, (4, 10), (5, 0), 2)
    pygame.draw.line(s, c1, (7, 10), (7, 2), 2)
    pygame.draw.line(s, c2, (10, 10), (9, 1), 2)
    return s


def make_small_rock_sprite():
    s = pygame.Surface((12, 9), pygame.SRCALPHA)
    pygame.draw.polygon(s, (115, 115, 120), [(1, 8), (3, 3), (8, 3), (11, 8)])
    pygame.draw.polygon(s, (150, 150, 155), [(3, 5), (5, 3), (8, 5)])
    return s


def make_flower_sprite(color=(240, 80, 120)):
    s = pygame.Surface((10, 12), pygame.SRCALPHA)
    pygame.draw.line(s, (50, 110, 50), (5, 11), (5, 5), 1)
    pygame.draw.circle(s, color, (5, 4), 3)
    pygame.draw.circle(s, (255, 240, 120), (5, 4), 1)
    return s


SPECTATOR_COLORS = [
    (220, 70, 70),
    (90, 130, 220),
    (240, 210, 60),
    (60, 180, 110),
    (235, 120, 180),
    (240, 140, 50),
]


def make_spectator_sprite(shirt, arms_up):
    s = pygame.Surface((12, 22), pygame.SRCALPHA)
    skin = (225, 195, 160)
    pants = (40, 50, 70)
    shoes = (22, 22, 28)
    hair = (60, 40, 25)
    pygame.draw.rect(s, hair, (4, 0, 4, 2))
    pygame.draw.rect(s, skin, (4, 2, 4, 3))
    pygame.draw.rect(s, shirt, (3, 5, 6, 8))
    pygame.draw.rect(s, pants, (3, 13, 6, 6))
    pygame.draw.rect(s, shoes, (3, 19, 2, 2))
    pygame.draw.rect(s, shoes, (7, 19, 2, 2))
    if arms_up:
        pygame.draw.rect(s, shirt, (1, 5, 2, 3))
        pygame.draw.rect(s, shirt, (9, 5, 2, 3))
        pygame.draw.rect(s, skin, (1, 0, 2, 5))
        pygame.draw.rect(s, skin, (9, 0, 2, 5))
    else:
        pygame.draw.rect(s, shirt, (1, 5, 2, 3))
        pygame.draw.rect(s, shirt, (9, 5, 2, 3))
        pygame.draw.rect(s, skin, (1, 8, 2, 5))
        pygame.draw.rect(s, skin, (9, 8, 2, 5))
    return s


def make_rock_decor_sprite(big=False):
    if big:
        s = pygame.Surface((30, 22), pygame.SRCALPHA)
        pygame.draw.polygon(s, (110, 110, 115), [(2, 20), (8, 6), (22, 4), (28, 18), (24, 21)])
        pygame.draw.polygon(s, (140, 140, 145), [(10, 8), (16, 5), (22, 9), (18, 14)])
    else:
        s = pygame.Surface((20, 14), pygame.SRCALPHA)
        pygame.draw.polygon(s, (115, 115, 120), [(2, 12), (6, 4), (16, 5), (18, 12)])
        pygame.draw.polygon(s, (145, 145, 150), [(8, 6), (12, 4), (14, 8)])
    return s


def make_puddle_sprite(w=44, h=20):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (35, 55, 90, 210), (0, 0, w, h))
    pygame.draw.ellipse(s, (75, 125, 195, 220), (3, 3, w - 6, h - 6))
    pygame.draw.arc(s, (215, 235, 250), (10, 4, w - 20, h - 8), 0.3, 1.1, 1)
    pygame.draw.arc(s, (180, 210, 240), (6, 9, w - 14, h - 12), 3.2, 4.0, 1)
    return s


def make_snowpatch_sprite(w=44, h=20):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (215, 225, 235, 230), (0, 0, w, h))
    pygame.draw.ellipse(s, (245, 248, 255, 245), (4, 3, w - 8, h - 6))
    pygame.draw.circle(s, (255, 255, 255), (w // 3, h // 2), 2)
    pygame.draw.circle(s, (255, 255, 255), (2 * w // 3, h // 2 - 1), 2)
    return s


def make_haybale_sprite():
    s = pygame.Surface((38, 34), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (110, 80, 35), (1, 5, 36, 28))
    pygame.draw.ellipse(s, (195, 160, 75), (3, 7, 32, 22))
    pygame.draw.ellipse(s, (225, 195, 110), (6, 10, 24, 14))
    cx, cy = 19, 18
    for ang in (0.0, math.pi / 4, math.pi / 2, 3 * math.pi / 4):
        x1 = cx + math.cos(ang) * 14
        y1 = cy + math.sin(ang) * 10
        x2 = cx - math.cos(ang) * 14
        y2 = cy - math.sin(ang) * 10
        pygame.draw.line(s, (155, 115, 45), (x1, y1), (x2, y2), 1)
    return s


def make_rock_obstacle_sprite():
    s = pygame.Surface((30, 22), pygame.SRCALPHA)
    pygame.draw.polygon(s, (95, 95, 100), [(2, 20), (6, 6), (22, 3), (28, 18), (24, 21)])
    pygame.draw.polygon(s, (130, 130, 135), [(8, 8), (16, 4), (22, 10), (18, 16)])
    pygame.draw.polygon(s, (160, 160, 165), [(12, 8), (16, 5), (18, 10)])
    return s


def make_landmark_lighthouse_sprite():
    """Sanremo-Leuchtturm — Erkennungszeichen der Mittelmeerstrecke."""
    s = pygame.Surface((28, 64), pygame.SRCALPHA)
    body = (245, 245, 240)
    red = (220, 60, 60)
    dark = (60, 60, 70)
    yellow = (250, 230, 60)
    pygame.draw.rect(s, body, (10, 18, 8, 46))
    for y in (24, 32, 40, 48):
        pygame.draw.rect(s, red, (10, y, 8, 4))
    pygame.draw.rect(s, dark, (7, 12, 14, 6))
    pygame.draw.rect(s, yellow, (8, 13, 12, 4))
    pygame.draw.polygon(s, dark, [(6, 12), (14, 0), (22, 12)])
    pygame.draw.line(s, yellow, (3, 10), (10, 14), 2)
    pygame.draw.line(s, yellow, (18, 14), (25, 10), 2)
    return s


def make_landmark_siena_sprite():
    """Torre del Mangia auf der Piazza del Campo — Strade Bianche Ziel."""
    s = pygame.Surface((30, 84), pygame.SRCALPHA)
    body = (200, 120, 60)
    body_dark = (150, 85, 45)
    pygame.draw.rect(s, body, (10, 12, 10, 72))
    pygame.draw.rect(s, body_dark, (10, 12, 10, 72), 1)
    for x in (10, 13, 16, 19):
        pygame.draw.rect(s, body_dark, (x, 6, 2, 6))
    pygame.draw.rect(s, body, (10, 12, 10, 2))
    for y in (28, 44, 60):
        pygame.draw.rect(s, (30, 30, 40), (13, y, 4, 6))
    pygame.draw.rect(s, (250, 220, 80), (14, 0, 2, 6))
    pygame.draw.rect(s, (250, 220, 80), (13, 1, 4, 1))
    return s


def make_landmark_kapellemuur_sprite():
    """Kleine flandrische Kapelle auf einem Pavé-Hügel."""
    s = pygame.Surface((42, 56), pygame.SRCALPHA)
    body = (245, 240, 230)
    roof = (130, 60, 40)
    door = (60, 40, 30)
    pygame.draw.polygon(s, (140, 125, 105), [(0, 46), (21, 32), (42, 46), (42, 56), (0, 56)])
    pygame.draw.rect(s, body, (10, 22, 22, 24))
    pygame.draw.polygon(s, roof, [(8, 22), (21, 10), (34, 22)])
    pygame.draw.rect(s, body, (19, 4, 4, 18))
    pygame.draw.polygon(s, roof, [(18, 4), (21, 0), (24, 4)])
    pygame.draw.rect(s, (220, 200, 80), (20, 6, 2, 6))
    pygame.draw.rect(s, (220, 200, 80), (19, 7, 4, 1))
    pygame.draw.rect(s, door, (18, 34, 6, 12))
    return s


def make_landmark_velodrome_sprite():
    """Steilwand-Bogen des Roubaix-Velodroms mit Pavé-Stein."""
    s = pygame.Surface((70, 50), pygame.SRCALPHA)
    rim = (200, 180, 140)
    rim_dark = (140, 120, 90)
    pygame.draw.arc(s, rim_dark, (4, 16, 62, 70), math.pi, 2 * math.pi, 7)
    pygame.draw.arc(s, rim, (8, 20, 54, 60), math.pi, 2 * math.pi, 3)
    pygame.draw.rect(s, rim_dark, (4, 44, 62, 4))
    pygame.draw.rect(s, (160, 160, 165), (30, 34, 10, 12))
    pygame.draw.rect(s, (140, 140, 145), (30, 34, 10, 12), 1)
    font = pygame.font.Font(None, 12)
    t = font.render("ROUBAIX", True, (40, 40, 50))
    s.blit(t, (35 - t.get_width() // 2, 38))
    return s


def make_landmark_castle_sprite():
    """Burg in den Ardennen — Lüttich-Bastogne."""
    s = pygame.Surface((48, 44), pygame.SRCALPHA)
    body = (140, 140, 142)
    body_dark = (100, 100, 105)
    roof = (115, 65, 55)
    pygame.draw.rect(s, body, (10, 20, 28, 24))
    pygame.draw.rect(s, body, (4, 10, 8, 34))
    pygame.draw.rect(s, body, (36, 10, 8, 34))
    pygame.draw.polygon(s, roof, [(2, 10), (8, 2), (14, 10)])
    pygame.draw.polygon(s, roof, [(34, 10), (40, 2), (46, 10)])
    for x in (10, 14, 18, 22, 26, 30, 34):
        pygame.draw.rect(s, body_dark, (x, 16, 2, 4))
    pygame.draw.rect(s, body_dark, (10, 20, 28, 1))
    pygame.draw.rect(s, (40, 30, 20), (22, 30, 8, 14))
    pygame.draw.rect(s, (40, 30, 20), (6, 22, 4, 6))
    pygame.draw.rect(s, (40, 30, 20), (38, 22, 4, 6))
    return s


def make_landmark_ventoux_obs_sprite():
    """Wetter-Observatorium am Mont Ventoux mit Geröllhalde."""
    s = pygame.Surface((30, 66), pygame.SRCALPHA)
    pygame.draw.polygon(s, (225, 225, 230),
                        [(0, 66), (9, 32), (21, 32), (30, 66)])
    pygame.draw.rect(s, (240, 240, 245), (10, 6, 10, 30))
    pygame.draw.rect(s, (250, 250, 255), (12, 9, 6, 24))
    pygame.draw.rect(s, (220, 60, 60), (14, 0, 2, 8))
    pygame.draw.line(s, (60, 60, 70), (15, 0), (15, 6), 1)
    return s


def make_landmark_ghisallo_sprite():
    """Madonna del Ghisallo — Schutzheilige der Radfahrer (Lombardia)."""
    s = pygame.Surface((38, 54), pygame.SRCALPHA)
    body = (240, 235, 225)
    roof = (130, 75, 50)
    door = (60, 40, 30)
    pygame.draw.rect(s, body, (4, 22, 30, 32))
    pygame.draw.polygon(s, roof, [(2, 22), (19, 10), (36, 22)])
    pygame.draw.rect(s, body, (17, 4, 6, 18))
    pygame.draw.polygon(s, roof, [(15, 4), (20, 0), (25, 4)])
    pygame.draw.rect(s, (250, 220, 80), (19, 7, 2, 6))
    pygame.draw.rect(s, (250, 220, 80), (18, 8, 4, 1))
    pygame.draw.rect(s, door, (16, 38, 8, 16))
    pygame.draw.rect(s, (60, 90, 130), (9, 30, 4, 6))
    pygame.draw.rect(s, (60, 90, 130), (25, 30, 4, 6))
    return s


def make_landmark_giro_arch_sprite():
    """Pinker Giro-Bogen — Maglia-Rosa-Stimmung."""
    s = pygame.Surface((100, 54), pygame.SRCALPHA)
    pink = (235, 80, 150)
    pink_dark = (180, 50, 110)
    pygame.draw.arc(s, pink, (4, 4, 92, 90), math.pi, 2 * math.pi, 8)
    pygame.draw.arc(s, pink_dark, (4, 4, 92, 90), math.pi, 2 * math.pi, 2)
    font = pygame.font.Font(None, 22)
    t = font.render("GIRO", True, (255, 255, 255))
    s.blit(t, ((100 - t.get_width()) // 2, 4))
    return s


def make_landmark_tour_marker_sprite():
    """Gelber Tour-Bogen mit Schriftzug."""
    s = pygame.Surface((100, 54), pygame.SRCALPHA)
    yellow = (250, 210, 60)
    yellow_dark = (180, 150, 30)
    pygame.draw.arc(s, yellow, (4, 4, 92, 90), math.pi, 2 * math.pi, 8)
    pygame.draw.arc(s, yellow_dark, (4, 4, 92, 90), math.pi, 2 * math.pi, 2)
    font = pygame.font.Font(None, 22)
    t = font.render("TOUR", True, (40, 40, 50))
    s.blit(t, ((100 - t.get_width()) // 2, 4))
    return s


def make_landmark_alpe21_sprite():
    """Schild "ALPE 21" — die 21 Kehren von Alpe d'Huez."""
    s = pygame.Surface((34, 48), pygame.SRCALPHA)
    pygame.draw.rect(s, (110, 75, 40), (16, 28, 2, 20))
    pygame.draw.rect(s, (250, 210, 60), (0, 4, 34, 24))
    pygame.draw.rect(s, (40, 40, 50), (0, 4, 34, 24), 2)
    font = pygame.font.Font(None, 18)
    t = font.render("ALPE", True, (40, 40, 50))
    s.blit(t, ((34 - t.get_width()) // 2, 6))
    font2 = pygame.font.Font(None, 22)
    t2 = font2.render("21", True, (220, 60, 60))
    s.blit(t2, ((34 - t2.get_width()) // 2, 16))
    return s


def make_landmark_steepness_sign_sprite():
    """Steigungs-Warnschild — Angliru / Mauer-Strecken."""
    s = pygame.Surface((32, 40), pygame.SRCALPHA)
    pygame.draw.rect(s, (110, 75, 40), (15, 22, 2, 18))
    pygame.draw.polygon(s, (250, 250, 240),
                        [(0, 4), (32, 4), (32, 20), (16, 24), (0, 20)])
    pygame.draw.polygon(s, (60, 60, 70),
                        [(0, 4), (32, 4), (32, 20), (16, 24), (0, 20)], 1)
    font = pygame.font.Font(None, 18)
    t = font.render("23%", True, (220, 60, 60))
    s.blit(t, ((32 - t.get_width()) // 2, 8))
    return s


ROUTE_LANDMARKS = {
    "milano_sanremo":  make_landmark_lighthouse_sprite,
    "strade_bianche":  make_landmark_siena_sprite,
    "flandern":        make_landmark_kapellemuur_sprite,
    "paris_roubaix":   make_landmark_velodrome_sprite,
    "liege":           make_landmark_castle_sprite,
    "tourmalet":       make_landmark_tour_marker_sprite,
    "alpedhuez":       make_landmark_alpe21_sprite,
    "galibier":        make_landmark_tour_marker_sprite,
    "ventoux":         make_landmark_ventoux_obs_sprite,
    "mortirolo":       make_landmark_giro_arch_sprite,
    "zoncolan":        make_landmark_giro_arch_sprite,
    "stelvio":         make_landmark_giro_arch_sprite,
    "angliru":         make_landmark_steepness_sign_sprite,
    "lombardia":       make_landmark_ghisallo_sprite,
}


def make_beach_hut_sprite():
    """Bunte Strandhütte — Markenzeichen ligurischer Küstenstrecken."""
    s = pygame.Surface((24, 28), pygame.SRCALPHA)
    body = (240, 240, 245)
    stripe = (50, 130, 200)
    roof = (220, 70, 70)
    door = (40, 60, 110)
    pygame.draw.rect(s, body, (2, 12, 20, 14))
    for x in (5, 9, 13, 17):
        pygame.draw.rect(s, stripe, (x, 12, 1, 14))
    pygame.draw.polygon(s, roof, [(0, 14), (12, 4), (24, 14)])
    pygame.draw.rect(s, door, (9, 18, 6, 8))
    return s


def make_boat_sprite():
    """Kleines Fischerboot — passt zur Mittelmeerküste."""
    s = pygame.Surface((30, 20), pygame.SRCALPHA)
    hull = (110, 75, 40)
    hull_dark = (80, 55, 30)
    sail = (245, 245, 240)
    pygame.draw.polygon(s, hull, [(0, 14), (30, 14), (26, 19), (4, 19)])
    pygame.draw.rect(s, hull_dark, (4, 18, 22, 1))
    pygame.draw.line(s, (60, 60, 70), (15, 0), (15, 14), 1)
    pygame.draw.polygon(s, sail, [(15, 1), (24, 12), (15, 12)])
    return s


def make_frittenbude_sprite():
    """Belgische Frittenbude mit Banner — Pavé-Strecken-Klassiker."""
    s = pygame.Surface((30, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (220, 220, 230), (2, 10, 26, 22))
    pygame.draw.rect(s, (60, 60, 70), (2, 10, 26, 22), 1)
    pygame.draw.rect(s, (200, 60, 60), (0, 6, 30, 6))
    pygame.draw.rect(s, (250, 220, 60), (4, 12, 22, 4))
    pygame.draw.rect(s, (40, 40, 50), (12, 16, 8, 8))
    pygame.draw.polygon(s, (250, 230, 90), [(7, 24), (11, 24), (10, 30), (8, 30)])
    pygame.draw.polygon(s, (250, 230, 90), [(20, 24), (24, 24), (23, 30), (21, 30)])
    return s


def make_belgian_flag_sprite():
    """Schwarz-Gelb-Rot — Flandern-Stimmung."""
    s = pygame.Surface((20, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (60, 60, 70), (9, 2, 1, 30))
    pygame.draw.rect(s, (25, 25, 30), (10, 4, 9, 6))
    pygame.draw.rect(s, (250, 210, 60), (10, 10, 9, 6))
    pygame.draw.rect(s, (220, 60, 60), (10, 16, 9, 6))
    return s


def make_brick_church_sprite():
    """Backsteinkirche mit Turm — passt zu cobbles/Flandern."""
    s = pygame.Surface((26, 40), pygame.SRCALPHA)
    body = (190, 90, 70)
    roof = (130, 60, 50)
    pygame.draw.rect(s, body, (5, 18, 16, 22))
    pygame.draw.polygon(s, roof, [(3, 18), (13, 12), (23, 18)])
    pygame.draw.rect(s, body, (11, 4, 5, 16))
    pygame.draw.polygon(s, roof, [(10, 4), (13, 0), (17, 4)])
    pygame.draw.rect(s, (220, 220, 90), (13, 7, 1, 4))
    pygame.draw.rect(s, (220, 220, 90), (12, 8, 3, 1))
    pygame.draw.rect(s, (50, 50, 70), (8, 24, 3, 6))
    pygame.draw.rect(s, (50, 50, 70), (15, 24, 3, 6))
    return s


def make_vineyard_post_sprite():
    """Rebstock-Stütze mit Trauben — Toskana/Strade Bianche."""
    s = pygame.Surface((14, 24), pygame.SRCALPHA)
    pygame.draw.rect(s, (110, 75, 40), (6, 8, 2, 16))
    for x, y in ((1, 10), (4, 6), (9, 11), (11, 7), (7, 14), (2, 16), (10, 17)):
        pygame.draw.circle(s, (90, 140, 60), (x, y), 2)
    for x, y in ((3, 12), (8, 9), (10, 14)):
        pygame.draw.circle(s, (140, 90, 160), (x, y), 1)
    return s


def make_stone_house_sprite():
    """Toskanisches Steinhaus mit Pultdach."""
    s = pygame.Surface((30, 30), pygame.SRCALPHA)
    body = (200, 180, 145)
    stone = (160, 140, 110)
    roof = (150, 80, 50)
    pygame.draw.rect(s, body, (3, 12, 24, 18))
    for x, y in ((5, 16), (12, 14), (20, 18), (24, 16), (8, 24), (18, 26), (22, 22)):
        pygame.draw.rect(s, stone, (x, y, 3, 2))
    pygame.draw.polygon(s, roof, [(0, 14), (15, 2), (30, 14)])
    pygame.draw.rect(s, (60, 90, 140), (13, 20, 4, 6))
    return s


def make_sunflower_sprite():
    """Sonnenblume — Sommer in der Toskana."""
    s = pygame.Surface((14, 24), pygame.SRCALPHA)
    pygame.draw.line(s, (60, 110, 50), (7, 23), (7, 10), 2)
    pygame.draw.circle(s, (250, 200, 50), (7, 7), 5)
    pygame.draw.circle(s, (110, 70, 30), (7, 7), 2)
    pygame.draw.line(s, (50, 110, 50), (3, 18), (7, 14), 1)
    return s


def make_tornante_sign_sprite():
    """Kehren-Schild mit Kurven-Pfeil — Berg-Etappen."""
    s = pygame.Surface((24, 32), pygame.SRCALPHA)
    pygame.draw.rect(s, (110, 75, 40), (11, 16, 2, 16))
    pygame.draw.rect(s, (250, 250, 240), (0, 6, 24, 12))
    pygame.draw.rect(s, (60, 60, 70), (0, 6, 24, 12), 1)
    pygame.draw.arc(s, (220, 60, 60), (4, 8, 16, 9), 0.2, math.pi - 0.2, 2)
    pygame.draw.polygon(s, (220, 60, 60), [(4, 11), (1, 14), (7, 14)])
    return s


def make_mountain_goat_sprite():
    """Bergziege am Hang — selten, aber sehr Alpin-typisch."""
    s = pygame.Surface((22, 16), pygame.SRCALPHA)
    body = (225, 220, 210)
    horn = (60, 50, 40)
    pygame.draw.rect(s, body, (4, 6, 12, 6))
    pygame.draw.rect(s, body, (15, 4, 5, 4))
    pygame.draw.polygon(s, horn, [(18, 4), (20, 0), (19, 4)])
    pygame.draw.polygon(s, horn, [(16, 4), (16, 0), (17, 4)])
    for x in (5, 8, 12, 14):
        pygame.draw.rect(s, (80, 70, 50), (x, 12, 1, 4))
    pygame.draw.rect(s, (50, 40, 30), (4, 8, 1, 1))  # Auge
    return s


def make_ski_lift_sprite():
    """Skilift-Mast mit Gondel — alpine Strecken."""
    s = pygame.Surface((16, 44), pygame.SRCALPHA)
    pygame.draw.rect(s, (130, 130, 135), (7, 8, 2, 36))
    pygame.draw.line(s, (40, 40, 50), (1, 6), (14, 4), 1)
    pygame.draw.rect(s, (220, 60, 60), (4, 10, 8, 6))
    pygame.draw.rect(s, (40, 50, 70), (4, 10, 8, 1))
    pygame.draw.rect(s, (140, 180, 220), (5, 12, 6, 2))
    return s


def make_chalet_sprite():
    """Holzchalet mit Schneehäubchen — Hochalpen."""
    s = pygame.Surface((30, 32), pygame.SRCALPHA)
    body = (170, 120, 65)
    body_dark = (120, 80, 45)
    roof = (90, 70, 60)
    snow = (240, 245, 250)
    pygame.draw.polygon(s, roof, [(0, 18), (15, 4), (30, 18)])
    pygame.draw.polygon(s, snow, [(2, 17), (15, 8), (28, 17)])
    pygame.draw.rect(s, body, (4, 18, 22, 14))
    for y in (20, 24, 28):
        pygame.draw.rect(s, body_dark, (4, y, 22, 1))
    pygame.draw.rect(s, (60, 90, 130), (11, 22, 8, 6))
    pygame.draw.rect(s, (40, 40, 50), (11, 22, 8, 6), 1)
    return s


def make_old_stone_wall_sprite():
    """Alte Trockensteinmauer — herbstliche Streckenränder."""
    s = pygame.Surface((32, 14), pygame.SRCALPHA)
    pygame.draw.rect(s, (170, 155, 130), (0, 4, 32, 10))
    for x, y in ((2, 6), (10, 6), (18, 6), (26, 6),
                 (6, 10), (14, 10), (22, 10), (28, 10)):
        pygame.draw.rect(s, (130, 115, 95), (x, y, 4, 3))
    return s


def make_helicopter_shadow_sprite():
    """Schwebender Heli-Schatten: dunkler Blob mit Heckausleger und vier
    Rotorblättern. Semi-transparent, damit der Asphalt durchschimmert."""
    w, h = 120, 56
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    # Body
    pygame.draw.ellipse(s, (0, 0, 0, 90), (14, 12, w - 28, h - 24))
    # Heckausleger
    pygame.draw.rect(s, (0, 0, 0, 70), (w - 26, h // 2 - 3, 24, 6))
    pygame.draw.ellipse(s, (0, 0, 0, 80), (w - 12, h // 2 - 6, 10, 12))
    # Rotorblätter (vier statt rotierend — kürzt sich aufm Asphalt eh ab)
    cx, cy = w // 2 - 12, h // 2
    for a in (0.2, 1.7, 3.3, 4.9):
        x2 = cx + math.cos(a) * 42
        y2 = cy + math.sin(a) * 16
        pygame.draw.line(s, (0, 0, 0, 55), (cx, cy), (x2, y2), 4)
    return s


def make_photo_motorbike_sprite():
    """Foto-Motorrad mit Kameramann hinten — überholt den Pulk meist links."""
    s = pygame.Surface((22, 42), pygame.SRCALPHA)
    tire = (20, 20, 25)
    rim = (160, 160, 165)
    body = (215, 55, 55)
    helmet_d = (40, 40, 50)
    visor = (250, 220, 100)
    cam = (35, 35, 42)
    cam_lens = (190, 200, 220)
    arm = (220, 195, 165)
    # Vorderrad
    pygame.draw.rect(s, tire, (9, 0, 4, 9))
    pygame.draw.rect(s, rim, (10, 2, 2, 5))
    # Tank
    pygame.draw.rect(s, body, (7, 9, 8, 6))
    pygame.draw.rect(s, (255, 255, 255), (7, 12, 8, 1))
    # Fahrer
    pygame.draw.ellipse(s, helmet_d, (7, 13, 8, 8))
    pygame.draw.rect(s, visor, (8, 14, 6, 2))
    pygame.draw.rect(s, body, (6, 18, 10, 6))
    # Fotograf
    pygame.draw.ellipse(s, helmet_d, (6, 22, 10, 8))
    pygame.draw.rect(s, arm, (3, 24, 3, 4))
    # Kamera links rausgehalten
    pygame.draw.rect(s, cam, (0, 23, 5, 5))
    pygame.draw.circle(s, cam_lens, (2, 25), 2)
    # Auspuff
    pygame.draw.rect(s, (130, 130, 135), (15, 26, 3, 4))
    # Hinterrad
    pygame.draw.rect(s, tire, (9, 33, 4, 9))
    pygame.draw.rect(s, rim, (10, 35, 2, 5))
    return s


def make_team_car_sprite():
    """Teamwagen mit Ersatzrädern auf dem Dach."""
    s = pygame.Surface((28, 54), pygame.SRCALPHA)
    body = (45, 110, 195)
    body_hi = (75, 140, 225)
    glass = (140, 200, 230)
    tire = (20, 20, 25)
    rim = (160, 160, 165)
    spare = (35, 35, 42)
    spare_rim = (180, 180, 185)
    # Räder
    for ry in (8, 38):
        pygame.draw.rect(s, tire, (1, ry, 4, 10))
        pygame.draw.rect(s, tire, (23, ry, 4, 10))
        pygame.draw.rect(s, rim, (2, ry + 2, 2, 6))
        pygame.draw.rect(s, rim, (24, ry + 2, 2, 6))
    # Karosserie
    pygame.draw.rect(s, body, (4, 4, 20, 46))
    pygame.draw.rect(s, body_hi, (4, 4, 20, 3))
    # Frontscheibe
    pygame.draw.rect(s, glass, (6, 9, 16, 6))
    # Dachgepäckträger + Ersatzräder von oben (Ovale quer)
    for ry in (18, 24, 30, 36):
        pygame.draw.rect(s, spare, (7, ry, 14, 4))
        pygame.draw.rect(s, spare_rim, (13, ry + 1, 2, 2))
    # Heckscheibe
    pygame.draw.rect(s, glass, (6, 42, 16, 4))
    # Logo
    pygame.draw.rect(s, (250, 220, 80), (10, 11, 8, 2))
    return s


def make_diablo_spectator_sprite():
    """Der berühmte Tour-Devil-Fan: roter Anzug, Dreizack, Hörner."""
    s = pygame.Surface((16, 26), pygame.SRCALPHA)
    skin = (220, 195, 165)
    red = (210, 30, 30)
    dark = (140, 20, 20)
    yellow = (250, 210, 60)
    # Hörner
    pygame.draw.polygon(s, dark, [(3, 5), (6, 0), (6, 5)])
    pygame.draw.polygon(s, dark, [(12, 5), (9, 0), (9, 5)])
    # Kopf
    pygame.draw.rect(s, skin, (5, 4, 5, 4))
    # Roter Anzug
    pygame.draw.rect(s, red, (3, 9, 9, 10))
    pygame.draw.rect(s, yellow, (5, 11, 1, 6))
    pygame.draw.rect(s, yellow, (9, 11, 1, 6))
    # Beine
    pygame.draw.rect(s, red, (3, 19, 3, 5))
    pygame.draw.rect(s, red, (9, 19, 3, 5))
    # Dreizack rechts
    pygame.draw.line(s, (60, 60, 70), (13, 8), (13, 22), 2)
    pygame.draw.polygon(s, yellow, [(11, 6), (13, 0), (15, 6), (13, 4)])
    return s


def make_drummer_spectator_sprite():
    """Zuschauer mit Trommel — typisch in Bergetappen."""
    s = pygame.Surface((16, 24), pygame.SRCALPHA)
    skin = (225, 195, 160)
    shirt = (60, 130, 220)
    pants = (40, 50, 70)
    drum_red = (190, 60, 60)
    drum_top = (240, 220, 180)
    # Kopf
    pygame.draw.rect(s, (60, 40, 25), (5, 0, 5, 2))
    pygame.draw.rect(s, skin, (5, 2, 5, 3))
    # Körper
    pygame.draw.rect(s, shirt, (4, 5, 7, 6))
    # Trommel
    pygame.draw.ellipse(s, drum_red, (2, 10, 12, 9))
    pygame.draw.ellipse(s, drum_top, (3, 10, 10, 5))
    # Arme schlagen Trommel
    pygame.draw.rect(s, skin, (1, 8, 2, 4))
    pygame.draw.rect(s, skin, (13, 8, 2, 4))
    pygame.draw.rect(s, (220, 200, 160), (0, 12, 3, 2))
    pygame.draw.rect(s, (220, 200, 160), (13, 12, 3, 2))
    # Beine
    pygame.draw.rect(s, pants, (4, 19, 3, 4))
    pygame.draw.rect(s, pants, (9, 19, 3, 4))
    return s


SPONSORS = [
    ("CIAO",     (220, 80, 60)),
    ("VELO+",    (40, 120, 200)),
    ("PEDALE",   (235, 195, 60)),
    ("BIKEPRO",  (50, 160, 90)),
    ("CARBONIA", (140, 60, 180)),
    ("FORZA",    (240, 110, 40)),
]


def make_sponsor_barrier_sprite(color=(50, 130, 220)):
    """Absperrgitter mit Werbebanner — wie an echten Renn-Zielgeraden."""
    s = pygame.Surface((42, 20), pygame.SRCALPHA)
    rail = (190, 190, 195)
    pygame.draw.rect(s, color, (0, 6, 42, 12))
    pygame.draw.rect(s, (250, 250, 250), (0, 6, 42, 1))
    pygame.draw.rect(s, (30, 30, 40), (0, 17, 42, 1))
    for x in (6, 20, 34):
        pygame.draw.rect(s, (255, 255, 255), (x - 2, 9, 4, 4))
    pygame.draw.rect(s, rail, (0, 4, 42, 1))
    pygame.draw.rect(s, rail, (4, 4, 1, 14))
    pygame.draw.rect(s, rail, (20, 4, 1, 14))
    pygame.draw.rect(s, rail, (36, 4, 1, 14))
    return s


def make_km_sign_sprite(text="100m"):
    """Hölzernes Distanz-Schild am Straßenrand."""
    s = pygame.Surface((24, 30), pygame.SRCALPHA)
    pygame.draw.rect(s, (110, 75, 40), (11, 14, 3, 16))
    pygame.draw.rect(s, (245, 245, 235), (0, 4, 24, 12))
    pygame.draw.rect(s, (60, 60, 70), (0, 4, 24, 12), 1)
    font = pygame.font.Font(None, 16)
    t = font.render(text, True, (40, 40, 50))
    s.blit(t, ((24 - t.get_width()) // 2, 6))
    return s


def make_gantry_sprite(text="", color=(60, 130, 220), kind="banner"):
    """Banner-Gantry über der Strecke: Start, Sponsor, Flamme Rouge, Ziel.
    Breite passt sich grob an ROAD_WIDTH an, damit Pfosten am Straßenrand
    landen."""
    w = max(200, ROAD_WIDTH + 50)
    h = 76
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    post = (38, 38, 46)
    # Pfosten + Querbalken
    pygame.draw.rect(s, post, (6, 24, 6, h - 24))
    pygame.draw.rect(s, post, (w - 12, 24, 6, h - 24))
    pygame.draw.rect(s, post, (4, 22, w - 8, 4))
    pygame.draw.rect(s, (60, 60, 72), (4, 22, w - 8, 1))

    if kind == "flamme":
        cx = w // 2
        kite = [(cx - 30, 28), (cx + 30, 28),
                (cx + 18, 56), (cx, 68), (cx - 18, 56)]
        pygame.draw.polygon(s, (210, 30, 30), kite)
        pygame.draw.polygon(s, (255, 255, 255), kite, 1)
        font = pygame.font.Font(None, 18)
        t = font.render(text or "FLAMME ROUGE", True, (245, 245, 245))
        s.blit(t, ((w - t.get_width()) // 2, 4))
    elif kind == "finish":
        # Karo-Banner oben + ZIEL-Text darunter
        banner_h = 18
        ncols = 14
        cell = (w - 24) / ncols
        for c in range(ncols):
            cc = (250, 250, 250) if c % 2 == 0 else (30, 30, 35)
            pygame.draw.rect(s, cc, (12 + c * cell, 2, cell + 1, banner_h))
        font = pygame.font.Font(None, 26)
        t = font.render(text or "ZIEL", True, (250, 210, 60))
        s.blit(t, ((w - t.get_width()) // 2, banner_h + 2))
    else:
        banner_h = 20
        pygame.draw.rect(s, color, (12, 2, w - 24, banner_h))
        pygame.draw.rect(s, (255, 255, 255), (12, 2, w - 24, 2))
        pygame.draw.rect(s, (255, 255, 255), (12, banner_h, w - 24, 2))
        font = pygame.font.Font(None, 20)
        t = font.render(text, True, (255, 255, 255))
        s.blit(t, ((w - t.get_width()) // 2, 4))
    return s


ASPHALT_TAGS = ["ALLEZ", "VIVA", "GO GO", "HOP HOP", "DAJE", "FORZA"]


def make_asphalt_paint_sprite(text="ALLEZ"):
    """Bemaltes Asphalt-Tag (Kreide-Schrift) in Renn-Mitte."""
    w, h = 100, 26
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    font = pygame.font.Font(None, 28)
    t = font.render(text, True, (250, 250, 240))
    t.set_alpha(150)
    s.blit(t, ((w - t.get_width()) // 2, (h - t.get_height()) // 2))
    return s


def make_decor_sprites():
    d = {
        "pine":        make_pine_sprite(),
        "pine_snow":   make_pine_sprite(snow=True),
        "oak":         make_oak_sprite(),
        "oak_autumn":  make_oak_sprite(autumn=True),
        "palm":        make_palm_sprite(),
        "cypress":     make_cypress_sprite(),
        "bush":        make_bush_sprite(),
        "bush_autumn": make_bush_sprite(autumn=True),
        "rock_big":    make_rock_decor_sprite(big=True),
        "rock_small":  make_rock_decor_sprite(big=False),
        "rock_tiny":   make_small_rock_sprite(),
        "grass_green":  make_grass_tuft_sprite("green"),
        "grass_dry":    make_grass_tuft_sprite("dry"),
        "grass_snow":   make_grass_tuft_sprite("snow"),
        "grass_autumn": make_grass_tuft_sprite("autumn"),
        "grass_alpine": make_grass_tuft_sprite("alpine"),
        "grass_rocky":  make_grass_tuft_sprite("rocky"),
        "grass_coast":  make_grass_tuft_sprite("coast"),
        "flower_pink":   make_flower_sprite((240, 80, 120)),
        "flower_yellow": make_flower_sprite((250, 220, 70)),
        "flower_white":  make_flower_sprite((250, 250, 250)),
        "diablo":        make_diablo_spectator_sprite(),
        "drummer":       make_drummer_spectator_sprite(),
        "km_sign":       make_km_sign_sprite(),  # Default; richtige Texte in run_race
        "beach_hut":     make_beach_hut_sprite(),
        "boat":          make_boat_sprite(),
        "frittenbude":   make_frittenbude_sprite(),
        "belgian_flag":  make_belgian_flag_sprite(),
        "brick_church":  make_brick_church_sprite(),
        "vineyard":      make_vineyard_post_sprite(),
        "stone_house":   make_stone_house_sprite(),
        "sunflower":     make_sunflower_sprite(),
        "tornante":      make_tornante_sign_sprite(),
        "goat":          make_mountain_goat_sprite(),
        "ski_lift":      make_ski_lift_sprite(),
        "chalet":        make_chalet_sprite(),
        "stone_wall":    make_old_stone_wall_sprite(),
    }
    for i, col in enumerate(SPECTATOR_COLORS):
        d[f"spec_{i}_up"] = make_spectator_sprite(col, arms_up=True)
        d[f"spec_{i}_dn"] = make_spectator_sprite(col, arms_up=False)
    for i, (_name, col) in enumerate(SPONSORS):
        d[f"barrier_{i}"] = make_sponsor_barrier_sprite(col)
    return d


SPECTATOR_KINDS = [f"spec_{i}" for i in range(len(SPECTATOR_COLORS))]
SPECIAL_SPECTATORS = ["diablo", "drummer"]
BARRIER_KINDS = [f"barrier_{i}" for i in range(len(SPONSORS))]


def make_star_sprite(filled=True, size=14):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = (size // 2) if i % 2 == 0 else (size // 4)
        pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
    if filled:
        pygame.draw.polygon(s, YELLOW, pts)
    else:
        pygame.draw.polygon(s, (110, 100, 70), pts, 1)
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


def event_tap_pos(event):
    """Pixel-Position eines Tap-/Klick-Events oder None."""
    if event.type == pygame.FINGERDOWN:
        return (int(event.x * W), int(event.y * H))
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return event.pos
    return None


class TouchPad:
    """Hält den State aller aktiven Pointer (Finger + Maus) und welche
    benannten Buttons gerade gedrückt sind. Multi-touch-fähig, damit man
    gleichzeitig lenken und beschleunigen kann."""

    def __init__(self, buttons):
        self.buttons = buttons  # [{"key": str, "rect": Rect, "label": str}]
        self.pointers = {}  # pointer_id -> (x, y)

    def handle_event(self, event):
        if event.type == pygame.FINGERDOWN:
            self.pointers[("f", event.finger_id)] = (event.x * W, event.y * H)
        elif event.type == pygame.FINGERMOTION:
            pid = ("f", event.finger_id)
            if pid in self.pointers:
                self.pointers[pid] = (event.x * W, event.y * H)
        elif event.type == pygame.FINGERUP:
            self.pointers.pop(("f", event.finger_id), None)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pointers[("m", 0)] = event.pos
        elif event.type == pygame.MOUSEMOTION:
            if ("m", 0) in self.pointers:
                self.pointers[("m", 0)] = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.pointers.pop(("m", 0), None)

    def pressed_keys(self):
        out = set()
        for pos in self.pointers.values():
            for btn in self.buttons:
                if btn["rect"].collidepoint(pos):
                    out.add(btn["key"])
        return out

    def key_at(self, pos, only=None):
        for btn in self.buttons:
            if only is not None and btn["key"] not in only:
                continue
            if btn["rect"].collidepoint(pos):
                return btn["key"]
        return None

    def draw(self, screen, font, only=None):
        pressed = self.pressed_keys()
        for btn in self.buttons:
            if only is not None and btn["key"] not in only:
                continue
            rect = btn["rect"]
            held = btn["key"] in pressed
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            bg = (60, 80, 120, 210) if held else (25, 30, 45, 130)
            border = (220, 230, 250, 220) if held else (140, 150, 180, 160)
            pygame.draw.rect(surf, bg, surf.get_rect(), border_radius=12)
            pygame.draw.rect(surf, border, surf.get_rect(), 2, border_radius=12)
            if "icon" in btn:
                self._draw_icon(surf, btn["icon"])
            screen.blit(surf, rect.topleft)
            if "label" in btn:
                label = font.render(btn["label"], True, WHITE)
                screen.blit(label, label.get_rect(center=rect.center))

    @staticmethod
    def _draw_icon(surf, kind, color=WHITE):
        r = surf.get_rect()
        cx, cy = r.centerx, r.centery
        # Icon-Größe richtet sich nach der kleineren Button-Dimension.
        s = max(14, min(r.w, r.h) // 3)
        if kind == "left":
            pygame.draw.polygon(surf, color,
                                [(cx - s, cy), (cx + s // 2, cy - s), (cx + s // 2, cy + s)])
        elif kind == "right":
            pygame.draw.polygon(surf, color,
                                [(cx + s, cy), (cx - s // 2, cy - s), (cx - s // 2, cy + s)])
        elif kind == "up":
            pygame.draw.polygon(surf, color,
                                [(cx, cy - s), (cx - s, cy + s // 2), (cx + s, cy + s // 2)])
        elif kind == "down":
            pygame.draw.polygon(surf, color,
                                [(cx, cy + s), (cx - s, cy - s // 2), (cx + s, cy - s // 2)])


class Player:
    def __init__(self, save_data):
        self.stats = compute_stats(save_data)
        lvl, _, _ = level_from_points(save_data.get("xp", save_data.get("points", 0)))
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
        self.pedal_phase = 0.0

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

    def update(self, dt, keys, route, wind_phase, touch=None):
        accel = keys[pygame.K_UP] or keys[pygame.K_w]
        brake = keys[pygame.K_DOWN] or keys[pygame.K_s]
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        if touch:
            accel = accel or "accel" in touch
            brake = brake or "brake" in touch
            left = left or "left" in touch
            right = right or "right" in touch

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

        base_drain = 0.22
        over = max(0.0, (self.speed - 26) / 20)
        drain = base_drain + over ** 2 * 2.2
        drain *= 1.0 + route.get("heat", 0) * 0.6
        drain *= self.stats["drain_mult"]
        self.energy = max(0.0, self.energy - drain * dt)

        if not accel and not self.on_grass:
            regen_rate = 1.6 * max(0.1, (1 - self.speed / 50))
            self.energy = min(self.max_energy, self.energy + regen_rate * dt)

        if self.flash_timer > 0:
            self.flash_timer -= dt

        self.pedal_phase += dt * (3.0 + self.speed * 0.18)


class Opponent:
    def __init__(self, start_distance, base_speed, top_speed=56):
        self.distance = start_distance
        self.target_speed = base_speed
        self.speed = base_speed
        self.top_speed = top_speed
        self.lane_pref = random.uniform(-ROAD_WIDTH // 2 + 22, ROAD_WIDTH // 2 - 22)
        self.world_x = road_curve(start_distance) + self.lane_pref
        self.jersey = (random.randint(40, 230), random.randint(40, 230), random.randint(40, 230))
        self.helmet = (random.randint(30, 220), random.randint(30, 220), random.randint(30, 220))
        base = make_cyclist_sprite(self.jersey, self.helmet)
        self.sprite_frames = (
            pygame.transform.rotate(base, 3),
            pygame.transform.rotate(base, -3),
        )
        self.wobble_phase = random.uniform(0, math.tau)
        self.pedal_phase = random.uniform(0, math.tau)

    def update(self, dt):
        self.target_speed += random.gauss(0, 1.4) * dt
        self.target_speed = max(20, min(self.top_speed, self.target_speed))
        self.speed += (self.target_speed - self.speed) * 1.2 * dt
        self.distance += self.speed / 3.6 * dt
        target = road_curve(self.distance) + self.lane_pref
        self.world_x += (target - self.world_x) * 2.2 * dt
        self.wobble_phase += dt * 2
        self.world_x += math.sin(self.wobble_phase) * 9 * dt
        self.pedal_phase += dt * (3.0 + self.speed * 0.18)


class Vehicle:
    """Begleitfahrzeug (Foto-Motorrad oder Teamwagen). Bleibt in seiner
    Spur entlang der Straßenmitte und fährt mit konstanter Geschwindigkeit
    — rein dekorativ, keine Kollision mit dem Spieler."""

    def __init__(self, distance, lane_offset, speed_kmh, sprite):
        self.distance = distance
        self.lane_offset = lane_offset
        self.speed = speed_kmh
        self.sprite = sprite

    @property
    def world_x(self):
        return road_curve(self.distance) + self.lane_offset

    def update(self, dt):
        self.distance += self.speed / 3.6 * dt


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


class Decor:
    def __init__(self, distance, world_x, kind):
        self.distance = distance
        self.world_x = world_x
        self.kind = kind


class HayBale:
    """Rollt quer über die Straße. world_x interpoliert über duration von
    start_x zu end_x, sodass der Ballen mittig auf der Strecke ist, wenn der
    Spieler distance erreicht."""

    def __init__(self, distance, start_x, end_x, duration):
        self.distance = distance
        self.start_x = start_x
        self.end_x = end_x
        self.duration = max(0.5, duration)
        self.elapsed = 0.0
        self.spin = 0.0
        self.hit = False

    @property
    def world_x(self):
        t = max(0.0, min(1.0, self.elapsed / self.duration))
        return self.start_x + (self.end_x - self.start_x) * t

    @property
    def alive(self):
        return self.elapsed < self.duration + 0.6

    def update(self, dt):
        self.elapsed += dt
        direction = 1 if self.end_x > self.start_x else -1
        self.spin += dt * 7 * direction


def init_weather_particles(weather, strong_wind):
    rain, snow, wind = [], [], []
    if weather == "rain":
        for _ in range(140):
            rain.append({
                "x": random.uniform(0, W + 200),
                "y": random.uniform(-H, H),
                "vy": random.uniform(760, 900),
                "len": random.randint(10, 16),
            })
    elif weather == "snow":
        for _ in range(90):
            snow.append({
                "x": random.uniform(0, W),
                "y": random.uniform(-H, H),
                "phase": random.uniform(0, math.tau),
                "drift": random.uniform(18, 46),
                "vy": random.uniform(55, 95),
                "r": random.randint(1, 2),
            })
    if strong_wind:
        for _ in range(26):
            wind.append({
                "x": random.uniform(-100, W),
                "y": random.uniform(0, H - 130),
                "len": random.randint(28, 64),
            })
    return rain, snow, wind


def update_weather_particles(rain, snow, wind, dt):
    for r in rain:
        r["y"] += r["vy"] * dt
        r["x"] -= 220 * dt
        if r["y"] > H + 20:
            r["y"] -= H + 40
            r["x"] = random.uniform(0, W + 200)
        if r["x"] < -30:
            r["x"] += W + 60
    for fl in snow:
        fl["phase"] += dt * 1.6
        fl["y"] += fl["vy"] * dt
        fl["x"] += math.sin(fl["phase"]) * fl["drift"] * dt
        if fl["y"] > H + 10:
            fl["y"] -= H + 30
            fl["x"] = random.uniform(0, W)
    for w in wind:
        w["x"] += 460 * dt
        if w["x"] > W + 80:
            w["x"] -= W + 160
            w["y"] = random.uniform(0, H - 130)


def draw_weather_particles(screen, rain, snow, wind):
    for r in rain:
        pygame.draw.line(screen, (170, 195, 230),
                         (r["x"], r["y"]), (r["x"] - 6, r["y"] + r["len"]), 1)
    for w in wind:
        pygame.draw.line(screen, (215, 225, 240),
                         (w["x"], w["y"]), (w["x"] + w["len"], w["y"]), 1)
    for fl in snow:
        col = (240, 248, 255) if fl["r"] >= 2 else (220, 232, 248)
        pygame.draw.circle(screen, col, (int(fl["x"]), int(fl["y"])), fl["r"])


def player_position(player, opponents):
    ahead = sum(1 for o in opponents if o.distance > player.distance)
    return ahead + 1


def spawn_obstacles_ahead(player, obstacles, density, next_distance, theme_data):
    horizon = player.distance + 240
    kinds = [k for k, _ in theme_data["obstacles"]]
    weights = [w for _, w in theme_data["obstacles"]]
    while next_distance < horizon:
        rc = road_curve(next_distance)
        x = rc + random.uniform(-ROAD_WIDTH // 2 + 18, ROAD_WIDTH // 2 - 18)
        kind = random.choices(kinds, weights=weights)[0]
        obstacles.append(Obstacle(next_distance, x, kind))
        gap = random.uniform(14, 32) / max(density, 0.15)
        next_distance += gap
    return next_distance


def spawn_decor_ahead(player, decor, theme_data, next_distance):
    horizon = player.distance + 240
    kinds = theme_data["decor"]
    if not kinds:
        return horizon + 100
    density = theme_data["decor_density"]
    while next_distance < horizon:
        rc = road_curve(next_distance)
        side = random.choice([-1, 1])
        offset = ROAD_WIDTH // 2 + random.randint(28, 200)
        x = rc + side * offset
        kind = random.choice(kinds)
        decor.append(Decor(next_distance, x, kind))
        gap = random.uniform(10, 32) / max(density, 0.15)
        next_distance += gap
    return next_distance


def spawn_clutter_ahead(player, decor, theme_data, next_distance):
    """Gras-Büschel, kleine Steine, Blumen — eng am Straßenrand, sehr dicht."""
    horizon = player.distance + 220
    kinds = theme_data.get("clutter", ["grass_green"])
    density = theme_data.get("clutter_density", 1.0)
    while next_distance < horizon:
        rc = road_curve(next_distance)
        side = random.choice([-1, 1])
        offset = ROAD_WIDTH // 2 + random.randint(2, 36)
        x = rc + side * offset
        kind = random.choice(kinds)
        decor.append(Decor(next_distance, x, kind))
        gap = random.uniform(2.5, 7.0) / max(density, 0.2)
        next_distance += gap
    return next_distance


def spawn_spectators_ahead(player, decor, next_distance, hype=1.0):
    """Zuschauer am Straßenrand. Dichter gepackt und näher dran als normale Deko,
    oft in kleinen Gruppen. `hype` skaliert die Wahrscheinlichkeit für Sponsor-
    Barrieren und Special-Fans (Diablo, Trommler) — vorm Ziel hochziehen."""
    horizon = player.distance + 240
    while next_distance < horizon:
        rc = road_curve(next_distance)
        side = random.choice([-1, 1])
        # Hin und wieder eine Sponsor-Barriere statt Fan-Gruppe direkt am Rand
        if random.random() < 0.18 * hype:
            offset = ROAD_WIDTH // 2 + random.randint(4, 10)
            x = rc + side * offset
            decor.append(Decor(next_distance, x, random.choice(BARRIER_KINDS)))
            next_distance += random.uniform(8, 18)
            continue
        group = random.randint(1, 4)
        for _ in range(group):
            offset = ROAD_WIDTH // 2 + random.randint(8, 28)
            jitter_d = random.uniform(-1.5, 1.5)
            jitter_x = random.uniform(-6, 6)
            x = rc + side * offset + jitter_x
            if random.random() < 0.06 * hype:
                kind = random.choice(SPECIAL_SPECTATORS)
            else:
                kind = random.choice(SPECTATOR_KINDS)
            decor.append(Decor(next_distance + jitter_d, x, kind))
        next_distance += random.uniform(14, 38)
    return next_distance


def spawn_weather_hazards_ahead(player, obstacles, next_distance, kind):
    horizon = player.distance + 240
    while next_distance < horizon:
        rc = road_curve(next_distance)
        x = rc + random.uniform(-ROAD_WIDTH // 2 + 18, ROAD_WIDTH // 2 - 18)
        obstacles.append(Obstacle(next_distance, x, kind))
        next_distance += random.uniform(35, 80)
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


OBSTACLE_REACH = {"pothole": 16, "branch": 18, "rock": 19, "puddle": 20, "snowpatch": 20}


def check_collisions(player, obstacles):
    half_w = PLAYER_W // 2
    for o in obstacles:
        if o.hit:
            continue
        dd = o.distance - player.distance
        if -0.4 < dd < 0.9:
            reach = OBSTACLE_REACH.get(o.kind, 18)
            if abs(o.world_x - player.world_x) < half_w + reach - 6:
                o.hit = True
                if o.kind == "pothole":
                    player.target_speed *= 0.45
                    player.speed *= 0.55
                    player.crashed_timer = 0.5
                    player.energy = max(0, player.energy - 3)
                elif o.kind == "branch":
                    player.target_speed *= 0.75
                    player.speed *= 0.8
                    player.energy = max(0, player.energy - 8)
                    player.crashed_timer = 0.3
                elif o.kind == "rock":
                    player.target_speed *= 0.35
                    player.speed *= 0.5
                    player.crashed_timer = 0.55
                    player.energy = max(0, player.energy - 6)
                elif o.kind == "puddle":
                    player.target_speed *= 0.86
                    player.speed *= 0.92
                    player.flash_timer = 0.15
                elif o.kind == "snowpatch":
                    player.target_speed *= 0.78
                    player.speed *= 0.88
                    player.flash_timer = 0.15
                else:
                    player.flash_timer = 0.25
                if o.kind in ("pothole", "branch", "rock"):
                    player.flash_timer = 0.25


def check_haybales(player, bales):
    half_w = PLAYER_W // 2
    for b in bales:
        if b.hit:
            continue
        dd = b.distance - player.distance
        if -0.4 < dd < 0.9:
            if abs(b.world_x - player.world_x) < half_w + 16:
                b.hit = True
                player.target_speed *= 0.28
                player.speed *= 0.38
                player.crashed_timer = 0.65
                player.energy = max(0, player.energy - 7)
                player.flash_timer = 0.3


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


def draw_road(screen, player, theme_data):
    screen.fill(theme_data["grass"])
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
    pygame.draw.polygon(screen, theme_data["road"], poly)
    if len(left_pts) >= 2:
        pygame.draw.lines(screen, theme_data["edge"], False, left_pts, 3)
        pygame.draw.lines(screen, theme_data["edge"], False, right_pts, 3)

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


def draw_player(screen, player, sprite_frames):
    s = math.sin(player.pedal_phase)
    frame = sprite_frames[0] if s > 0 else sprite_frames[1]
    bob = int(s * 2)
    x = int(W // 2 - frame.get_width() // 2)
    y = int(PLAYER_Y - frame.get_height() // 2 + bob)
    if player.flash_timer > 0 and int(player.flash_timer * 20) % 2 == 0:
        flash = frame.copy()
        flash.fill((255, 100, 100, 0), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(flash, (x, y))
    else:
        screen.blit(frame, (x, y))


def draw_hud(screen, player, position, total, distance_remaining, distance_target,
             fonts, route, recent_pickup, weather_label="", strong_wind=False):
    h = HUD_H
    # HUD sitzt jetzt oben, damit Daumen am Smartphone die Werte nicht verdecken.
    pygame.draw.rect(screen, HUD_BG, (0, 0, W, h))
    pygame.draw.rect(screen, (40, 50, 70), (0, h - 2, W, 2))

    # Streckenfortschritt: dünner Balken quer über die volle Breite, ganz oben.
    pbar_h = 6
    progress = 0.0
    if distance_target > 0:
        progress = max(0.0, min(1.0, 1.0 - distance_remaining / distance_target))
    pygame.draw.rect(screen, (30, 35, 48), (0, 0, W, pbar_h))
    pygame.draw.rect(screen, CYAN, (0, 0, int(W * progress), pbar_h))

    speed_int = int(round(player.speed))
    speed_text = fonts["big"].render(f"{speed_int}", True, WHITE)
    screen.blit(speed_text, (20, pbar_h + 6))
    unit = fonts["small"].render("km/h", True, HUD_DIM)
    screen.blit(unit, (20 + speed_text.get_width() + 6, pbar_h + 30))

    bar_w = max(120, min(220, W // 3))
    bar_h_ = 12
    bar_x = 20
    bar_y = h - 28
    pygame.draw.rect(screen, (30, 35, 48), (bar_x, bar_y, bar_w, bar_h_), border_radius=4)
    pct = player.energy / player.max_energy
    color = GREEN if pct > 0.5 else (YELLOW if pct > 0.2 else RED)
    pygame.draw.rect(screen, color, (bar_x, bar_y, int(bar_w * pct), bar_h_), border_radius=4)
    label = fonts["small"].render(f"Energie {int(player.energy)}/{player.max_energy}", True, HUD_TEXT)
    screen.blit(label, (bar_x, bar_y - 16))

    bx = bar_x + bar_w + 14
    for i in range(player.max_bottles):
        c = BLUE if i < player.water else (50, 60, 80)
        pygame.draw.rect(screen, c, (bx + i * 18, bar_y, 14, bar_h_), border_radius=2)
    screen.blit(fonts["small"].render("Wasser", True, HUD_TEXT), (bx, bar_y - 16))

    pos_text = fonts["mid"].render(f"Platz {position}/{total}", True, WHITE)
    screen.blit(pos_text, (W - pos_text.get_width() - 20, pbar_h + 4))
    lvl_text = fonts["small"].render(f"Lvl {player.level}", True, YELLOW)
    screen.blit(lvl_text, (W - lvl_text.get_width() - 20, pbar_h + 34))

    cond_x = W // 2 - 56
    indicators = []
    if strong_wind:
        indicators.append(("Sturm", ORANGE))
    elif route.get("wind", 0) > 0.4:
        indicators.append(("Wind", HUD_DIM))
    if route.get("heat", 0) > 0.5:
        indicators.append(("Hitze", HUD_DIM))
    if weather_label:
        indicators.append((weather_label, BLUE if weather_label == "Regen" else WHITE))
    if player.on_grass:
        indicators.append(("WIESE!", ORANGE))
    for i, (txt, col) in enumerate(indicators[:3]):
        screen.blit(fonts["small"].render(txt, True, col), (cond_x, pbar_h + 6 + i * 16))

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
            screen.blit(surf, (W // 2 - surf.get_width() // 2, h + 6))


async def run_menu(screen, save_data, fonts):
    clock = pygame.time.Clock()
    cursor = 0
    row_h = 64
    # Layout: 0 = Schwierigkeit, 1 = Shop, 2..N+1 = Routen.
    options_count = len(ROUTES) + 2

    def activate(idx):
        if idx == 0:
            cycle_difficulty(save_data)
            return None
        if idx == 1:
            return ("shop", None)
        return ("race", ROUTES[idx - 2])

    def build_layout():
        list_x = 20
        list_w = W - (96 if IS_TOUCH else 40)
        list_y0 = 140
        visible = max(4, min(options_count, (H - list_y0 - 60) // row_h))
        if IS_TOUCH:
            touch = TouchPad([
                {"key": "up",   "rect": pygame.Rect(W - 70, list_y0,                       62, 62), "icon":  "up"},
                {"key": "down", "rect": pygame.Rect(W - 70, list_y0 + visible * row_h - 68, 62, 62), "icon":  "down"},
            ])
        else:
            touch = TouchPad([])
        return list_x, list_w, list_y0, visible, touch

    list_x, list_w, list_y0, visible, touch = build_layout()
    star_full = make_star_sprite(filled=True)
    star_empty = make_star_sprite(filled=False)
    row_rects = []
    while True:
        clock.tick(FPS)
        screen, resized = maybe_resize(screen, fonts)
        if resized:
            list_x, list_w, list_y0, visible, touch = build_layout()
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
                    result = activate(cursor)
                    if result is not None:
                        return result
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d) and cursor == 0:
                    cycle_difficulty(save_data)
            touch.handle_event(event)
            tap = event_tap_pos(event)
            if tap is not None:
                tkey = touch.key_at(tap)
                if tkey == "up":
                    cursor = (cursor - 1) % options_count
                elif tkey == "down":
                    cursor = (cursor + 1) % options_count
                else:
                    for idx, rect in row_rects:
                        if rect.collidepoint(tap):
                            cursor = idx
                            result = activate(idx)
                            if result is not None:
                                return result
                            break

        screen.fill((22, 26, 40))
        title = fonts["huge"].render("RADGAME", True, WHITE)
        screen.blit(title, (W // 2 - title.get_width() // 2, 20))
        level, xp, need = level_from_points(save_data.get("xp", 0))
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
        row_rects = []
        for slot in range(min(visible, options_count)):
            i = scroll_start + slot
            if i >= options_count:
                break
            y = list_y0 + slot * row_h
            sel = (i == cursor)
            row_rects.append((i, pygame.Rect(list_x, y, list_w, row_h - 6)))
            if i == 0:
                bg = (50, 50, 70) if sel else (30, 32, 46)
                pygame.draw.rect(screen, bg, (list_x, y, list_w, row_h - 6), border_radius=10)
                if sel:
                    pygame.draw.rect(screen, CYAN, (list_x, y, list_w, row_h - 6), 2, border_radius=10)
                cur_diff = save_data.get("difficulty", "medium")
                cur_label = DIFFICULTY_PRESETS[cur_diff]["label"]
                name = fonts["mid"].render(f"Schwierigkeit: {cur_label}", True, CYAN)
                screen.blit(name, (list_x + 14, y + 4))
                desc = fonts["small"].render("Tap / Enter / ←→: wechseln (Leicht · Mittel · Schwer)", True, HUD_DIM)
                screen.blit(desc, (list_x + 14, y + 34))
            elif i == 1:
                bg = (60, 50, 30) if sel else (40, 35, 25)
                pygame.draw.rect(screen, bg, (list_x, y, list_w, row_h - 6), border_radius=10)
                if sel:
                    pygame.draw.rect(screen, YELLOW, (list_x, y, list_w, row_h - 6), 2, border_radius=10)
                name = fonts["mid"].render("SHOP — Upgrades", True, YELLOW)
                screen.blit(name, (list_x + 14, y + 4))
                desc = fonts["small"].render("Punkte ausgeben, Rad aufmotzen", True, HUD_DIM)
                screen.blit(desc, (list_x + 14, y + 34))
            else:
                r = ROUTES[i - 2]
                bg = (40, 52, 80) if sel else (28, 32, 48)
                pygame.draw.rect(screen, bg, (list_x, y, list_w, row_h - 6), border_radius=10)
                if sel:
                    pygame.draw.rect(screen, BLUE, (list_x, y, list_w, row_h - 6), 2, border_radius=10)
                name = fonts["mid"].render(r["name"], True, WHITE)
                screen.blit(name, (list_x + 14, y + 4))
                race_short = r["race"].split(" – ")[0].split(" (")[0]
                if len(race_short) > 14:
                    race_short = race_short[:13] + "…"
                region_short = r["region"].split(",")[0]
                if len(region_short) > 14:
                    region_short = region_short[:13] + "…"
                meta = fonts["small"].render(
                    f"{race_short} · {region_short} · {r['distance_m']}m",
                    True, HUD_DIM,
                )
                screen.blit(meta, (list_x + 14, y + 34))
                sx = list_x + list_w - 5 * 16 - 14
                sy = y + 36
                for j in range(5):
                    spr = star_full if j < r["difficulty"] else star_empty
                    screen.blit(spr, (sx + j * 16, sy))
                best = save_data.get("best", {}).get(r["id"])
                if best:
                    b = fonts["small"].render(f"Best P{best}", True, YELLOW)
                    screen.blit(b, (list_x + list_w - b.get_width() - 14, y + 10))

        if scroll_start > 0:
            screen.blit(fonts["small"].render("▲", True, HUD_DIM), (W // 2 - 6, list_y0 - 14))
        if scroll_start + visible < options_count:
            screen.blit(fonts["small"].render("▼", True, HUD_DIM),
                        (W // 2 - 6, list_y0 + visible * row_h - 4))

        hint = fonts["small"].render(
            "Tap · ↑/↓ wählen · Enter starten",
            True, HUD_DIM,
        )
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 26))
        # Versionsnummer unten rechts — wird pro Push hochgezaehlt, damit man
        # im Browser-Cache vs. Live-Build vergleichen kann.
        ver = fonts["small"].render(VERSION, True, (90, 100, 120))
        screen.blit(ver, (W - ver.get_width() - 8, H - 18))

        touch.draw(screen, fonts["mid"])

        pygame.display.flip()
        await asyncio.sleep(0)


async def run_shop(screen, save_data, fonts):
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
    list_y0 = 110
    row_h = 44

    def build_layout():
        visible_rows = max(6, min(22, (H - list_y0 - 60) // row_h))
        # Esc bleibt immer sichtbar — der Shop braucht einen klickbaren Rückweg.
        buttons = [
            {"key": "esc",  "rect": pygame.Rect(W - 90, 10, 80, 40), "label": "Menü"},
        ]
        if IS_TOUCH:
            buttons += [
                {"key": "up",   "rect": pygame.Rect(W - 70, list_y0,                            62, 62), "icon":  "up"},
                {"key": "down", "rect": pygame.Rect(W - 70, list_y0 + visible_rows * row_h - 68, 62, 62), "icon":  "down"},
            ]
        return visible_rows, TouchPad(buttons)

    visible_rows, touch = build_layout()
    item_rects = []  # [(item_list_index, Rect)]

    def activate_item(item):
        nonlocal msg, msg_t
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

    while True:
        dt = clock.tick(FPS) / 1000.0
        msg_t = max(0.0, msg_t - dt)
        screen, resized = maybe_resize(screen, fonts)
        if resized:
            visible_rows, touch = build_layout()

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
                    activate_item(items_list[selectable[cur]][1])
            touch.handle_event(event)
            tap = event_tap_pos(event)
            if tap is not None:
                tkey = touch.key_at(tap)
                if tkey == "esc":
                    return
                if tkey == "up":
                    cur = (cur - 1) % len(selectable)
                elif tkey == "down":
                    cur = (cur + 1) % len(selectable)
                else:
                    for idx, rect in item_rects:
                        if rect.collidepoint(tap):
                            cur = selectable.index(idx)
                            activate_item(items_list[idx][1])
                            break

        screen.fill((20, 24, 36))
        title = fonts["huge"].render("SHOP", True, YELLOW)
        screen.blit(title, (20, 20))
        pts = fonts["mid"].render(f"{save_data['points']} Punkte", True, WHITE)
        screen.blit(pts, (W - pts.get_width() - 20, 28))
        level, _, _ = level_from_points(save_data.get("xp", 0))
        lvl = fonts["small"].render(
            f"Level {level} · max Energie {max_energy_for_level(level)}",
            True, HUD_DIM,
        )
        screen.blit(lvl, (W - lvl.get_width() - 20, 58))

        cursor_row = selectable[cur]
        scroll_start = max(0, min(len(items_list) - visible_rows, cursor_row - visible_rows // 2))
        item_rects = []
        row_w = W - 100   # Platz rechts für Touch-Buttons frei lassen
        row_x = 20
        for slot in range(min(visible_rows, len(items_list))):
            i = scroll_start + slot
            if i >= len(items_list):
                break
            kind, data = items_list[i]
            y = list_y0 + slot * row_h
            if kind == "item":
                item_rects.append((i, pygame.Rect(row_x, y - 2, row_w, row_h - 4)))
            if kind == "header":
                lbl = ITEM_TYPE_LABELS.get(data, data).upper()
                t = fonts["mid"].render(lbl, True, CYAN)
                screen.blit(t, (row_x, y + 10))
            else:
                item = data
                owned = item["id"] in save_data["owned"]
                equipped = save_data["equipped"].get(item["type"]) == item["id"]
                sel = (i == cursor_row)
                if sel:
                    pygame.draw.rect(screen, (40, 50, 75), (row_x, y - 2, row_w, row_h - 4), border_radius=6)
                    pygame.draw.rect(screen, BLUE, (row_x, y - 2, row_w, row_h - 4), 2, border_radius=6)
                name_c = WHITE if owned else HUD_TEXT
                if equipped:
                    name_c = GREEN
                if item.get("color") and item["type"] in ("jersey", "helmet"):
                    pygame.draw.rect(screen, item["color"], (row_x + 8, y + 6, 16, 16), border_radius=3)
                    if item.get("secondary"):
                        pygame.draw.rect(screen, item["secondary"], (row_x + 16, y + 8, 6, 12), border_radius=2)
                name = fonts["small"].render(item["name"], True, name_c)
                screen.blit(name, (row_x + 34, y + 4))
                ss = []
                for k, v in item.get("stat", {}).items():
                    if k == "drain_mult":
                        ss.append(f"Verbr ×{v}")
                    elif k == "accel_mult":
                        ss.append(f"Beschl ×{v}")
                    elif k == "max_speed_bonus":
                        ss.append(f"+{v} km/h")
                    elif k == "wind_resist":
                        ss.append(f"Wind -{int(v*100)}%")
                    elif k == "bottles":
                        ss.append(f"{v} Flaschen")
                if ss:
                    s_text = fonts["small"].render(" · ".join(ss), True, HUD_DIM)
                    screen.blit(s_text, (row_x + 34, y + 22))
                if equipped:
                    r = fonts["small"].render("Angelegt", True, GREEN)
                elif owned:
                    r = fonts["small"].render("Anlegen", True, YELLOW)
                else:
                    can = save_data["points"] >= item["cost"]
                    color = YELLOW if can else (140, 80, 80)
                    r = fonts["small"].render(
                        f"{item['cost']} pt" if can else f"{item['cost']} pt!",
                        True, color,
                    )
                screen.blit(r, (row_x + row_w - r.get_width() - 8, y + 14))

        if scroll_start > 0:
            screen.blit(fonts["small"].render("▲", True, HUD_DIM), (W // 2 - 6, list_y0 - 14))
        if scroll_start + visible_rows < len(items_list):
            screen.blit(fonts["small"].render("▼", True, HUD_DIM),
                        (W // 2 - 6, list_y0 + visible_rows * row_h - 2))

        if msg_t > 0:
            t = fonts["mid"].render(msg, True, WHITE)
            screen.blit(t, (W // 2 - t.get_width() // 2, H - 60))

        hint = fonts["small"].render(
            "Tap auf Item · Enter kaufen/anlegen",
            True, HUD_DIM,
        )
        screen.blit(hint, (W // 2 - hint.get_width() // 2, H - 26))

        touch.draw(screen, fonts["mid"])

        pygame.display.flip()
        await asyncio.sleep(0)


async def run_race(screen, route, save_data, fonts):
    clock = pygame.time.Clock()
    theme_data = THEMES.get(route.get("theme", "classic"), THEMES["classic"])
    set_curve_amp_mult(theme_data["curve_mult"])

    preset = difficulty_preset(save_data)
    player = Player(save_data)
    player.stats["drain_mult"] *= preset["drain_mult"]
    opp_count = 50
    # Gegner skalieren mit der Spieler-Ausrüstung: bessere Räder/Rahmen/Helm
    # erhöhen player.max_speed und damit auch das Gegner-Tempo und ihr Cap.
    # Schwierigkeit skaliert das Gegner-Tempo zusätzlich linear.
    gear_bonus = player.stats["max_speed_bonus"]
    base = (34 - route["difficulty"] * 1.0 + gear_bonus * 0.7) * preset["opp_speed_mult"]
    opp_top = (50 + gear_bonus * 0.8) * preset["opp_speed_mult"]
    opponents = [Opponent(random.uniform(15, 110),
                          base + random.uniform(-4, 8),
                          top_speed=opp_top)
                 for _ in range(opp_count)]
    obstacles = []
    bales = []
    goodies = []
    decor = []
    next_obs_d = 50.0
    next_hazard_d = 80.0
    next_goodie_d = 60.0
    next_decor_d = 30.0
    next_spec_d = 25.0
    next_clutter_d = 20.0
    next_bale_t = random.uniform(2.5, 6.0)
    vehicles = []
    next_moto_t = random.uniform(8, 16)
    next_car_t = random.uniform(12, 22)
    heli_active = False
    heli_t = random.uniform(6, 14)
    heli_x = 0.0
    heli_y = 0.0
    heli_vx = 0.0
    spawn_density = route["obstacle_density"] * preset["obstacle_mult"]
    distance_target = route["distance_m"]

    theme_name = route.get("theme", "classic")
    strong_wind = route.get("wind", 0) >= 0.55
    if theme_name in ("mountain", "alpine") and random.random() < 0.45:
        weather = "snow"
    elif random.random() < 0.28:
        weather = "rain"
    else:
        weather = "clear"
    rain_particles, snow_particles, wind_particles = init_weather_particles(weather, strong_wind)
    weather_label = {"rain": "Regen", "snow": "Schnee", "clear": ""}[weather]

    _player_base = make_cyclist_sprite(
        player.stats["jersey_color"],
        player.stats["helmet_color"],
        player.stats["jersey_secondary"],
    )
    player_sprite_frames = (
        pygame.transform.rotate(_player_base, 3),
        pygame.transform.rotate(_player_base, -3),
    )
    obstacle_sprites = {
        "pothole":   make_pothole_sprite(),
        "branch":    make_branch_sprite(),
        "rock":      make_rock_obstacle_sprite(),
        "puddle":    make_puddle_sprite(),
        "snowpatch": make_snowpatch_sprite(),
    }
    haybale_sprite = make_haybale_sprite()
    photo_moto_sprite = make_photo_motorbike_sprite()
    team_car_sprite = make_team_car_sprite()
    heli_shadow_sprite = make_helicopter_shadow_sprite()
    goodie_sprites = {k: make_goodie_sprite(k) for k in ("bottle", "gel", "bar")}
    decor_sprites = make_decor_sprites()

    # KM-Schilder an festen Distanzen vorm Ziel — abhängig davon, wie lang die
    # Strecke wirklich ist, schmeißen wir die kurzen mit rein.
    for m in (500, 400, 300, 200, 100, 50):
        sign_d = distance_target - m
        if sign_d < 25:
            continue
        rc_sign = road_curve(sign_d)
        side = random.choice([-1, 1])
        x = rc_sign + side * (ROAD_WIDTH // 2 + 24)
        key = f"km_{m}"
        if key not in decor_sprites:
            decor_sprites[key] = make_km_sign_sprite(f"{m}m")
        decor.append(Decor(sign_d, x, key))

    # Banner-Gantries über der Strecke: Start, Sponsoren, Flamme Rouge, Ziel.
    # Die werden in decor abgelegt — gleicher Render-Pfad wie alles andere,
    # nur die Sprites sind streckenspezifisch gerendert und werden hier in
    # decor_sprites registriert.
    gantry_specs = [(12.0, "START", (60, 180, 90), "banner")]
    sd = 90.0
    while sd < distance_target - 100:
        name, col = random.choice(SPONSORS)
        gantry_specs.append((sd, name, col, "banner"))
        sd += random.uniform(95, 150)
    fr_d = distance_target - 60 if distance_target > 140 else distance_target * 0.75
    gantry_specs.append((fr_d, "", (210, 30, 30), "flamme"))
    gantry_specs.append((distance_target + 1.0, "ZIEL", (250, 210, 60), "finish"))
    for i, (gd, text, color, kind) in enumerate(gantry_specs):
        key = f"gantry_{i}"
        decor_sprites[key] = make_gantry_sprite(text, color, kind)
        decor.append(Decor(gd, road_curve(gd), key))

    # Streckenspezifisches Landmark kurz vorm Ziel — das markanteste Bauwerk
    # der echten Strecke (Sanremo-Leuchtturm, Torre del Mangia in Siena,
    # Roubaix-Velodrom, etc.). Steht am Straßenrand, damit es nicht den
    # Ziel-Bogen verdeckt.
    lm_factory = ROUTE_LANDMARKS.get(route["id"])
    if lm_factory and distance_target > 80:
        lm_sprite = lm_factory()
        lm_key = f"landmark_{route['id']}"
        decor_sprites[lm_key] = lm_sprite
        lm_d = distance_target - 35
        lm_side = random.choice([-1, 1])
        lm_x = road_curve(lm_d) + lm_side * (ROAD_WIDTH // 2 + lm_sprite.get_width() // 2 + 28)
        decor.append(Decor(lm_d, lm_x, lm_key))

    # Bemaltes Asphalt (Kreide-Tags) alle ~70m mitten auf der Straße.
    paints = []
    paint_cache = {}
    pd = 40.0
    while pd < distance_target - 30:
        text = random.choice(ASPHALT_TAGS)
        if text not in paint_cache:
            paint_cache[text] = make_asphalt_paint_sprite(text)
        rc_p = road_curve(pd)
        paints.append((pd, rc_p + random.uniform(-30, 30), paint_cache[text]))
        pd += random.uniform(55, 130)

    def build_touch():
        # Zurück (post-Finish) und Menü-Knopf sind UI-Affordances und immer
        # sichtbar — Steuerkreuz und TRINK nur, wenn wir wirklich Touch sind.
        menu_w = min(260, W - 40)
        buttons = [
            {"key": "esc",  "rect": pygame.Rect(W - 90, HUD_H + 10, 80, 40),                                "label": "Menü"},
            {"key": "menu", "rect": pygame.Rect(W // 2 - menu_w // 2, int(H * 0.5), menu_w, 70),            "label": "Zurück zum Menü"},
        ]
        if IS_TOUCH:
            btn_h = max(80, min(int(H * 0.13), 140))
            margin = max(8, W // 60)
            gap = max(10, W // 50)
            btn_w = max(96, (W - 2 * margin - 2 * gap) // 3)
            pad_y = H - 16 - btn_h
            drink_h = max(40, int(H * 0.055))
            buttons += [
                {"key": "left",  "rect": pygame.Rect(margin, pad_y, btn_w, btn_h),                          "icon":  "left"},
                {"key": "right", "rect": pygame.Rect(margin + btn_w + gap, pad_y, btn_w, btn_h),            "icon":  "right"},
                {"key": "accel", "rect": pygame.Rect(W - margin - btn_w, pad_y, btn_w, btn_h),              "icon":  "up"},
                {"key": "drink", "rect": pygame.Rect(margin, pad_y - drink_h - 8, W - 2 * margin, drink_h), "label": "TRINK"},
            ]
        return TouchPad(buttons)

    touch = build_touch()

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
        screen, resized = maybe_resize(screen, fonts)
        if resized:
            touch = build_touch()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if IS_WEB:
                    return
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_SPACE and state == "racing":
                    player.drink()
                if event.key == pygame.K_RETURN and state == "finished":
                    return
            touch.handle_event(event)
            tap = event_tap_pos(event)
            if tap is not None:
                # Im Finish-Overlay nur Zurück/Menü zulassen, sonst klaut der
                # darunterliegende TRINK/accel-Button den Klick (vorher musste
                # man oft mehrmals tippen, bis es geklappt hat).
                if state == "finished":
                    key = touch.key_at(tap, only={"menu", "esc"})
                    if key in ("menu", "esc"):
                        return
                else:
                    key = touch.key_at(tap)
                    if key == "esc":
                        return
                    if key == "drink":
                        player.drink()

        keys = pygame.key.get_pressed()
        pressed_touch = touch.pressed_keys() if state == "racing" else set()

        if state == "racing":
            elapsed += dt
            wind_phase += dt * 1.3
            player.update(dt, keys, route, wind_phase, touch=pressed_touch)
            for o in opponents:
                o.update(dt)
            next_obs_d = spawn_obstacles_ahead(player, obstacles, spawn_density, next_obs_d, theme_data)
            if weather == "rain":
                next_hazard_d = spawn_weather_hazards_ahead(player, obstacles, next_hazard_d, "puddle")
            elif weather == "snow":
                next_hazard_d = spawn_weather_hazards_ahead(player, obstacles, next_hazard_d, "snowpatch")
            next_goodie_d = spawn_goodies_ahead(player, goodies, next_goodie_d)
            next_decor_d = spawn_decor_ahead(player, decor, theme_data, next_decor_d)
            # Vor der Ziellinie heizen die Tribünen mehr auf: doppelt so viele
            # Sponsor-Barrieren und Special-Fans.
            hype = 2.2 if (distance_target - player.distance) < 120 else 1.0
            next_spec_d = spawn_spectators_ahead(player, decor, next_spec_d, hype=hype)
            next_clutter_d = spawn_clutter_ahead(player, decor, theme_data, next_clutter_d)
            if strong_wind:
                next_bale_t -= dt
                if next_bale_t <= 0:
                    speed_mps = max(7.0, player.speed / 3.6)
                    lead_t = random.uniform(2.0, 3.0)
                    bd = player.distance + speed_mps * lead_t
                    rc = road_curve(bd)
                    side = random.choice([-1, 1])
                    start_x = rc + side * (ROAD_WIDTH // 2 + 70)
                    end_x = rc - side * (ROAD_WIDTH // 2 + 70)
                    duration = lead_t * 2.0
                    bales.append(HayBale(bd, start_x, end_x, duration))
                    next_bale_t = random.uniform(4.5, 9.0)
            for b in bales:
                b.update(dt)
            for v in vehicles:
                v.update(dt)
            # Foto-Motorrad: kommt von hinten und überholt schneller als der Spieler.
            next_moto_t -= dt
            if next_moto_t <= 0:
                next_moto_t = random.uniform(14, 28)
                side = random.choice([-1, 1])
                offset = side * (ROAD_WIDTH // 2 - 14)
                vehicles.append(Vehicle(
                    distance=player.distance - 28,
                    lane_offset=offset,
                    speed_kmh=max(player.speed + random.uniform(6, 12), 38),
                    sprite=photo_moto_sprite,
                ))
            # Teamwagen: hängt knapp hinterm Pulk, etwas langsamer.
            next_car_t -= dt
            if next_car_t <= 0:
                next_car_t = random.uniform(18, 35)
                side = random.choice([-1, 1])
                offset = side * (ROAD_WIDTH // 2 - 18)
                vehicles.append(Vehicle(
                    distance=player.distance - 40,
                    lane_offset=offset,
                    speed_kmh=max(player.speed - random.uniform(2, 6), 26),
                    sprite=team_car_sprite,
                ))
            # Heli-Schatten driftet quer über den Bildschirm. Außerhalb des
            # Renn-Geschehens, also reine Screen-Animation.
            if heli_active:
                heli_x += heli_vx * dt
                if heli_x < -200 or heli_x > W + 200:
                    heli_active = False
                    heli_t = random.uniform(12, 28)
            else:
                heli_t -= dt
                if heli_t <= 0:
                    heli_active = True
                    side = random.choice([-1, 1])
                    heli_x = -150.0 if side == 1 else float(W + 150)
                    heli_vx = (90 if side == 1 else -90) * random.uniform(0.9, 1.4)
                    heli_y = float(HUD_H + 30 + random.uniform(0, max(40, H * 0.35)))
            update_weather_particles(rain_particles, snow_particles, wind_particles, dt)
            check_collisions(player, obstacles)
            check_haybales(player, bales)
            picked = check_goodies(player, goodies)
            if picked:
                recent_pickup = picked[-1]
                recent_pickup_t = 1.5
            # Sichtbar bis sie unten aus dem Bild fallen. Spieler sitzt bei
            # PLAYER_Y, die Welt rollt nach unten — also (H - PLAYER_Y) / PX_PER_M
            # Meter passen unter den Spieler. Plus etwas Reserve für hohe Sprites.
            cull_behind = (H - PLAYER_Y) / PX_PER_M + 4
            obstacles[:] = [o for o in obstacles if o.distance > player.distance - cull_behind]
            goodies[:] = [g for g in goodies
                          if not g.collected and g.distance > player.distance - cull_behind]
            decor[:] = [d for d in decor if d.distance > player.distance - cull_behind]
            bales[:] = [b for b in bales if b.alive and b.distance > player.distance - cull_behind]
            paints[:] = [p for p in paints if p[0] > player.distance - cull_behind]
            vehicles[:] = [v for v in vehicles
                           if -cull_behind < (v.distance - player.distance) < 140]
            if player.distance >= distance_target:
                state = "finished"
                final_position = player_position(player, opponents)
                final_time = elapsed
                total = len(opponents) + 1
                # Prozentrang statt linearer Skala mit Gegnerzahl, sonst
                # geben 50 Gegner viel zu viele Punkte. Steile Kurve, damit
                # Mid-Pack deutlich weniger als ein Sieg gibt.
                pct = (total - final_position) / max(1, total - 1)
                base = 50 + route["difficulty"] * 22
                awarded = max(5, int(pct ** 1.4 * base))
                save_data["points"] = save_data.get("points", 0) + awarded
                save_data["xp"] = save_data.get("xp", 0) + awarded
                save_data["races"] = save_data.get("races", 0) + 1
                best = save_data.setdefault("best", {})
                rid = route["id"]
                if rid not in best or final_position < best[rid]:
                    best[rid] = final_position
                new_lvl, _, _ = level_from_points(save_data["xp"])
                if new_lvl > prev_level:
                    level_up = True
                save_state(save_data)

        recent_pickup_t = max(0.0, recent_pickup_t - dt)

        draw_road(screen, player, theme_data)
        # Heli-Schatten direkt aufm Asphalt — unter allem anderen.
        if heli_active:
            screen.blit(heli_shadow_sprite,
                        (int(heli_x) - heli_shadow_sprite.get_width() // 2,
                         int(heli_y) - heli_shadow_sprite.get_height() // 2))
        # Asphalt-Tags zuerst — gehören direkt auf den Belag.
        for pdist, px, pspr in paints:
            draw_world_obj(screen, pdist, px, pspr, player)
        anim_t = pygame.time.get_ticks() / 220.0
        for d in sorted(decor, key=lambda x: x.distance, reverse=True):
            if d.kind.startswith("spec_"):
                frame = "_up" if (math.sin(anim_t + d.distance * 0.7) > 0) else "_dn"
                spr = decor_sprites[d.kind + frame]
            else:
                spr = decor_sprites[d.kind]
            draw_world_obj(screen, d.distance, d.world_x, spr, player)
        # Begleitfahrzeuge zwischen Pulk-Deko und Gegnern, damit sie nicht von
        # einer Trommler-Gruppe am Rand überlagert werden, aber Gegner-Trikots
        # weiter sichtbar bleiben.
        for v in sorted(vehicles, key=lambda x: x.distance):
            draw_world_obj(screen, v.distance, v.world_x, v.sprite, player)
        for o in sorted(opponents, key=lambda x: x.distance):
            s = math.sin(o.pedal_phase)
            frame = o.sprite_frames[0] if s > 0 else o.sprite_frames[1]
            draw_world_obj(screen, o.distance, o.world_x, frame, player,
                           y_jitter=s * 1.5)
        for o in obstacles:
            draw_world_obj(screen, o.distance, o.world_x, obstacle_sprites[o.kind], player)
        for g in goodies:
            if not g.collected:
                bob = math.sin(pygame.time.get_ticks() / 200 + g.distance) * 2
                draw_world_obj(screen, g.distance, g.world_x, goodie_sprites[g.kind],
                               player, y_jitter=bob)
        for b in bales:
            rotated = pygame.transform.rotate(haybale_sprite, math.degrees(b.spin))
            draw_world_obj(screen, b.distance, b.world_x, rotated, player)
        draw_finish_line(screen, player, distance_target)
        draw_player(screen, player, player_sprite_frames)
        draw_weather_particles(screen, rain_particles, snow_particles, wind_particles)

        pos = player_position(player, opponents)
        remaining = max(0, distance_target - player.distance)
        rp = (recent_pickup, recent_pickup_t) if recent_pickup else None
        draw_hud(screen, player, pos, len(opponents) + 1, remaining, distance_target,
                 fonts, route, rp, weather_label=weather_label, strong_wind=strong_wind)

        if state == "racing":
            touch.draw(screen, fonts["mid"],
                       only={"left", "right", "accel", "drink", "esc"})

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
            new_lvl, xp, need = level_from_points(save_data["xp"])
            lvl = fonts["small"].render(f"Level {new_lvl} · {xp}/{need} XP", True, HUD_DIM)
            screen.blit(lvl, (W // 2 - lvl.get_width() // 2, 290))
            if level_up:
                lup = fonts["mid"].render(f"LEVEL UP! Max-Energie jetzt {max_energy_for_level(new_lvl)}", True, GREEN)
                screen.blit(lup, (W // 2 - lup.get_width() // 2, 322))
            hint = fonts["small"].render("Enter / Tap: zurück zum Menü", True, HUD_DIM)
            screen.blit(hint, (W // 2 - hint.get_width() // 2, 380))
            touch.draw(screen, fonts["mid"], only={"menu"})

        pygame.display.flip()
        await asyncio.sleep(0)


async def main():
    pygame.init()
    pygame.display.set_caption("Radgame")
    pygame.display.set_mode((W, H), _display_flags())
    fonts = make_fonts()
    while True:
        save_data = load_save()
        # get_surface() liefert die aktuelle Display-Surface, auch nach Resize.
        screen = pygame.display.get_surface()
        choice = await run_menu(screen, save_data, fonts)
        if choice is None:
            break
        kind, payload = choice
        screen = pygame.display.get_surface()
        if kind == "shop":
            await run_shop(screen, save_data, fonts)
        elif kind == "race":
            await run_race(screen, payload, save_data, fonts)
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
