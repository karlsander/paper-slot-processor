"""Export native assemblies and oriented manufacturing geometry."""

import hashlib
import json
from pathlib import Path

import build123d as bd
import trimesh

from .model import assembly, plates

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export(output, p):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "plates").mkdir(exist_ok=True)
    (output / "parameters.json").write_text(json.dumps(p, indent=2) + "\n")
    report = {
        "passed": False,
        "build123d": bd.__version__,
        "physical_fit_accepted": False,
        "plates": {},
        "assemblies": {},
        "parameters_sha256": sha(output / "parameters.json"),
        "sources": {
            str(f.relative_to(ROOT)): sha(f)
            for f in sorted((ROOT / "cad/enlarger").glob("*.py"))
            + [
                ROOT / name
                for name in (
                    "scripts/build_enlarger.py",
                    "scripts/check_enlarger.py",
                    "scripts/build_native_bambu.py",
                    "scripts/bambu_common.py",
                    "cad/fonts/LiberationSans-Bold.ttf",
                    "cad/requirements.txt",
                )
            ]
        },
    }
    for name, shape in plates(p).items():
        expected = 2 if name.startswith("masks_") else 3 if name == "fit_coupon" else 1
        assert shape.is_valid and len(shape.solids()) == expected, (
            name,
            "invalid solids",
        )
        bounds = shape.bounding_box()
        assert all(
            v <= limit + 1e-5 for v, limit in zip(bounds.size, [174, 174, 178])
        ), name
        assert bounds.min.X >= -1e-5 and bounds.min.Y >= -1e-5, name
        assert abs(bounds.min.Z) < 1e-5 and all(
            abs(s.bounding_box().min.Z) < 1e-5 for s in shape.solids()
        ), name
        step = output / "plates" / f"{name}.step"
        stl = step.with_suffix(".stl")
        bd.export_step(shape, step)
        bd.export_stl(shape, stl, tolerance=0.01, angular_tolerance=0.05)
        mesh = trimesh.load_mesh(stl)
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, (
            name
        )
        assert len(mesh.split()) == expected, (name, "disconnected mesh")
        assert abs(mesh.volume / shape.volume - 1) < 0.001, (
            name,
            "tessellation volume",
        )
        mesh.export(stl)
        imported = bd.import_step(step)
        assert imported.is_valid and len(imported.solids()) == expected, name
        assert abs(imported.volume / shape.volume - 1) < 1e-7, name
        report["plates"][name] = {
            "solids": expected,
            "volume_mm3": shape.volume,
            "dimensions_mm": list(bounds.size),
            "step_sha256": sha(step),
            "stl_sha256": sha(stl),
        }
        print("PASS native plate", name, flush=True)
    for fmt, label in [("16:9", "16x9"), ("4:3", "4x3")]:
        shapes = assembly(p, fmt, count=4)
        for name, shape in shapes.items():
            shape.label = name
        path = output / f"assembly-{label}.step"
        bd.export_step(bd.Compound(children=list(shapes.values())), path)
        report["assemblies"][label] = {
            "file": path.name,
            "sha256": sha(path),
            "solids": len(shapes),
        }
    report["passed"] = True
    (output / "model-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
