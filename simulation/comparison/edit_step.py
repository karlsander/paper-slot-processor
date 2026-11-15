"""Import a common STEP fixture, drill a small bore, then export a new solid."""

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("backend", choices=("build123d", "cadquery"))
parser.add_argument("folder", type=Path)
args = parser.parse_args()
source = args.folder / "build123d-default.step"
destination = args.folder / f"{args.backend}-step-edit.step"
if args.backend == "build123d":
    import build123d as bd

    imported = bd.import_step(source)
    tool = bd.Pos(6, 1, -1) * bd.Cylinder(
        0.4, 11, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    result = imported - tool
    assert result.is_valid and len(result.solids()) == 1
    removed = imported.volume - result.volume
    bd.export_step(result, destination)
else:
    import cadquery as cq

    imported = cq.importers.importStep(str(source)).val()
    tool = cq.Solid.makeCylinder(0.4, 11, cq.Vector(6, 1, -1))
    result = imported.cut(tool)
    assert result.isValid() and len(result.Solids()) == 1
    removed = imported.Volume() - result.Volume()
    cq.exporters.export(result, str(destination))
assert removed > 0
(args.folder / f"{args.backend}-step-edit.json").write_text(
    json.dumps(
        {
            "passed": True,
            "source": source.name,
            "output": destination.name,
            "removed_mm3": removed,
            "note": "Demonstration bore, not a production clip change.",
        },
        indent=2,
    )
    + "\n"
)
