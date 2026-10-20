# Modular paper processor · v2

Two removable vessels for a **102 mm Fuji roll**, with interchangeable paper guides, an A/B cradle, and one shared flat 20 W heating mat. Each wet vessel is a single printed piece. All printed parts fit a Bambu A1 mini in the supplied orientations. Use in darkness suitable for the paper; this is an open processor, not a daylight tank.

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

Open **http://127.0.0.1:8765/**. Select Assembly, Exploded, Inspect vessel A/B, or a print plate. Drag to rotate; use Cutaway, Fill level and Paper to inspect the inside. Paper toggles the liquid preview to the displaced, loaded level. Assembly estimates include both covers and **six guard tiles**. Selected plate estimates are for one copy; the tile view states its required quantity.

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
| heater_clamps | 1 | Two lower metal-plate clamps |
| guard_tile | **6** | Six identical vented panels; one per plate |
| guard_links | 1 | Two four-hole panel joining plates |
| guard_mounts | 1 | Four metal-edge mounts, on their sides |
| strap_anchors | 1 | Three anchors; the centre one includes the upper mat keeper |
| mat_keepers | 1 | Bottom keeper and two side keepers |
| cable_saddle | 1 | One cable restraint |
| fit, trial_* | Optional | Fit section and alternative guides; excluded from full-set totals |

The complete default set is approximately **808 g / 32 h 9 min**; the 2:1 set is **858 g / 34 h 7 min**, including six guard tiles and both covers, excluding optional fit/trial pieces. These are local Bambu Studio 2.7.1 estimates and can vary with slicer settings.

Supplied profiles use Generic PETG, 0.20 mm layers, four walls and 15% infill. Vessel projects enable build-plate-only tree supports at a 30° threshold and a 3 mm outer brim. **Keep their tilt and placement; do not auto-orient or auto-arrange them.** The printed rail is two layers high and is trimmed off. Other parts print without supports.

The default vessel occupies about 147.2 × 158.1 × 160.4 mm; the 2:1 vessel about 147.2 × 173.9 × 176.7 mm. Geometry checks reserve 3 mm at each bed edge and 2 mm in height. A manifold mesh does not establish a leak-free FDM print. Inspect seams and layers, remove supports and the rail, then water-test each vessel independently before using chemistry. Do not sand a guide while it is mounted over a bath.

## Hardware

For the default 350 × 200 mm mat envelope:

- One **Lucky Reptile Thermo Mat PRO HTP-20**, 20 W. See [heating notes](docs/heating.md) for the verified Amazon.de listing and operating workflow.
- One flat aluminium spreader **366 × 232 × 1.5 mm**, with deburred edges. It has no liquid contact and needs no drilled holes.
- Two compliant thermal interface pads, **124 × 192.3 × 0.5 mm** for 16:9. The viewer reports the dimensions for other settings. These sit between the vessel backs and metal, never inside a bath.
- Two **15 mm × approximately 500 mm** reusable hook-and-loop straps, trimmed after fitting. Each vessel releases separately.
- Four M4 × 10 mm screws, four M4 nuts and approximately 1 mm washers for the cradle links. Add four or more **3 mm rubber feet** so underside hardware clears the table.
- Four M3 × 25 mm screws and nuts for the lower heater clamps; two M3 × 16 mm screws and nuts for their horizontal clamping screws.
- Eight M3 × 10 mm screws/nuts for the guard links. Four M3 × 16 mm screws/nuts with **1 mm washers** for the guard mounts. Check that their tips stop short of the metal plate; use a shorter screw or another washer if needed.
- One M4 × 16 mm screw/nut and approximately 1 mm washer for the cable saddle; two small cable ties. Leave a gentle cable loop, without pulling on the mat connection.

Mat thickness is not specified in the product listing: **measure the actual mat before printing fittings**. The default 3 mm envelope, spreader thickness, pad thickness and guard clearance are adjustable. The mat is represented by its rectangular bounding envelope; its actual outline is rounded. Keeper positions capture the middle of its four edges. Physical fits still need checking.

## Assemble

