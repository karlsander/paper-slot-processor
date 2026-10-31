# Bambu Studio projects — processor v1.8

## Individual files for printing

The current handoff is `build/processor-individual-bambu-2026-10-28.zip`:
**seven single-part, single-plate projects**, all for A1 mini / 0.4 mm nozzle /
PETG / Textured PEI / 0.20 mm layers. Open each `.3mf` as a project and retain
its settings and orientation.

| File prefix | Part | Print for |
| --- | --- | --- |
| 01 | Shared base | Either bath length |
| 02 | Top A | Either bath length |
| 03 | Top B | Either bath length |
| 04 | Short bath A | 102 × 208 mm paper |
| 05 | Short bath B | 102 × 208 mm paper |
| 06 | Tall bath A | 102 × 230 mm paper |
| 07 | Tall bath B | 102 × 230 mm paper |

For one complete processor, print **01–03 plus either 04–05 or 06–07**. Printing
all seven gives one base, two tops and two interchangeable bath pairs. The shared
base now has A/B labels without a size-specific volume. The fill ridge inside
each bath remains calibrated to its own volume: 323 ml short, 360 ml tall.

Both tops are identical across the two length presets. Both slots are 110 mm
long, giving nominally 4 mm at each end of centered 102 mm paper; the cavity is
122 mm wide, giving 10 mm per side below the top. The slot has rounded ends.

Chamber body heights are 204.33 mm (short) and 227 mm (tall). At the supplied
44.2° print tilt, the taller chamber mesh occupies 152 × 173.31 × 176.68 mm.
The top prints separately. Preserve the tilt, supports and 3 mm brim.

Each saved single-part file is reopened without preset overrides and sliced;
the exporter checks exactly one plate/object, source mesh preservation, printer
and material settings, generated supports, warnings and embedded G-code.
Per-file estimates and hashes are in
[individual project evidence](evidence/v1.8-bambu-individual.json).

Reproduce one file by adding `--part` to the command below, for example:

```sh
.venv-cad/bin/python scripts/build_native_bambu.py build/native-16x9 build/bambu-base --nozzle .4 --part base --name 01-Base-A1mini-PETG-0.4mm
```

Allowed parts: `base`, `guide_a`, `guide_b`, `vessel_a`, `vessel_b`. Use the
appropriate native preset folder for short/tall vessels. Regenerate the shared
base from current CAD to get the A/B-only labels.

## Earlier five-plate projects

These earlier exports are retained for reference; the individual files above
are the simpler printing handoff.

Each .3mf is one complete five-plate project: base, chamber A, chamber B, top A,
top B. Print each plate once. The files include the latest half-height tapered
base with 16 mm exposed sleeves, a 180 × 180 mm footprint and 25 mm chamber gap.

Choose a paper size and installed nozzle:
- 16x9: 102 × 208 mm paper cut, 102 × 181 mm image, 323 ml per bath.
- 2x1: 102 × 230 mm paper cut, 102 × 204 mm image, 360 ml per bath.
- 0.4mm: recommended first prototype; 0.20 mm layers.
- 0.2mm: alternative for the smaller nozzle; 0.10 mm layers, much slower.

All files use Bambu Lab A1 mini, Generic PETG, Textured PEI Plate, four walls,
15% infill and 1.2 mm top/bottom shells (six or twelve layers). Set your actual
filament/plate if they differ. The colour shown is just the project colour.

Chambers retain their supplied 44.2° tilt and sacrificial bed rail. Their object
settings enable build-plate-only tree supports at 30° and a 3 mm outer brim.
Base and inverted tops have support/brim disabled. Do not auto-orient, scale or
rearrange the parts; the full-bed base has no spare margin for a brim.

Open the file as a project in Bambu Studio, keeping its embedded configuration.
Use Prepare for editing and Slice plate/all then Preview to inspect the selected
plate before printing. All four saved projects were reopened and all 20 plates
successfully sliced with no warnings using Bambu Studio 2.7.1.57. Saved printer,
nozzle, filament, layer/shell settings and per-object supports were verified.
The .3mf archives include the generated G-code as well as editable geometry.
The default 16x9 / 0.4 mm project was also opened in the GUI and visually checked.

Slicer estimates (including supports/brims, excluding handling/failed prints):

| Project | Total time | PETG |
| --- | ---: | ---: |
| 16x9-02 | 155h 45m 24s | 621.96 g |
| 16x9-04 | 27h 05m 43s | 715.38 g |
| 2x1-02 | 166h 45m 55s | 665.93 g |
| 2x1-04 | 28h 52m 55s | 763.32 g |

Use these saved-project estimates for the supplied files. Re-slicing the taller
vessels changes the previous estimates by up to several minutes and less than
0.5 g per complete set; the nominal shapes and settings are preserved. [saved project evidence](evidence/v1.8-bambu-projects.json) records
per-part results and SHA-256 hashes for the four .3mf files.

First physical trials remain untested: water tightness, wet-paper handling,
magnet fit/retention and actual printer performance need checking. No print job
has been sent. Geometry and reproducible exporter: PR #13,
https://github.com/karlsander/paper-slot-processor/pull/13

## Reproduce

```sh
.venv-cad/bin/python scripts/build_native_bambu.py build/native-16x9 build/bambu-16x9-04 --nozzle .4 --name Processor-v1.8-16x9-A1mini-PETG-0.4mm
```

Pass a native export folder containing `plates/`. The exporter resolves installed
Bambu Studio profiles, creates five plates using Bambu's assemble-list importer,
then reopens the saved project without external setting overrides and slices all
five plates. It verifies saved settings, generated supports, plate counts, warnings
and embedded G-code before replacing the project with the sliced version.
