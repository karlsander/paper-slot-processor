#!/usr/bin/env python3
"""Check carrier connectivity, optical/film clearance and the hinge sweep.

These are geometric tests of the proposed prototype, not proof of printed fit.
Uses the same OpenSCAD and Python dependencies as the main build pipeline.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

import build_openscad as build

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/geometry-checks/durst-c35"
PARTS = ROOT / "parts/durst_c35"


def render(source: Path, name: str, defines: tuple[str, ...] = (), empty_ok=False):
    target = OUT / f"{name}.stl"
    target.unlink(missing_ok=True)
    command = [build.OPENSCAD, "--backend", "Manifold", "--hardwarnings", "-o", str(target)]
    for define in defines:
        command.extend(["-D", define])
    result = subprocess.run(command + [str(source)], text=True, capture_output=True, cwd=ROOT)
    (OUT / f"{name}.log").write_text(result.stdout + result.stderr)
    if empty_ok and not target.exists() and "Current top level object is empty" in result.stderr:
        assert "WARNING:" not in result.stderr and "ERROR:" not in result.stderr, result.stderr
        return None
    assert result.returncode == 0, result.stderr
    # Coplanar contact probes can produce zero-volume closed meshes. Their
    # centre of mass is undefined and unused; all mesh/volume assertions remain.
    with np.errstate(divide="ignore", invalid="ignore"):
        report = build.validate_mesh(target)
    assert report["is_watertight"] and report["is_winding_consistent"], (name, report)
    assert report["degenerate_faces"] == 0 and report["duplicate_faces"] == 0, (name, report)
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for part in ("a", "b"):
        name = f"durst_c35_{part}"
        report = render(PARTS / f"{name}.scad", name)
        assert report["body_count"] == 1, (name, "Each half must be one connected part", report)
        bounds = np.array(report["bounds_mm"])
        assert abs(bounds[0, 2]) < 1e-4, (name, "Part must stand on the bed", bounds)
        assert np.all(np.array(report["extents_mm"]) <= [174, 174, 178]), (name, report)
        results[name] = report

    checks = PARTS / "checks.scad"
    # Include intermediate positions near the rear edge, not just open/closed.
    for angle in (0, 5, 15, 30, 45, 55, 60, 75, 90, 105, 120, 150, 180):
        name = f"hinge-{angle}"
        report = render(checks, name, ('check="collision"', f"angle={angle}"), empty_ok=True)
        volume = abs(report["volume_mm3"]) if report else 0
        assert volume < 1e-4, (name, "Parts collide", volume)
        results[name] = {"intersection_mm3": volume}

    for check in ("window", "film", "b_relief"):
        report = render(checks, check, (f'check="{check}"',), empty_ok=True)
        volume = abs(report["volume_mm3"]) if report else 0
        assert volume < 1e-4, (check, "Clearance is obstructed", volume)
        results[check] = {"intersection_mm3": volume}

    window = render(checks, "window_dimensions_a", ('check="window_dimensions_a"',))
    assert np.allclose(window["extents_mm"], [36, 24, 0.1], atol=1e-4), window
    results["window_dimensions_a"] = window
    corners = render(checks, "b_corner_insets", ('check="b_corner_insets"',))
    assert corners["body_count"] == 4, corners
    assert abs(corners["volume_mm3"] - 4 * 0.2**3) < 1e-5, corners
    results["b_corner_insets"] = corners
    (OUT / "summary.json").write_text(json.dumps({"status": "ok", "checks": results}, indent=2) + "\n")
    print(f"Durst C35: {len(results)} geometry checks passed. {OUT / 'summary.json'}")


if __name__ == "__main__":
    main()
