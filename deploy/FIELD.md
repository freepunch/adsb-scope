# Field Deployment

Turning the bench build into something you can switch on anywhere and
switch off by pulling the plug.

## 1. Autostart on boot

```bash
cd ~/adsb-scope
git pull
sudo bash deploy/install.sh
sudo reboot
```

The deck now boots straight to the radar with no login, no SSH, no
sudo. The service restarts itself if the app ever exits.

Why a systemd unit rather than the manual `sudo cage` command: the unit
uses `PAMName=login` with `TTYPath=/dev/tty1`, which makes logind open a
real session with a seat. That is what lets cage become DRM master.
Running cage over SSH fails for exactly this reason (no controlling
terminal, no seat), which is why sudo was needed by hand.

Control it:

```bash
sudo systemctl stop adsb-scope@$USER      # frees the screen for bench work
sudo systemctl start adsb-scope@$USER
journalctl -u adsb-scope@$USER -f          # live logs
```

## 2. Config for field use

In `~/adsb-scope/config.json`:

```json
{
  "host": "127.0.0.1",
  "port": 30003,
  "gps_enabled": true,
  "fullscreen": true,
  "hide_cursor": true,
  "render_fps": 15
}
```

`gps_enabled` is what makes "power on anywhere" true: the scope
recenters on the GPS fix instead of the coordinates baked into the file.

GPS setup, if not already done:

```bash
sudo apt install -y gpsd gpsd-clients
sudo systemctl enable --now gpsd
cgps        # confirm a fix; Ctrl+C to exit
```

Indoors a first fix can take several minutes. Outdoors it is usually
under a minute.

## 3. Surviving power cuts

The SD card is the fragile part: yanking power mid-write corrupts it.
The overlay filesystem makes the root filesystem read-only, with all
writes going to a RAM layer that is discarded on reboot. Nothing is
ever mid-write, so pulling the plug becomes safe.

```bash
sudo raspi-config
#   Performance Options -> Overlay File System -> Enable
#   (also enable the read-only boot partition when prompted)
sudo reboot
```

**Do this last.** Once enabled, the system forgets changes on every
reboot: no `git pull`, no config edits, no `apt install` will persist.

To make changes later:

```bash
sudo raspi-config      # disable overlay FS
sudo reboot
# ...make changes...
sudo raspi-config      # re-enable
sudo reboot
```

Consequence worth knowing: `coverage.json` will not persist across
reboots while the overlay is on. For antenna A/B testing at home, turn
the overlay off, or copy the file to a USB stick before rebooting.

## 4. Power rail

Symptoms of a sagging 5V rail, all seen on this build:

- `hwmon hwmon1: Undervoltage detected!` in `dmesg`
- `error -71` and USB disconnects, especially the SDR dropping out
- `vcgencmd get_throttled` returning anything other than `0x0`

The fix is a **self-powered USB hub** (its own supply, not bus-powered)
carrying the screen, SDR, and GPS, so those draws come off the hub
rather than the Pi's rail. A short, thick micro-USB cable to the Pi and
a genuine 2.5A+ supply help but are not usually sufficient alone on a
Pi 3 driving a display plus two radios.

## 5. Pre-flight checklist

```bash
vcgencmd get_throttled                  # want 0x0
lsusb                                   # SDR, GPS, touch controller present
systemctl is-active readsb              # active
systemctl is-active adsb-scope@$USER    # active
timeout 10 nc localhost 30003 | head -3 # real MSG, lines
```

Then: antenna on, lid open, power on. Boot to radar is about 30 s.
