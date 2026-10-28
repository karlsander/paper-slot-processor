# Evidence, 28 October 2026

Current geometry: 180 × 180 mm tapered base, 25 mm clear chamber gap, 1.3 mm
outer magnet ligament, five printed parts. FreeCAD checks both 16:9 and 2:1 presets.

- `freecad-validation.json`: geometry, fit, travel, capacity and STEP/mesh checks.
- `print-audit.json`: Bambu Studio 2.7.1.57 actual slicer reports plus sampled
  feature deposition checks, Generic PETG, A1 mini 0.2/0.4 mm nozzles.
- `print-times.json`: all five final plates and totals, including supports/brims.
- `results.json`, `thermal-curves.csv/png`: corrected continuous four-corrector
  OpenFOAM v2606 transients, refinement/sensitivity cases and VOF fill budgets.
- `equilibrium.json/png`: separate SciPy steady solid conduction / well-mixed
  liquid heater-sizing model. It does not resolve steady fluid motion.
- `heater-section.png`: actual transient solver temperatures through the stack.
- `tapered-*.png`: actual current CAD geometry, rendered with PyVista.

Full methods, interpretation and uncertainties: [physics report](../../../../docs/processor-physics.md).
Raw fields remain in the local worktree's `build/physics/verified` and linked case
folders. The dated delivery bundle contains videos, STEP/STL/FreeCAD files,
scenario inputs, postProcessing tables, logs and source. Large volumetric time
fields are retained locally rather than copied into Git.

Rejected exploratory thermal runs (two outer correctors and unconverged steady
CFD) are excluded. The cold-start transient retains a localized 0.33°C numerical
undershoot; spill quantities are mesh-sensitive. No physical print or chemistry
performance has been validated by this evidence.
