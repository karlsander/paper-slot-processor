# Durst C35 insertion-area reference

This model replaces the *assumptions* behind the earlier two-ledge sketch with the visible head neck, black underside plate, six screw heads, and the raised lower support with its wider flange. It is a partial reconstruction for future carrier studies, not a dimensionally complete OEM model or a print replacement for the enlarger.

The measured front profile uses **88.55 mm external neck width**, **11.4 mm neck height (L)**, **86.7 mm lower support width (M)**, **10.5 mm lower support height (N)** and **95.3 mm flange width (O)**. The unloaded vertical gap is **approximately 6 mm**. The closed original carrier is approximately **6.15 mm** high. The user reports that the lower support moves when inserting it. These are separate observations: they do not establish spring stiffness, insertion force, local screw clearances, or the film plane.

![Front-view measurement endpoints](measurements-L-O.png)

## Recorded front measurements: L-O

These labels are new and do not reuse the earlier A-K sheet. The previous **C / assumed support ledges is withdrawn**. B-head means the outside width of the narrow head, not an inside slot width.

| Label | Reading (mm) | Measurement | Exact endpoints |
| --- | --- | --- | --- |
| L | 11.4 | Narrow white band height | From underside of the wider white shoulder to the flat underside of the narrow white band; exclude slot and protruding screws. |
| M | 86.7 | Raised black support width | Outside left to outside right of the raised black section directly below the slot; exclude its wider thin flange. |
| N | 10.5 | Raised black support height | Top contact surface down to **top of flange**, excluding flange thickness. Use the straight part away from rounded corners. |
| O | 95.3 | Black flange overall width | Its leftmost to rightmost outside edges, immediately above the bellows. |

These readings were supplied on 2026-11-01 and are applied to the model. The original annotation retains its request labels as an endpoint guide. It is an imagegen overlay on IMG_1078; the original photo and actual caliper readings remain authoritative. It must not be used to extract numerical dimensions. The exact built-in imagegen prompt is saved in [annotation-prompt.txt](annotation-prompt.txt).

Next: measure actual lower opening/contact surfaces, optical opening and front-to-optical position. Then locate each screw centre and protrusion, any physical insertion stop, and the original carrier's rim spacing/film seat height. The outer housing and rear flange extents also remain provisional. Those later dimensions are not being inferred from photographs.

## Recorded side-view measurements: P-S

IMG_1079 shows the front on the left and the column/rear on the right. The user supplied these readings and explicitly confirmed that **the narrow white head and raised black support end at the same rear plane**. The earlier shallow lower-support model and misleading Q arrow are superseded by this correction.

| Label | Reading (mm) | Measurement / model parameter |
| --- | --- | --- |
| P | 98.3 | Narrow white band's front-to-back depth, excluding the wider housing (`neck_depth`). |
| Q | 98.3 | Raised black support's front-to-back depth, excluding the fixed rear housing (`lower_depth`). Its rear face coincides with P's rear face. |
| R | 2.5 | Thin black flange's thickness, excluding raised support and bellows (`flange_thickness`). |
| S | 4.5 | Flange projection ahead of the raised support's straight front face (`flange_front_overhang`). |

Equal depths plus the explicitly shared rear plane imply a **0 mm front-face offset** (`lower_front_offset = Q - P`). That offset is labelled `derived_from_user`, not a separate caliper reading. The neck and raised support now both span Y=-98.3 to Y=0. A section-based native check verifies these end planes, excluding the wider housing and flange. Q is not an established insertion stop or usable travel.

The cropped outer housing remains an envelope: its former unmeasured 4 mm front/rear overhangs are retained, giving a provisional depth of 106.3 mm. The flange retains its former **unmeasured 9 mm rear extension**; its provisional total depth is now Q + S + 9 = 111.8 mm. Neither total is a user measurement. The shared rear plane applies to the neck and raised support; rear flange extent still needs confirmation.

The [original photo annotation](measurements-P-S.png) and [built-in imagegen prompts](side-annotation-prompts.txt) remain as historical records. Their uncertain Q endpoint does not override the corrected readings or datum relationship above. No new values were inferred from pixels.

