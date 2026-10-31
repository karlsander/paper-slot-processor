# Modular paper processor · v2

**For the first unheated prototype, use [v1.8: two reusable baths in one shared base](docs/v1.8.md).**

The [fluid/thermal study and PETG print audit](docs/processor-physics.md) cover actual OpenFOAM simulations and A1 mini slicing with both 0.2 and 0.4 mm nozzles.
The complete unheated set now has a [native build123d workflow](docs/native-processor.md),
with STEP parts, oriented STL plates, FreeCAD checks and video generation.
[Five-plate Bambu Studio projects](docs/bambu-projects.md) include the tested A1 mini PETG settings.
It has exactly **five printed parts**: one base, two chambers and two magnetic
slotted tops. Fill directly through the open top to the internal ridge; no side
wells, clips or separate closing lids are included. Its tapered 180 × 180 mm base uses
the A1 mini footprint, with 25 mm between the chamber bodies. Current fills are 323 ml (16:9) and 360 ml (2:1).

For the separate enlarger project, see the [B1 negative-strip cartridges and motion videos](docs/negative-carrier-b/README.md). These use full-length holders on a larger printer; the processor's A1 mini requirement does not apply to them.

## Earlier heated v2 configuration

The remaining instructions and browser viewer describe the older heated v2 design.

Two removable vessels for a **102 mm Fuji roll**, with interchangeable paper guides, two joining bases, and one flat heating mat per chamber. Each wet vessel is a single printed piece. All printed parts fit a Bambu A1 mini in the supplied orientations. Use in darkness suitable for the paper; this is an open processor, not a daylight tank.

| Preset | Finished image | Cut from roll | Handling strip | Fill per vessel |
| --- | --- | --- | --- | --- |
| 16:9 | 181.3 × 102 mm | 208 × 102 mm | 26.7 mm | 325 ml |
| 2:1 panorama | 204 × 102 mm | 230 × 102 mm | 26 mm | 362 ml |

The image runs down the vessel. The remaining strip extends above it for a finger grip and is trimmed off afterward. The default guide leaves at least 8 mm of grip above its top. The image remains submerged during the designed **6 mm vertical and ±3 mm sideways agitation**. The loaded bath retains more than 6 mm of freeboard; vigorous splashing is outside this allowance.

**Prototype status:** digital geometry and slicer checks are provided. Printed liquid tightness, wet-paper clearance, emulsion contact, physical flow and heating performance require a water-and-scrap trial.

## Local preview and print estimates

```sh
./scripts/start_viewer.sh --no-browser
```

Open **http://127.0.0.1:8765/**. Select Assembly, Exploded, Inspect vessel A/B, or a print plate. Drag to rotate; use Cutaway, Fill level and Paper to inspect the inside. Paper toggles the liquid preview to the displaced, loaded level. Assembly estimates include both covers and **four guard tiles**. Selected plate estimates are for one copy; the tile view states its required quantity.

Parameters update the geometry, derived fill and recipe, cut length, capacity estimate, print material and time. Assembly builds slice every standard plate and provide a ZIP. Individual print views provide oriented STL and Bambu projects. Inspection views provide the tilted vessel project. Invalid settings leave the old preview visibly stale and disable downloads.

The server binds only to loopback. Builds are isolated and cancellable; source files are unchanged. OpenSCAD with the Manifold backend is required for previews. Bambu Studio supplies actual slicer estimates; without it previews still work and estimates are explicitly unavailable. Install Python dependencies from `requirements.txt`; the launcher creates `.venv` and bundles the frontend.

## Print

Open `v2/processor.scad` in OpenSCAD, or use the build script:

```sh
.venv/bin/python scripts/build_v2.py --trials
.venv/bin/python scripts/build_v2.py --aspect 2 --trials --output build/v2-wide
```

The ZIP includes STL, Bambu projects, a quantity manifest and these instructions. `--mesh-only` skips Bambu. Print the **fit section, one guide and a retaining clip first**, using wet scrap paper to choose the guide gap. Start at 1.2 mm; optional 0.8 and 0.6 mm guides are experiments, not a promise of scratch-free squeegeeing.

