# Enclosure concept

Clear, non-conducting hood on a non-conducting base, with a lid interlock. Parametric source:
`hardware/enclosure/charger_test_enclosure.scad` (not yet rendered or checked; OpenSCAD wasn't available when it was written).

## Cut list (defaults, charger assumed 250 × 150 × 90 mm)
| Part | Size (mm) | Qty | Material |
|---|---|---|---|
| Base | 402 × 302 × 10 | 1 | FR4 / phenolic / HDPE (no metal, no plywood) |
| Back (cable) panel | 362 × 150 × 6, 2 × Ø22 grommet holes | 1 | clear polycarbonate (acrylic acceptable) |
| Side panels | 256 × 150 × 6 | 2 | same |
| Top | 362 × 262 × 6 | 1 | same |
| Door | 350 × 150 × 6, top hinge | 1 | same |
| Mat | 600 × 450 | 1 | see `03-mat-spec.md` |

Inside: 350 × 250 × 150 mm. That leaves 50 mm clearance each side and 60 mm headroom.
Re-run `openscad -D 'part="bom"' -o /dev/null charger_test_enclosure.scad` after changing the charger size.

## Fixture items inside / on the base
- 3-pin socket for the charger plug, L and N bridged, with insulated terminal posts for L+N and PE (rated for the test voltage).
- Two insulated binding posts for the output leads, so the operator does not re-clip alligators every cycle.
- HV and return leads from the CC2670P through the back grommets to posts; keep the HV lead short, away from the base edge.

## Interlock
- Normally-closed or normally-open microswitch (choose per the CC2670P remote connector pinout; **check the manual**) on the door, opening the circuit when the door opens.
- Add a second switch for redundancy if the safety review requires it.
- Optional: red "HV ON" lamp driven from the tester's HV-output indicator.
- Optional later: a read-back input so the GUI shows the real lid state (the `Instrument.lid_closed()` hook is already in the driver API).

## To do before building
1. Measure the charger and update parameters.
2. Confirm interlock pinout on the CC2670P.
3. Pick the material and a fabricator; get the safety review.
