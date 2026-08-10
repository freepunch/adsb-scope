# Lid Panel Spec: Apache 2800 + Waveshare 7" HDMI LCD (C)

The one precision part of the cyberdeck. A single printed plate that
drops into the case lid, bezel-mounts the display face-out, and routes
cables to the base. Model it in Fusion with the user parameters below
so a caliper correction is a one-field edit, not a remodel.

## Fusion user parameters

Verified (hardcode these):

| Parameter        | Value      | Source                          |
|------------------|------------|---------------------------------|
| panel_w          | 164.90 mm  | Waveshare spec, panel outline   |
| panel_h          | 106.96 mm  | Waveshare spec                  |
| panel_t          | 8.0 mm     | Waveshare spec, panel thickness |
| view_w           | 154.21 mm  | Waveshare spec, display area    |
| view_h           | 85.92 mm   | Waveshare spec                  |

Measure on your hardware (fill in before modeling):

| Parameter        | How to measure                                    |
|------------------|---------------------------------------------------|
| lid_inner_w/h    | Apache lid opening, wall to wall at the inner lip |
| lid_depth        | Inner lip face to closed-lid interior ceiling     |
| hole_x/hole_y    | Display mounting holes, center-to-center both axes (varies by board revision; measure yours) |
| boss_standoff    | Rear face of LCD glass to PCB hole plane          |

Derived (formulas, not numbers):

| Parameter   | Formula            | Why                              |
|-------------|--------------------|----------------------------------|
| cutout_w    | view_w + 1.6 mm    | 0.8 mm reveal per side           |
| cutout_h    | view_h + 1.6 mm    |                                  |
| pocket_w    | panel_w + 0.6 mm   | slip fit for the module          |
| pocket_h    | panel_h + 0.6 mm   |                                  |
| pocket_d    | panel_t + 0.3 mm   | glass sits just below plate face |

## Plate design

1. **Base plate**: (lid_inner_w minus 0.8) x (lid_inner_h minus 0.8),
   4 mm thick. Seats against the lid's inner lip.
2. **Display pocket**: pocket_w x pocket_h x pocket_d, centered,
   opening toward the case interior. The screen drops in from behind;
   glass faces out through the cutout.
3. **View cutout**: cutout_w x cutout_h through the plate, centered in
   the pocket, 45-degree chamfer on the outer edge (looks intentional,
   prints clean face-down).
4. **Retention**: four printed corner tabs screwed into bosses behind
   the panel (M3 heat-set inserts), clamping the module into its
   pocket. This works regardless of the display's own hole positions.
   If your measured hole_x/hole_y are convenient, add four M3
   clearance holes and screw the module directly instead.
5. **Cable slot**: 60 x 14 mm along the hinge edge, corners filleted
   R3, positioned over the display's connector edge. Add a printed
   half-bridge clamp (two M3 inserts) to strain-relieve the HDMI,
   touch, and power cables where they cross into the base.
6. **Panel-to-lid mounting**: four L-brackets screwed to the plate's
   rear, spring-clipping over the lid's inner lip. Zero holes through
   the case shell, so the IP65 rating survives and the whole assembly
   pops out with thumb pressure for service. (If you chose the SMA
   bulkhead route, the rating is already gone and you can simply
   screw through the lid wall into the plate edge.)

## Print

- PETG, matte black. Face down on a textured plate for the finish.
- 5 perimeters, 25 percent gyroid, no supports needed if the pocket
  walls are modeled with 45-degree overhangs.
- Print a 40 mm corner coupon first: one pocket corner + one cutout
  corner. Verify the display's corner seats and the reveal looks
  right before committing to the ~6 hour full plate.
- Label plates ("ADS-B RCVR 1090 MHZ") as separate 1.2 mm prints in
  white or a color swap, glued into shallow recesses; crisper than
  multicolor-on-one-face.

## Sanity checks before printing

- pocket_d must not exceed plate thickness minus 1.2 mm; if it does,
  thicken the plate, never thin the pocket floor.
- Dry-fit the display's connector edge against the cable slot
  position: connectors must align with the slot, not the plate.
- Confirm lid_depth clears panel_t plus the corner tabs (~12 mm
  total). If the Apache lid is shallower than that at the edges,
  move the tabs inboard where the lid is deepest.
