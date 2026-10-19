# Paper slot processor

An open-top, unheated darkroom tank for dipping photographic paper into two separate baths. Each chamber has an outward-facing 40 mm fill/pour opening, a sloped connecting passage, a fill-level mark, and a large engraved **A** or **B** below its inlet. There are no light traps or plumbed drains.

The default is **120 × 120 mm paper**. The tank, including its funnels, is **144 × 132 × 145.1 mm**. Its wiping slit is **0.6 mm wide** for 0.3 mm paper, with a short **0.4 mm land** and only a **1.5 mm taper above it**. Drips caught by that taper return to the same chamber. Rounded slot ends leave room for the full sheet and insertion clearance.

Hold the paper by the **8 mm grip above the rim**. Fingers stay above the slot. The nominal liquid level leaves about **14 mm of the top edge dry**, including that grip, so allow a handling border on the image. The body and fill height follow the sheet size and grip allowance.

The A-side base is engraved with **182 ml** on the left and **36:146** on the right. The numbers are millilitres in one-part-to-four-parts order, matching `100:400` for a 500 ml batch. Both chambers have the same working volume, so the base labels appear only on side A. All lettering is recessed 0.6 mm.

## Parts

| File | Default output | Print orientation |
| --- | --- | --- |
| `paper_slot_processor.scad` | One two-chamber tank | Base on the bed |
| `paper_slot_processor_inlet_caps.scad` | Two fill caps | Flat outside faces down, plugs up |
| `paper_slot_processor_slit_caps.scad` | Two slot covers | Flat outside faces down, locating ribs up |

Print each file once for a complete five-piece set. The slot covers have shallow locating ribs matched to the drip taper. Rebuild them with the tank when changing the paper or slit settings.

## Change the size

Edit **`lib/parameters.scad`**. All three exports read the same settings. Dimensions are in millimetres.

| Setting | Purpose |
| --- | --- |
| `paper_width`, `paper_height`, `paper_thickness` | Actual sheet dimensions |
| `chamber_count` | One or two independently filled chambers |
| `slot_gap` | Space between the broad chamber walls |
| `paper_face_clearance` | Wiping gap on each face; slit width is paper thickness plus twice this value |
| `paper_grip_height` | Paper exposed above the rim, default 8 mm |
| `entry_depth`, `entry_land_height` | Drip-taper depth and short wiping land, default 1.5 and 0.4 mm |
| `side_clearance`, `entry_end_clearance` | Width clearance; rounded entry ends are accounted for |
| `bottom_clearance` | Space below the fully immersed sheet |
| `inlet_opening_diameter` | Fill mouth and matching cap size |
| `cap_clearance` | Per-side gap for both cap types; decrease only after a fit test |
| `base_enabled`, `rib_enabled`, `inlets_enabled` | Optional features |
| `chamber_labels`, `chamber_names`, `chamber_label_size` | Outside chamber lettering, default A/B at 24 mm |
| `base_volume_labels`, `base_label_size`, `label_depth` | Calculated markings on the A-side base; omitted when the base is disabled |
| `mix_parts` | Two positive whole-number mixing parts in printed order; default `[1, 4]` |
| `volume_rounding_limit_ml` | Maximum adjustment for an exact whole-ml ratio; default 2 ml |
| `build_size`, `bed_margin`, `height_margin` | Printer limits and reserved space |

