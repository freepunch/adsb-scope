# Mains Wiring Spec: Gift Build (120V AC In)

Bringing 120V into a sealed plastic case that other people will handle.
This is the one part of the project where a mistake hurts someone, so
the spec is written to be followed literally, and it ends with tests to
run before the unit is ever plugged in.

## Part choice matters more than technique

Use an **enclosed metal-case supply with a screw terminal block and a
PE (earth) terminal**. Mean Well LRS-35-5 (5V 7A) or RS-25-5 (5V 5A).

Do **not** use a PCB-mount encapsulated module such as the IRM-20 series
for a hand-wired build. Those have solder pins intended for a circuit
board, and soldering mains conductors to pins in free air is a poor
joint mechanically and thermally. Screw terminals with crimped ferrules
are the correct termination for hand assembly.

Do **not** use an open-frame supply. Live traces are exposed.

## Wiring chain

```
IEC C14 panel-mount inlet, fused (1A slow-blow)
    |
    |  L  (black)   ----------------> LRS-35-5  "L"  terminal
    |  N  (white)   ----------------> LRS-35-5  "N"  terminal
    |  PE (green/yellow) -----------> LRS-35-5  "⏚"  terminal
    |                                    + any exposed metal (SMA bulkhead)
    |
    +-- LRS-35-5 output:
            V+ (5V, red) --> rocker switch --> Pi 5V
            V- (GND, black) ---------------->  Pi GND
```

**Switch the DC side, never the AC side.** The rocker is the part a
person touches. With it on the 5V line, no mains voltage ever reaches
it. The supply idles at well under a watt when the Pi is off.

## Rules

1. **Crimped ferrules or insulated spade terminals** into every screw
   terminal. Never bare stranded wire (strands escape and bridge),
   never tinned/soldered wire in a screw terminal (solder creeps under
   pressure and the joint loosens over months).
2. **Fuse the line side.** Use an IEC inlet with an integrated fuse
   holder; 1A slow-blow is right for a 20 to 35W supply.
3. **Earth every exposed conductive part.** The case is plastic, so
   there may be nothing to bond except a metal SMA bulkhead if you fit
   one. Bond it. The supply's own metal case goes to PE regardless.
4. **Mains wire rated 300V minimum**, 18 AWG stranded. Keep the AC run
   as short as the layout allows.
5. **Heat shrink over every terminal**, including the terminal block if
   its cover does not fully enclose the screws.
6. **Physical separation.** AC wiring down one side of the case, DC and
   USB down the other. Never bundle AC alongside the SDR's USB cable:
   switching noise at 1090 MHz is a real reception problem, not just a
   safety one.
7. **Strain relief.** A panel-mount IEC inlet provides it inherently. A
   captive cord needs a cord grip rated for mains, not a zip tie.
8. **Mount the supply so its terminals face away from the lid**, where
   nothing can be pressed onto them when the case closes.

## Pre-power test procedure

Run all of these with the unit unplugged, before it ever sees a wall
socket. A multimeter is the only tool needed.

**1. Continuity, line path**
- IEC inlet L pin to supply "L" terminal: continuity.
- IEC inlet N pin to supply "N" terminal: continuity.
- IEC inlet PE pin to supply earth terminal: continuity.
- IEC inlet PE pin to SMA bulkhead (if fitted): continuity.

**2. Isolation, the important one**
- L to N: no continuity (open). Continuity here is a dead short; find
  it before plugging in.
- L to PE: open.
- N to PE: open.
- L to DC output V+: open.
- L to DC output V-: open.
- N to either DC output: open.

The AC and DC sides must be fully isolated with the supply's
transformer between them. Any continuity across that boundary means a
wiring error or a damaged supply.

**3. First power-up, nothing connected downstream**
- Disconnect the Pi.
- Plug in, switch on.
- Measure DC output: should read 5.0 to 5.2V.
- Switch off, unplug, then connect the Pi.

**4. Under load**
- Power up with everything connected.
- `vcgencmd get_throttled` should read `0x0`.
- Measure DC output again under load: still 5.0V or better.

## Honest caveats

- Cutting an IEC hole ends the case's IP65 rating. This unit is indoor
  equipment now. Do not describe it otherwise to the people using it.
- This is a one-off built by hand. It is not a listed appliance, and it
  has not been through the safety testing a commercial product gets.
  That is fine for a gift among people who understand it, but be
  straightforward about what it is.
- If anything about the AC side feels uncertain while you are building
  it, the external-brick version from `GIFT_BUILD_1800.md` gives the
  same user experience with none of this risk.
