#!/usr/bin/env python3
"""Build native parts and compare both image presets in FreeCAD and OpenSCAD."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad.parameters import parameters


def run(command, log, **kwargs):
    result = subprocess.run(
        command, check=False, capture_output=True, text=True, timeout=900, **kwargs
    )
    log.write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"Failed: {command}; inspect {log}")
    return result.stdout + result.stderr


def check(output, aspect, freecad, skip_export=False):
    output.mkdir(parents=True, exist_ok=True)
    report = output / "validation.json"
    report.unlink(missing_ok=True)
    if not skip_export:
        run(
            [
                sys.executable,
                "-m",
                "cad.export",
                "--aspect",
                str(aspect),
                "--output",
                str(output),
            ],
            output / "export.log",
            cwd=ROOT,
        )
    p = json.loads((output / "parameters.json").read_text())
    assert p == parameters(image_aspect=aspect), (
        "Export configuration differs from requested validation"
    )
    openscad = (
        os.environ.get("OPENSCAD_BIN")
        or shutil.which("openscad")
        or "/opt/homebrew/bin/openscad"
    )
    fields = [
        k
        for k, v in p.items()
        if isinstance(v, (int, float, list))
        and k
        not in ("socket_wall", "socket_height", "base_width", "base_depth", "vessel_x")
    ]
    fields += ["socket_wall", "socket_height", "base_width", "base_depth", "vessel_x"]
    # Check numerical design authority independently of the native geometry.
    probe = output / "parameter-oracle.scad"
    probe.write_text(
        f"include <{ROOT / 'v2/parameters.scad'}>\ninclude <{ROOT / 'v1_8/base.scad'}>\nvalid() valid_base() echo(values=["
        + ",".join("vessel_x()" if k == "vessel_x" else k for k in fields)
        + "]);\n"
    )
    log = run(
        [
            openscad,
            "--hardwarnings",
            "-D",
            f"image_aspect={aspect}",
            "-o",
            str(output / "parameter-oracle.csg"),
            str(probe),
        ],
        output / "parameter-oracle.log",
    )
    if "ERROR:" in log or "WARNING:" in log:
        raise RuntimeError(log)
    values = json.loads(re.search(r"values = (\[.*\])", log)[1])

    def delta(a, b):
        return (
            max(delta(*ab) for ab in zip(a, b, strict=True))
            if isinstance(a, list)
            else abs(a - b)
        )

    errors = {k: delta(p[k], v) for k, v in zip(fields, values, strict=True)}
    assert max(errors.values()) < 0.001, errors
    (output / "parameter-parity.json").write_text(
        json.dumps({"passed": True, "absolute_errors": errors}, indent=2) + "\n"
    )
    oracle = {
        "base": {"part": "base"},
        "clip": {"part": "clip"},
        "fit": {"part": "fit"},
    }
    for i, letter in enumerate("ab"):
        oracle[f"vessel_{letter}"] = {"part": "vessel", "chamber": i}
        oracle[f"guide_{letter}"] = {"part": "guide", "chamber": i}
        oracle[f"cover_{letter}"] = {"part": "guide", "chamber": i, "closed": True}
        for gap in (0.6, 0.8):
            oracle[f"trial_{letter}_{int(gap * 10)}"] = {
                "part": "guide",
                "chamber": i,
                "guide_gap": gap,
            }
    for name, defines in oracle.items():
        command = [
            openscad,
            "--backend",
            "Manifold",
            "--hardwarnings",
            "--export-format",
            "asciistl",
        ]
        for key, value in {"image_aspect": aspect, **defines}.items():
            command += ["-D", f"{key}={json.dumps(value)}"]
        log = run(
            command
            + [
                "-o",
                str(output / "parity" / f"{name}.stl"),
                str(ROOT / "cad/reference.scad"),
            ],
            output / "parity" / f"{name}.log",
        )
        if "ERROR:" in log or "WARNING:" in log:
            raise RuntimeError(log)
    script = ROOT / "cad/verify_freecad.py"
    run(
        [freecad],
        output / "freecad-validation.log",
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        env=os.environ | {"PROCESSOR_NATIVE_OUTPUT": str(output)},
    )
    if not report.exists() or json.loads(report.read_text()).get("passed") is not True:
        raise RuntimeError(
            f"No fresh passing report; inspect {output / 'freecad-validation.log'}"
        )
    print(f"PASS: {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/native-checked")
    parser.add_argument("--aspect", type=float, help="Omit to check both 16:9 and 2:1")
    parser.add_argument(
        "--skip-export", action="store_true", help="Validate existing matching exports"
    )
    parser.add_argument(
        "--freecad",
        default=os.environ.get("FREECAD_CMD")
        or shutil.which("FreeCADCmd")
        or "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
    )
    args = parser.parse_args()
    for name, aspect in (
        [("16x9", 16 / 9), ("2x1", 2)] if args.aspect is None else [("", args.aspect)]
    ):
        check((args.output / name).resolve(), aspect, args.freecad, args.skip_export)


if __name__ == "__main__":
    main()
