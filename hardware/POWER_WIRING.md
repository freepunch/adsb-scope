# Power Entry Spec: Panel USB-C + Switch (5V)

The gift unit takes 5V from an external wall supply through a
panel-mount USB-C socket, with a rocker switch inside on the positive
line. No mains voltage enters the case.

This supersedes the earlier 120V approach in `MAINS_WIRING.md`. That
design worked, but the external brick gives the recipients an identical
experience with none of the risk, and a socket on the case means they
can replace a lost supply with any USB-C cable and brick rather than
calling you.

## Chain

```
wall supply (5.1V 2.5A official Pi PSU, or any good 5V 3A USB-C brick)
      |  user's own USB-C cable
      v
panel-mount USB-C socket  (threaded bulkhead, dust cap, pigtail inside)
      |
      +-- V+ (red)  --> rocker switch --> Pi 5V input
      +-- GND (black) -----------------> Pi GND
```

## Parts

- **Panel-mount USB-C socket with pigtail.** Search "panel mount USB-C
  female waterproof pigtail". A threaded bulkhead socket with 20 to
  30 cm of attached cable, usually IP67 with a dust cap, ~$10. One
  drilled hole, no soldering on the socket side.
- **SPST rocker switch, panel mount.** Any 5V-capable switch; these are
  universally rated far above what 3A at 5V needs.
- **5V supply.** The official Raspberry Pi supply is worth the few
  dollars: it outputs **5.1V** deliberately, to compensate for cable
  drop. Generic bricks that sag to 4.8V are exactly what caused the
  undervoltage and SDR dropouts on build one.

## Wiring notes

**Wire gauge matters more at 5V than you would expect.** Voltage drop
that is trivial at 120V is significant at 5V. Use 20 AWG minimum for
the internal run, 18 AWG if the routing is long. Keep the run short.

**Feed the Pi through its normal power input** (micro-USB on a Pi 3,
USB-C on a Pi 4), not the GPIO pins. GPIO power injection is common in
cyberdeck builds and it works, but it bypasses the Pi's input
protection. For something you are handing to other people, keep the
protection in the path.

To get from the pigtail to the Pi's connector, either:
- buy the pigtail terminated in bare wires and solder it to a cut
  micro-USB cable, or
- use a USB-C-male-ended pigtail plus a short adapter cable.

Either way the rocker switch interrupts **V+ only**. Ground runs
straight through.

**Solder and heat shrink** every joint. At 5V this is ordinary
low-voltage work, no ferrules or terminal blocks needed.

**Strain relief.** The threaded bulkhead handles the outside. Inside,
anchor the pigtail to the chassis with a cable clip so a tug on the
external cable never pulls on a solder joint or the Pi's connector.

**Separation.** Keep the 5V run away from the SDR's USB cable and the
antenna. Switching noise at 1090 MHz costs you reception.

## Test before closing the case

1. With nothing connected to the Pi, plug in the supply and switch on.
   Measure at the Pi end of the harness: **5.0 to 5.2V**. Below 4.9V,
   find the drop before proceeding.
2. Switch off, confirm the voltage goes to zero.
3. Connect the Pi, power up, and with everything running:
   ```
   vcgencmd get_throttled
   ```
   Want `0x0`. Anything else means the supply or the wiring is sagging,
   and a self-powered USB hub for the screen and radios is the fix.
4. Cycle the switch several times and confirm it boots cleanly each
   time. With the overlay filesystem enabled, this is safe by design and
   is exactly how the recipients will use it.

## Why the switch, given the overlay filesystem

The overlay already makes pulling power safe, so the switch is not
strictly necessary. It is there because a counter-top device should
have an on button, and reaching behind a case for a plug does not feel
like equipment. If you would rather have one less hole and one less
connection to fail, the design works without it.