| Plate | Copies of plate | Contents / orientation |
| --- | ---: | --- |
| vessel_a, vessel_b | 1 each | One vessel each, tilted 44.2°, with a sacrificial bed rail |
| guide_a, guide_b | 1 each | Top face down, locating skirt up |
| cover_a, cover_b | 1 each | Closed resting covers; not airtight storage caps |
| clips | 1 | Four retaining clips, on their sides |
| cradle_a, cradle_b | 1 each | Flat bases |
| links | 1 | Two cradle joining plates |
| heater_clamps | **2** | Two lower metal-plate clamps per module |
| guard_tile | **4** | Two vented panels per module; one per plate |
| guard_links | 1 | Two four-hole panel joining plates |
| guard_mounts | **2** | Four metal-edge mounts per module, on their sides |
| strap_anchors | **2** | Two side strap anchors per module |
| mat_keepers | **2** | Four edge keepers per module |
| cable_saddle | **2** | One cable restraint per module |
| fit, trial_* | Optional | Fit section and alternative guides; excluded from full-set totals |

Use the live viewer or the exported quantity manifest for complete-set material and time estimates. They include both covers, all four guard tiles and both sets of heater fittings. Commercial mats, metal and straps are excluded.

Supplied profiles use Generic PETG, 0.20 mm layers, four walls and 15% infill. Vessel projects enable build-plate-only tree supports at a 30° threshold and a 3 mm outer brim. **Keep their tilt and placement; do not auto-orient or auto-arrange them.** The printed rail is two layers high and is trimmed off. Other parts print without supports.

The default vessel occupies about 147.2 × 158.1 × 160.4 mm; the 2:1 vessel about 147.2 × 173.9 × 176.7 mm. Geometry checks reserve 3 mm at each bed edge and 2 mm in height. A manifold mesh does not establish a leak-free FDM print. Inspect seams and layers, remove supports and the rail, then water-test each vessel independently before using chemistry. Do not sand a guide while it is mounted over a bath.

## Independent heater modules

The paper slots are parallel, **70 mm apart**. The two bases occupy **170.8 × 138 mm**, with cable restraints and heater fittings extending beyond the sides. Each base holds one removable vessel and a separate heater cassette. There is no shared metal plate between baths. Repeating the front/rear M4 link pattern permits more modules; current viewer and print bundles contain A and B. Join at least two modules for use, or screw a single module to a stable support through its spare base holes.

Each module uses a nominal **140 × 150 mm, 5 W mat**, a **156 × 182 × 1.5 mm metal plate**, and two identical **156 × 91 mm vented guard panels**. All printed parts fit the A1 mini. Mat dimensions and thickness remain adjustable for fitting the actual small unit; this version is built around 5 W per chamber. Test the measured equilibrium temperature before considering a different heater or redesign.

The mount is an adjustable prototype envelope, **not a verified fitting or compatibility approval for a specific mat**. The INVITAL listing specifies glass terrariums in its support answer; see [heating notes](docs/heating.md). The nominal mat thickness is 3 mm; measure the mat and its connection before printing fittings. Cable bulbs and connectors are not modeled. Leave these clear of keepers and the guard; the edges remain open for cable routing.

## Hardware

For two modules:

- Two suitable flat heating mats of the selected size; each has its own power connection or manual power adjustment.
- Two deburred aluminium plates of the size above. No aluminium touches chemistry; the plates require no drilled holes.
- Two compliant thermal interface pads **124 × 179 × 0.5 mm** with the default plate. The viewer reports dimensions for other settings. These sit between vessel backs and metal.
- Two **15 mm reusable hook-and-loop straps**, approximately 500 mm, trimmed after fitting.
- Four M4 × 10 mm screws, nuts and approximately 1 mm washers for the two base links. Add at least four **3 mm rubber feet** to clear underside hardware.
- Eight M3 × 25 mm screws and nuts for the four lower heater clamps; four M3 × 16 mm screws and nuts for their horizontal clamping screws.
- Eight M3 × 10 mm screws/nuts and eight 1 mm washers for the two guard links. Eight M3 × 16 mm screws/nuts with **1 mm washers** for the side guard mounts. Check their tips stop short of the metal; use a shorter screw or another washer if necessary.
- Two M4 × 16 mm screws/nuts and approximately 1 mm washers for cable saddles; four small cable ties.

## Assemble

