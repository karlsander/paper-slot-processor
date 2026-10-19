#!/usr/bin/env python3
"""Export real solids and check paper/cap fits, liquid isolation and printer bounds.

Requires OpenSCAD with the Manifold backend and trimesh. No slicer is needed.
Outputs go under build/geometry-checks; an assertion or bad mesh fails the run.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
import shutil
import subprocess

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "geometry-checks"
OPENSCAD = os.environ.get("OPENSCAD_BIN") or shutil.which("openscad") or "openscad"


def components(mesh):
    # Avoid optional scipy/networkx dependencies for this small mesh graph.
    parent = list(range(len(mesh.faces)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in mesh.face_adjacency:
        parent[find(int(a))] = find(int(b))
    groups = {}
    for i in range(len(parent)):
        groups.setdefault(find(i), []).append(i)
    return [mesh.submesh([g], append=True) for g in groups.values()]


def export(name, case, overrides=(), invalid=False):
    path = OUT / f"{name}-{case}.stl"
    path.unlink(missing_ok=True)
    args = [OPENSCAD, "--backend", "Manifold", "--hardwarnings", "-o", str(path),
            "-D", f'case_name="{case}"']
    for value in overrides:
        args += ["-D", value]
    result = subprocess.run([*args, str(ROOT / "tests/geometry.scad")], capture_output=True, text=True)
    if invalid:
        assert "Assertion" in result.stderr and "ERROR" in result.stderr, result.stderr
        return None
    assert result.returncode == 0 and "ERROR" not in result.stderr and "WARNING" not in result.stderr, result.stderr
    mesh = trimesh.load_mesh(path, force="mesh")
    if case in {"water", "loaded_water", "fill_water"}:
        mesh.metadata["volume_check"] = json.loads(re.search(r"volume_check = (\[[^\n]+\])", result.stderr)[1])
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
    # Capping the virtual liquid at its fill plane can create collinear triangles.
    # Require clean triangulation for printable solids; the water probe tests topology.
    if case not in {"water", "loaded_water", "fill_water"}:
        assert mesh.nondegenerate_faces().all(), f"degenerate faces: {name}/{case}"
    return mesh


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scenarios = {
        "default": ([], 2),
        "one-chamber": (["chamber_count=1"], 1),
        "largest-square": (["paper_width=146.5", "paper_height=146.5"], 2),
        "largest-rectangle": (["paper_width=146.5", "paper_height=152.9"], 2),
        "small-no-inlets": (["paper_width=80", "paper_height=80", "chamber_count=1", "inlets_enabled=false"], 1),
        "derived-clearance": (["side_clearance=0", "cap_clearance=0.5", "inlet_opening_diameter=36"], 2),
        "no-base-ribs": (["base_enabled=false", "rib_enabled=false"], 2),
        "thick-paper": (["paper_thickness=0.5", "paper_face_clearance=0.2"], 2),
    }
    report = []
    for name, (overrides, count) in scenarios.items():
        for case in ("tank", "paper", "caps", "separation", "water", "fill_water", "loaded_water", "slit_caps", "inlet_caps", "handling"):
            mesh = export(name, case, overrides)
            parts = components(mesh)
            if case in {"paper", "caps", "separation", "handling"}:
                assert len(parts) == 1 and abs(mesh.volume - 1) < 1e-5, f"Collision: {name}/{case}: {mesh.volume:.6f} mm3"
            elif case in {"water", "loaded_water", "fill_water"}:
                assert len(parts) == count + 1, f"Leak/disconnected fill passage: {name}: {len(parts)} bodies"
                baths = [p for p in parts if p.bounds[0, 0] > 0]
                assert len(baths) == count, f"Liquid cavity count: {name}"
                for p in baths:
                    assert p.volume > 1000, f"Unexpected tiny liquid cavity: {name}"
                nominal, marked, first, second, empty = mesh.metadata["volume_check"]
                if case == "loaded_water":
                    assert all(p.volume / 1000 > marked for p in baths), f"Insufficient loaded headroom: {name}"
                    report[-1]["capacity_below_wiper_ml"] = [round(p.volume / 1000, 2) for p in baths]
                    print(f"PASS {name}/{case}", flush=True)
                    continue
                for p in baths:
                    # Compare the label calculation with the independently meshed liquid.
                    assert abs((empty if case == "water" else nominal) - p.volume / 1000) < 0.15, f"Fill calculation: {name}/{case}"
                    if case == "fill_water":
                        assert abs(p.volume / 1000 - marked) <= 2, f"Fill label: {name}"
                if case == "fill_water":
                    report[-1]["bath_with_paper_ml"] = [round(p.volume / 1000, 2) for p in baths]
                    print(f"PASS {name}/{case}", flush=True)
                    continue
                assert abs(first + second - marked) < 1e-6, f"Mix sum: {name}"
                assert first == round(first) and second == round(second), f"Fractional mixing amounts: {name}"
                assert abs(first - marked / 5) <= 0.5, f"Mix ratio rounding: {name}"
                report.append({"scenario": name, "empty_bath_ml": [round(p.volume / 1000, 2) for p in baths],
                               "marked_ml": marked, "mix_ml": [first, second]})
            else:
                expected = {"tank": 1, "slit_caps": count, "inlet_caps": count}[case]
                assert len(parts) == expected, f"Disconnected part: {name}/{case}: {len(parts)}"
                assert np.all(mesh.extents <= [174.001, 174.001, 178.001]), f"Printer bounds: {name}/{case}: {mesh.extents}"
            print(f"PASS {name}/{case}", flush=True)
    for name, settings in {
        "too-wide": ["paper_width=147"], "too-tall": ["paper_height=153"],
        "three-chambers": ["chamber_count=3"], "blocked-guide": ["paper_face_clearance=0.01"],
        "overlapping-caps": ["slit_cap_overlap=6"], "buried-fingers": ["paper_grip_height=0"],
        "unsupported-funnel": ["inlet_opening_diameter=70", "base_extension=76"],
        "too-deep-cap": ["slit_cap_rib_depth=2"],
    }.items():
        export(name, "tank", settings, invalid=True)
        print(f"PASS rejects {name}", flush=True)
    export("rounding", "rounding")
    print("PASS rounding boundaries and whole-ml quantities", flush=True)
    (OUT / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Passed {len(scenarios) * 10} geometry cases, rounding checks and 8 invalid configurations.")

if __name__ == "__main__":
    main()
