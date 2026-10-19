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
WATER_CASES = {"water", "loaded_water", "fill_water", "cue_water", "below_cue_water", "low_water"}
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
    if case in WATER_CASES:
        mesh.metadata["volume_check"] = json.loads(re.search(r"volume_check = (\[[^\n]+\])", result.stderr)[1])
    if case == "sight_pool":
        mesh.metadata["indicator_check"] = json.loads(re.search(r"indicator_check = (\[[^\n]+\])", result.stderr)[1])
    assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0, name
    # Capping the virtual liquid at its fill plane can create collinear triangles.
    # Require clean triangulation for printable solids; the water probe tests topology.
    if case not in WATER_CASES | {"sight_pool"}:
        assert mesh.nondegenerate_faces().all(), f"degenerate faces: {name}/{case}"
    return mesh


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    scenarios = {
        "default": ([], 2),
        "one-chamber": (["chamber_count=1"], 1),
        "largest-square": (["paper_width=146.5", "paper_height=146.5"], 2),
        "largest-rectangle": (["paper_width=146.5", "paper_height=152.4"], 2),
        "small-no-inlets": (["paper_width=80", "paper_height=80", "chamber_count=1", "inlets_enabled=false"], 1),
        "derived-clearance": (["side_clearance=0", "cap_clearance=0.5", "inlet_opening_diameter=36"], 2),
        "no-base-ribs": (["base_enabled=false", "rib_enabled=false"], 2),
        "thick-paper": (["paper_thickness=0.5", "paper_face_clearance=0.2"], 2),
    }
    report = []
    for name, (overrides, count) in scenarios.items():
        for case in ("tank", "paper", "caps", "separation", "water", "fill_water", "cue_water", "loaded_water", "slit_caps", "inlet_caps", "handling"):
            mesh = export(name, case, overrides)
            parts = components(mesh)
            if case in {"paper", "caps", "separation", "handling"}:
                assert len(parts) == 1 and abs(mesh.volume - 1) < 1e-5, f"Collision: {name}/{case}: {mesh.volume:.6f} mm3"
            elif case in WATER_CASES:
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
                    assert abs((empty if case == "water" else marked) - p.volume / 1000) < 0.15, f"Fill calculation: {name}/{case}"
                    if case in {"fill_water", "cue_water"}:
                        assert abs(p.volume / 1000 - marked) <= 2, f"Fill label: {name}"
                if case in {"fill_water", "cue_water"}:
                    report[-1]["bath_with_paper_ml" if case == "fill_water" else "visible_cue_ml"] = [round(p.volume / 1000, 2) for p in baths]
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
    # Independent cavity meshes must remain connected even below the cue.
    for name, overrides in {"default": [], "small-bore": ["inlet_bore_diameter=12", "inlet_funnel_height=22"],
                           "wide-bore": ["inlet_bore_diameter=18"],
                           "one-chamber": ["chamber_count=1"]}.items():
        count = 1 if name == "one-chamber" else 2
        for case in ("below_cue_water", "low_water"):
            mesh = export(name, case, overrides)
            assert len(components(mesh)) == count + 1, f"Inlet pocket or leak: {name}/{case}"
        flow = export(name, "inlet_flow", overrides)
        assert len(components(flow)) == 1 and abs(flow.volume - 1) < 1e-5, f"Obstructed bore: {name}"
        pool = export(name, "sight_pool", overrides)
        assert len(components(pool)) == 1 and 0.05 < pool.volume / 1000 < 1, f"Indicator is not a small pool: {name}"
        depth, volume = pool.metadata["indicator_check"]
        assert 0.5 <= depth <= 2.5 and abs(pool.volume / 1000 - volume) < 0.01, f"Indicator calibration: {name}"
        # Actual loft triangles, excluding the horizontal end faces inside the
        # bath and at the open mouth, must stay within 45° of vertical.
        inlet = export(name, "inlet", overrides)
        sides = np.abs(inlet.face_normals[:, 2]) < 0.999
        assert np.max(np.abs(inlet.face_normals[sides, 2])) <= 2**-0.5 + 1e-5, f"Unsupported inlet wall: {name}"
        print(f"PASS {name}/inlet drainage, bore, indicator and overhang checks", flush=True)
    for name, settings in {
        "too-wide": ["paper_width=147"], "too-tall": ["paper_height=152.5"],
        "three-chambers": ["chamber_count=3"], "blocked-guide": ["paper_face_clearance=0.01"],
        "overlapping-caps": ["slit_cap_overlap=6"], "buried-fingers": ["paper_grip_height=0"],
        "unsupported-funnel": ["inlet_opening_diameter=70", "base_extension=76"],
        "too-deep-cap": ["slit_cap_rib_depth=2"],
        "no-displacement-reserve": ["fill_headroom=2"],
        "deep-indicator": ["inlet_sight_depth=4"],
    }.items():
        export(name, "tank", settings, invalid=True)
        print(f"PASS rejects {name}", flush=True)
    export("rounding", "rounding")
    print("PASS rounding boundaries and whole-ml quantities", flush=True)
    (OUT / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Passed {len(scenarios) * 11} geometry cases, 20 inlet cases, rounding checks and 10 invalid configurations.")

if __name__ == "__main__":
    main()
