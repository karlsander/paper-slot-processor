"""Run in FreeCAD console: native imports, continuous travel and controls."""

import hashlib
import json
import os
from itertools import combinations
from pathlib import Path

import FreeCAD as App
import Part

out = Path(os.environ["CARRIER_B2_OUTPUT"])
manifest = out / "manifest.json"
data = json.loads(manifest.read_text())
assert data["passed"]


def overlap(a, b):
    if not a.BoundBox.intersect(b.BoundBox):
        return 0
    return abs(a.common(b).Volume)


def placed(s, n, pose):
    s = s.copy()
    x, y, z, a = pose[n]
    if a:
        s.rotate(App.Vector(0, 57, 0), App.Vector(0, 0, 1), a)
    s.translate(App.Vector(x, y, z))
    return s


reports = []
for model in data["formats"]:
    cfg = model["config"]
    shapes = {}
    volume_errors = {}
    for n, r in model["parts"].items():
        path = out / r["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == r["sha256"]
        s = Part.read(str(path))
        assert s.isValid() and len(s.Solids) == 1, (cfg, n)
        relative = abs(s.Volume / r["volume_mm3"] - 1)
        volume_errors[n] = relative
        # The two OCCT builds integrate the helical B-spline faces slightly
        # differently. STEP bytes are hashed; allow 0.01% for those two solids.
        tolerance = 1e-4 if n in ("sleeve", "screw") else 1e-7
        assert relative < tolerance, (cfg, n, s.Volume, r["volume_mm3"])
        shapes[n] = s
    steps = model["phases"]
    closed = next(
        s["end"]
        for s in steps
        if s["label"] == "Turn the coarse screw to seat the indexing shoe"
    )
    released = next(
        s["end"]
        for s in steps
        if s["label"] == "Continue turning: lift the rigid shoe clear"
    )
    assembly = {n: placed(s, n, closed) for n, s in shapes.items()}
    max_closed = max(overlap(a, b) for a, b in combinations(assembly.values(), 2))
    assert max_closed < 1e-5, max_closed
    moving = [
        n for n in shapes if n in ("base", "lid", "film") or n.startswith("wedge-")
    ]
    travel = abs(steps[-1]["end"]["base"][0] - closed["base"][0])
    vector = App.Vector(-travel, 0, 0)
    prisms = 0
    sweep_max = 0
    posed = {n: placed(s, n, released) for n, s in shapes.items()}
    for n in moving:
        for face in posed[n].Faces:
            # Ruled notch lofts arrive as planar B-spline surfaces in STEP.
            # Ask OCCT to establish planarity instead of checking storage type.
            plane = face.findPlane(1e-7)
            assert plane is not None
            if abs(plane.Axis.dot(vector)) < 1e-7:
                continue
            prism = face.extrude(vector)
            if prism.Volume < 0:
                prism.reverse()
            assert prism.isValid() and prism.Solids
            prisms += 1
            for other, s in posed.items():
                if other not in moving:
                    sweep_max = max(sweep_max, overlap(prism, s))
    assert sweep_max < 1e-5, (cfg, sweep_max)
    shifted = assembly["base"].copy()
    shifted.translate(App.Vector(0.5, 0, 0))
    blocked = overlap(shifted, assembly["shoe"])
    assert blocked > 0.01
    lifted = assembly["lid"].copy()
    lifted.translate(App.Vector(0, 0, 0.4))
    lid_blocked = sum(
        overlap(lifted, s) for n, s in assembly.items() if n.startswith("wedge-")
    )
    assert lid_blocked > 0.01
    doc = App.newDocument("B2_Manual_Carrier")
    for n, s in assembly.items():
        obj = doc.addObject("PartDesign::Feature", n.replace("-", "_"))
        obj.Label = n
        obj.Shape = s
    doc.recompute()
    path = out / Path(model["parts"]["base"]["file"]).parent / "assembly.FCStd"
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    reopen = App.openDocument(str(path))
    assert len(reopen.Objects) == len(shapes)
    App.closeDocument(reopen.Name)
    reports.append(
        {
            "config": cfg,
            "passed": True,
            "native_parts": len(shapes),
            "relative_import_volume_errors": volume_errors,
            "max_closed_overlap_mm3": max_closed,
            "continuous_sweep_mm": travel,
            "sweep_prisms": prisms,
            "max_sweep_overlap_mm3": sweep_max,
            "negative_controls": {
                "unreleased_index_blocks_slide_mm3": blocked,
                "wedges_block_lid_lift_mm3": lid_blocked,
            },
            "assembly_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    )
(out / "freecad-validation.json").write_text(
    json.dumps(
        {
            "passed": True,
            "freecad_version": App.Version(),
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
            "models": reports,
        },
        indent=2,
    )
    + "\n"
)
