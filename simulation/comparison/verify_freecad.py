"""FreeCADCmd cross-check of the STEP results from the three implementations."""

import json
import os
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

folder = Path(os.environ["CLIP_COMPARISON_OUTPUT"])
target = folder / "comparison.json"
target.unlink(missing_ok=True)
backends = ("build123d", "cadquery", "cadquery_func")
reports = {name: json.loads((folder / f"{name}.json").read_text()) for name in backends}
rows = {
    name: {row["name"]: row for row in report["cases"]}
    for name, report in reports.items()
}
comparisons = []
for case in rows["build123d"]:
    entries = [rows[backend][case] for backend in backends]
    if not all(entry["success"] for entry in entries):
        assert entries[0]["kind"] == "exploratory", entries
        comparisons.append(
            {
                "case": case,
                "success_by_backend": {
                    backend: rows[backend][case]["success"] for backend in backends
                },
            }
        )
        continue
    shapes = [Part.read(str(folder / entry["step"])) for entry in entries]
    for shape, entry in zip(shapes, entries, strict=True):
        assert shape.isValid() and len(shape.Solids) == 1
        assert abs(shape.Volume - entry["volume_mm3"]) < 1e-5
    difference = max(
        shapes[0].cut(shape).Volume + shape.cut(shapes[0]).Volume
        for shape in shapes[1:]
    )
    assert difference < 1e-5, (case, difference)
    comparisons.append({"case": case, "max_symmetric_difference_mm3": difference})

edited = [
    Part.read(str(folder / f"{backend}-step-edit.step")) for backend in backends[:2]
]
assert all(shape.isValid() and len(shape.Solids) == 1 for shape in edited)
edit_difference = edited[0].cut(edited[1]).Volume + edited[1].cut(edited[0]).Volume
assert edit_difference < 1e-5
native = Part.read(str(folder / "build123d-default.step"))
mesh = Mesh.Mesh(str(folder / "openscad-reference.stl"))
boundary = Part.makeCompound(native.Shells)
points = [point.Vector for point in mesh.Points]
points += [
    App.Vector(*facet.Points[0])
    .add(App.Vector(*facet.Points[1]))
    .add(App.Vector(*facet.Points[2]))
    .multiply(1 / 3)
    for facet in mesh.Facets
]
deviation = max(Part.Vertex(point).distToShape(boundary)[0] for point in points)
volume_error = abs(native.Volume - mesh.Volume) / mesh.Volume
assert deviation < 0.01 and volume_error < 0.001, (deviation, volume_error)
doc = App.newDocument("ClipComparison")
for i, backend in enumerate(backends):
    for j, case in enumerate(("default", "grid-14")):
        obj = doc.addObject("PartDesign::Feature", f"Clip_{i}_{j}")
        obj.Label = f"{backend}: {'original' if j == 0 else '0.8 mm root fillets'}"
        obj.Shape = Part.read(str(folder / rows[backend][case]["step"]))
        obj.Placement.Base = App.Vector(i * 20, j * 18, 0)
doc.recompute()
doc.saveAs(str(folder / "clip-comparison.FCStd"))
target.write_text(
    json.dumps(
        {
            "passed": all(report["passed"] for report in reports.values()),
            "freecad_version": App.Version(),
            "comparisons": comparisons,
            "step_import_edit_symmetric_difference_mm3": edit_difference,
            "openscad_reference": {
                "sample_points": len(points),
                "max_boundary_deviation_mm": deviation,
                "relative_volume_error": volume_error,
            },
            "limitations": [
                "Rigid geometry only; no elastic clip force or physical fit tested.",
                "Different installed OCCT versions: timings compare complete stacks, not isolated library overhead.",
                "FreeCAD also uses Open Cascade; the STEP comparison is not an independent geometry kernel.",
                "Root fillets and parameter variations are comparison experiments, not production design changes.",
            ],
        },
        indent=2,
    )
    + "\n"
)
print("PASS: clip STEP equivalence and OpenSCAD reference")