1. Bolt the cradle halves together using the front and rear links. The A base carries the calculated fill and both recipes. One raised bar identifies A; two identify B.
2. Bolt on the two lower heater clamps. Seat the metal plate in their slots, then gently tighten the horizontal screws against the **metal only**.
3. Place the mat flat against the rear of the metal, centred horizontally and with its bottom **24 mm above the metal's bottom edge**. Fit the bottom and side keepers. Slide on the three strap anchors from above; the centre anchor also captures the mat's top edge. Do not bend, pierce or pinch the mat.
4. Join six guard tiles into three columns and two rows with the two four-hole links at the internal intersections. Fit the four edge mounts and screw the guard on. Its rear air gap remains open. Fit the cable saddle in the spare rear-left base hole and restrain the cable gently.
5. Put the thermal pads against the flat vessel backs and lower the vessels into their cradle guides. Route one strap through the centre and each outer anchor, around that vessel's front. Tighten just enough to maintain contact. Release that strap to lift out its vessel; the mat stays in the frame.
6. Seat the A/B guides on the rims and slide two retaining clips onto each front rim. Remove clips and lift the guide for filling or cleaning. The guide skirt ends above the liquid; there is no submerged seal.

## Use and chemistry

Mix with water around **35–38°C**, following the chemistry's mixing instructions. Fill **empty** vessels with their guides removed. The A base volume is for **each bath**, not the sum of both. Pour through the open top; use the side well for the final small adjustment. Pause and allow the level to settle: a small persistent pool in the well, at the mark, is the fill cue. It is calibrated before paper insertion. Adding paper raises the liquid by roughly 3.2 mm at the default size.

Refit the guides and clips. Hold the paper's top strip in your fingers, lower it to the rounded bottom-edge stops, and agitate gently within the stated travel. Lift slowly through the guide and let drips return to the same bath before transfer. Keep A and B vessels/guides identified during cleaning to avoid bleachfix entering the developer. Empty each vessel separately with its guide removed; rinse the open cavity and well, then dry fully. Use separate proper bottles for chemistry storage.

Both default recipes are **65 ml concentrate + 260 ml water = 325 ml**, matching ADOX RA-4's 1+4 dilution. The 2:1 preset uses **72 + 290 = 362 ml**, rounded to whole millilitres. Recipes remain independently adjustable. The volume solver accounts for rounded corners, stops, the connected well, sheet displacement and agitation headroom. It prefers exact-ratio integer batches within 2 ml of the geometric target and within the usable level range; otherwise it rounds one component and computes the other as the remainder.

ADOX rates its kit at **2 m² per litre of working solution**. A 325 ml fill corresponds to 0.65 m². Counting each complete 102 × 208 mm cut gives **about 30 prints per fresh pair of fills**; test strips count too. This is an area-based planning estimate, not a lifetime guarantee. The two bath capacities are not added: every print goes through both. The full 2.5 litre kit is rated for 5 m², or about 235 complete cuts of this size. [ADOX / FOTOIMPEX specifications](https://www.fotoimpex.de/shop/fotochemie/adox-ra-4-kit-entwickler-und-bleichfixierbad-monokonzentrate-zum-ansatz-von-2500-ml.html)

The chosen workflow is manual: measure both baths after settling and use your previously tested temperature/time procedure. No thermostat or permanent sensor is included. ADOX's published standard process is 35°C and 45 seconds per bath; temperature compensation here is an intentional experiment, not a supplied manufacturer curve. Wash separately according to the kit instructions. See [heating notes](docs/heating.md).

## Validation and source

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
npm --prefix viewer test
.venv/bin/python scripts/check_v2.py
.venv/bin/python scripts/check_v2_toolpaths.py build/v2-print/vessel_a/vessel_a.gcode
```

The v2 checks cover both aspect presets, manifold solids, printer bounds and placement, liquid volume, whole-image immersion throughout agitation, guide/clip fit, paper clearance, vessel removal, heater-frame clearances and rejected invalid parameters. The optional toolpath check samples deposited paths and verifies that support centre lines do not enter the wet cavity beyond a 0.25 mm boundary tolerance. It is not a physical support-removal test. CI runs geometry and viewer tests; Bambu slicing runs locally.

`v2/parameters.scad` is the shared parameter source. Geometry, volume calculation, vessels, guides, cradle and heater fittings are separated into small modules. Viewer jobs evaluate the same CAD defaults and metadata. The old monolithic design remains available at the repository root; its instructions are in [docs/v1.md](docs/v1.md).
