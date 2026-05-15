# Roadmap

Aktueller Stand: MVP. Spielbar, ein Rennen pro Sitzung, 15 Strecken, Punkte werden gespeichert.

## Done

**v0.1 (MVP, 2026-05-15)**
- Pygame-Setup, venv-Bootstrap, Punkte-/Best-Persistenz
- Top-Down-Spielfeld mit scrollender (gerader) Straße
- Player mit Speed/Energie/Wasser, Hindernisse, KI-Gegner, Platzierung
- 14 echte Strecken (Monumente, Grand-Tour-Etappen)
- Doku-Set

**v0.2 (GodMode, 2026-05-15)**
- [x] Kurven (`road_curve()` mit drei Sinus-Layern)
- [x] Schmälere Straße (220 px) für mehr Pulks im Feld
- [x] Mindestens 10 Gegner pro Rennen
- [x] Goodies (Flasche, Gel, Riegel) zum Aufsammeln
- [x] Passive Energie-Regeneration im Coasting
- [x] Level-System mit wachsendem max-Energy-Pool
- [x] Shop mit Trikots, Helmen, Rädern, Rahmen und Flaschenoptionen — multiplikative + additive Stat-Modifikatoren
- [x] Wiese / Off-Road-Penalty
- [x] „Heimrunde Garsten" entfernt — Spiel startet direkt bei den großen Klassikern

## Als Nächstes (kurzfristig)

- [ ] **Oberflächen-Effekte:** Cobbles → leichtes Rütteln + Speed-Verlust, Gravel → Lenk-Slip.
- [ ] **Höhenprofil:** pro Strecke ein Profil [(distance_m, gradient_pct), …]. Bergauf kostet mehr Energie, bergab Speed-Bonus.
- [ ] **Animation** am Player-Sprite (Speichen-Blur, Pedal-Phase) für Geschwindigkeitsgefühl.
- [ ] **Sound:** Wind, Reifen, Trinken, Crash, Goodie-Pickup.
- [ ] **Pausen-Menü** (Esc → resume/quit statt direkt zurück).
- [ ] **Goodies feinjustieren:** noch sind sie sehr generös; ggf. an Strecken-Hitze koppeln.

## Mittelfristig

- [ ] **Wetter je Rennen variabel** (Regen → mehr Hindernisse, Kälte → kein Hitze-Drain, aber Eis-Risiko).
- [ ] **Karriere-Modus:** Strecken stufenweise freischalten, Saisonstruktur.
- [ ] **Mehrere Wertungen:** Tagessieg, Bergwertung, Punkte-Trikot.
- [ ] **Live-Gegner-Anzeige am Streckenrand** (mini-Tabelle mit nächsten Verfolgern/Vorderen).
- [ ] **Mehr Upgrades:** Schaltgruppe, Pedale, Lenker (jeweils mit eigenem Stat-Profil).

## Langfristig

- [ ] **Echte Pixel-Art-Sprites** statt programmatischer Rects. Eventuell vom User-Asset analog zu Radplaner-Biker.
- [ ] **Mehrtages-Etappen-Rennen:** Tour de France als 5–8 verkürzte Etappen mit Gesamtwertung.
- [ ] **Teammitglieder:** Helfer im Windschatten (saugen Wind ab).
- [ ] **Online-Bestenliste** (separates Backend).

## Bekannte Schwächen / Tech-Debt

- Sprites sind extrem simpel (Rects). Sieht "ok" aus, aber nicht "wow". Echte Sprites sind ein großer Hebel.
- `main.py` ~480 Zeilen. Bei Verdopplung sollte aufgeteilt werden (siehe ARCHITECTURE.md → Refactorings).
- Wind ist nur sinusförmiger Drift, kein gerichtetes Phänomen. Real wäre Rückenwind = leichter, Gegenwind = härter.
- Keine Tests. Bei mehr Mechanik-Komplexität sollten zumindest die Formeln (Energie-Drain, Punktevergabe) Property-getestet werden.
- Frame-Rate-Cap auf 60 FPS hardgecoded. Sollte konfigurierbar werden, falls jemand auf 120-Hz-Display spielt.
