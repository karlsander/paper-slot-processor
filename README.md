# Paper slot processor

V2 is being rebuilt on `codex/processor-v2`. Its CAD entry point is
`v2/processor.scad`, with removable vessels, interchangeable guides, a split
cradle and a flat heater mounting plate. The default 102 mm roll produces a
181.3 × 102 mm image from a 208 mm cut; `image_aspect=2` produces a 204 × 102 mm
image from a 230 mm cut. Each cut includes a sacrificial handling strip.

Run `python scripts/check_v2.py` for the new geometry and assembly checks, and
`python scripts/build_v2.py vessel_a vessel_b` to export and slice the tilted
vessels. The heater guard, heating assessment, full print bundle and viewer
integration are still in progress. The instructions below describe v1.

An open-top, unheated darkroom tank for dipping photographic paper into two separate baths. Each chamber has an outward-facing 40 mm fill/pour opening, a smoothly flared bowl and rounded descending bore, a fill-level mark, and a large engraved **A** or **B** below its inlet. There are no light traps or plumbed drains.

The default is **120 × 120 mm paper**. The tank, including its funnels, is **144 × 132 × 145.6 mm**. Its wiping slit is **0.6 mm wide** for 0.3 mm paper, with a short **0.4 mm land** and only a **1.5 mm taper above it**. Drips caught by that taper return to the same chamber. Rounded slot ends leave room for the full sheet and insertion clearance.

Hold the paper by the **8 mm grip above the rim**. Fingers stay above the slot. The nominal liquid level leaves about **14 mm of the top edge dry**, including that grip, so allow a handling border on the image. The body and fill height follow the sheet size and grip allowance. The indicated fill is calibrated before paper insertion; the dry border is calculated after insertion.

The A-side base is engraved with **187 ml** on the left and **37:150** on the right. The numbers are millilitres in one-part-to-four-parts order, matching `100:400` for a 500 ml batch. Both chambers have the same working volume, so the base labels appear only on side A. All lettering is recessed 0.6 mm.

## Parts

| File | Default output | Print orientation |
| --- | --- | --- |
| `paper_slot_processor.scad` | One two-chamber tank | Base on the bed |
| `paper_slot_processor_inlet_caps.scad` | Two fill caps | Flat outside faces down, plugs up |
| `paper_slot_processor_slit_caps.scad` | Two slot covers | Flat outside faces down, locating ribs up |

Print each file once for a complete five-piece set. The slot covers have shallow locating ribs matched to the drip taper. Rebuild them with the tank when changing the paper or slit settings.

## Change the size

For interactive changes, use the local viewer below. To change the checked-in defaults, edit the shared OpenSCAD file.

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
| `inlet_bore_diameter`, `inlet_bend_height` | Rounded passage size and gradual turn into its 45° descent |
| `inlet_funnel_height` | Smooth flare height; must be tall enough for the mouth diameter to print without supports |
| `inlet_sight_depth` | Target depth of the small visible pool before whole-ml rounding, default 1.5 mm |
| `fill_headroom` | Empty-tank level below the wiping edge; default 6 mm reserves paper displacement |
| `cap_clearance` | Per-side gap for both cap types; decrease only after a fit test |
| `base_enabled`, `rib_enabled`, `inlets_enabled` | Optional features |
| `chamber_labels`, `chamber_names`, `chamber_label_size` | Outside chamber lettering, default A/B at 24 mm |
| `base_volume_labels`, `base_label_size`, `label_depth` | Calculated markings on the A-side base; omitted when the base is disabled |
| `mix_parts` | Two positive whole-number mixing parts in printed order; default `[1, 4]` |
| `volume_rounding_limit_ml` | Maximum adjustment for an exact whole-ml ratio; default 2 ml |
| `build_size`, `bed_margin`, `height_margin` | Printer limits and reserved space |

