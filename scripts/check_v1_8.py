#!/usr/bin/env python3
"""Check shared-base printing/removal and exact v2 wet-part compatibility."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import numpy as np
import build_openscad as build
from build_v1_8 import PARTS, STANDARD_PARTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/v1.8-checks"


def render(name, source, parameters, empty=False):
    target = OUT / f"{name}.stl"
    target.unlink(missing_ok=True)
    command = [build.OPENSCAD, "--backend", "Manifold", "--hardwarnings", "--export-format", "asciistl"]
    for key, value in parameters.items():
        command += ["-D", f"{key}={json.dumps(value)}"]
    result = subprocess.run(command + ["-o", str(target), str(ROOT / source)],
                            capture_output=True, text=True, timeout=180)
    log = result.stdout + result.stderr
    (OUT / f"{name}.log").write_text(log)
    assert "ERROR:" not in log and "WARNING:" not in log, log
    if empty:
        assert "Current top level object is empty" in log, f"{name}: collision\n{log}"
        return {"name": name, "empty": True}
    assert result.returncode == 0 and target.is_file(), log
    mesh = build.validate_mesh(target)
    assert mesh["is_watertight"] and mesh["is_winding_consistent"], mesh
    assert not mesh["degenerate_faces"] and not mesh["duplicate_faces"], mesh
    assert all(size<=limit+0.001 for size,limit in zip(mesh["extents_mm"],[174,174,178])), mesh
    assert abs(mesh["bounds_mm"][0][2])<0.001, mesh
    return {"name": name, "mesh": mesh}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reports = []
    assert sum(PARTS[name][3] for name in STANDARD_PARTS) == 9
    for preset, aspect in [("16x9",16/9),("2x1",2)]:
        parameters = {"image_aspect":aspect}
        base = render(f"{preset}-base", "tests/v1_8_geometry.scad", parameters)
        assert base["mesh"]["body_count"] == 1
        np.testing.assert_allclose(base["mesh"]["extents_mm"], [170.8,138,36], atol=0.001)
        reports.append(base)
        for check in ("removal","neighbor"):
            for chamber in (0,1):
                reports.append(render(f"{preset}-{check}-{chamber}", "tests/v1_8_geometry.scad",
                    parameters | {"check":check,"chamber":chamber}, empty=True))
        for name in ("vessel_a","vessel_b","guide_a","guide_b","clips","cover_a","cover_b"):
            _, part, overrides, count = PARTS[name]
            meshes = []
            for version, source in [("v18","v1_8/processor.scad"),("v2","v2/processor.scad")]:
                ident = f"{preset}-{name}-{version}"
                report = render(ident, source, parameters | overrides | {"part":part})
                assert report["mesh"]["body_count"] == count
                meshes.append(build.require_trimesh().load_mesh(OUT / f"{ident}.stl"))
            # Compare actual exported surfaces independent of vertex/triangle ordering.
            def surface(mesh):
                triangles = np.round(mesh.triangles, 5)
                canonical = [tuple(sorted(map(tuple, triangle))) for triangle in triangles]
                return sorted(canonical)
            assert surface(meshes[0]) == surface(meshes[1]), f"{name}: changed v2 surface"
            reports.append({"name":f"{preset}-{name}-v2-compatibility", "identical_surface":True})
    # This guard is additional to v2's individual-module bound check.
    result = subprocess.run([build.OPENSCAD,"--hardwarnings","-D","module_gap=50",
        "-o",str(OUT / "oversized.csg"),str(ROOT / "v1_8/processor.scad")],
        capture_output=True,text=True,timeout=60)
    assert "Shared base exceeds" in result.stderr, result.stderr
    reports.append({"name":"oversized-base", "rejected":True})
    (OUT / "summary.json").write_text(json.dumps(reports,indent=2)+"\n")
    print(f"PASS: {len(reports)} v1.8 geometry and compatibility checks")


if __name__ == "__main__":
    main()
