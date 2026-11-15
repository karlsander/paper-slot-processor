"""Run in FreeCAD console to independently check STEP and saved native documents."""

import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App
import Part

out = Path(os.environ["ENLARGER_OUTPUT"])
manifest = out / "model-report.json"
report = json.loads(manifest.read_text())
assert report["passed"] and not report["physical_fit_accepted"]
checked = {}
for name, record in report["plates"].items():
    path = out / "plates" / f"{name}.step"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["step_sha256"]
    shape = Part.read(str(path))
    assert shape.isValid() and len(shape.Solids) == record["solids"], name
    assert abs(shape.Volume / record["volume_mm3"] - 1) < 1e-7, name
    bounds = shape.BoundBox
    assert (
        abs(bounds.ZMin) < 1e-5
        and bounds.XLength <= 174.00001
        and bounds.YLength <= 174.00001
    ), name
    assert all(abs(s.BoundBox.ZMin) < 1e-5 for s in shape.Solids), name
    checked[name] = len(shape.Solids)
for name, record in report["assemblies"].items():
    source = out / record["file"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == record["sha256"]
    shape = Part.read(str(source))
    assert shape.isValid() and len(shape.Solids) == record["solids"], name
    doc = App.newDocument("Enlarger_" + name)
    for i, solid in enumerate(shape.Solids):
        obj = doc.addObject("Part::Feature", f"Part_{i + 1}")
        obj.Shape = solid
    doc.recompute()
    path = out / f"assembly-{name}.FCStd"
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    assert len(doc.Objects) == record["solids"] and all(
        o.Shape.isValid() for o in doc.Objects
    )
    App.closeDocument(doc.Name)
(out / "freecad-validation.json").write_text(
    json.dumps(
        {
            "passed": True,
            "freecad_version": App.Version(),
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "plates": checked,
            "assemblies_saved_and_reopened": list(report["assemblies"]),
            "physical_fit_accepted": False,
        },
        indent=2,
    )
    + "\n"
)