1. Place A in front of B, with their slots parallel. Join the bases using a link at each side. The A base carries the fill volume and both recipes. One raised bar identifies A; two identify B.
2. Bolt two lower clamps to each base. Seat a separate plate in each pair of slots, then gently tighten the horizontal screws against **metal only**.
3. Place each mat flat on its plate's rear, centred horizontally, with its bottom **24 mm above the plate bottom**. Fit four loose edge keepers. The top keeper sits opposite the vessel's filling well; the bottom keeper sits just outside the vessel's left edge. Do not bend, pierce or squeeze the mat.
4. Join two guard tiles vertically using one four-hole link at its centre, with a 1 mm washer between link and panel at each hole. Fit the four side-edge mounts, 36 mm from the top and bottom of the metal, and screw on the guard. Its rear air gap stays open and at least 10 mm deep. Fit each cable saddle at the left side of its base and leave slack at the mat connection.
5. Fit one strap anchor at each plate side, halfway up the vessel. Place the interface pad against the vessel's flat back and lower the vessel into its base. Route the strap through both anchors and around the vessel front; tighten just enough to maintain contact. Release it to lift the vessel out independently, leaving heater and wiring in the base.
6. Seat the A/B guides and slide two retaining clips onto each front rim. Remove clips and lift the guide for filling or cleaning. Its skirt ends above the liquid; there is no submerged seal.

## Use and chemistry

Mix with water around **35–38°C**, following the chemistry's mixing instructions. Fill **empty** vessels with their guides removed. The A base volume is for **each bath**, not the sum of both. Pour through the open top; use the side well for the final small adjustment. Pause and allow the level to settle: a small persistent pool in the well, at the mark, is the fill cue. It is calibrated before paper insertion. Adding paper raises the liquid by roughly 3.2 mm at the default size.

Refit the guides and clips. Hold the paper's top strip in your fingers, lower it to the rounded bottom-edge stops, and agitate gently within the stated travel. Lift slowly through the guide and let drips return to the same bath before transfer. Keep A and B vessels/guides identified during cleaning to avoid bleachfix entering the developer. Empty each vessel separately with its guide removed; rinse the open cavity and well, then dry fully. Use separate proper bottles for chemistry storage.

Both default recipes are **65 ml concentrate + 260 ml water = 325 ml**, matching ADOX RA-4's 1+4 dilution. The 2:1 preset uses **72 + 290 = 362 ml**, rounded to whole millilitres. Recipes remain independently adjustable. The volume solver accounts for rounded corners, stops, the connected well, sheet displacement and agitation headroom. It prefers exact-ratio integer batches within 2 ml of the geometric target and within the usable level range; otherwise it rounds one component and computes the other as the remainder.

ADOX rates its kit at **2 m² per litre of working solution**. A 325 ml fill corresponds to 0.65 m². Counting each complete 102 × 208 mm cut gives **about 30 prints per fresh pair of fills**; test strips count too. This is an area-based planning estimate, not a lifetime guarantee. The two bath capacities are not added: every print goes through both. The full 2.5 litre kit is rated for 5 m², or about 235 complete cuts of this size. [ADOX / FOTOIMPEX specifications](https://www.fotoimpex.de/shop/fotochemie/adox-ra-4-kit-entwickler-und-bleichfixierbad-monokonzentrate-zum-ansatz-von-2500-ml.html)

The chosen workflow is manual: measure both baths after settling and use your previously tested temperature/time procedure. No thermostat or permanent sensor is included. ADOX's published standard process is 35°C and 45 seconds per bath; temperature compensation here is an intentional experiment, not a supplied manufacturer curve. Wash separately according to the kit instructions. See [heating notes](docs/heating.md).

## Native CAD and FreeCAD pilot

The [build123d / FreeCAD study](docs/freecad-study.md) provides native STEP solids,
scripted fit and removal checks, and a headless Gmsh/CalculiX thermal benchmark.
The completed [native v1.8 migration](docs/native-processor.md) now provides magnetic tops, internal fill ridges
and five print plates; the original pilot remains a historical study.
The [build123d/CadQuery comparison](docs/cad-library-comparison.md) tests the same
retaining clip in three APIs, parameter variations and STEP import/edit/export.

## Validation and source

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
npm --prefix viewer test
.venv/bin/python scripts/check_v2.py
.venv/bin/python scripts/check_v2_toolpaths.py build/v2-print/vessel_a/vessel_a.gcode
```

The v2 checks cover both aspect presets, manifold solids, printer bounds and placement, liquid volume, whole-image immersion throughout agitation, guide/clip fit, paper clearance, vessel removal, heater-frame clearances and rejected invalid parameters. The optional toolpath check samples deposited paths and verifies that support centre lines do not enter the wet cavity beyond a 0.25 mm boundary tolerance. It is not a physical support-removal test. CI runs geometry and viewer tests; Bambu slicing runs locally.

`v2/parameters.scad` is the shared parameter source. Geometry, volume calculation, vessels, guides, cradle and heater fittings are separated into small modules. Viewer jobs evaluate the same CAD defaults and metadata. The old monolithic design remains available at the repository root; its instructions are in [docs/v1.md](docs/v1.md).
