# Radgame

Top-down Pixel-Art Rennradspiel in Python/Pygame. Vom Noob zum Sieger — auf den berühmten Strecken der Rennrad-Welt.

## Schnellstart

```bash
./run.sh
```

Beim ersten Start wird automatisch ein `.venv` angelegt und `pygame` installiert.

Falls `./run.sh` nicht funktioniert (z. B. Windows), manuell:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

## Steuerung

| Taste                | Aktion                         |
|----------------------|--------------------------------|
| ↑ / W                | Härter treten (schneller, mehr Energieverbrauch) |
| ↓ / S                | Tempo rausnehmen               |
| ← / A , → / D        | Lenken / Ausweichen            |
| Leertaste            | Wasser trinken (Energie zurück) |
| Enter                | Auswahl bestätigen / nach Rennen weiter |
| ↑↓ im Menü           | Strecke wählen                 |
| PgUp / PgDn          | Streckenliste schneller scrollen |
| Esc                  | Zurück / Beenden                |

## Was es zu tun gibt

- **Hindernissen ausweichen:** Schlaglöcher bremsen stark, Äste kosten Energie
- **Gegner überholen:** Jede Position weiter vorne bringt Punkte
- **Energie managen:** Hartes Treten kostet, Wasser füllt zurück (limitiert)
- **Wind & Hitze** in höheren Strecken-Schwierigkeiten merklich

## Doku

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Code-Struktur
- [docs/GAMEPLAY.md](docs/GAMEPLAY.md) — Mechaniken im Detail
- [docs/ROUTES.md](docs/ROUTES.md) — Wie Strecken funktionieren, neue ergänzen
- [docs/ROADMAP.md](docs/ROADMAP.md) — Was geht, was kommt
- [CLAUDE.md](CLAUDE.md) — Kontext für Claude/AI-Sessions

## Strecken im Spiel

Echte Klassiker und Grand-Tour-Etappen, in einer fürs Game verkürzten Form:

- **Monumente:** Mailand–Sanremo, Flandern, Paris–Roubaix, Lüttich–Bastogne–Lüttich, Il Lombardia
- **Klassiker:** Strade Bianche
- **Tour de France:** Mont Ventoux, Alpe d'Huez, Col du Tourmalet, Col du Galibier
- **Giro d'Italia:** Stelvio, Mortirolo, Zoncolan
- **Vuelta a España:** Alto de l'Angliru