## Evidence and editable parameters

[`measurements.json`](../../cad/durst_c35_interface/measurements.json) is the single source for dimensions. Every value has a status, source and (where applicable) photo label. `user_measured` records the supplied reading without claiming caliper accuracy; `user_approximate` preserves the approximate gap. `derived_from_user` records a dimension calculated from explicit readings/observations. Unmeasured values remain `provisional`, and the truncated upper housing height is a `display_extent`.

When a reading arrives, change its `value`, `status` and `source` together, then rebuild. Never turn a visually estimated number into a measured one merely because a CAD check passes. Local photo filenames and hashes are recorded in `photo-evidence.json` so geometry observations are traceable without committing the original high-resolution photos.

The lower interior is an **open rectangular envelope**, not a claim that its unseen contact surfaces form four uniform lands. Screw heads are simple cylinders for collision checks: six are visible, but their diameter, projection and coordinates are unmeasured. The black plate's front tab is represented with its function left unassigned. No rear stop or hidden spring mounting has been invented.

## Datums and lower-support movement

- X: left/right; positive to the right when facing the entry.
- Y: positive toward the operator. Insertion is along negative Y.
- Z: upward. **Z=0 is the flat underside of the head**, excluding screw protrusions.
- Origin: centre of the narrow head's front edge at that underside plane.
- Resting lower contact plane: `Z = -slot_gap`.
- A positive `lower_drop_mm` moves only the lower support downward.

The FreeCAD document exposes `InterfaceParameters.LowerDrop`, with an expression driving the lower support. The other native solids stay fixed. This is an inspectable placement scenario, **not a force simulation or reconstructed bending shape**. The 0.15 mm illustrative placement is only `6.15 - 6.0`; it does not prove the actual deflection or force because contact locations, original compliance and screw clearance remain unknown.

With the **provisional** 0.5 mm screw projection, the local plane separation under a screw is 5.5 mm at rest, even though the flat gap is 6 mm. That example demonstrates why the screws must remain explicit obstacles. It is not a measured 5.5 mm clearance or evidence that a carrier actually passes beneath those heads.

The native file contains imported B-reps and editable lower-support placement. To change dimensions such as L-O, regenerate it from build123d/JSON; changing the informational FreeCAD `HeadWidth` property alone does not rebuild the B-rep.

## Build and verify

```sh
python -m pip install -r cad/requirements.txt
python -m unittest discover -s tests -p test_durst_interface.py
python scripts/check_durst_interface.py --freecad /path/to/freecadcmd
```

Without FreeCAD, `python -m cad.durst_c35_interface.export` exports and checks build123d geometry only. `--measurements path.json` and `--output folder` support another measured revision without editing source code.

Outputs under `build/durst-c35-interface/`:

- `assembly.step` and nine separately named STEP solids.
- `insertion-area.FCStd`, saved/reopened and with lower-support placement checked.
- `measurements.json`, `manifest.json`, `freecad-validation.json` and console log.

The controls test imported solid validity and volume agreement, separation between fixture parts, the measured neck section width, clear optical passage through the provisional openings, interference above the nominal slot height and local interference at a screw. They also verify the saved lower-support expression after reopening the FreeCAD document. They do **not** test the complete carrier, force, light leakage, repeatability or physical manufacture.

Optional preview, rendered from the verified STEP files:

```sh
python -m pip install 'pyvista==0.49.1'
python -m cad.durst_c35_interface.render
```

![Native model preview](model-preview.png)

## Integration with the carrier studies

This fixture is an independent module on current `main`; the B2 carrier work remains in open PR #15. The old fixture's optical-origin coordinates and 2.6 mm gap must not be silently reused. `legacy_carrier_alignment` is deliberately unset. Once the film-seat height and optical position are measured, place the carrier explicitly in these datums and rerun insertion/contact checks against these solids. The new reference does not inherit the old fixture's passing fit results.

No material, support stiffness, friction or force result is attached to this model. All reports keep `physical_fit_accepted: false` until physical fit is established independently.
