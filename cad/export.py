"""Export the complete unheated processor, print plates and native assembly."""

import argparse
import hashlib
import json
from pathlib import Path

import build123d as bd
import trimesh

from . import parts
from .parameters import parameters


def export(output, p, trials=True):
    output.mkdir(parents=True, exist_ok=True)
    (output / "parameters.json").write_text(json.dumps(p, indent=2) + "\n")
    shapes = {"base": parts.base(p), "clip": parts.clip(p)}
    for i, letter in enumerate("ab"):
        shapes[f"vessel_{letter}"] = parts.vessel(p, i)
        shapes[f"guide_{letter}"] = parts.guide(p, i)
        shapes[f"cover_{letter}"] = parts.guide(p, i, closed=True)
        if trials:
            for gap in (0.6, 0.8):
                shapes[f"trial_{letter}_{int(gap * 10)}"] = parts.guide(p, i, gap=gap)
    shapes["fit"] = parts.fit_sample(p, shapes["vessel_a"])
    reports = []
    for name, shape in shapes.items():
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError(f"{name}: expected one valid solid")
        bd.export_step(shape, output / f"{name}.step")
        reports.append(
            {
                "name": name,
                "volume_mm3": shape.volume,
                "faces": len(shape.faces()),
                "bounds_mm": list(shape.bounding_box().size),
            }
        )
        print("Exported", name, flush=True)
    assembly = parts.assembly_parts(p, shapes)
    for name, shape in assembly.items():
        shape.label = name
    bd.export_step(
        bd.Compound(children=list(assembly.values())), output / "assembly.step"
    )
    for i, letter in enumerate("ab"):
        bd.export_step(parts.liquid_void(p, i), output / f"liquid-cavity-{letter}.step")
    plates = {
        "base": shapes["base"],
        "fit": shapes["fit"],
        "clips": parts.clip_plate(p, shapes["clip"]),
    }
    for name, shape in shapes.items():
        if name.startswith("vessel_"):
            plates[name] = parts.print_vessel(p, shape, "ab".index(name[-1]))
        elif name.startswith(("guide_", "cover_", "trial_")):
            plates[name] = parts.print_guide(p, shape)
    (output / "plates").mkdir(exist_ok=True)
    plate_reports = []
    for name, shape in plates.items():
        box = shape.bounding_box()
        expected = 4 if name == "clips" else 1
        assert shape.is_valid and len(shape.solids()) == expected, (
            name,
            len(shape.solids()),
        )
        assert abs(box.min.Z) < 1e-4, (name, box.min.Z)
        assert all(
            v <= lim + 1e-4
            for v, lim in zip(box.size, p["usable_xy"] + [p["usable_z"]])
        ), (name, box.size)
        assert (
            box.min.X >= -1e-4
            and box.min.Y >= -1e-4
            and box.max.X <= 180
            and box.max.Y <= 180
        ), (name, box)
        bd.export_step(shape, output / "plates" / f"{name}.step")
        bd.export_stl(
            shape,
            output / "plates" / f"{name}.stl",
            tolerance=0.01,
            angular_tolerance=0.05,
        )
        mesh = trimesh.load_mesh(output / "plates" / f"{name}.stl")
        before = len(mesh.faces)
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        removed = before - len(mesh.faces)
        if (
            not mesh.is_watertight
            or not mesh.is_winding_consistent
            or not mesh.unique_faces().all()
        ):
            raise ValueError(f"{name}: invalid printable tessellation")
        mesh.export(output / "plates" / f"{name}.stl")
        plate_reports.append(
            {
                "name": name,
                "solid_count": expected,
                "degenerate_triangles_removed": removed,
                "bounds_min_mm": list(box.min),
                "bounds_max_mm": list(box.max),
                "size_mm": list(box.size),
                "copies": 1,
                "optional": name.startswith(("cover_", "trial_")) or name == "fit",
            }
        )
    # Unlettered functional surfaces are compared independently of font tessellation.
    reference = output / "parity"
    reference.mkdir(exist_ok=True)
    for name, shape in [
        ("base", parts.base(p, labels=False)),
        ("vessel_a", parts.vessel(p, 0, labels=False)),
        ("vessel_b", parts.vessel(p, 1, labels=False)),
        ("guide_a", parts.guide(p, 0, labels=False)),
        ("guide_b", parts.guide(p, 1, labels=False)),
        ("cover_a", parts.guide(p, 0, closed=True, labels=False)),
        ("cover_b", parts.guide(p, 1, closed=True, labels=False)),
        ("clip", shapes["clip"]),
    ]:
        bd.export_step(shape, reference / f"{name}.step")
    for i, letter in enumerate("ab"):
        for gap in (0.6, 0.8):
            bd.export_step(
                parts.guide(p, i, gap=gap, labels=False),
                reference / f"trial_{letter}_{int(gap * 10)}.step",
            )
    bd.export_step(
        parts.fit_sample(p, parts.vessel(p, 0, labels=False)), reference / "fit.step"
    )
    root = Path(__file__).resolve().parent
    report = {
        "passed": True,
        "build123d": bd.__version__,
        "parts": reports,
        "plates": plate_reports,
        "working_piece_count": 9,
        "optional_cover_count": 2,
        "source_sha256": {
            f.name: hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(root.glob("*.py"))
        },
        "notes": [
            "Analytic arcs replace SCAD polygon approximations.",
            "Lettering uses OCCT font metrics and is excluded from SCAD functional-surface comparison.",
            "Print plate vessels include the original sacrificial bed rail.",
            "Capsule-limit slot corners retain 0.001 mm straight segments for stable loft topology.",
            "Zero-area STL triangles are removed before watertightness validation; no holes are filled.",
        ],
    }
    (output / "model-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/native-processor"))
    parser.add_argument("--aspect", type=float, default=16 / 9)
    parser.add_argument(
        "--config", type=Path, help="JSON overrides for cad.parameters.DEFAULTS"
    )
    args = parser.parse_args()
    overrides = json.loads(args.config.read_text()) if args.config else {}
    overrides.setdefault("image_aspect", args.aspect)
    export(args.output.resolve(), parameters(**overrides))


if __name__ == "__main__":
    main()
