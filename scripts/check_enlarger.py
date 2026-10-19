#!/usr/bin/env python3
"""Check real enlarger meshes, A1 mini bounds, fits and exposed test-strip areas."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import numpy as np
import trimesh

from check_geometry import components

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/enlarger"
OPENSCAD = os.environ.get("OPENSCAD_BIN") or shutil.which("openscad") or "openscad"
PLATES = ("base_left", "base_right", "masks_16x9", "masks_4x3",
          "cover_1", "cover_2", "cover_3", "cover_4", "fit_coupon")


def export(source: Path, name: str, defines=(), invalid=False):
    destination = OUT / "meshes" / f"{name}.stl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    command = [OPENSCAD, "--backend", "Manifold", "--hardwarnings", "-o", str(destination)]
    for define in defines:
        command += ["-D", define]
    result = subprocess.run([*command, str(source)], capture_output=True, text=True)
    if invalid:
        assert "ERROR" in result.stderr and "Assertion" in result.stderr, result.stderr
        return None
    assert result.returncode == 0 and "ERROR" not in result.stderr and "WARNING" not in result.stderr, result.stderr
    mesh = trimesh.load_mesh(destination, force="mesh")
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
    assert mesh.nondegenerate_faces().all(), f"Degenerate triangles: {name}"
    return mesh


def main():
    report = {"plates": [], "checks": []}
    for name in PLATES:
        mesh = export(ROOT / f"enlarger/plates/{name}.scad", name)
        expected = 2 if name.startswith("masks_") else 3 if name == "fit_coupon" else 1
        assert len(components(mesh)) == expected, f"Disconnected plate: {name}"
        assert np.all(mesh.extents <= [174.001, 174.001, 178.001]), f"A1 mini bounds: {name}: {mesh.extents}"
        assert abs(mesh.bounds[0, 2]) < 1e-5, f"Not on the bed: {name}"
        for part in components(mesh):
            assert abs(part.bounds[0, 2]) < 1e-5, f"Floating component: {name}"
        report["plates"].append({"name": name, "bodies": expected,
            "dimensions_mm": mesh.extents.round(3).tolist(), "solid_volume_cm3": round(mesh.volume / 1000, 3)})
        print(f"PASS plate {name}: {mesh.extents.round(2)}", flush=True)

    source = ROOT / "tests/enlarger_geometry.scad"
    for scenario, overrides, width in (
        ("default", [], 102),
        ("thicker-paper", ["paper_thickness=0.5"], 102),
        ("narrower-roll", ["paper_width=100"], 100),
    ):
        for format in ("16:9", "4:3"):
            label = format.replace(":", "x")
            settings = [*overrides, f'format="{format}"']
            for case in ("joint", "paper", "masks", "covers", "magnets", "light"):
                for sign in ((-1, 1) if case == "light" else (1,)):
                    name = f"{scenario}-{label}-{case}-{sign}"
                    mesh = export(source, name, [*settings, f'case_name="{case}"', f"ray_sign={sign}"])
                    assert len(components(mesh)) == 1 and abs(mesh.volume - 1) < 1e-5, f"Collision: {name}: {mesh.volume}"
                    report["checks"].append(name)
            length = width * (16 / 9 if format == "16:9" else 4 / 3)
            for count in range(5):
                name = f"{scenario}-{label}-exposure-{count}"
                mesh = export(source, name, [*settings, 'case_name="exposure"', f"cover_count={count}"])
                exposed_length = length - count * 30 - (0.8 if 0 < count < 4 else 0)
                expected = exposed_length * width
                assert len(components(mesh)) == 1, f"Stray light slit: {name}"
                assert abs(mesh.volume - expected) < 0.05, f"Exposed area {name}: {mesh.volume} != {expected}"
                assert abs(mesh.extents[0] - exposed_length) < 0.001, f"Remaining image length: {name}"
                assert abs(mesh.extents[1] - width) < 0.001, f"Band must span the full paper width: {name}"
                report["checks"].append(name)
            print(f"PASS {scenario} {format}: paper, joint, magnets, masks, covers, edge rays and all five exposure stages", flush=True)

    for name, overrides in {
        "guides-above-paper": ["guide_height=0.4"],
        "wide-roll": ["paper_width=120"],
        "thin-magnet-floor": ["deck_thickness=3.2"],
        "wrong-magnets": ["magnet_diameter=8"],
        "no-fifth-band": ["band_width=34"],
        "no-joint-clearance": ["joint_clearance=0"],
        "covers-touch-paper": ["outer_rail_height=0.2"],
    }.items():
        export(source, f"invalid-{name}", overrides, invalid=True)
        report["checks"].append(f"rejects-{name}")
    report["status"] = "passed"
    report["limits"] = "Digital geometry only. Curl, opacity, magnet retention, surface finish and printed fit need a physical trial."
    (OUT / "geometry-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Passed {len(PLATES)} plates and {len(report['checks'])} geometry checks.")


if __name__ == "__main__":
    main()
