"""Export source solids and sampled rigid-body checks for the manual carrier."""

import argparse
import json
from dataclasses import asdict
from itertools import combinations
from pathlib import Path

import build123d as bd
import numpy as np

from cad.negative_carrier_b.fixture import fixtures
from cad.negative_carrier_fem.solver import sha

from .model import Config, parts
from .workflow import blend, phases, place, transform

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/negative-carrier-b2"


def volume(a, b):
    cut = a.intersect(b)
    return sum(s.volume for s in cut) if cut else 0


def print_shape(name, shape):
    if name.startswith("wedge-") or name == "dock-wedge":
        shape = shape.rotate(bd.Axis.X, 90 if name.endswith("--1") else -90)
    elif name == "sleeve":
        shape = shape.rotate(bd.Axis.Y, -90)
    elif name == "screw":
        shape = shape.rotate(bd.Axis.X, 180)
    return bd.Pos(0, 0, -shape.bounding_box().min.Z) * shape


def print_record(name, shape, path, root):
    printable = print_shape(name, shape)
    bd.export_stl(printable, path, tolerance=0.03, angular_tolerance=0.1)
    return {
        "file": str(path.relative_to(root)),
        "sha256": sha(path),
        "extents_mm": list(printable.bounding_box().size),
        "minimum_z_mm": printable.bounding_box().min.Z,
    }


def refresh_prints(root):
    """Reorient STL assets from hashed STEP without rebuilding native geometry."""
    path = root / "manifest.json"
    data = json.loads(path.read_text())
    assert data["source_sha256"] == sha(Path(__file__).with_name("model.py"))
    for model in data["formats"]:
        for name, record in model["parts"].items():
            if name == "film":
                continue
            source = root / record["file"]
            assert sha(source) == record["sha256"]
            record["print"] = print_record(
                name, bd.import_step(source), source.with_suffix(".stl"), root
            )
        folder = root / Path(model["parts"]["base"]["file"]).parent
        (folder / "manifest.json").write_text(json.dumps(model, indent=2) + "\n")
    path.write_text(json.dumps(data, indent=2) + "\n")


def export(formats=("135", "half", "aps", "110"), check=True, full_size=False):
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"source_sha256": sha(Path(__file__).with_name("model.py")), "formats": []}
    for fmt in formats:
        p = (
            Config(fmt)
            if full_size
            else Config(fmt, frame_count={"135": 4, "half": 7, "aps": 4, "110": 7}[fmt])
        )
        folder = OUT / fmt
        folder.mkdir(exist_ok=True)
        shapes = parts(p)
        records = {}
        for n, s in shapes.items():
            assert s.is_valid and len(s.solids()) == 1, (fmt, n)
            path = folder / f"{n}.step"
            bd.export_step(s, path)
            records[n] = {
                "file": str(path.relative_to(OUT)),
                "sha256": sha(path),
                "volume_mm3": s.volume,
                "extents_mm": list(s.bounding_box().size),
            }
            if n != "film":
                records[n]["print"] = print_record(n, s, folder / f"{n}.stl", OUT)
        seq = phases(p)
        errors = []
        checks = 0
        cache = {}
        if check:
            for phase in seq:
                for t in np.linspace(0, 1, 5):
                    pose = blend(phase["start"], phase["end"], float(t))
                    active = {n: place(shapes[n], n, pose) for n in phase["show"]}
                    for (a, s), (b, q) in combinations(active.items(), 2):
                        # Broad phase bounding boxes first, then exact solid common.
                        if not s.bounding_box().overlaps(q.bounding_box()):
                            continue
                        relative = np.linalg.inv(transform(a, pose)) @ transform(
                            b, pose
                        )
                        key = (a, b, tuple(relative.round(8).ravel()))
                        if key not in cache:
                            cache[key] = volume(s, q)
                        v = cache[key]
                        checks += 1
                        if v > 1e-5:
                            errors.append(
                                {
                                    "phase": phase["label"],
                                    "t": float(t),
                                    "a": a,
                                    "b": b,
                                    "volume": v,
                                }
                            )
            final = seq[-1]["end"]
            for n, s in shapes.items():
                for f, q in fixtures().items():
                    v = volume(place(s, n, final), q)
                    checks += 1
                    if v > 1e-5:
                        errors.append(
                            {"phase": "enlarger fixture", "a": n, "b": f, "volume": v}
                        )
        item = {
            "config": asdict(p),
            "format_data": p.fmt.data(),
            "profile": "full" if full_size else "compact",
            "parts": records,
            "phases": seq,
            "checks": checks,
            "errors": errors,
        }
        report["formats"].append(item)
        (folder / "manifest.json").write_text(json.dumps(item, indent=2) + "\n")
        print(fmt, checks, "checks", len(errors), "errors", flush=True)
        if errors:
            print(json.dumps(errors[:30], indent=2), flush=True)
    report["passed"] = check and all(not r["errors"] for r in report["formats"])
    assert report["source_sha256"] == sha(Path(__file__).with_name("model.py")), (
        "CAD changed during export"
    )
    (OUT / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--formats", nargs="+", default=["135", "half", "aps", "110"])
    p.add_argument("--no-check", action="store_true")
    p.add_argument("--full-size", action="store_true")
    a = p.parse_args()
    if a.full_size:
        OUT = ROOT / "build/negative-carrier-b2-full"
    r = export(a.formats, not a.no_check, a.full_size)
    if not a.no_check:
        assert r["passed"]
