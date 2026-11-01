# B2 manual negative carrier

B2 replaces B1's spring latch, clearance leaf, roof/guide springs, clip catches
and small quarter-turn keys with a manual screw, a rigid locating shoe and
broad tapered clamps. It uses **13 printed pieces including the shared receiver**:
base, lift-off lid, six identical edge wedges, format sleeve, locating shoe,
thumbscrew, receiver and docking wedge. There are no purchased fasteners.
Each additional prepared strip holder needs eight pieces: base, lid and six
wedges. For quick format swaps, fit each format sleeve with its own identical
shoe and screw. The receiver and docking wedge are shared between formats.

This is a digitally checked **prototype**, with an unmeasured C35 interface.
The force study is elastic finite-element screening of explicitly defined
fixtures. It does not establish real-machine fit, photographic repeatability,
film friction, light tightness, wear or force retention at 35 °C.

## Slow mechanism videos

[Watch the complete paired-angle walkthrough](videos/B2-mechanisms-slow-multiple-angles.mp4).

| Chapter | Detail |
|---|---|
| [Load film and lower the lid](videos/01-load.mp4) | Film margins and full-holder view |
| [Push on the edge wedges](videos/02-wedges.mp4) | Top and underside close-ups; removal and refitting |
| [Insert through the format sleeve](videos/03-mask.mp4) | Overall view and stationary optical mask |
| [Dock the sleeve](videos/04-dock.mp4) | Receiver insertion and broad docking wedge |
| [Seat and release the index shoe](videos/05-index.mp4) | Coarse thread, captured flange and three locating faces |
| [Advance and return](videos/06-advance.mp4) | Whole carrier and close-up of the locating tooth |

Both views use the actual STEP solids and the checked rigid-body paths.
Transparency reveals otherwise hidden contacts. Numbered film rectangles are
illustrative markings. The motion is prescribed; elastic preload deformation
and forces come from the separate [force study](forces/README.md).

## Operation

1. At the workbench, put the strip on the base's margin and interframe supports.
   Match its actual frame spacing to the holder. Both ends remain open.
2. Lower the lid straight down. Push the six broad edge wedges onto the recessed
   rails and snug them evenly. Pull straight off to open; there is no release
   tongue to find. The tapered faces accommodate a limited amount of fit
   variation. Their friction and useful seating range still need a print test.
3. With the indexing shoe raised, slide the loaded holder through its matching
   format sleeve. Slide the sleeve into the shared receiver and fit its broad
   docking wedge. Push fully against the rear stop before snugging the wedge.
   The rear tongue passes under the retaining lip; broad bevelled rails locate
   the sleeve sideways and control yaw under the clamp's downward force.
   An integral stop limits the docking wedge to 2 mm of positive travel.
4. Turn the large knob gently to seat the shoe. Its two side faces locate the
   selected frame along X; the third face presses the holder toward its side
   references. All three supply downward force toward the support pads. A broad
   tapered bearing under the screw centers the shoe under preload; the clearance
   around its capture flange is not used as an X locating surface.
5. To advance, loosen the screw. The first 0.4 mm of axial movement takes up the
   flange-capture clearance; a further 4.4 mm lifts the shoe, leaving 0.9 mm
   nominal clearance over the 8 mm index rail. Slide to the next notch and seat
   again. The screw pitch is 3 mm, so the demonstrated release takes 1.6 turns.

The mask remains stationary as the strip moves. Each format has its own mask
opening and frame pitch, allowing adjacent 110 or half-frame images to be
blocked without making them inaccessible. The lamp must be off while moving
frames or changing sleeves; this design has no shutter.

Unused film can protrude from both ends. Support long tails independently.
To expose another group on an uncut developed roll, remove the holder, open it
at the workbench and reposition the film. This is not continuous film feed;
registration to an earlier exposure is lost when the film itself is unclamped.

## Why the closure changed during testing

The first B2 layout used three large keys at the front, away from the film.
Contact analysis found that the intervening thin frame bent: its local clamp
reaction was only about 0.034 N at 1 mm of key travel. That arrangement was
discarded. Moving the clamps beside the film shortened the force path. The
final closures retain a broad C-shaped cross-section, but have **no snap catch,
release tongue or separately designed spring**. Ordinary elastic deflection of
the short jaws and mating frame supplies preload, and is included in the study.

The smaller formats move their clamp stations and matching sleeve references
inward, keeping the same short span between clamp and film margin. Keeping the
110 clamps at the 35 mm outer edges gave only about 0.10 N at the film-side cut
for 0.5 mm snugging travel, and was discarded. The docking wedge also uses a
longer free jaw span: the first thick, short version required about 40 N at
0.5 mm travel; merely thinning those short jaws still required about 20 N.

The entire film-region moving envelope remains thin: nominal Z = −1.2 to
+1.3 mm including the clamps. The thick index rail and large controls begin
outside the hypothetical enlarger front at Y = 42 mm. The independent fixture
was not enlarged to make the new parts fit.

## Formats and printing

| Format | Compact positions / length | Default positions / length |
|---|---:|---:|
| 35 mm full frame | 4 / 168 mm | 6 / 244 mm |
| 35 mm half frame | 7 / 168 mm | 12 / 263 mm |
| APS | 4 / 150 mm | 6 / 214 mm |
| 110 | 7 / 174 mm | 6 / 154 mm |

These use the earlier provisional pitches. APS/110 spacing and the actual
strip's interframe gaps must be measured before relying on their registration.
`Config` accepts measured film thickness, pitch and image-width overrides.
Medium format remains outside this design.

Build outputs contain native assembly-coordinate STEP files and separately
oriented STL files. The large sleeve prints on its side (layer normal along
model X); edge/dock wedges print on their backs (layer normal along model Y);
the knob prints face-down. Frames and shoe use model Z as the layer normal.
Those orientations are represented in the material model where applicable.

Use Bambu PETG Basic and solid infill for an initial force-comparison prototype:
the analysis models solid material, not a sparse infill structure. A 0.4 mm
nozzle and 0.16 mm layers are a starting configuration, not a validated slicer
profile. Inspect the thin jaws, thread surfaces and bridge paths before printing.
Check brim allowance separately: the 174 mm compact 110 holder leaves only
3 mm per end on a 180 mm bed. Native dimensions are not sliced print-time or
material estimates.

The custom D12 × 3 trapezoidal thread has 0.25 mm nominal radial and 0.15 mm
profile-width allowance in its mating cut. It is not a certified metric/Acme
thread. Fit, drag and hand torque need a coupon test; the force report separates
thread structural screening from contact and friction results.

## Reproduce

```sh
python -m pip install -r cad/requirements-fem.txt
python -m cad.negative_carrier_b2.export
python -m cad.negative_carrier_b2.export --full-size
python scripts/check_negative_carrier_b2.py
python -m cad.negative_carrier_b2.suite
python scripts/render_negative_carrier_b2.py
python -m unittest discover -s tests -p 'test_*.py'
```

The checks cover single-solid validity, source hashes, sampled loading/docking
paths, the independent enlarger envelope, native FreeCAD STEP imports, exact
translational frame sweeps and deliberately blocked motions. A forced return
to the same CAD coordinates is not measured photographic repeatability.

The [previous B1 design](../negative-carrier-b/README.md) and its failed force
screen remain available as a comparison rather than being overwritten.
