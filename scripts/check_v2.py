#!/usr/bin/env python3
"""Independent v2 solid, liquid, swept-paper and assembly-clearance checks."""
from __future__ import annotations
import json
from pathlib import Path
import re
import subprocess
import build_openscad as build

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/v2-checks"


def render(check, defines=None, *, empty=False, printable=False, ident=None):
    values = {"check": check, **(defines or {})}
    name = ident or check
    target = OUT / f"{name}.stl"
    target.unlink(missing_ok=True)
    cmd = [build.OPENSCAD, "--backend", "Manifold", "--hardwarnings", "--export-format", "asciistl"]
    for k, v in values.items():
        cmd += ["-D", f"{k}={json.dumps(v)}"]
    cmd += ["-o", str(target), str(ROOT / "tests/v2_geometry.scad")]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    log = proc.stdout + proc.stderr
    (OUT / f"{name}.log").write_text(log)
    match = re.search(r"check_values = (\[[^\n]+\])", log)
    assert match, f"{name}: no metadata\n{log}"
    meta = json.loads(match[1])
    assert "ERROR:" not in log and "WARNING:" not in log, f"{name}: {log}"
    if empty:
        if "Current top level object is empty" in log:
            return {"name": name, "empty": True}
        # Exact seating/contact planes can survive Manifold intersection as zero-volume
        # triangles. Require a genuinely flat plane, not merely a small collision volume.
        contact = build.require_trimesh().load_mesh(target)
        signed_volume = float((contact.triangles[:,0] * contact.triangles_cross).sum() / 6)
        assert min(contact.extents) < 1e-6 and abs(signed_volume) < 1e-5, f"{name}: unwanted solid intersection\n{log}"
        return {"name": name, "contact_plane_only": True}
    assert proc.returncode == 0 and target.exists(), f"{name}: {log}"
    mesh = build.validate_mesh(target)
    assert mesh["is_watertight"] and mesh["is_winding_consistent"], f"{name}: invalid mesh {mesh}"
    assert mesh["body_count"] == 1, f"{name}: disconnected regions {mesh}"
    assert not mesh["degenerate_faces"] and not mesh["duplicate_faces"], name
    if printable:
        assert all(a <= b + 0.001 for a, b in zip(mesh["extents_mm"], [174,174,178])), f"{name}: printer bounds {mesh['extents_mm']}"
        assert abs(mesh["bounds_mm"][0][2]) < 0.001, f"{name}: floats above the bed"
        if check == "vessel":
            assert min(mesh["bounds_mm"][0][:2]) >= 3-0.001 and max(mesh["bounds_mm"][1][:2]) <= 177+0.001, f"{name}: bed placement loses the reserved margin"
    if check in {"empty_water", "loaded_water"}:
        assert abs(mesh["volume_mm3"] / 1000 - meta[0]) < 0.22, f"{name}: volume mismatch"
    # Test full image immersion at the top of the stroke using the raised-sheet liquid level.
    assert meta[3] - meta[4] >= 1, f"{name}: image leaves liquid during agitation"
    assert meta[5] - meta[2] >= 6, f"{name}: insufficient loaded freeboard"
    assert 0.5 <= meta[8] <= 2.5 and 0 < meta[9] < 0.5, f"{name}: fill cue"
    assert sum(meta[10]) == meta[0] and sum(meta[11]) == meta[0], f"{name}: recipe sum"
    return {"name": name, "mesh": mesh, "metadata": meta}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reports = []
    for preset, params in [("16x9", {}), ("2x1", {"image_aspect": 2})]:
        for chamber in [0, 1]:
            for part in ["vessel", "guide", "cover", "cradle"]:
                reports.append(render(part, params | {"chamber": chamber}, printable=True, ident=f"{preset}-{part}-{chamber}"))
        for part in ["clip", "link", "heater_clamp", "guard_tile", "guard_link", "guard_mount", "strap_anchor", "central_anchor", "mat_keeper", "cable_saddle"]:
            reports.append(render(part, params, printable=True, ident=f"{preset}-{part}"))
        for part in ["empty_water", "loaded_water", "low_water"]:
            reports.append(render(part, params, ident=f"{preset}-{part}"))
        for part in ["paper_collision", "guide_collision", "clip_collision", "cradle_removal", "heater_collision", "holder_collision", "fittings_mat_collision", "fittings_plate_collision", "fittings_removal", "fittings_cradle_collision"]:
            for chamber in ([0, 1] if part in {"paper_collision", "guide_collision", "clip_collision", "cradle_removal"} else [0]):
                reports.append(render(part, params | {"chamber": chamber}, empty=True, ident=f"{preset}-{part}-{chamber}"))
    for gap in [0.6, 0.8, 1.6]:
        reports.append(render("guide", {"guide_gap": gap}, printable=True, ident=f"guide-{gap}"))
        reports.append(render("paper_collision", {"guide_gap": gap}, empty=True, ident=f"paper-gap-{gap}"))
    for index, params in enumerate([{"image_aspect": 2.3}, {"guide_gap": 0.35},
            {"freeboard": 3}, {"well_mouth": 24}, {"heater_width": 400},
            {"recipe_b": [1,0]}, {"guard_gap": 2}]):
        cmd = [build.OPENSCAD, "--hardwarnings", "-o", str(OUT / f"invalid-{index}.csg")]
        for key, value in params.items():
            cmd += ["-D", f"{key}={json.dumps(value)}"]
        proc = subprocess.run(cmd + [str(ROOT / "v2/processor.scad")], capture_output=True, text=True)
        assert "ERROR: Assertion" in proc.stderr, f"Invalid geometry accepted: {params}"
        reports.append({"invalid_parameters": params, "rejected": True})
    (OUT / "summary.json").write_text(json.dumps(reports, indent=2) + "\n")
    print(f"PASS: {len(reports)} v2 geometry checks")


if __name__ == "__main__":
    main()
