# B2 manual negative carrier

B2 replaces B1's spring latch, clearance leaf, roof/guide springs, clip catches
and small quarter-turn keys with a manual screw, a rigid locating shoe and
broad tapered clamps. It uses **13 printed pieces including the shared receiver**:
base, lift-off lid, six identical edge wedges, format sleeve, locating shoe,
thumbscrew, receiver and docking wedge. There are no purchased fasteners.
Each additional prepared strip holder needs eight pieces: base, lid and six
wedges. For quick format swaps, fit each format sleeve with its own identical
shoe and screw. The receiver and docking wedge are shared between formats.

This is a digitally checked **prototype**, assessed against the measured C35
reference with explicitly provisional registration and release travel.
The force study is elastic finite-element screening of explicitly defined
fixtures. It does not establish real-machine fit, photographic repeatability,
film friction, light tightness, wear or force retention at 35 °C.

## Measured-interface assessment (2026-11-15)

The active B2 export and the new native machine-clearance checker now use the
[measured reference from PR #16](../durst-c35-interface/README.md), unchanged.
The old B1 fixture remains historical development evidence and is no longer
B2's active machine-clearance test. No machine dimension was enlarged or
reclassified as measured to obtain a pass. The receiver, sleeve, wedges, frame, thread and bearing/capture geometry are
unchanged. The screw now has a 21 mm scalloped grip; corrected seating and
installation are defined separately in [interface.py](../../cad/negative_carrier_b2/interface.py).

| Item | Source / status |
| --- | --- |
| Head neck 88.55 × 98.3 mm; lower support 86.7 × 98.3 mm | User measurements from #16 |
| Lower opening 55.3 × 56.1 mm, centre X=+0.8 / Y=-43.35; bevel 0.8 mm drop / 1.5 mm run | User measurements and derived coordinates |
| Unloaded gap 6 mm | Approximate user reading |
| Carrier translation `(0, -42, -2.6)` mm | Proposed registration, **not measured original film position** |
| Film-plane Z=-2.6 mm | Derived by seating the actual receiver rail underside on the lower support at Z=-6 mm; contact/retention still unverified physically |
| X=0, Y=-42 mm and straight optical clearance | Uses the **provisional head optical opening**, not the measured lower opening centre |
| Lower-support/carrier release 0.4 mm | Prescribed installation scenario, **not measured available travel or force** |
| Screw diameters, positions and 0.5 mm protrusion; wider housing and hidden surfaces | Provisional envelopes retained from #16 |

**The previous placement was wrong for this reference.** Aligning its old upper
contact plane gave Z=-1.4 mm and 1350.4 mm³ of sleeve/underside-plate overlap.
The corrected seating removes that collision while leaving 0.3 mm nominal
clearance below the flat underside. The receiver has zero modeled distance to
the support; a deliberate 0.01 mm downward displacement detects support
penetration. This establishes a geometric seating scenario, not preload,
friction, lateral retention or photographic registration.

**Insertion needs a separate release scenario.** At the seated height, the
sleeve hits the provisional front screw during insertion/withdrawal (about
3.3238 mm³ in the continuous sweep). Lowering both carrier and lower support
by 0.4 mm clears that path, leaving 0.2 mm nominal clearance beneath the
0.5 mm screw envelope. After insertion, they rise together to the seated pose.
The actual gap tolerance, screw positions/protrusion and available release
travel must be checked on the machine. The checker never treats 0.4 mm as a
spring measurement or solves an insertion force.

**The screw grip also needed clearance through rotation.** Its old projecting
wings collided with the provisional outer housing when turned: the 90-degree
wing control intersects by 37.8 mm³. The replacement 21 mm scalloped grip stays
inside a 10.5 mm radius, giving 0.5 mm nominal clearance to that housing. The
native checker proves the entire screw is contained by the rotation cylinder,
then checks that cylinder over the full 4.8 mm axial lift. This covers every
angle, not sampled turns. An old/new geometry comparison below Z=29.19 mm found
zero difference: the thread, bearing and capture geometry are unchanged. Grip
comfort, hand torque and the provisional housing extent still need physical
confirmation. The earlier screw force study predates this grip revision and
is not validation of its hand loading; no new force or creep claim is made.

The checked installation sequence docks the format sleeve and receiver on the
workbench, then inserts the complete assembly. In-machine docking at the seated
height is not an accepted operation: its leading sleeve roof crosses the same
screw envelope. The original mechanism videos remain bench demonstrations;
they do not depict this measured-reference installation scenario.

The native FreeCAD assessment covers all eight combinations of compact/full
size and 35 mm, half-frame, APS and 110. It checks:

- Seated interference, receiver/support contact distance and straight optical
  passage through the selected frame and both machine openings.
- Continuous frame travel, complete insertion/withdrawal and release/seating,
  plus the full screw rotation/lift envelope.
  Planar faces generate exact translation prisms; curved faces use conservative
  swept bounding boxes. These machine checks do not rely on sampled poses.
- Negative controls: unreleased insertion, the obsolete Z=-1.4 mm placement,
  a receiver pushed 0.2 mm into the support, and an old rotated grip wing must
  all show interference.
- Hashed STEP imports and saved/reopened native assemblies with the reference.

A collision-screening bug was also fixed: build123d's `BoundBox.overlaps()`
excludes containment, so a small obstacle fully inside a large part's bounds
could be skipped. Both the #16 overlap helper and B2's internal broad-phase
check now include containment. Regression tests cover nested/equal bounds and
the front-screw collision. FreeCAD independently checks actual intersections.
The corrected broad phase also exposed 0.2 mm of front-wedge/spine interference
in the withdrawn loading pose. Reducing withdrawal from 7 to 6.5 mm keeps the
wedges inside the open loading pockets, with 0.3 mm nominal clearance to the
front spine. A regression test checks every withdrawn wedge against the base.

Run with the pinned CAD dependencies and FreeCAD:

```sh
python scripts/check_negative_carrier_interface.py --freecad /path/to/freecadcmd
```

Outputs are under `build/negative-carrier-interface/`: hash-linked manifests,
all carrier/reference STEP solids, eight `measured-assembly.FCStd` documents,
and `interface-validation.json`. `--release-drop` changes only the explicit
release scenario; insufficient release is expected to fail validation.
[Recorded validation](evidence/measured-interface-validation.json) accompanies
[the source/measurement manifest](evidence/measured-interface-manifest.json).

Reports keep `physical_fit_accepted: false` and `registration_measured: false`.
Before relying on a print, confirm the head aperture and optical position,
original film-seat height, screw envelopes, real support/stop/retention geometry,
and release travel. Printed threads, film retention, light leaks, repeatability
and warm PETG preload/creep remain physical tests. The FEM results continue to
be elastic screening, with mesh-sensitive indexing compliance and prescribed
thread bearing rather than solved mating-thread contact.

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

These archived views use the original STEP solids and rigid-body paths.
They predate the containment correction: their 7 mm wedge withdrawal is
superseded by the currently checked 6.5 mm motion, and their projecting knob
wings are superseded by the 21 mm scalloped grip. They also predate the
measured-reference installation scenario above and are not current path
validation evidence.
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
3. On the workbench, with the indexing shoe raised, slide the loaded holder through its matching
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
python scripts/check_negative_carrier_interface.py
python -m cad.negative_carrier_b2.suite
python scripts/render_negative_carrier_b2.py
python -m unittest discover -s tests -p 'test_*.py'
```

The checks cover single-solid validity, source hashes, sampled loading/docking
paths, the measured reference under explicit provisional registration, native
FreeCAD STEP imports, exact
translational frame sweeps and deliberately blocked motions. A forced return
to the same CAD coordinates is not measured photographic repeatability.

The 2026-11-15 integration passed 86 local Python tests, all four compact
internal-motion/native-assembly checks, all eight measured-interface scenarios,
and the nine-solid reference fixture verification. The native interface reports
separate geometric clearance from physical acceptance.

The [previous B1 design](../negative-carrier-b/README.md) and its failed force
screen remain available as a comparison rather than being overwritten.
