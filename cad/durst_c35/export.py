"""Export the corrected thin-shell carrier, assembly STEP and individual print meshes."""

import argparse
import hashlib
import json
from pathlib import Path

import build123d as bd
import trimesh

from . import parts
from .parameters import parameters


def check_shell(shape, p, half):
    """Section probes distinguish a thin panel from a valid solid slab."""
    local = bd.mirror(shape, about=bd.Plane.XY) if half == "a" else shape
    samples = []
    for x, y in [
        (-35, 25),
        (35, 25),
        (-35, 54),
        (35, 54),
        (-35, 80),
        (35, 80),
        (0, 20),
        (0, 85),
    ]:
        probe = parts.box(x - 1, y - 1, 0, 2, 2, p[f"outer_height_{half}"] + 1)
        measured = (local & probe).volume / 4
        if abs(measured - p["sheet_thickness"]) > 1e-6:
            raise ValueError(
                f"{half}: panel at {x, y} is {measured:g} mm, expected thin sheet {p['sheet_thickness']:g}"
            )
        samples.append({"xy_mm": [x, y], "thickness_mm": measured})
    cavity = parts.box(
        -40,
        16,
        p["window_rim_height"] + 0.1,
        80,
        75,
        min(p["outer_height_a"], p["outer_height_b"]) - p["window_rim_height"] - 0.2,
    )
    if (local & cavity).volume > 1e-6:
        raise ValueError(f"{half}: exterior cavity filled above local window rim")
    return samples


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(output, p):
    output.mkdir(parents=True, exist_ok=True)
    for name in ("model-report.json", "validation.json"):
        (output / name).unlink(missing_ok=True)
    (output / "plates").mkdir(exist_ok=True)
    (output / "parameters.json").write_text(json.dumps(p, indent=2) + "\n")
    shapes = {"a": parts.lower(p), "b": parts.upper(p)}
    reports = []
    for half, shape in shapes.items():
        assert shape.is_valid and len(shape.solids()) == 1, half
        samples = check_shell(shape, p, half)
        bd.export_step(shape, output / f"{half}.step")
        plate = parts.print_part(shape, half)
        b = plate.bounding_box()
        assert abs(b.min.Z) < 1e-6 and b.min.X >= 3 and b.min.Y >= 3
        assert b.max.X <= 177 and b.max.Y <= 177 and b.max.Z <= 178
        bd.export_step(plate, output / "plates" / f"{half}.step")
        mesh_path = output / "plates" / f"{half}.stl"
        bd.export_stl(plate, mesh_path, tolerance=0.01, angular_tolerance=0.05)
        mesh = trimesh.load_mesh(mesh_path)
        assert (
            mesh.is_watertight and mesh.is_winding_consistent and mesh.body_count == 1
        )
        assert mesh.unique_faces().all() and mesh.nondegenerate_faces().all()
        assert abs(mesh.volume - shape.volume) / shape.volume < 0.001
        reports.append(
            {
                "name": half,
                "volume_mm3": shape.volume,
                "size_mm": list(b.size),
                "sheet_sections": samples,
                "mesh_volume_mm3": mesh.volume,
                "mesh_watertight": True,
            }
        )
        print(f"{half}: valid thin shell, {shape.volume:.1f} mm³", flush=True)
    for angle, name in [(0, "assembly"), (110, "assembly-open")]:
        a, b = shapes["a"], parts.opened(p, shapes["b"], angle)
        a.label, b.label = "Lower A", "Upper B"
        bd.export_step(bd.Compound(children=[a, b]), output / f"{name}.step")
    paths = [
        output / "parameters.json",
        *output.glob("*.step"),
        *(output / "plates").glob("*"),
    ]
    source = Path(__file__).parent
    report = {
        "passed": True,
        "version": "0.2",
        "build123d": bd.__version__,
        "parts": reports,
        "source_sha256": {f.name: sha(f) for f in sorted(source.glob("*.py"))},
        "files_sha256": {str(f.relative_to(output)): sha(f) for f in sorted(paths)},
        "physical_fit_verified": False,
        "enlarger_slot_modeled": False,
    }
    (output / "model-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("build/durst-c35-native"))
    parser.add_argument(
        "--config", type=Path, help="JSON overrides of the editable Python defaults"
    )
    args = parser.parse_args()
    export(
        args.output.resolve(),
        parameters(**(json.loads(args.config.read_text()) if args.config else {})),
    )


if __name__ == "__main__":
    main()
