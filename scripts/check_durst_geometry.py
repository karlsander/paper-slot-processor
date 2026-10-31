#!/usr/bin/env python3
"""Export with build123d, then verify geometry and hinge motion in FreeCAD."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad.durst_c35.parameters import parameters


def verify(output, freecad):
    report = output / "validation.json"
    report.unlink(missing_ok=True)
    model = json.loads((output / "model-report.json").read_text())
    if model.get("passed") is not True:
        raise RuntimeError("Model export did not pass")
    for relative, expected in model["files_sha256"].items():
        if hashlib.sha256((output / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Export changed since model verification: {relative}")
    script = ROOT / "cad/durst_c35/verify_freecad.py"
    result = subprocess.run(
        [freecad],
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=600,
        env=os.environ | {"DURST_C35_OUTPUT": str(output)},
    )
    log = output / "freecad-validation.log"
    log.write_text(result.stdout + result.stderr)
    if (
        result.returncode
        or not report.exists()
        or json.loads(report.read_text()).get("passed") is not True
    ):
        raise RuntimeError(f"No fresh passing FreeCAD report; inspect {log}")
    return json.loads(report.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/durst-c35-native")
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--freecad",
        default=os.environ.get("FREECAD_CMD")
        or shutil.which("FreeCADCmd")
        or shutil.which("freecadcmd")
        or "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
    )
    args = parser.parse_args()
    from cad.durst_c35.export import export

    output = args.output.resolve()
    export(
        output,
        parameters(**(json.loads(args.config.read_text()) if args.config else {})),
    )
    verify(output, args.freecad)
    print(f"PASS: carrier geometry and sampled hinge motion — {output}")


if __name__ == "__main__":
    main()
