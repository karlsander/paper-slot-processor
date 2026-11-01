"""Export evidence-linked STEP solids and geometric clearance controls."""

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

import build123d as bd

from .model import (
    DEFAULT_MEASUREMENTS,
    box,
    clearance_scenario,
    load_measurements,
    parts,
    screw_centres,
    values,
)

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def overlap(a, b):
    if not a.bounding_box().overlaps(b.bounding_box()):
        return 0.0
    result = a.intersect(b)
    return sum(s.volume for s in result) if result else 0.0


def export(output, measurements=DEFAULT_MEASUREMENTS):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    data = load_measurements(measurements)
    (output / "measurements.json").write_text(json.dumps(data, indent=2) + "\n")
    p = values(data)
    shapes = parts(data)
    records = {}
    for name, shape in shapes.items():
        assert shape.is_valid and len(shape.solids()) == 1, name
        path = output / f"{name}.step"
        shape.label = name
        bd.export_step(shape, path)
        bounds = shape.bounding_box()
        records[name] = {
            "file": path.name,
            "sha256": sha(path),
            "volume_mm3": shape.volume,
            "bounds_mm": {"min": list(bounds.min), "max": list(bounds.max)},
            "role": "prescribed moving support"
            if name == "lower-support"
            else "fixed head",
        }
    maximum_overlap = max(overlap(a, b) for a, b in combinations(shapes.values(), 2))
    assert maximum_overlap < 1e-6, maximum_overlap
    bd.export_step(
        bd.Compound(children=list(shapes.values())), output / "assembly.step"
    )
    # These probes deliberately do not represent the complete carrier. They test
    # whether the fixture exposes contact/interference, rather than passing all poses.
    controls = {}
    plate = shapes["underside-plate"]
    for label, thickness in (
        ("below", p["slot_gap"] - 0.1),
        ("at", p["slot_gap"]),
        ("above", p["slot_gap"] + 0.1),
    ):
        probe = box(0, -4, -p["slot_gap"], 8, 2, thickness)
        controls[label] = {
            "thickness_mm": thickness,
            "overlap_mm3": overlap(probe, plate),
        }
    assert (
        controls["below"]["overlap_mm3"] < 1e-6
        and controls["at"]["overlap_mm3"] < 1e-6
        and controls["above"]["overlap_mm3"] > 0.1
    )
    screw_overlap = None
    if p["screw_protrusion"] > 0:
        x, y = screw_centres(p)[0]
        probe = box(x, y, -p["slot_gap"], 2, 2, p["slot_gap"])
        screw_overlap = overlap(probe, shapes["screw-head-1"])
        assert screw_overlap > 1e-6
    # Original-minus-gap is an illustrative displacement, NOT a measured spring travel.
    illustrative_drop = max(
        0, data["observations"]["original_closed_height_mm"]["value"] - p["slot_gap"]
    )
    scenario = clearance_scenario(data, illustrative_drop)
    report = {
        "schema_version": 1,
        "geometry_passed": True,
        "physical_fit_accepted": False,
        "material_or_force_model": None,
        "measurement_sha256": sha(output / "measurements.json"),
        "sources": {
            str(f.relative_to(ROOT)): sha(f)
            for f in sorted(Path(__file__).parent.glob("*.py"))
        },
        "parts": records,
        "assembly_sha256": sha(output / "assembly.step"),
        "maximum_part_overlap_mm3": maximum_overlap,
        "negative_controls": {
            "flat_plate_probe_overlap_mm3": controls,
            "screw_probe_overlap_mm3": screw_overlap,
        },
        "states": {
            "rest": clearance_scenario(data),
            "illustrative_original_height": scenario,
        },
        "pending_parameters": [
            key
            for key, entry in data["parameters"].items()
            if entry["status"] == "provisional"
        ],
        "scope": "Insertion area only. Shell cropped above shoulder; bellows, spring mounts, diffuser internals and rear stop not reconstructed.",
        "legacy_carrier_alignment": None,
        "limitations": [
            "Measured head width and approximate rest gap do not establish full fit.",
            "Lower support placement is rigid and prescribed, not elastic deformation.",
            "Screw dimensions/positions and lower-frame interior are provisional collision envelopes.",
            "No inferred force, preload, maximum travel, friction or spring material.",
            "No automatic reuse of old 2.6 mm fixture acceptance or film-plane alignment.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, default=DEFAULT_MEASUREMENTS)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/durst-c35-interface"
    )
    args = parser.parse_args()
    report = export(args.output, args.measurements)
    print(
        f"Exported {len(report['parts'])} native solids; geometry passed; physical fit unverified."
    )
