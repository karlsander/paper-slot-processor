# Paper slot processor

An open-top, unheated darkroom tank for dipping photographic paper into two separate baths. Each chamber has an outward-facing 40 mm fill/pour opening, a sloped connecting passage, a fill-level mark, and a large engraved **A** or **B** below its inlet. There are no light traps or plumbed drains.

The default is **120 × 120 mm paper**. The tank is **144 × 132 × 159 mm** and holds approximately **209 ml per chamber** at the fill mark, before paper displacement. The entry is an 8 mm guide that admits the closed tong jaws. Its rounded ends leave enough space for the full sheet and insertion clearance.

The A-side base is engraved with **210 ml** on the left and **42:168** on the right. The numbers are millilitres in one-part-to-four-parts order, matching `100:400` for a 500 ml batch. Both chambers have the same working volume, so the base labels appear only on side A. All lettering is recessed 0.6 mm.

## Parts

| File | Default output | Print orientation |
| --- | --- | --- |
| `paper_slot_processor.scad` | One two-chamber tank | Base on the bed |
| `paper_slot_processor_inlet_caps.scad` | Two fill caps | Flat outside faces down, plugs up |
| `paper_slot_processor_slit_caps.scad` | Two slot covers | Flat outside faces down, locating ribs up |
| `paper_slot_processor_tong.scad` | Tong and separate locking collar | As laid out in the file |

Print each file once for a complete seven-piece set. These caps match the current openings; the earlier 30 mm inlet caps and narrow-slot accessories do not fit this revision.

## Change the size

Edit **`lib/parameters.scad`**. All four exports read the same settings. Dimensions are in millimetres.

| Setting | Purpose |
| --- | --- |
| `paper_width`, `paper_height`, `paper_thickness` | Actual sheet dimensions |
| `chamber_count` | One or two independently filled chambers |
| `slot_gap` | Space between the broad chamber walls |
| `paper_slit_width` | Guide width; must also admit the closed tong |
| `side_clearance`, `entry_end_clearance`, `paper_face_clearance` | Clearance around the sheet; rounded entry ends are accounted for |
| `bottom_clearance` | Space below the fully immersed sheet |
| `inlet_opening_diameter` | Fill mouth and matching cap size |
| `cap_clearance` | Per-side gap for both cap types; decrease only after a fit test |
| `base_enabled`, `rib_enabled`, `inlets_enabled` | Optional features |
| `chamber_labels`, `chamber_names`, `chamber_label_size` | Outside chamber lettering, default A/B at 24 mm |
| `base_volume_labels`, `base_label_size`, `label_depth` | Calculated markings on the A-side base; omitted when the base is disabled |
| `mix_parts` | Two positive whole-number mixing parts in printed order; default `[1, 4]` |
| `volume_rounding_limit_ml` | Maximum adjustment for an exact whole-ml ratio; default 2 ml |
| `build_size`, `bed_margin`, `height_margin` | Printer limits and reserved space |

