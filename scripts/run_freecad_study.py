#!/usr/bin/env python3
"""Evaluate current CAD dimensions, build native STEP solids and run FreeCAD headlessly."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "body_width",
    "body_depth",
    "body_height",
    "wall",
    "floor",
    "inner_width",
    "bath_gap",
    "inside_radius",
    "rim_overhang",
    "rim_height",
    "bottom_clearance",
    "well_cy",
    "well_top",
    "well_stations",
    "well_wall",
    "vessel_xmax",
    "cradle_floor",
    "cradle_clearance",
    "vessel_y",
    "vessel_pitch",
    "base_width",
    "base_depth",
    "socket_wall",
    "socket_height",
    "working_ml",
    "empty_level",
    "image_aspect",
]


def dimensions(output, aspect, openscad):
    probe = output / "parameters.scad"
    names = FIELDS + ["vessel_x"]
    expressions = FIELDS + ["vessel_x()"]
    probe.write_text(
        f"include <{ROOT / 'v2/parameters.scad'}>\n"
        f"include <{ROOT / 'v1_8/base.scad'}>\n"
        "valid() valid_base() { echo(study_values=["
        + ",".join(expressions)
        + "]); cube(1); }\n"
    )
    result = subprocess.run(
        [
            openscad,
            "--hardwarnings",
            "-D",
            f"image_aspect={aspect}",
            "-o",
            str(output / "parameters.csg"),
            str(probe),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    log = result.stdout + result.stderr
    (output / "parameters.log").write_text(log)
    if "ERROR:" in log or "WARNING:" in log:
        raise RuntimeError(log)
    match = re.search(r"study_values = (\[.*\])", log)
    if not match:
        raise RuntimeError("OpenSCAD did not return study dimensions")
    data = dict(zip(names, json.loads(match[1]), strict=True))
    data["source_sha256"] = hashlib.sha256(
        b"".join(
            path.read_bytes()
            for path in sorted(
                [*(ROOT / "v2").glob("*.scad"), *(ROOT / "v1_8").glob("*.scad")]
            )
        )
    ).hexdigest()
    (output / "parameters.json").write_text(json.dumps(data, indent=2) + "\n")
    return data


def run_stage(stage, output, executable):
    """FreeCAD's console can return zero after a Python error: require a fresh report."""
    environment = os.environ | {"PROCESSOR_STUDY_OUTPUT": str(output)}
    script = ROOT / f"simulation/freecad_{stage}.py"
    report_path = output / f"{stage}-report.json"
    report_path.unlink(missing_ok=True)
    code = f"exec(compile(open({str(script)!r}).read(), {str(script)!r}, 'exec'))\n"
    result = subprocess.run(
        [executable],
        check=False,
        input=code,
        text=True,
        capture_output=True,
        env=environment,
        timeout=300,
    )
    (output / f"freecad-{stage}.log").write_text(result.stdout + result.stderr)
    if result.returncode or not report_path.exists():
        raise RuntimeError(
            result.stdout + result.stderr or f"No fresh {stage} report was produced"
        )
    report = json.loads(report_path.read_text())
    if report.get("passed") is not True:
        raise RuntimeError(f"{stage} study failed; inspect {report_path}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aspect", type=float, default=16 / 9)
    parser.add_argument("--output", type=Path, default=ROOT / "build/freecad-study")
    parser.add_argument("--freecad", default=os.environ.get("FREECAD_CMD"))
    parser.add_argument(
        "--thermal",
        action="store_true",
        help="Also run the Gmsh/CalculiX wall benchmark",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    openscad = (
        os.environ.get("OPENSCAD_BIN")
        or shutil.which("openscad")
        or "/opt/homebrew/bin/openscad"
    )
    dimensions(output, args.aspect, openscad)
    subprocess.run(
        [sys.executable, str(ROOT / "simulation/export_model.py"), str(output)],
        check=True,
    )
    for part in ("base", "vessel"):
        result = subprocess.run(
            [
                openscad,
                "--backend",
                "Manifold",
                "--hardwarnings",
                "--export-format",
                "asciistl",
                "-D",
                f"image_aspect={args.aspect}",
                "-D",
                f'part="{part}"',
                "-o",
                str(output / f"reference-{part}.stl"),
                str(ROOT / "simulation/reference.scad"),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        (output / f"reference-{part}.log").write_text(result.stdout + result.stderr)
    executable = (
        args.freecad
        or shutil.which("FreeCADCmd")
        or shutil.which("freecadcmd")
        or "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
    )
    # Console stdin avoids GUI startup and also works with macOS application bundles.
    stages = ["fit"] + (["thermal"] if args.thermal else [])
    for stage in stages:
        run_stage(stage, output, executable)
        print(f"PASS: {stage} study — {output / (stage + '-report.json')}")


if __name__ == "__main__":
    main()
