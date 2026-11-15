#!/usr/bin/env python3
"""Build and verify both image presets in FreeCAD."""

import argparse
import json
import os
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
