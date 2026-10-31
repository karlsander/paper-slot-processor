# Local V0.2 evidence — 2026-10-31

These reports come from `scripts/check_durst_geometry.py` (build123d 0.13.0,
FreeCAD 1.1.4 on macOS) and `scripts/build_durst_bambu.py` (installed Bambu Studio).
The geometry source hashes and exported STEP/STL hashes are in `model-report.json`.
The FreeCAD and Bambu reports identify that model report by SHA-256.

Both halves passed the 1.2 mm panel probes, hollow-exterior checks, print-mesh
checks, optical/film checks, and 181 sampled hinge positions. Both native FreeCAD
documents were saved and reopened successfully. Each single-part Bambu project
was reopened and sliced without warnings; source vertices, bed placement and
embedded A1 mini / PETG / 0.4 mm settings were verified. All 36 repository Python
tests passed in the native CAD environment, including deliberate slab regressions.

This snapshot is local evidence. Hosted CI results are attached to the PR separately.
No GUI slider interaction was established by this headless run. No printed-part,
enlarger insertion, flexible-hinge, light-leak or thermal acceptance is implied.
The physical reference photographs remain private in the ignored build directory.
