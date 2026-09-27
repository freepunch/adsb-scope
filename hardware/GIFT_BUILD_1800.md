# Gift Build: Apache 1800, Mains Powered

A second deck for the airport crew. Same software, same display, smaller
case, and wall power instead of a battery. Wall power removes the two
hardest problems from the first build: the sagging 5V rail and the USB
dropouts it caused.

## Why the 1800

| Case | Lid opening | Bezel around the 165 x 107 mm panel |
|------|-------------|-------------------------------------|
| 2800 | 302 x 229 mm | ~68 mm per side — screen floats in a black field |
| 1800 | 206 x 143 mm | ~20 mm long axis, ~18 mm short — reads as an instrument |

The 1800 is the better-looking build. The panel fills the lid the way a
panel-mount display should.

**The one thing to verify with calipers before printing**: lid depth.
The panel is 8 mm thick and its HDMI and micro-USB connectors need
roughly 15 to 20 mm of clearance behind it, so about 30 mm total. If the
1800 lid is shallower than that, route the cables flat out the hinge
side with right-angle connectors instead of straight back.

## Parts

| Item | Note |
|------|------|
| Apache 1800 | ~$25, frequently couponed |
| Raspberry Pi 3B or 4 | Pi 4 is fine here; no battery budget to protect |
| Waveshare 7" HDMI LCD (C) | same panel as build one |
| FlightAware Pro Stick Plus | SMA female port |
| Stubby SMA whip + right-angle SMA adapter | screws straight onto the dongle, no coax |
| VK-162 USB GPS puck | ~$15 |
| 5V 3A USB supply | a real one, not a phone charger |
| Panel-mount USB-C or barrel jack + short pigtail | mains entry through the case wall |
| IP68 cable gland or O-ring bulkhead | seals the power entry (see build one's notes) |
| M3 heat-set inserts, M3x8 screws | lid panel mounting |
| PETG filament, matte black | lid panel, base tray, label plates |

No power bank, no cradle, no split-power wiring. One cable in from the
wall, and the Pi feeds everything.

## Power

```
wall supply (5V 3A)
      |
  panel-mount entry (sealed gland)
      |
  Raspberry Pi
      |-- USB -> screen (power + touch, one cable)
      |-- USB -> Pro Stick Plus -> stubby antenna
      |-- USB -> GPS puck
```

If `vcgencmd get_throttled` returns anything but `0x0` under load, add a
self-powered USB hub for the screen and radios exactly as in build one.
With a genuine 3A supply and a Pi 3 this usually is not needed, but check
rather than assume.

## Lid panel

Use `hardware/LID_PANEL.md` unchanged. Every formula there is driven by
Fusion user parameters, so only the measured values change:

- `lid_inner_w` / `lid_inner_h`: measure the 1800's lid opening, nominal
  206 x 143 mm
- `lid_depth`: measure — this is the critical one
- `hole_x` / `hole_y`, `boss_standoff`: measure this panel; revisions vary

Everything derived (pocket, cutout, reveal, chamfer) recomputes on its
own. Print the 40 mm corner coupon first, as before.

With only ~18 mm of bezel, keep the corner retention tabs inboard and
thin, or skip them and screw the module directly through its own
mounting holes if the measured positions allow.

## Antenna

A stubby SMA whip screws directly onto the dongle with no coax. That is
the cleanest build and what this unit is specced for.

Honest tradeoff: direct mount puts the antenna wherever the case sits.
If the unit lives on a counter away from a window, range will be
noticeably worse than a magnetic whip on a metre of RG174 stuck to
something steel near a window. Ask the crew where it will live. If the
answer is "one spot, forever," consider shipping both antennas and
letting them try each.

## Software differences

Same repo, same install. Two config changes for a fixed installation:

```json
{
  "gps_enabled": true,
  "fullscreen": true,
  "hide_cursor": true,
  "render_fps": 15,
  "home_lat": 0.0,
  "home_lon": 0.0
}
```

Set `home_lat` / `home_lon` to the field's coordinates as the fallback
before GPS gets a fix. Indoors the puck may never get one, so the
fallback matters more here than on a portable unit; put it near a window
if possible.

Run `sudo bash deploy/install.sh` for autostart, then enable the overlay
filesystem last. The overlay matters more for a gift than for your own
unit: it means the crew can switch it off at the wall without ever
corrupting the card, and there is no shutdown ritual to explain.

## Before handing it over

The recipients will not have SSH or your patience. Make sure:

- it boots to the radar with no interaction, from cold power
- pulling the plug and replugging recovers cleanly, tested several times
- a label plate on the case names the thing and lists nothing they need
  to do
- the failure mode is visible: if the receiver drops out, the screen
  should say so rather than sitting empty (see roadmap)
