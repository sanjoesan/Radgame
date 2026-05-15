# Architektur

Stand: MVP, Single-File-Game-Loop.

## Verzeichnis

```
Radgame/
├── main.py             # Game-Loop, Klassen, Render, Scenes (Menu + Race)
├── routes.py           # Streckendaten (reine Liste von Dicts)
├── requirements.txt    # pygame
├── run.sh              # venv bootstrap + Start
├── save.json           # Persistenz (gitignored, wird zur Laufzeit angelegt)
├── README.md
├── CLAUDE.md
└── docs/
    ├── ARCHITECTURE.md (dieses File)
    ├── GAMEPLAY.md
    ├── ROADMAP.md
    └── ROUTES.md
```

## Aufbau von `main.py`

Reihenfolge im File:

1. **Konstanten** — Auflösung, Farben, Streckenfeld, Speed-/Energie-Parameter.
2. **Save-Helpers** — `load_save()` / `save_state()`.
3. **Sprite-Bauer** — `make_cyclist_sprite()`, `make_pothole_sprite()`, `make_branch_sprite()`. Produzieren `pygame.Surface`-Objekte aus `draw.rect` und `draw.ellipse`.
4. **Klassen:** `Player`, `Opponent`, `Obstacle`.
5. **Hilfsfunktionen:** `player_position()`, `spawn_obstacles_ahead()`, `check_collisions()`.
6. **Render-Funktionen:** `draw_road()`, `draw_finish_line()`, `draw_obstacle()`, `draw_player()`, `draw_hud()`.
7. **Scenes:** `run_menu()`, `run_race()`.
8. **`main()`** — initialisiert Pygame, lädt Save, schaltet zwischen Menu und Race.

## Welt-Modell

Die Welt ist 1D entlang der Streckenrichtung:

- `player.distance` und `opponent.distance` sind reale Meter entlang der Route.
- Obstacles haben `distance` und `x` (Pixel-Spalte auf der Straße).
- Render: alles wird relativ zum Player gezeichnet, der visuell auf `PLAYER_Y` fixiert ist. Die Welt rollt unter ihm durch.
- Die Bildschirm-Y-Koordinate eines Welt-Punkts ist `PLAYER_Y - (distance - player.distance) * PX_PER_M`.

`PX_PER_M = 25` bedeutet 25 Bildschirm-Pixel pro Meter. Bei 30 km/h scrollt die Welt mit ~208 px/s.

## Game-Loop

```text
clock.tick(60)  → dt in Sekunden
events:
    QUIT     → exit
    KEYDOWN  → Drink / Restart / Menu
keys.pressed → Bewegung
update():
    player.update(dt, keys, route, wind_phase)
    for o in opponents: o.update(dt)
    spawn_obstacles_ahead()
    check_collisions()
    cull obstacles behind player
    distance >= target → finished, points award, save
render():
    draw_road
    draw_opponents (sorted by distance, back-to-front)
    draw_obstacles
    draw_finish_line (wenn nah)
    draw_player (mit flash bei crash)
    draw_hud
    overlay if finished
pygame.display.flip()
```

## Persistenz

`save.json` Struktur:

```json
{
  "points": 0,
  "races": 0,
  "best": { "ventoux": 3, "alpedhuez": 2 }
}
```

`best` ist Mapping route_id → bester (= niedrigster) Platz, der je erreicht wurde.

Punkte werden nach jedem Rennen vergeben:
`punkte = max(0, (total - position + 1) * 22) + difficulty * 18`

Beispiel: Bei 7 Gegnern (= 8 Fahrer) und Platz 1 auf Stelvio (★5): `8*22 + 5*18 = 176 + 90 = 266`.

## Was bewusst nicht in `main.py` ist

- Strecken-Daten → `routes.py`. Sonst müsste man Code anpacken für jede neue Route.
- Streckenspezifische Mechaniken wie Cobblestones (Vibration) → noch nicht implementiert; werden über das `surface`-Feld in der Route künftig in `Player.update` einfließen.

## Nächste sinnvolle Refactorings (wenn nötig)

Erst wenn `main.py` schmerzt. Mögliche Schnitte:

- `sprites.py` — alle `make_*_sprite`-Funktionen
- `render.py` — `draw_*`-Funktionen
- `game.py` — Klassen + Loop
- `menu.py` — Menu-Scene
- `save.py` — Persistenz

Aktuell: nicht nötig.
