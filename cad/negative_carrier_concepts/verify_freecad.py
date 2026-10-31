"""Run in FreeCAD Python. Verify concept envelopes, not spring or film behavior."""

import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App
import Part

out = Path(os.environ["NEGATIVE_CONCEPT_OUTPUT"])
manifest_path = out / "manifest.json"
manifest = json.loads(manifest_path.read_text())
report = {
    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    "freecad_version": App.Version(),
    "evidence_level": "sampled rigid translation and normal-ray masking only",
    "physical_fit_verified": False,
    "latches_hinges_springs_and_drive_verified": False,
    "models": [],
}
for model in manifest["models"]:
    fmt = manifest["formats"][model["format"]]
    shapes = {}
    for record in model["parts"]:
        path = out / record["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        shape = Part.read(str(path))
        assert shape.isValid() and len(shape.Solids) == 1
        assert abs(shape.Volume - record["volume_mm3"]) < 1e-4
        shapes[record["name"]] = shape
    moving = [p["name"] for p in model["parts"] if p["motion"] == "moving"]
    fixed = [p["name"] for p in model["parts"] if p["motion"] == "fixed"]
    # Discrete regular sweep plus all exact stations, including first and last.
    shifts = sorted(
        set(
            [-c for c in fmt["centers"]]
            + [fmt["travel"] * (i / 20 - 0.5) for i in range(21)]
        )
    )
    samples = []
    for dx in shifts:
        maximum = 0
        for name in moving:
            shape = shapes[name].copy()
            shape.translate(App.Vector(dx, 0, 0))
            for other in fixed:
                maximum = max(maximum, shape.common(shapes[other]).Volume)
        samples.append({"translation_mm": dx, "max_overlap_mm3": maximum})
    # Deliberately excessive upper-mask thickness must intrude into the sled.
    bad_gate = shapes["gate"].copy()
    bad_gate.translate(App.Vector(0, 0, -1))
    control = shapes["lid"].common(bad_gate).Volume
    # Independently reproduce the 2D mask result as a 3D FreeCAD intersection.
    optical = []
    aw, ah = fmt["aperture"]
    aperture = Part.makeBox(aw, ah, 1, App.Vector(-aw / 2, -ah / 2, 0))
    for origin in fmt["centers"]:
        areas = []
        for center in fmt["centers"]:
            frame = Part.makeBox(
                fmt["image_width"],
                fmt["image_height"],
                1,
                App.Vector(
                    center - origin - fmt["image_width"] / 2,
                    -fmt["image_height"] / 2,
                    0,
                ),
            )
            areas.append(frame.common(aperture).Volume)
        selected = fmt["centers"].index(origin)
        optical.append(
            {
                "selected_area_mm2": areas[selected],
                "neighbour_area_mm2": sum(
                    a for i, a in enumerate(areas) if i != selected
                ),
            }
        )
    doc = App.newDocument("Concept")
    for name, shape in shapes.items():
        obj = doc.addObject("PartDesign::Feature", name.replace("-", "_"))
        obj.Shape = shape
        obj.Label = name
        obj.addProperty("App::PropertyString", "Evidence", "Concept")
        obj.Evidence = "Layout envelope only; not print-ready or fitted to C35"
    doc.recompute()
    path = out / model["name"] / "concept.FCStd"
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    check = App.openDocument(str(path))
    assert len(check.Objects) == len(shapes) and all(
        o.Shape.isValid() for o in check.Objects
    )
    App.closeDocument(check.Name)
    passed = (
        all(s["max_overlap_mm3"] < 1e-4 for s in samples)
        and control > 1e-4
        and all(
            s["neighbour_area_mm2"] < 1e-4
            and abs(s["selected_area_mm2"] - aw * ah) < 1e-4
            for s in optical
        )
    )
    report["models"].append(
        {
            "name": model["name"],
            "passed": passed,
            "translation_samples": samples,
            "optical_samples": optical,
            "lowered_gate_negative_control_overlap_mm3": control,
            "freecad_document_reopened": True,
        }
    )
    print(model["name"], "passed:", passed, flush=True)
report["passed"] = all(m["passed"] for m in report["models"])
(out / "freecad-validation.json").write_text(json.dumps(report, indent=2) + "\n")
