# Strecken

Strecken sind reine Daten in `routes.py`. Eine neue Strecke einzufügen heißt: einen Eintrag in die Liste `ROUTES` ergänzen.

## Schema

```python
{
    "id": "tourmalet",                # eindeutig, wird in save.json verwendet
    "name": "Col du Tourmalet",       # Anzeigename im Menü
    "race": "Tour de France",         # Wettkampf-Kontext (Flavor)
    "region": "Pyrenäen, Frankreich", # Geographie (Flavor)
    "distance_m": 4500,               # Spiel-Distanz in Metern (1500..7000 sinnvoll)
    "real_distance_km": 19,           # echte Länge (Flavor)
    "difficulty": 4,                  # 1..5 Sterne
    "opponents": 6,                   # 3..7
    "obstacle_density": 0.6,          # 0.3..1.6, 1.0 = normal
    "wind": 0.6,                      # 0..1
    "heat": 0.4,                      # 0..1
    "surface": "asphalt",             # "asphalt" | "cobbles" | "gravel"
}
```

## Richtwerte

| Parameter        | niedrig | mittel | hoch |
|------------------|---------|--------|------|
| distance_m       | 1500    | 3500   | 7000 |
| difficulty       | 1       | 3      | 5    |
| opponents        | 3       | 5      | 7    |
| obstacle_density | 0.5     | 0.8    | 1.6  |
| wind             | 0.1     | 0.4    | 0.9  |
| heat             | 0.1     | 0.4    | 0.8  |

## Aktuelle Strecken

Sortiert nach Schwierigkeit:

| ★ | Strecke                       | Rennen                     | distance_m | Besonderheit          |
|---|-------------------------------|----------------------------|------------|------------------------|
| 2 | Mailand–Sanremo              | Monument                   | 3000       | Lang-flach             |
| 3 | Strade Bianche               | Klassiker (Schotter)        | 3400       | Hitze, gravel          |
| 3 | Ronde van Vlaanderen         | Monument                   | 3600       | Wind, cobbles          |
| 3 | Lüttich – Bastogne – Lüttich | Monument                   | 4000       | Hügelig                |
| 3 | Il Lombardia                 | Monument                   | 4400       | Herbst, hügelig        |
| 4 | Paris – Roubaix              | Monument                   | 4200       | Cobbles, viele Hindernisse |
| 4 | Col du Tourmalet             | Tour de France             | 4500       | Wind                   |
| 4 | Alpe d'Huez                  | Tour de France             | 4800       | Hitze                  |
| 4 | Col du Galibier              | Tour de France             | 5000       | Wind                   |
| 5 | Passo del Mortirolo          | Giro d'Italia              | 5200       | sehr steil             |
| 5 | Monte Zoncolan               | Giro d'Italia              | 5400       | brutal steil           |
| 5 | Mont Ventoux                 | Tour de France             | 5500       | Wind + Hitze max       |
| 5 | Alto de l'Angliru            | Vuelta a España            | 5600       | Vuelta-Hammer          |
| 5 | Passo dello Stelvio          | Giro d'Italia (Cima Coppi) | 6000       | Königsetappe           |

## Wenn du eine neue Strecke vorschlägst

1. ID, Name, Race, Region recherchieren oder vom User übernehmen.
2. `distance_m`: 1500–7000 — niemals real verwenden, das Spiel-Rennen soll 1–3 Minuten dauern.
3. Schwierigkeit grob am Höhenprofil/Anstieg/Klima orientieren.
4. `surface` ehrlich setzen — auch wenn der Cobbles-Effekt noch nicht implementiert ist, wird es später matchen.

## Save-Kompatibilität

`save.json` speichert Bestplatzierungen pro `id`. Eine bestehende ID nicht umbenennen, sonst verliert der Spieler die Bestmarke. Lieber `_v2` anhängen oder eine ID frisch vergeben.
