# Changelog

Die `VERSION`-Konstante in `main.py` zeigt den aktuellen Build unten rechts im Hauptmenü. Schema: einfacher Zähler `v1`, `v2`, … — bei jedem `git push` hochzählen.

## v21 — 2026-05-16

Mobile, UX, Web-Deploy:

- HUD nach oben verschoben (Finger verdecken sonst die Werte am Smartphone)
- Distanz als cyaner Fortschrittsbalken statt Meter-Text
- Zurück-Button-Tap-Bug gefixt (`TouchPad.key_at(only=…)` gegen den TRINK-Button-Klau)
- Resize-Handling pro Frame (Browser-Viewport, Reload, Rotation)
- Touch-Steuerkreuz nur auf echten Touch-Geräten (`navigator.maxTouchPoints`)
- Mobile-Squeeze gefixt: pygbag-Framebuffer auf Viewport-Aspect umgestellt via `tools/patch_pygbag_index.py`, `100vh`-Falle behoben
- ESC im Hauptmenü zeigt keine graue Seite mehr
- Cull-Margin korrigiert (Objekte bleiben sichtbar bis zum unteren Bildrand)
- Fehlende Unicode-Glyphen (←→↑↓▲▼) durch ASCII-Worte und `pygame.draw.polygon`-Dreiecke ersetzt

Menü und Persistenz:

- Schwierigkeit (Leicht/Mittel/Schwer) als Menü-Item, persistiert in `save.json`
- Musik An/Aus, SFX An/Aus, Lautstärke Leise/Mittel/Laut — drei separate, persistierte Toggles
- „Best P{n}" klar gelabelt
- Versionsnummer unten rechts im Menü, bei jedem Push hochgezählt — siehst sofort, ob der Browser noch eine alte Version aus dem Cache hat

Spielwelt — Renn-Atmosphäre (6 Phasen):

1. **Banner-Gantries** quer über die Strecke (Start, Sponsoren CIAO/VELO+/PEDALE/…, Flamme Rouge mit rotem Kite, Karo-ZIEL), KM-Schilder am Rand, Sponsor-Barrieren, El Diablo + Trommler als Special-Spectators, bemalte Asphalt-Tags (ALLEZ/VIVA/DAJE)
2. **Begleitfahrzeuge**: Foto-Motorrad (überholt von unten) und Teamwagen in 8 Team-Farben (wandert von oben rein) mit echten Fahrrad-Silhouetten längs am Dach
3. **Helikopter-Schatten** mit Rotor-Scheibe, Heckausleger, Heckrotor — flippt nach Flugrichtung
4. **Theme-Decor pro Strecke**: Strandhütten, belgische Flaggen + Frittenbude + Backsteinkirche, Zypressen + Sonnenblumen + Steinhaus, Tornante-Schilder + Bergziegen, Skilift + Chalet, alte Steinmauer
5. **14 Route-Landmarks** kurz vorm Ziel: Sanremo-Leuchtturm, Torre del Mangia, Kapellemuur, Roubaix-Velodrom, Ardennen-Burg, Mont-Ventoux-Observatorium, Tour-Bogen, Alpe-21-Schild, Giro-Bogen, Steigungsschild, Madonna del Ghisallo
6. **Peloton-Trikots** je nach Rennserie: Maillot Jaune / Maglia Rosa / Maillot Rojo / Regenbogen

Finale-Polish:

- Flamme-Rouge-Zone: 3-reihiger Zuschauer-Wall + Sponsor-Barrieren alle 6–10 m
- Konfetti-Burst beim Zieleinlauf aus 3 Quellen (links/rechts/Mitte) mit Schwerkraft + Drift + 1.2 s Nachschuss-Bursts
- Heuballen rund statt zitronen-oval (konzentrische Wicklung + Strohhalme + Glanzlicht)

Audio (procedural, kein File):

- **8-Bit-Chiptune**: 8-Takt-Loop mit zwei Phrasen — Phrase A in C-Dur-Arpeggien, Phrase B in vi-IV-I-V mit Walking-Bass-Achteln, ~105 BPM, Square-Lead + Triangle-Bass
- **SFX-Bibliothek**: Pickup-Chirp, Drink-Glucks, Hit-Small-Noise, Hit-Big-Layered-Crash, Finish-Fanfare, **TR-808-Klatscher** (Multi-Tap + Reverb-Tail) als `clap_one` und `applause`, zweisilbiges **wuhuu**
- **Zuschauer-Trigger**: zählt Spectators in ±6 m um den Spieler — bei 1–3 einzelner `clap_one`, ab 4+ `applause`, 18 % Chance `wuhuu`, Frequenz und Lautstärke skalieren mit Dichte
- **Peak-Normalisierung** plus **Per-SFX-Gain-Tabelle**: Klatscher 1.5x, Crash 0.6x — kompensiert, dass sustained Sounds perceptuell lauter wirken als Transienten
- Audio-Buffer auf 4096 gegen Browser-Rauschen bei Tasten-Events
