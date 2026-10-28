"""Export the native model; run with the isolated build123d Python environment."""

import json
import sys
from pathlib import Path

import build123d as bd
from processor import base, liquid_void, placed_vessel, vessel

output = Path(sys.argv[1])
p = json.loads((output / "parameters.json").read_text())
reports = []
solids = {}
for name, shape in [
    ("base", base(p)),
    ("vessel_a", vessel(p, 0)),
    ("vessel_b", vessel(p, 1)),
]:
    assert shape.is_valid and len(shape.solids()) == 1, name
    solids[name] = shape
    bd.export_step(shape, output / f"{name}.step")
    bd.export_stl(shape, output / f"{name}.stl", tolerance=0.01, angular_tolerance=0.05)
    reports.append(
        {
            "name": name,
            "volume_mm3": shape.volume,
            "faces": len(shape.faces()),
            "bounds_mm": list(shape.bounding_box().size),
        }
    )
parts = [
    solids["base"],
    placed_vessel(p, solids["vessel_a"], 0),
    placed_vessel(p, solids["vessel_b"], 1),
]
for name, shape in zip(("Base", "Bath A", "Bath B"), parts):
    shape.label = name
bd.export_step(bd.Compound(children=parts), output / "assembly.step")
(output / "model-report.json").write_text(
    json.dumps(
        {
            "build123d": bd.__version__,
            "parts": reports,
            "simplifications": [
                "Text, tactile marks and fill-cue engraving omitted.",
                "Analytic curves replace OpenSCAD polygon approximations. No guides or clips in this first study.",
            ],
        },
        indent=2,
    )
    + "\n"
)
print("Exported native build123d solids and assembly STEP")

bd.export_step(liquid_void(p), output / "liquid-cavity.step")
