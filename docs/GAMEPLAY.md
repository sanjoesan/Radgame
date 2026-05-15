# Gameplay-Mechaniken

Stand: MVP. Werte siehe Konstanten oben in `main.py`.

## Geschwindigkeit

- Spielbare Range: `MIN_SPEED=8` … `MAX_SPEED=58` km/h.
- Player hat `speed` (aktuell) und `target_speed` (anvisiert). `speed` nähert sich `target_speed` mit einem leichten Lag (~ ein paar Zehntel Sekunden), das gibt Trägheit.
- Ohne Input zerfällt `target_speed` Richtung 24 km/h (rollendes Tempo).
- Bei Energie ≤ 0 wird `target_speed` auf maximal 14 km/h gecappt — Erschöpfung.

## Energie

- Max `MAX_ENERGY=100`, Drain pro Sekunde:
  ```
  drain = 0.35 + max(0, (speed - 22) / 18)^2 * 3.4
  drain *= 1 + heat * 0.6
  ```
- Bei 22 km/h: ~0.35 Energie/s, ohne Hitze. Reicht ewig.
- Bei 50 km/h: ~5 Energie/s. 100 Energie verbraucht in ~20 s.
- Hitze multipliziert nochmal: Mont Ventoux (heat 0.8) → +48 %.

## Wasser

- 3 Flaschen zu Beginn. Eine Leertaste = +32 Energie, –1 Flasche.
- Energie wird auf max 100 gecappt; trinken ohne Bedarf wird ignoriert (Flasche bleibt voll).

## Lenken & Wind

- Player lenkt mit `±230 px/s` auf der Straße.
- Wind (`route.wind` 0..1) erzeugt sinusförmige Seitendrift, die der Fahrer durch Gegenlenken ausgleichen muss. Bei `wind ≥ 0.5` deutlich spürbar.

## Hindernisse

Zwei Typen, zufällig auf der Strecke vorgelagert (`spawn_obstacles_ahead`):

| Typ        | Effekt bei Kontakt                                |
|------------|---------------------------------------------------|
| Schlagloch | `target_speed *= 0.45`, `speed *= 0.55`, –3 Energie, 0.5 s Erholzeit |
| Ast        | `target_speed *= 0.75`, `speed *= 0.8`, –8 Energie, 0.3 s Erholzeit  |

Spawn-Dichte hängt vom Route-Feld `obstacle_density` ab. 1.0 = normal; Paris-Roubaix hat 1.6 (Kopfsteinpflaster simuliert als viele kleine Hindernisse).

## Gegner

- Pro Rennen `route.opponents` KI-Fahrer (3–7).
- Jeder hat `target_speed` mit kleinem Random-Walk (`gauss(0, 1.5)` pro Sekunde).
- Speed-Bereich pro Gegner: 16…46 km/h.
- Jeder hat eine zufällige Trikot-/Helmfarbe.
- Position des Spielers = Anzahl Gegner, deren `distance` höher ist, +1.

## Punktevergabe

Nach jedem Rennen:

```
total = opponents + 1
platzierung = max(0, (total - position + 1) * 22)
schwierigkeit = difficulty * 18
punkte = platzierung + schwierigkeit
```

- Sieg bei 8 Fahrern, ★5 Strecke: `8*22 + 5*18 = 266`.
- Letzter Platz, ★1: `1*22 + 1*18 = 40` (Trostpreis fürs Fertigfahren).

## Zielgerade

Wenn der Player weniger als 30 m vom Ziel entfernt ist, wird ein Schachbrett-Banner gezeichnet, das mit der Welt heranscrollt.

## Was noch nicht da ist (Stand jetzt)

- Oberflächen-Effekte: Cobbles (Vibration), Gravel (Driften) — Daten in Route gibt's, Mechanik noch nicht.
- Upgrades: Punkte werden gespart, aber es gibt noch keinen Shop.
- Wind als gerichtetes Phänomen (immer nur Seitenwind, kein Rückenwind/Gegenwind).
- Höhenprofil: Strecken haben keinen Anstieg/Abfahrt-Effekt auf Speed.

Siehe [ROADMAP.md](ROADMAP.md).
