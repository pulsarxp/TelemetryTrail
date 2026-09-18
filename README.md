**English description below.**

# TelemetryTrail

A TelemetryTrail GPS- és telemetria-naplókból készít animált műholdas térképes videó-overlayt.

Az első támogatott bemeneti formátum az **EdgeTX CSV telemetria log**. A program a GPS-pozíció alapján mozgó műholdas térképet készít, megjeleníti az addig megtett útvonalat, az aktuális pozíciót, valamint több telemetriaértéket. Az elkészült MP4 videó egyszerűen ráhelyezhető az eredeti felvételre például DaVinci Resolve-ban.

## Demo

[![TelemetryTrail Demo](https://img.youtube.com/vi/4vrVpWsQ1Sg/maxresdefault.jpg)](https://youtu.be/4vrVpWsQ1Sg)

*Animált műholdas térkép-overlay EdgeTX telemetria logból.*

## Funkciók

- animált műholdas térkép
- aktuális GPS-pozíció jelölése
- az addig megtett teljes útvonal folyamatos megjelenítése
- sebesség
- magasság
- Home ponttól mért távolság
- Link Quality (LQ)
- állítható térképzoom, képméret és FPS
- térképcsempék helyi gyorsítótárazása
- MP4 export FFmpeg használatával
- EdgeTX CSV telemetria támogatás

## Követelmények

- Python 3.13 ajánlott
- FFmpeg elérhető a PATH-ban
- internetkapcsolat az első térképcsempe-letöltéshez

Python csomagok telepítése:

```bash
pip install -r requirements.txt
```

## Használat

Alapértelmezés szerint egy 30 másodperces tesztvideót készít:

```bash
python telemetry_trail.py telemetry.csv
```

A teljes log renderelése:

```bash
python telemetry_trail.py telemetry.csv --duration 0
```

Példa egy adott részlet renderelésére:

```bash
python telemetry_trail.py telemetry.csv --start 60 --duration 30
```

További opciók:

```bash
python telemetry_trail.py --help
```

A kimenet alapértelmezett neve `fpv_minimap.mp4`; az `--out` kapcsolóval módosítható.

> Megjegyzés: a jelenlegi verzió EdgeTX CSV oszlopneveire épül (`GPS`, `GSpd(kmh)`, `GAlt(m)`, `RQly(%)`). További bemeneti formátumok támogatása később hozzáadható.

---

# English

TelemetryTrail generates animated satellite-map video overlays from GPS and telemetry logs.

The first supported input format is **EdgeTX CSV telemetry logs**. The application creates a moving satellite map from GPS coordinates, keeps the complete travelled route visible, marks the current position, and displays useful telemetry values. The generated MP4 can be placed over the original footage in an editor such as DaVinci Resolve.

## Demo

[![TelemetryTrail Demo](https://img.youtube.com/vi/4vrVpWsQ1Sg/maxresdefault.jpg)](https://youtu.be/4vrVpWsQ1Sg)

*Animated satellite map overlay generated from an EdgeTX telemetry log.*

## Features

- animated satellite map
- live GPS position marker
- persistent travelled route
- speed display
- altitude display
- distance from Home
- Link Quality (LQ)
- configurable map zoom, output size and frame rate
- local map tile caching
- MP4 export using FFmpeg
- EdgeTX CSV telemetry support

## Requirements

- Python 3.13 recommended
- FFmpeg available in PATH
- internet connection for the initial map tile download

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Usage

By default, TelemetryTrail renders a 30-second test video:

```bash
python telemetry_trail.py telemetry.csv
```

Render the complete log:

```bash
python telemetry_trail.py telemetry.csv --duration 0
```

Render a selected part of the log:

```bash
python telemetry_trail.py telemetry.csv --start 60 --duration 30
```

See all available options:

```bash
python telemetry_trail.py --help
```

The default output filename is `fpv_minimap.mp4`; use `--out` to change it.

> Note: the current version expects EdgeTX CSV column names (`GPS`, `GSpd(kmh)`, `GAlt(m)`, `RQly(%)`). Support for additional telemetry formats can be added later.

## License

MIT
