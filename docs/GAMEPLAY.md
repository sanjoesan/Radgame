# Gameplay-Mechaniken

Stand: nach „GodMode"-Update. Werte stehen als Konstanten oben in `main.py`.

## Strecke

- **Breite:** `ROAD_WIDTH = 220` Pixel. Schmal genug, dass man auf 10+ Gegnern richtig drum kämpft.
- **Kurven:** `road_curve(distance)` ist eine Überlagerung von drei Sinus-Schwingungen (große, mittlere und enge Schwünge). Die Straßen-Mittellinie schlängelt sich also durch die Welt.
- Die Spielfigur ist auf dem Bildschirm fixiert in der Mitte. Die Welt wandert unter ihr durch. Steht man zu weit vom Road-Center, ist man auf der Wiese.
- **Wiese:** `target_speed` wird auf 24 km/h gecappt und nochmal mit Faktor `(1 − 0.6·dt)` runtergedrückt. Ein paar Sekunden Wiese vernichten Position.

## Geschwindigkeit

- `MIN_SPEED=8` … `MAX_SPEED_BASE=56` km/h (plus Frame-/Rad-Bonus).
- Player hat `speed` und `target_speed`. Smoothing-Faktor 2.8 → halb so langsam wie Echtzeit.
- Ohne Input zerfällt `target_speed` Richtung 24 km/h.
- Bei Energie ≤ 0 ist `target_speed` auf 14 km/h gedeckelt.

## Energie

- Maximum: `BASE_MAX_ENERGY = 100`, plus `(level - 1) * 8` durch Aufstieg.
- Drain pro Sekunde:
  ```
  drain = 0.30 + max(0, (speed - 22) / 18)^2 * 3.0
  drain *= 1 + heat * 0.6
  drain *= drain_mult (Equipment)
  ```
- **Passive Regeneration:** wenn nicht beschleunigt wird und nicht auf der Wiese:
  ```
  regen = 1.6 * max(0.1, 1 - speed/50)
  ```
  Bei niedriger Geschwindigkeit füllt sich also langsam wieder auf. Bei Vollgas regeneriert nichts.

## Wasser

- `WATER_BOTTLES_BASE = 3`, plus Bottle-Item-Upgrade (4 oder 5).
- Leertaste = 1 Flasche × `DRINK_AMOUNT = 32` Energie. Nur, wenn nicht voll.

## Goodies (Pickups)

Spawnen mit 55–130 m Abstand am Straßenrand:

| Typ      | Effekt                                          |
|----------|-------------------------------------------------|
| 💧 Flasche | +1 Trinkflasche (gecappt am Max)              |
| 🍯 Gel    | +30 Energie sofort                              |
| 🍫 Riegel | +15 Energie, +3 km/h Speed-Boost                |

## Lenken & Wind

- Lenken `±240 px/s`.
- Wind erzeugt sinusförmige Seitendrift, deren Stärke mit `route.wind` * (1 − wind_resist) skaliert. Aero-Helm/-Rahmen helfen.

## Hindernisse

| Typ        | Effekt                                          |
|------------|-------------------------------------------------|
| Schlagloch | `target_speed *= 0.45`, –3 Energie, 0.5 s Schock |
| Ast        | `target_speed *= 0.75`, –8 Energie, 0.3 s Schock |

Spawn-Dichte per `route.obstacle_density`.

## Gegner

- Mindestens 10 pro Rennen (Setting per Route, mit Floor von 10).
- Jeder hat persönliche Lane-Preference (Offset von Mittellinie) und Speed-Bereich 16…48 km/h.
- AI strebt zur (road_center + lane_pref), wobbelt leicht.
- Position des Spielers = (Gegner mit größerer Distanz) + 1.

## Punktevergabe

```
total = opponents + 1                               # mind. 11
placement = max(0, (total - position + 1) * 18)
diff_bonus = difficulty * 22
punkte = placement + diff_bonus
```

Beispiel: Sieg bei 11 Fahrern (10 Gegner), Stelvio ★5 → 11*18 + 5*22 = 198 + 110 = **308 Punkte**.

## Level

```
Level 1: 0–199    (200 XP)
Level 2: 200–499  (300 XP)
Level 3: 500–899  (400 XP)
Level 4: 900–1399 (500 XP)
Level 5: 1400+    (600 XP)
…
```

Pro Level: `+8` max Energie. Lvl 10 = 172 max Energie.

## Shop

Aufrufbar als oberster Eintrag im Hauptmenü. Items in 5 Kategorien:

- **Trikot:** Optik (Klassik Rot, Sky Blau, Bergtrikot, Maillot Jaune, Maglia Rosa, Regenbogen)
- **Helm:** Standard / Aero (wind_resist 0.3) / TT-Helm (wind_resist 0.5, +2 km/h)
- **Räder:** Standard / Carbon (drain ×0.88, accel ×1.1) / Aero (drain ×0.92, +4 km/h)
- **Rahmen:** Alu / Carbon (drain ×0.92, +3 km/h) / Climber (accel ×1.25, drain ×0.9) / Aero (+7 km/h, wind_resist 0.2)
- **Flaschen:** 3 (default) / 4 (260 pt) / 5 (520 pt)

Equipped-Items werden multiplikativ verrechnet (drain/accel) bzw. addiert (speed_bonus/wind_resist). Sehr fettes Setup ist erreichbar, aber nicht in einer Stunde — Level- und Punkte-Grind nötig.

## Tuning-Stellschrauben

In `main.py`:

- `ROAD_WIDTH` — Straßenbreite
- `road_curve()` — Kurven-Intensität
- `STEER_SPEED` — Lenk-Reaktivität
- `MAX_SPEED_BASE`, `BASE_MAX_ENERGY`
- Goodie-Spawn-Gap (55–130 m)
- Hindernis-Spawn-Gap (14–32 m / density)
- Drain-Formel
- Punkteformel und Level-Threshold (`level_from_points`)
