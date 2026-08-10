# Cyberdeck Build: Hard-Case Flight Radar

A portable ADS-B receiver in an Apache 2800 (or Pelican 1200) hard
case: open the lid anywhere on earth, power on, see what's above you.

## Case

Apache 2800 (Harbor Freight): interior 302 x 229 x 135 mm,
polypropylene, IP65, purge valve, padlock-ready. The 7" screen fits
the lid with ~60 mm margin on every side.

## Layout

**Lid**: a 3D-printed panel replaces the lid foam, bezel-mounting the
Waveshare 7" (C) face-out. Wires (HDMI + touch + power) run down the
lid hinge side with a printed cable clamp so they flex, not snag.

**Base**: a printed deck plate with bays for:
- Raspberry Pi 4 (ports facing the hinge gap)
- Anker 323 in a snap cradle (removable to recharge)
- RTL-SDR clipped away from the Pi (both run warm)
- USB GPS puck (VK-162 style) flat against the deck, sky side up
- spare stubby antenna + coiled pigtail storage

**Antenna**, two options, honest tradeoff:
1. SMA bulkhead through the case wall + external stubby: best
   reception, military look, but drilling ends the IP65 rating.
2. Internal printed mast near the hinge that stands the stubby
   vertical when the lid is open: keeps the case sealed, costs some
   signal when aircraft are low on the horizon.

## Power

```
Anker 323 (5V, 3.6A combined)
 |-- USB-C  -> Pi 4 power input        (verify port sustains 3A)
 |-- USB-A  -> screen PWR micro-USB    (power-only cable)
Pi USB-A ----> screen TOUCH micro-USB  (data)
Pi USB-A ----> RTL-SDR
Pi USB-A ----> GPS puck
```

Runtime: ~10 W average from ~30 usable Wh, so 2.5 to 3 hours.

## OS setup (Raspberry Pi OS Bookworm 64-bit desktop)

1. Flash with auto-login enabled.
2. Display: stock EDID usually works. If not, in
   /boot/firmware/config.txt:
   `hdmi_group=2`, `hdmi_mode=87`, `hdmi_cvt 1024 600 60 6 0 0 0`,
   `hdmi_drive=1`; KMS fallback in cmdline.txt:
   `video=HDMI-A-1:1024x600M@60D`
3. Decoder: install readsb (wiedehopf scripts) or
   `sudo apt install dump1090-fa`. Confirm port 30003 is live:
   `nc localhost 30003 | head`
4. GPS: `sudo apt install gpsd gpsd-clients`, plug in the puck,
   verify with `cgps`. In adsb-scope's config.json set
   `"gps_enabled": true`.
5. App: install per README, set `"fullscreen": true`. Autostart via
   `~/.config/autostart/adsb-scope.desktop`:
   ```
   [Desktop Entry]
   Type=Application
   Name=adsb-scope
   Exec=/home/pi/adsb-scope/.venv/bin/python -m adsb_scope
   Path=/home/pi/adsb-scope
   ```
6. Survive hard power cuts: raspi-config -> Performance -> Overlay
   File System (enable only after everything is configured).

F11 toggles fullscreen, Esc exits it (for bench work with a keyboard).

## Field procedure

Open lid, attach antenna, press the bank's button. Boot to radar is
~30 s. GPS fix indoors may take minutes; near a window or outside,
usually under one. The status bar shows GPS state and current
position. Reset the Coverage tab per site; a coverage plot only means
something for one location.