The [A1 mini's nominal volume is 180 × 180 × 180 mm](https://cdn1.bambulab.com/documentation/Quick%20Start%20Guide%20for%20A1%20mini%20Combo.pdf). With the default 3 mm margin at each XY edge and 2 mm above the print, this design supports **139 × 139 mm square paper**, or **146.5 × 139 mm rectangular paper**. These limits include the separate cap plates. They are limits for these settings and upright orientation, not an absolute maximum for every possible design. Extra brim width may require more margin.

OpenSCAD reports the tank size, entry size, and paper limits. Invalid combinations stop with an assertion instead of silently producing mismatched parts. Changing the inlet or wall sizes may reduce the available paper size. One or two chambers are supported because each inlet connects directly through an outside wall.

The volume and mixing labels recalculate from the dimensions. The calculation includes the rounded bath and liquid in its inlet/passage up to the fill mark, leaving the upper headroom and paper entry empty. It subtracts overlapping cavity volumes. The independent liquid-mesh check verifies this calculation within 0.15 ml across the tested configurations.

Rounding prefers the nearest complete mixing batch: multiples of 5 ml for a 1:4 mix. It uses that total only when it differs from the calculated capacity by no more than 2 ml and fits below the tapered entry with the paper and tong immersed. Otherwise it rounds the total to the nearest millilitre, capped by that remaining capacity. The first mixing amount is rounded to a whole millilitre and the second is the total minus the first, so they always add up. The fallback can slightly approximate the ratio. For the default tank, about 209.3 ml becomes **210 ml = 42 + 168 ml**, without a fixed target in the code. For 139 mm square paper the headroom check selects **274 ml = 55 + 219 ml**. Parameter combinations with insufficient headroom for a fill within 2 ml of nominal are rejected.

## Assemble and use

1. Snap the C-shaped collar onto the arms from the side near the handle. Its flared opening guides the arms past the retaining lips. This avoids forcing a closed ring over the wider jaw pads. Park the collar near the handle to release the jaws.
2. Pour the printed working volume into each empty chamber through its outside funnel. The lower edge of the shallow mark inside the outward funnel wall indicates the unrounded nominal level; the rounded batch can settle slightly above or below it. Do not fill the upper paper entry.
3. Remove the slot cover, grip the paper's top edge between the smooth pads, and move the collar toward the jaws until it holds. The jaw reach is sized to place the paper edge at the liquid surface while keeping the collar above the tank rim. Hold and agitate the paper by hand; the tong is not a hanging clip.
4. Lift the sheet and allow it to drain above its bath before moving it. The wide guide does not squeeze chemistry off the paper.
5. Replace the slot and inlet covers between uses. The tabs lift them out without tools.

The caps are loose dust/evaporation covers, **not liquid-tight, airtight, or verified light-tight seals**. Keep the tank upright. To change one bath while the other remains full, withdraw liquid through the wide inlet with a suitable siphon or syringe. Do not rely on the caps to contain the other bath when tipping the tank. For independently pourable baths, build two one-chamber tanks instead. Rinse through both openings after emptying; the internal floor corners are rounded and the inlet passages slope back into the chambers.

## Print a fit section first

Set `view = "fit"` in the tank file, or use the command below. This exports the full-width upper **30 mm** of the default tank, including both entries and funnels. It is a fit gauge, with open bottoms, not a liquid container. The default PETG profile estimates about 3 h 15 min and 89 g for this section. Check it with the caps, tong, and an actual sheet before printing the full-height tank.

Other tank views are `tank`, `assembly`, `section`, and `handling`. The handling view uses a nominal flexed tong to check reach and clearance; it does not predict spring force. The tong file also accepts `show = "assembled"`, `"tong"`, or `"collar"`.

## Build and validate

Install an [OpenSCAD development build with the Manifold backend](https://openscad.org/downloads.html), Bambu Studio, and Python 3.10 or newer. The checked-in build script replaces the old packaged `.skill` archive.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# Check physical clearances and invalid settings without a slicer.
.venv/bin/python scripts/check_geometry.py
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'

# Build, render, check meshes, slice, and export Bambu projects for all four files.
.venv/bin/python scripts/build_openscad.py

# Faster iteration: keep slicing and validation, skip Bambu project thumbnails.
.venv/bin/python scripts/build_openscad.py --skip-bambu-project

# A full-width fit section, saved separately from the production tank.
.venv/bin/python scripts/build_openscad.py --variant fit \
  -D 'view="fit"' paper_slot_processor.scad

# Larger paper; every accessory uses the same overrides.
.venv/bin/python scripts/build_openscad.py --variant largest-square \
  -D paper_width=139 -D paper_height=139
```

Default results go in `build/<model>/`. Variants go in `build/<variant>/<model>/`, so parameter experiments do not overwrite the default exports. Each contains an openable Bambu `.3mf`, an STL and direct OpenSCAD 3MF under `generated/`, G-code, eight model renders, plate previews, and `validation-summary.json`. The summary includes the overrides, dimensions, mesh checks, slice warnings, time, and filament mass. Build files are ignored by Git.

The default profile is A1 mini / 0.4 mm nozzle / Generic PETG / textured PEI / 0.20 mm layers, with four walls, six top and bottom layers, 15% infill, and no supports. The complete default set is estimated at about **17 hours and 485 g**; the tank accounts for about **14 h 49 min and 423 g**. Estimates depend on the selected material and presets. Change the filament preset to match what is loaded before printing. The script reads mass from the slicer rather than assuming PLA density.

Tool and preset paths can be overridden with `OPENSCAD_BIN`, `BAMBU_STUDIO_BIN`, `BAMBU_SYSTEM_DIR`, `BAMBU_MACHINE`, `BAMBU_PROCESS`, and `BAMBU_FILAMENT`. `--root` or `OPENSCAD_BUILD_ROOT` can select another project root. Paths default to the macOS applications and Bambu system presets.

## Validation limits

The geometry suite checks 77 cases across the default, one-chamber, largest square, largest rectangle, smaller/no-inlet, reduced-clearance, and base/rib-free settings. It tests solid connectivity, printer bounds, the whole paper insertion path, seated caps, the collar's release position, and jaw immersion. A virtual liquid volume must contain exactly one isolated cavity per chamber, including its inlet. Its measured volume is compared with the calculation and rounded label. A second liquid probe checks that the printed volume fits below the tapered entry with the paper and nominal tong immersed. Rounding boundaries are tested separately, including whole-ml quantities and their exact sum. Seven invalid configurations must be rejected. GitHub Actions runs these checks with a pinned OpenSCAD container; Bambu slicing is validated locally.

A closed mesh is not evidence that a printed vessel holds liquid. [Print settings and layer adhesion affect watertightness](https://help.prusa3d.com/article/watertight-prints_112324). Test each chamber with water, including cross-leakage into the empty neighbouring chamber. Test the tong on wet scrap paper for grip, marking and repeated flexing, and check the actual cap fit. Material compatibility with the intended chemistry, long-term storage, light exclusion, and physical spring performance have not been established by these digital checks. PETG is the prototype profile, not a certification for a particular bath.

## Source layout

- `lib/parameters.scad`: shared editable settings, derived dimensions, and constraints.
- `lib/geometry.scad`: capsule, rounded rectangle, and inlet coordinate helpers.
- `lib/volume.scad`: working fill calculation for the base markings.
- `lib/tank.scad`, `lib/caps.scad`, `lib/tong.scad`: reusable geometry without automatic output.
- Root `.scad` files: print plates and assembly views.
- `tests/geometry.scad`, `scripts/check_geometry.py`: geometry regression fixtures and runner.
- `scripts/build_openscad.py`, `profiles/`: local rendering and slicing pipeline.