The [A1 mini's nominal volume is 180 × 180 × 180 mm](https://cdn1.bambulab.com/documentation/Quick%20Start%20Guide%20for%20A1%20mini%20Combo.pdf). With the default 3 mm margin at each XY edge and 2 mm above the print, this design supports **146.5 × 146.5 mm square paper**, or **146.5 × 152.4 mm rectangular paper**. These are sheet dimensions, including the dry handling border. The limits include the independent funnel height and separate cap plates, for these settings and upright orientation. Extra brim width may require more margin.

OpenSCAD reports the tank size, entry size, and paper limits. Invalid combinations stop with an assertion instead of silently producing mismatched parts. Changing the inlet or wall sizes may reduce the available paper size. One or two chambers are supported because each inlet connects directly through an outside wall.

The 40 mm mouth narrows smoothly to a 14 mm round horizontal section, then curves into a 45° descending bore. Its minimum normal section is approximately 14 × 9.9 mm (elliptical on the incline), with about 109 mm² of flow area. The bowl and bore share one continuous loft, with no flat sump or sideways rectangular throat. The bore finishes inside its own chamber and cannot enter the divider. Both inner and outer slopes are constrained for upright printing; the bulky buttress is no longer needed.

At the default **187 ml** fill, the liquid settles about **1.23 mm** above the start of the flare, leaving approximately **0.19 ml** visible in the bowl. This is the full cue. Before that level is reached, liquid can descend through the bore; the cue is connected to the bath and is not a retaining pocket. The indicator is for an empty tank on a level surface. Transient liquid during pouring is not the cue: slow down and pause near the mark to let the levels settle. After insertion of the default sheet, the calculated liquid level is about 2.47 mm higher, with about 13.7 mm of paper still dry.

The volume calculation integrates the actual loft stations and subtracts the overlap with the bath. It includes the liquid in the descending bore. Independent liquid meshes verify the calculation within 0.15 ml across the tested configurations. The engraved mark follows the actual rounded batch level, not an unrounded nominal height.

Rounding prefers complete mixing batches: multiples of 5 ml for a 1:4 mix. The candidate must stay within 2 ml of the nominal volume, leave at least 1 mm below the wiping edge with paper inserted, and keep the visible pool between 0.5 and 2.5 mm deep. Otherwise it chooses a whole-ml total within those limits. The first mixing amount is rounded and the second is total minus first, so they always add up; this fallback can slightly approximate the ratio. The default nominal 187.48 ml becomes **187 ml = 37 + 150 ml**. Invalid combinations are rejected rather than hiding the cue or consuming the paper's headroom.

## Assemble and use

1. Set the tank level and remove the inlet and slot covers from the chamber being filled, allowing air to escape.
2. With **no paper inserted**, pour the printed working volume through the wide inlet. Slow down near the engraved mark and pause. A small pool that remains at the lower edge of the mark indicates the intended fill. Do not fill the large funnel to its rim.
3. Insert the paper through the wiping slit, leaving the configured 8 mm grip exposed. The liquid rises by the reserved displacement. Do not use the empty-tank fill cue to top up while paper is present.
4. Withdraw the paper straight through the short wiping slit and pause above the same bath to let it drain. The shallow upper taper directs caught drips back into that bath.
5. Replace the slot and inlet covers between uses. The tabs lift them out without tools.

Test the fit section with wet scrap paper. The rigid printed wiping edge is intended to reduce carry-over; its finish and clearance determine drag and marking. It cannot guarantee a dry sheet. Increase `paper_face_clearance` if the paper catches or scratches, and rebuild the matching slot covers.

The caps are loose dust/evaporation covers, **not liquid-tight, airtight, or verified light-tight seals**. Keep the tank upright. To change one bath while the other remains full, withdraw liquid through the wide inlet with a suitable siphon or syringe. Do not rely on the caps to contain the other bath when tipping the tank. For independently pourable baths, build two one-chamber tanks instead. Rinse through both openings after emptying; the internal floor corners are rounded and the inlet passages slope back into the chambers.

## Print a fit section first

Set `view = "fit"` in the tank file, or use the command below. This exports the full-width upper **68 mm** of the default tank, including both wiping slits and the complete curved inlet paths. It is a fit gauge, with open bottoms, not a liquid container. Check it with the caps and wet scrap paper before printing the full-height tank.

Other tank views are `tank`, `assembly`, `section`, and `handling`. The handling view shows the sheet with its top grip above the rim.

## Build and validate

### Local interactive viewer

Install Node.js 22 or newer, Python 3.10 or newer, and the OpenSCAD development build described below. Bambu Studio and its A1 mini / Generic PETG presets provide the print estimates.

```sh
./scripts/start_viewer.sh
# Or keep the browser closed / choose a different port:
./scripts/start_viewer.sh --no-browser --port 8766
```

The launcher installs the local Python and npm dependencies on first use, bundles the viewer, and opens **http://127.0.0.1:8765**. It listens only on this computer. Press Ctrl+C in the launching terminal to stop it. After setup, the viewer loads its assets locally; no CDN or account is needed.

- Drag to rotate, scroll to zoom, or right-drag to pan. Top/front views, a cutaway, the empty-tank **Fill level** overlay and a 180 mm bed grid help inspect the geometry.
- Adjust paper dimensions, wiping clearance, grip height, chamber and inlet dimensions, or advanced wall/base/cap settings. The default and maximum-size paper presets restore the other source defaults as well.
- Choose the tank, inlet caps, slot covers or fit section. **Estimates apply to the selected plate**, including both caps when applicable.
- The model updates first, followed by Bambu's print time, filament weight and filament volume for the configured profile. Solid model volume is shown separately: it does not account for infill. Working bath volume and mixing quantities recalculate with the geometry.
- Download the current STL, Bambu project, and a JSON record of the dimensions and resolved print profile. The Bambu project contains the model and profile for reslicing; it is not a ready-to-send G-code package.

Edits are saved in this browser and do not alter the OpenSCAD sources. Each build takes an isolated source snapshot under `build/viewer/`. Invalid geometry shows the OpenSCAD error; older estimates are cleared immediately on an edit. New builds cancel older ones, and finished results are cached by source content, parameters, selected plate and print profile. Up to 12 jobs are kept per server session; prior-session files can be removed from `build/viewer/` while the server is stopped. The Settings download records a configuration; settings import is not implemented.

The viewer uses the same environment variables and checked-in PETG profile as the command-line builder. Restart it after changing tool or profile paths. If Bambu Studio or its presets are unavailable, previews and STL downloads still work, with a message explaining why print estimates are unavailable. OpenSCAD is required for both modes. Multiple browser tabs share one build queue; the newest edit takes precedence.

Frontend checks: `cd viewer && npm ci && npm test && npm run build`. Server checks are included in the Python unit-test command below. The interactive canvas uses [Three.js](https://threejs.org/) with its license included in the local bundle.

### Command-line exports

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

The geometry suite checks 88 cases across eight configurations, including both maximum sheet sizes, one chamber, no inlets, reduced clearance, no base/ribs, and thicker paper. It tests solid connectivity, printer bounds, paper insertion, seated caps and finger space above the rim. Liquid probes verify chamber isolation and the volume calculation with and without paper, plus remaining capacity below the wiping edge. Rounding boundaries are tested separately, including whole-ml quantities and their exact sum. Twenty further inlet cases check connected liquid below the cue and near the outlet, bore clearance, a small visible pool and printable inner slopes. Ten invalid configurations must be rejected. GitHub Actions runs these checks with a pinned OpenSCAD container; Bambu slicing is validated locally.

A closed mesh is not evidence that a printed vessel holds liquid. [Print settings and layer adhesion affect watertightness](https://help.prusa3d.com/article/watertight-prints_112324). Test each chamber with water, including cross-leakage into the empty neighbouring chamber. Check the wiping slit on wet scrap paper and the actual cap fit. The visible cue and drainage rate also need confirmation on a level water-filled print; surface finish and wetting can affect the apparent meniscus. Material compatibility with the intended chemistry, long-term storage, light exclusion and wiping performance have not been established by these digital checks. PETG is the prototype profile, not a certification for a particular bath.

## Source layout

- `lib/parameters.scad`: shared editable settings, derived dimensions, and constraints.
- `lib/geometry.scad`: capsule, rounded rectangle, and inlet coordinate helpers.
- `lib/inlet.scad`: round loft stations, curved bore and printable flare.
- `lib/volume.scad`: working fill, visible indicator and paper-displacement calculations.
- `lib/tank.scad`, `lib/caps.scad`: reusable geometry without automatic output.
- Root `.scad` files: print plates and assembly views.
- `tests/geometry.scad`, `scripts/check_geometry.py`: geometry regression fixtures and runner.
- `scripts/build_openscad.py`, `profiles/`: local rendering and slicing pipeline.