The [A1 mini's nominal volume is 180 × 180 × 180 mm](https://cdn1.bambulab.com/documentation/Quick%20Start%20Guide%20for%20A1%20mini%20Combo.pdf). With the default 3 mm margin at each XY edge and 2 mm above the print, this design supports **146.5 × 146.5 mm square paper**, or **146.5 × 152.9 mm rectangular paper**. These are sheet dimensions, including the dry handling border. The limits include the independent funnel height and separate cap plates, for these settings and upright orientation. Extra brim width may require more margin.

OpenSCAD reports the tank size, entry size, and paper limits. Invalid combinations stop with an assertion instead of silently producing mismatched parts. Changing the inlet or wall sizes may reduce the available paper size. One or two chambers are supported because each inlet connects directly through an outside wall.

The volume and mixing labels recalculate from the dimensions. The calculation includes the rounded bath, tapered roof and liquid in its inlet/passage up to the fill mark, subtracting both overlapping cavities and the immersed paper's displacement. The mark indicates the nominal level with the sheet inserted. The independent liquid-mesh check verifies the calculation within 0.15 ml across the tested configurations.

Rounding prefers the nearest complete mixing batch: multiples of 5 ml for a 1:4 mix. It uses that total only when it differs from the calculated working volume by no more than 2 ml and leaves at least 1 mm below the wiping edge with the paper immersed. Otherwise it rounds the total to the nearest millilitre, capped by that remaining capacity. The first mixing amount is rounded to a whole millilitre and the second is the total minus the first, so they always add up. The fallback can slightly approximate the ratio. For the default tank, about 182.35 ml becomes **182 ml = 36 + 146 ml**. For 146.5 mm square paper it selects **270 ml = 54 + 216 ml**. Parameter combinations with insufficient headroom for a fill within 2 ml of nominal are rejected.

## Assemble and use

1. Pour the printed working volume into each empty chamber through its outside funnel. Do not top up to the mark before inserting the sheet: the calculation already reserves paper displacement.
2. Remove the slot cover and lower the paper through the narrow slit, holding its dry top border above the rim. Leave the configured 8 mm grip exposed. The lower edge of the shallow mark inside the outward funnel wall is the nominal loaded level; rounding can shift it slightly.
3. Withdraw the paper straight through the short wiping slit and pause above the same bath to let it drain. The shallow upper taper directs caught drips back into that bath.
4. Replace the slot and inlet covers between uses. The tabs lift them out without tools.

Test the fit section with wet scrap paper. The rigid printed wiping edge is intended to reduce carry-over; its finish and clearance determine drag and marking. It cannot guarantee a dry sheet. Increase `paper_face_clearance` if the paper catches or scratches, and rebuild the matching slot covers.

The caps are loose dust/evaporation covers, **not liquid-tight, airtight, or verified light-tight seals**. Keep the tank upright. To change one bath while the other remains full, withdraw liquid through the wide inlet with a suitable siphon or syringe. Do not rely on the caps to contain the other bath when tipping the tank. For independently pourable baths, build two one-chamber tanks instead. Rinse through both openings after emptying; the internal floor corners are rounded and the inlet passages slope back into the chambers.

## Print a fit section first

Set `view = "fit"` in the tank file, or use the command below. This exports the full-width upper **30 mm** of the default tank, including both wiping slits and funnels. It is a fit gauge, with open bottoms, not a liquid container. Check it with the caps and wet scrap paper before printing the full-height tank.

Other tank views are `tank`, `assembly`, `section`, and `handling`. The handling view shows the sheet with its top grip above the rim.

## Build and validate

Install an [OpenSCAD development build with the Manifold backend](https://openscad.org/downloads.html), Bambu Studio, and Python 3.10 or newer. The checked-in build script replaces the old packaged `.skill` archive.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Check physical clearances and invalid settings without a slicer.
.venv/bin/python scripts/check_geometry.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'

# Build, render, check meshes, slice, and export Bambu projects for all three files.
.venv/bin/python scripts/build_openscad.py

# Faster iteration: keep slicing and validation, skip Bambu project thumbnails.
.venv/bin/python scripts/build_openscad.py --skip-bambu-project

# A full-width fit section, saved separately from the production tank.
.venv/bin/python scripts/build_openscad.py --variant fit \
  -D 'view="fit"' paper_slot_processor.scad

# Larger paper; every accessory uses the same overrides.
.venv/bin/python scripts/build_openscad.py --variant largest-square \
  -D paper_width=146.5 -D paper_height=146.5
```

Default results go in `build/<model>/`. Variants go in `build/<variant>/<model>/`, so parameter experiments do not overwrite the default exports. Each contains an openable Bambu `.3mf`, an STL and direct OpenSCAD 3MF under `generated/`, G-code, eight model renders, plate previews, and `validation-summary.json`. The summary includes the overrides, dimensions, mesh checks, slice warnings, time, and filament mass. Build files are ignored by Git.

The default profile is A1 mini / 0.4 mm nozzle / Generic PETG / textured PEI / 0.20 mm layers, with four walls, six top and bottom layers, 15% infill, and no supports. Current time and filament estimates are recorded in each build's validation summary. Change the filament preset to match what is loaded before printing. The script reads mass from the slicer rather than assuming PLA density.

Tool and preset paths can be overridden with `OPENSCAD_BIN`, `BAMBU_STUDIO_BIN`, `BAMBU_SYSTEM_DIR`, `BAMBU_MACHINE`, `BAMBU_PROCESS`, and `BAMBU_FILAMENT`. `--root` or `OPENSCAD_BUILD_ROOT` can select another project root. Paths default to the macOS applications and Bambu system presets.

## Validation limits

The geometry suite checks 80 cases across eight configurations, including both maximum sheet sizes, one chamber, no inlets, reduced clearance, no base/ribs, and thicker paper. It tests solid connectivity, printer bounds, paper insertion, seated caps and finger space above the rim. Liquid probes verify chamber isolation and the volume calculation with and without paper, plus remaining capacity below the wiping edge. Rounding boundaries are tested separately, including whole-ml quantities and their exact sum. Eight invalid configurations must be rejected. GitHub Actions runs these checks with a pinned OpenSCAD container; Bambu slicing is validated locally.

A closed mesh is not evidence that a printed vessel holds liquid. [Print settings and layer adhesion affect watertightness](https://help.prusa3d.com/article/watertight-prints_112324). Test each chamber with water, including cross-leakage into the empty neighbouring chamber. Check the wiping slit on wet scrap paper and the actual cap fit. Material compatibility with the intended chemistry, long-term storage, light exclusion and wiping performance have not been established by these digital checks. PETG is the prototype profile, not a certification for a particular bath.

## Source layout

- `lib/parameters.scad`: shared editable settings, derived dimensions, and constraints.
- `lib/geometry.scad`: capsule, rounded rectangle, and inlet coordinate helpers.
- `lib/volume.scad`: working fill calculation for the base markings.
- `lib/tank.scad`, `lib/caps.scad`: reusable geometry without automatic output.
- Root `.scad` files: print plates and assembly views.
- `tests/geometry.scad`, `scripts/check_geometry.py`: geometry regression fixtures and runner.
- `scripts/build_openscad.py`, `profiles/`: local rendering and slicing pipeline.
