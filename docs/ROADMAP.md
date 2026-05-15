# Roadmap

Aktueller Stand: MVP. Spielbar, ein Rennen pro Sitzung, 15 Strecken, Punkte werden gespeichert.

## Done (Stand 2026-05-15)

- [x] Pygame-Setup, venv-Bootstrap-Script
- [x] Top-Down-Spielfeld mit scrollender Straße
- [x] Player mit Geschwindigkeits-/Energie-/Wasser-Mechanik
- [x] Hindernisse (Schlagloch, Ast) mit unterschiedlichen Effekten
- [x] KI-Gegner mit zufälliger Geschwindigkeit
- [x] Live-Platzierung
- [x] Punkte- und Bestplatzierungs-Persistenz (`save.json`)
- [x] Menü mit Streckenwahl + Scrolling
- [x] 15 echte Strecken (Monumente, Grand-Tour-Etappen)
- [x] Doku (README, CLAUDE.md, ARCHITECTURE, GAMEPLAY, ROUTES, ROADMAP)

## Als Nächstes (kurzfristig)

- [ ] **Oberflächen-Effekte:** Cobbles → konstantes leichtes Rütteln (sideways jitter + minimaler Speed-Verlust), Gravel → größerer Lenk-Slip.
- [ ] **Höhenprofil:** pro Strecke ein Profil [(distance_m, gradient_pct), …]. Bergauf kostet mehr Energie, bergab gibt Speed.
- [ ] **Animierte Beine/Räder** am Player-Sprite, sodass man Geschwindigkeit auch visuell wahrnimmt.
- [ ] **Sound:** Wind, Reifen, Trinken, Crash. Schon allein das macht enorm viel aus.
- [ ] **Pausen-Menü** (Esc während Rennen → resume/quit).

## Mittelfristig

- [ ] **Upgrade-Shop:** zwischen Rennen Punkte ausgeben für:
  - Rad: leichterer Rahmen (höhere Top-Speed), bessere Reifen (weniger Energieverlust bei Hindernissen)
  - Bekleidung: Aero-Trikot (weniger Wind), helles Jersey (weniger Hitze-Drain)
  - Trinkflaschenhalter (4. oder 5. Flasche)
- [ ] **Wetter ist je Rennen variabel** (regnerisch → mehr Hindernisse, kalt → kein Hitze-Drain).
- [ ] **Karriere-Modus:** Strecken stufenweise freischalten (z. B. erst Garsten, dann Monumente, dann Grand Tours).
- [ ] **Mehrere Wertungen:** Tagessieg, Bergwertung, Punkte-Trikot.

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
