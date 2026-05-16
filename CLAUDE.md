# CLAUDE.md

Kontext für Claude Code, wenn an diesem Repo weitergearbeitet wird.

## Was das ist

Radgame ist ein Top-Down-Pixel-Art-Rennradspiel in Python/Pygame. Single-Player. Vom Noob zum Sieger über mehrere echte Strecken (Tour, Giro, Vuelta, Monumente). Geschrieben am 15. Mai 2026 als zweites Projekt nach `Radplaner` (siehe `~/Projekte/Radplaner`).

## Befehle

```bash
./run.sh                            # startet das Spiel (venv wird ggf. angelegt)
.venv/bin/python -m py_compile main.py routes.py   # Syntax-Check (es gibt keine echten Tests)
.venv/bin/pip install -r requirements.txt           # Deps neu
```

Es gibt keine Lint- oder Test-Suite. Pygame-Apps laufen sinnvoll nur in einer grafischen Umgebung — im Headless-Container kann man nur Syntax/Import prüfen, nicht den Game-Loop.

## Architektur (Kurz)

Single-File Game-Loop (`main.py`) plus Daten-Datei `routes.py`.

- `main.py` enthält: Player, Opponent, Obstacle, Render-Funktionen, Menu-Scene, Race-Scene, Main-Loop.
- `routes.py` definiert die `ROUTES`-Liste — Strecken sind reine Daten, kein Code.
- `save.json` (gitignored) wird im Repo-Root angelegt für Punkte / Bestplatzierungen.

Mehr Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Design-Prinzipien

- **Eine Datei zuerst.** `main.py` darf wachsen, bevor wir in Module aufteilen. Erst zerlegen, wenn etwas konkret weh tut.
- **Daten von Code trennen.** Neue Strecken sind ein Eintrag in `routes.py`, keine Code-Änderung.
- **Pixel-Sprites programmatisch.** Sprites werden zur Laufzeit aus `pygame.draw`-Rects gebaut. Das ist kein Dauerzustand — sobald wir richtige PNG-Sprites haben, ersetzen wir das.
- **Distanzen sind game-balanced**, nicht real. Ein Spiel-Rennen dauert 1–3 Minuten, nicht 4 Stunden. Reale Längen stehen in `real_distance_km` nur als Flavor.

## Conventions

- **Keine Type-Hints außer wo sie aufklären.** Pygame-Code ist meistens klar genug.
- **`dt`-basierte Bewegung überall.** Niemals fix pro Frame inkrementieren. Frame-Cap ist 60 FPS plus Clamp bei `dt > 1/20`, damit ein Lag-Spike nicht durch Hindernisse springt.
- **deutsche Strings in der UI**, englische im Code. Var-Namen englisch.
- **`VERSION` bei JEDEM `git push` hochzählen.** Konstante steht oben in `main.py` (`VERSION = "v1"`), wird unten rechts im Hauptmenü angezeigt. So sieht der User sofort, ob im Browser noch eine alte gecachte Version läuft. Schema: einfacher Zähler `v1`, `v2`, ... — vor jedem Push den Wert inkrementieren, im Commit mitnehmen.

## Was du wahrscheinlich tun wirst

Typische Aufgaben:

- **Neue Strecke ergänzen:** `routes.py` editieren. Schema siehe [docs/ROUTES.md](docs/ROUTES.md).
- **Mechanik anpassen** (Speed, Energie, Wasser, Hindernis-Wirkung): Konstanten oben in `main.py` und die `Player.update`-Methode.
- **Visuals tunen:** `make_*_sprite`-Funktionen, `draw_road`, `draw_hud`.
- **Upgrade-System bauen:** noch nicht da, siehe [docs/ROADMAP.md](docs/ROADMAP.md).

## Was du nicht tun solltest

- **Keine separate Engine.** Pygame ist genug.
- **Kein OOP-Overkill.** Aktuell drei Klassen (Player, Opponent, Obstacle) — das passt. Manager-Klassen-für-alles nicht.
- **Kein async / threading.** Game-Loop ist synchron.
- **Keine externen Assets ohne Rückfrage.** Wenn echte Sprites/Sounds rein sollen, dem User vorher sagen, was wo gespeichert wird.

## Verwandte Repos

- `~/Projekte/Radplaner` — der Wetter-basierte Trainingsplaner, der vorher mit demselben User gebaut wurde. Anderes Projekt, aber gleiche Ästhetik / gleicher Code-Stil-Wunsch.
