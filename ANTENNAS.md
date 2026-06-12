# Antenna Build & Test Plan

Two antennas, built in order, measured against each other with the
Coverage tab. Antenna A is the baseline; Antenna B is the experiment.
Everything is sized for 1090 MHz, where one wavelength is ~275 mm.

---

## Antenna A — quarter-wave ground plane ("spider")

The reference antenna. Simple enough that almost nothing can go wrong,
which is exactly what you want from a baseline.

### Materials
- ~50 cm of solid copper wire, 1.0–1.5 mm diameter (12–16 AWG), or the
  center conductor stripped from coax
- A panel-mount SMA female connector (4-hole flange type is easiest),
  or sacrifice one end of an SMA pigtail
- Solder, heat shrink

### Dimensions
- **Vertical radiator: 69 mm** (λ/4 at 1090 MHz). Measure from the top
  of the connector. Cut a touch long and trim — you can shorten wire,
  not lengthen it.
- **Four radials: 76 mm each**, soldered to the connector's ground
  flange, bent **45° downward**. The downward angle raises the feed
  impedance toward 50 Ω; flat radials give ~36 Ω and a worse match.

### Build
1. Solder the radiator to the SMA center pin, dead vertical.
2. Solder one radial to each flange corner, then bend all four down 45°.
3. Verify with calipers; at 1090 MHz a few mm is a real detuning.
4. Weatherproofing if outdoors: a PETG radome works — you have the
   printer. Keep metal and infill away from the radiator.

---

## Antenna B — coaxial collinear (CoCo)

The experiment: stacked half-wave segments of coax with alternating
connections, which adds gain by flattening the radiation pattern toward
the horizon — where the distant aircraft are. More gain at the horizon,
less wasted straight up.

### The one number that matters
Each segment is an **electrical** half wave, so the velocity factor
(VF) of your coax scales the physical length:

```
segment length = (275 mm / 2) x VF
```

- RG-6 foam dielectric (VF ≈ 0.85): **117 mm**
- RG-58 solid PE (VF ≈ 0.66): **91 mm**

Look up the VF for your exact cable — getting it wrong detunes every
segment at once, and the errors compound down the stack.

### Materials
- ~1.5 m of RG-6 (cheap, consistent, easy to strip)
- 8 segments (a sane first build; gain grows slowly past that, but cut
  precision matters more)
- One λ/4 whip (69 mm wire) for the top, heat shrink, a PVC tube or
  printed tube to keep the finished stack straight

### Build
1. Cut 8 segments to your computed length, ±1 mm. Precision here IS the
   antenna.
2. Strip each end ~8 mm. Join segments with the connection **crossed**:
   center conductor of one segment to the **shield** of the next, and
   shield to center. This phase flip is what makes the stack add
   instead of cancel.
3. Top: solder the 69 mm whip to the final center conductor.
4. Bottom: feedline coax, center-to-center and shield-to-shield (no
   cross on the feed joint).
5. Slide the whole stack into the tube — it must stay straight.

### Honest expectations
CoCos are famously hit-or-miss for home builders: a good one clearly
beats the spider at the horizon; a sloppy one loses to it. That's not a
bug for this project — it's the whole reason the Coverage tab exists.
You'll know, with data, which one you built.

---

## Test protocol

The discipline that makes the comparison meaningful:

1. **Fix every variable except the antenna.** Same mount position, same
   height, same coax, same dongle, same gain setting.
2. **Reset** coverage in the app at the start of each test.
3. **Log a fixed window** — 24 h is ideal because air traffic has a
   strong daily rhythm; if you compare a weekday morning against a
   Sunday night, you're measuring schedules, not antennas. Minimum
   useful window is a few hours at the same time of day.
4. **Save the artifacts.** Screenshot the Coverage tab and copy
   `coverage.json` to `results/<antenna>-<date>.json` before resetting.
5. **Read the shape, not just the max.** A single 150 nm spike means one
   high-altitude aircraft on a lucky path; a fatter outline at 60–80 nm
   in most directions is the real win. Terrain shadows (hills, your own
   roof) show up as consistent notches — those are real and won't move
   between antennas.

## Sequence

1. Build the spider. Verify the whole chain works end to end.
2. Log the baseline window. Save results.
3. Build the CoCo. Log the same window length. Compare.
4. Iterate: radial angle, segment count, mounting height. One change
   per test.
