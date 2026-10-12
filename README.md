# AirAware (adsb-scope)


A desktop ADS-B viewer and **antenna measurement tool** in Python/Qt.
Point it at any dump1090/readsb decoder and it gives you a live radar
scope, a traffic table, and a polar plot of your antenna's real-world
coverage — max reception range in every compass direction.

The coverage plot is the point: build an antenna, log a day of traffic,
reset, build a better antenna, compare the outlines.

## How it fits together

```
antenna -> RTL-SDR dongle -> dump1090/readsb (decoder) -> TCP :30003 -> adsb-scope
```

The decoder does the radio work; adsb-scope consumes its SBS text
stream (one CSV line per decoded message), merges partial messages into
per-aircraft state, computes range/bearing from your antenna location,
and draws.

## Setup

Requires Python 3.10+.

```bash
git clone <your-repo-url>
cd adsb-scope
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

You also need a decoder running with networking on:

```bash
# macOS (Homebrew)
brew install dump1090-mutability
dump1090 --net

# Linux
sudo apt install dump1090-fa     # or build readsb

# Windows: dump1090 builds are available; run with --net
```

## Run

```bash
python -m adsb_scope
```

First run writes a `config.json` next to where you launched it. Edit it
and restart:

| key            | meaning                                  |
|----------------|------------------------------------------|
| host, port     | where the decoder is (default localhost:30003) |
| home_lat/lon   | YOUR antenna location — set this first   |
| max_range_nm   | scope radius                             |
| stale_seconds  | drop aircraft unheard for this long      |
| hide_cursor    | blank the mouse pointer (default true)   |
| splash         | AirAware boot animation (default true)   |
| fullscreen     | start fullscreen (kiosk)                 |
| render_fps     | scope redraw rate; 15 on a Pi 3          |

## Tabs

- **Scope** — radar view, north up: aircraft glyphs rotated to track, coloured
  by altitude band, callsign + flight level. Zoom with the on-screen +/-
  buttons, the scroll wheel, or the +/- keys; ranges step through
  5/10/25/50/100/200/400 nm and the traffic list filters to match.
- **Traffic** — sortable live table, nearest first
- **Coverage** — polar max-range-per-bearing plot with a reset button for
  starting a new antenna test; persists to `coverage.json` across runs

## Testing without an SDR

`python tools/fake_feed.py` serves simulated traffic on port 30003.
Run it in one terminal and `python -m adsb_scope` in another, and the
scope populates with fake aircraft near the configured home position.

## Tests

```bash
python tests/test_core.py
```

Covers the geometry, the SBS parser, state merging/expiry, and coverage
persistence — everything except the Qt widgets.

## Airspace alerts (UAS operating area)

An encroachment monitor for protecting your own model's airspace,
centred on `store.home_lat/home_lon` (which GPS updates live, so the
rings follow you). Levels: ADVISORY 3 nm / 2000 ft AGL, WARNING
1.5 nm / 1000 ft or projected CPA under 0.5 nm within 90 s, ALERT
0.5 nm / 700 ft with a repeating tone, plus LOST for a threat that
stops reporting. Settings live in `alerts.json`.

**Both altitude references calibrate themselves.** Site elevation comes
from a 3D GPS fix. The altimeter setting is derived from the aircraft
themselves: most broadcast barometric *and* geometric altitude, and the
gap between them, once the GPS-reported geoid separation is removed,
gives the local pressure correction. The median across several aircraft
is used, outliers dropped, implausible results rejected.

Note these are not interchangeable. Site elevation converts MSL to AGL
for your position; the altimeter setting converts the *aircraft's*
pressure altitude to MSL and is a property of today's atmosphere. With
a perfectly known elevation, a 1.0 inHg pressure error is still 1000 ft
of AGL error.

Both can be switched to MANUAL on the SETUP page, which is also where
the alert radii and ceilings are adjustable. Ring changes are
session-only unless saved.

**Zoom to 5 or 10 nm when flying.** The alert rings are 0.5 to 3 nm, so
at the 100 nm default they collapse into a dot at the centre of the
scope. The alarm still works at any range; it is only the visual rings
that need the zoom.

Honest limits: only aircraft the receiver hears. No ADS-B Out means
invisible. Use it as a backup to watching the sky, never as clearance.

## Field-changeable settings

Design principle: anything that may need changing away from a keyboard
must be reachable from the screen. The SETUP page covers the altimeter
setting, site elevation, and the alert and sound toggles, all with
touch-sized steppers. Changes apply to the running monitor immediately;
SAVE writes `alerts.json`.

If the overlay filesystem is enabled, SAVE will fail and say so plainly
rather than pretending it worked. Settings still apply for the session.
To make them stick, disable the overlay, save, and re-enable it.

Also on-screen: scope zoom and range filter (the +/- buttons on the
scope), and the coverage reset button.

## Field deployment

See `deploy/FIELD.md` for boot-start setup, GPS, and making the SD card
survive power cuts. Short version:

```bash
sudo bash deploy/install.sh && sudo reboot
```

## Roadmap ideas

- Decode Mode S yourself with pyModeS (own the protocol, not just the pixels)
- Raw IQ demodulation straight from the SDR (own the DSP)
- Message-rate-over-time charts per antenna test
- Export coverage plots as images for side-by-side comparison
