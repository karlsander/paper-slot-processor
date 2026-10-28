# Native build123d processor

The complete **unheated v1.8** design is authored in Python under `cad/`: one shared
base, two baths, two guides and four retaining clips. Optional resting covers,
a top-rim fit sample and 0.6/0.8 mm trial guides are included. The bath geometry
preserves the flat rear interface for later heater development.

`cad/parameters.py` is the native configuration authority. It calculates image size,
cut length, capacity, recipe amounts, fill levels, print tilt and shared-base layout
without OpenSCAD. `cad/parts.py` creates the solids; `cad/export.py` exports the
complete set. OpenSCAD is used only as the migration comparison oracle. The older
v2 heater fittings and the existing v2 web viewer retain their original workflow.

## Generate parts

```sh
uv venv --python python3.13 .venv-cad  # omit when already present
uv pip install --python .venv-cad/bin/python -r cad/requirements.txt
.venv-cad/bin/python -m cad.export --output build/native-16x9
.venv-cad/bin/python -m cad.export --aspect 2 --output build/native-2x1
```

A `--config settings.json` file can override fields in `cad.parameters.DEFAULTS`.
Unknown keys, invalid dimensions and configurations outside the reserved A1 mini
bounds fail explicitly. The two supplied presets remain 325 ml / 208 mm cut and
362 ml / 230 mm cut. Both use the 170.8 × 138 mm shared base.

Each output contains:

- Individual STEP solids in their local design coordinates.
- `assembly.step`: the nine working pieces in assembled positions.
- `plates/*.stl` and `plates/*.step`: oriented print plates, including the vessel
  sacrificial rails. Print **one of each** base, vessel A/B, guide A/B and clips
  plate. The clips plate contains all four clips.
- Optional cover A/B, fit sample and trial guide plates. These are alternatives
  or accessories, not extra parts required by the nine-piece assembly.
- `parameters.json` and `model-report.json`: dimensions, quantities, native-solid
  validity, print bounds and any removed zero-area tessellation triangles.
- `parity/`: unlettered functional geometry used for comparison with OpenSCAD.

The STEP files in the top directory describe finished parts; use the **plates**
files for printing. Preserve the vessel orientation. Use the PETG, support and
brim settings in [the v1.8 instructions](v1.8.md); this command does not run a slicer
or claim print-time estimates. Start with the fit sample, guide and clips.

## Verify in FreeCAD

```sh
.venv-cad/bin/python scripts/check_native.py
# Or check an already exported matching preset:
.venv-cad/bin/python scripts/check_native.py --aspect 2 \
  --output build/native-2x1 --skip-export
```

The default checks both presets under `build/native-checked/`. It requires
OpenSCAD with Manifold and FreeCADCmd. Set `OPENSCAD_BIN` and `FREECAD_CMD`, or
use `--freecad`, when they are not discoverable. The macOS FreeCAD application
location is the fallback.

The checks cover:

- Native parameters against the original OpenSCAD calculation, to its printed
  numerical precision (0.001 mm/ml maximum absolute difference).
- Every exported part imported as one valid FreeCAD solid, with volume preserved.
- All 13 part variants compared with OpenSCAD: sampled boundary deviation below
  0.05 mm and relative volume difference below 0.3%, allowing polygonal arcs.
- All print plates: watertight STL, correct STEP solid count, bed contact and
  reserved 174 × 174 × 178 mm dimensions within the 180 mm printer volume.
- Every pair in the nine-piece assembly, cover substitution, clip sliding, guide
  lifting and each complete bath module lifting beside the other module.
- 0.6 mm socket clearance; empty and paper-loaded cavity volumes within 0.5 ml of
  the recipe; paper travel through all three guide gaps at the agitation extremes.
- A conservative continuous paper-travel envelope through the default guide and
  bath. Other movement checks use the listed sampled positions.

`validation.json` is written only after all checks pass. `processor.FCStd` contains
the working assembly plus raised optional covers. A headless-created document may
need its objects selected and toggled visible in FreeCAD. The runner removes a
previous report before starting, because a FreeCAD console exception can still
return process exit code zero.

The comparison intentionally excludes lettering: both models use Liberation Sans
Bold, but OCCT and OpenSCAD font metrics differ. The font and its SIL Open Font
License are bundled in `cad/fonts/` to avoid machine-dependent substitutions.
Tactile identifiers and engraved fill marks are included in functional comparison.
The guide loft retains a 0.001 mm straight segment at the fully rounded slot limit
to keep its corner correspondence stable. This is below the comparison tolerance;
it does not alter the nominal guide gap.

The exporter removes zero-area STL triangles before checking watertightness. It
does not fill mesh holes or alter a solid to force a passing result.

## Render video

After validation passes, render with FreeCAD's GUI and encode with ffmpeg:

```sh
python3 scripts/render_native_video.py build/native-checked/16x9
```

`FREECAD_GUI` or `--freecad` selects the GUI executable. The renderer uses the actual
exported STEP parts and captures FreeCAD's viewport, with captions and measurements.
The sequence shows assembly, clip removal, guide removal, bath removal, filling,
paper agitation and optional covers. A fresh passing frame report is required
before encoding; ffprobe verifies the frame count and 1280 × 720 output.

The result is `processor-build123d.mp4`, with `video-report.json`, encoding metadata
and source frames alongside it. Filling intersects the wet cavity with a horizontal
plane; paper displacement changes the equilibrium level during agitation. This is
**geometric visualization, not fluid dynamics**, and does not predict pouring,
splashing, mixing or cooling. The rendered movement is prescribed, not a mechanism
or force simulation.

## Local results (2026-10-28)

| Check | 16:9 | 2:1 |
| --- | ---: | ---: |
| Valid STEP part variants | 13/13 | 13/13 |
| Valid print plates | 13/13 | 13/13 |
| Clear working-assembly pairs | 36/36 | 36/36 |
| Complete bath removal samples | 18/18 | 18/18 |
| Paper / guide agitation cases | 54/54 | 54/54 |
| Maximum sampled SCAD surface deviation | 0.0192 mm | 0.0169 mm |
| Maximum relative SCAD volume difference | 0.0734% | 0.0734% |
| Working liquid per bath | 325 ml | 362 ml |
| Maximum measured fill error, empty or loaded | <0.00001 ml | <0.00001 ml |

The tiny fill errors describe numerical agreement, not a practical measuring or
printing tolerance. These checks used build123d 0.13.0 and FreeCAD 1.1.4 on macOS.

![Native processor assembly rendered in FreeCAD](images/native-processor.png)

## Evidence boundaries

The native CI job builds both presets and validates solids, meshes and print bounds.
FreeCAD checks and video rendering run locally. The original geometry CI remains as
a regression check for the retained OpenSCAD design.

Digital checks do not establish printed fit, elasticity, paper friction, liquid
tightness, chemical compatibility or support removal. Test with water and scrap
paper before chemistry. Neither build123d nor FreeCAD verification here models
those effects; both also share the Open Cascade geometry kernel.
