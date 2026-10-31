#!/usr/bin/env python3
"""Export v2 print plates with preserved orientations and actual Bambu estimates."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
import build_openscad as build

ROOT = Path(__file__).resolve().parents[1]
PARTS = {
    "vessel_a": ("Vessel A", "vessel", {"chamber": 0, "print_layout": True}, 1),
    "vessel_b": ("Vessel B", "vessel", {"chamber": 1, "print_layout": True}, 1),
    "guide_a": ("Paper guide A", "guide", {"chamber": 0, "print_layout": True}, 1),
    "guide_b": ("Paper guide B", "guide", {"chamber": 1, "print_layout": True}, 1),
    "cover_a": ("Cover A", "cover", {"chamber": 0}, 1),
    "cover_b": ("Cover B", "cover", {"chamber": 1}, 1),
    "clips": ("Four retaining clips", "clips", {}, 4),
    "cradle_a": ("Cradle A", "cradle", {"chamber": 0}, 1),
    "cradle_b": ("Cradle B", "cradle", {"chamber": 1}, 1),
    "links": ("Two cradle links", "links", {}, 2),
    "heater_clamps": ("Two heater clamps", "heater_clamps", {}, 2),
    "guard_tile": ("Heater guard tile (print four)", "guard_tile", {}, 1),
    "guard_links": ("Two guard links", "guard_links", {}, 2),
    "guard_mounts": ("Four guard mounts", "guard_mounts", {}, 4),
    "strap_anchors": ("Two strap anchors", "strap_anchors", {}, 2),
    "mat_keepers": ("Four mat edge keepers", "mat_keepers", {}, 4),
    "cable_saddle": ("Cable saddle", "cable_saddle", {}, 1),
    "fit": ("Guide and clip fit section", "fit", {}, 1),
}
for _gap in [0.6,0.8]:
    for _id,_letter in enumerate('ab'):
        PARTS[f'trial_{_letter}_{int(_gap*10)}'] = (f'Optional {_gap} mm guide {_letter.upper()}', 'guide',
            {'chamber':_id,'print_layout':True,'guide_gap':_gap},1)
QUANTITIES = {"guard_tile": 4, "heater_clamps": 2, "guard_mounts": 2,
              "strap_anchors": 2, "mat_keepers": 2, "cable_saddle": 2}
STANDARD_PARTS = tuple(k for k in PARTS if k != "fit" and not k.startswith("trial_"))


def preset_overrides(name):
    if name.startswith("vessel_"):
        return {"enable_support": "1", "support_type": "tree(auto)",
                "support_on_build_plate_only": "1", "support_threshold_angle": "30",
                "brim_type": "outer_only", "brim_width": "3"}
    return {"enable_support": "0", "brim_type": "no_brim"}


def export(name, folder, parameters, slice_model=True):
    return export_plate(name, folder, parameters, slice_model,
                        source=ROOT / "v2/processor.scad", definition=PARTS[name],
                        quantity=QUANTITIES.get(name, 1), optional=name not in STANDARD_PARTS)


def export_plate(name, folder, parameters, slice_model=True, *, source, definition,
                 quantity=1, optional=False):
    """Validate and slice a plate using the shared A1 mini print settings."""
    label, part, overrides, count = definition
    folder.mkdir(parents=True, exist_ok=True)
    defines = parameters | overrides | {"part": part}
    stl = folder / f"{name}.stl"
    cmd = [build.OPENSCAD, "--backend", "Manifold", "--hardwarnings", "--export-format", "asciistl"]
    for k, v in defines.items():
        cmd += ["-D", f"{k}={json.dumps(v)}"]
    result = subprocess.run(cmd + ["-o", str(stl), str(source)],
                            capture_output=True, text=True, timeout=180)
    (folder / "openscad.log").write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    mesh = build.validate_mesh(stl)
    if not (mesh["is_watertight"] and mesh["is_winding_consistent"] and mesh["body_count"] == count):
        raise RuntimeError(f"{name}: invalid mesh {mesh}")
    if mesh["degenerate_faces"] or mesh["duplicate_faces"]:
        raise RuntimeError(f"{name}: degenerate geometry")
    if any(x > limit + 0.001 for x, limit in zip(mesh["extents_mm"], [174,174,178])):
        raise RuntimeError(f"{name}: exceeds reserved printer bounds")
    report = {"name": name, "label": label, "parameters": parameters, "quantity": quantity, "optional": optional, "mesh": mesh, "stl": str(stl)}
    if slice_model:
        presets = build.resolved_bambu_presets(folder)
        process = json.loads(presets["process"].read_text()) | preset_overrides(name)
        presets["process"].write_text(json.dumps(process, indent=2))
        # Bambu's auto-arranger reserves a large theoretical tree envelope and can
        # reject a fitting vessel. Keep its designed orientation and centred import.
        arrange = not name.startswith("vessel_")
        sliced = build.bambu_slice(stl, folder, name, presets, arrange=arrange)
        result = build.read_json(sliced["bambu_result"])
        warnings = [p["warning_message"] for p in result.get("sliced_plates", []) if p.get("warning_message")]
        if result.get("return_code") != 0 or warnings:
            raise RuntimeError(f"{name}: slicer diagnostics {result}")
        project = build.bambu_project(stl, folder, folder, name, presets, arrange=arrange)
        report |= {"stats": build.parse_gcode(sliced["gcode"])["stats"], "project": str(project), "slicer": result}
    (folder / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="*", choices=list(PARTS))
    parser.add_argument("--aspect", type=float, default=16/9)
    parser.add_argument("--trials", action="store_true", help="Also export fit section and optional 0.6/0.8 mm guides")
    parser.add_argument("--mesh-only", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "build/v2-print")
    args = parser.parse_args()
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    names = list(args.parts or STANDARD_PARTS)
    if args.trials: names += [k for k in PARTS if k not in STANDARD_PARTS and k not in names]
    parameters = {"image_aspect": args.aspect}
    reports = [export(name, folder / name, parameters, not args.mesh_only) for name in names]
    (folder / "summary.json").write_text(json.dumps(reports, indent=2) + "\n")
    digest=hashlib.sha256()
    for path in sorted((ROOT / "v2").glob("*.scad")): digest.update(path.name.encode()+path.read_bytes())
    (folder / "configuration.json").write_text(json.dumps(parameters | {"cad_sha256":digest.hexdigest()},indent=2))
    with zipfile.ZipFile(folder / "processor-v2-print-files.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for report in reports:
            for key in ("stl", "project"):
                if key in report:
                    path = Path(report[key]); archive.write(path, path.relative_to(folder))
        archive.write(folder / "summary.json", "summary.json")
        archive.write(folder / "configuration.json", "configuration.json")
        archive.write(ROOT / "README.md", "README.md")
        archive.write(ROOT / "docs/heating.md", "docs/heating.md")
        archive.write(ROOT / "docs/v1.md", "docs/v1.md")
    print(f"Built {len(reports)} v2 plates in {folder}")


if __name__ == "__main__":
    main()
