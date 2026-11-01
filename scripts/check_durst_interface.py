#!/usr/bin/env python3
"""Build the insertion fixture and require fresh FreeCAD geometry verification."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad.durst_c35_interface.export import export, sha
from cad.durst_c35_interface.model import DEFAULT_MEASUREMENTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurements", type=Path, default=DEFAULT_MEASUREMENTS)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/durst-c35-interface"
    )
    parser.add_argument(
        "--freecad",
        default=os.environ.get(
            "FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
        ),
    )
    args = parser.parse_args()
    output = args.output.resolve()
    report = output / "freecad-validation.json"
    report.unlink(missing_ok=True)
    export(output, args.measurements)
    script = ROOT / "cad/durst_c35_interface/verify_freecad.py"
    result = subprocess.run(
        [args.freecad],
        check=False,
        input=f"exec(compile(open({str(script)!r}).read(), {str(script)!r}, 'exec'))\n",
        text=True,
        capture_output=True,
        timeout=300,
        env=os.environ | {"DURST_INTERFACE_OUTPUT": str(output)},
    )
    (output / "freecad-validation.log").write_text(result.stdout + result.stderr)
    if result.returncode or not report.exists():
        raise RuntimeError(
            f"No fresh native result; inspect {output / 'freecad-validation.log'}"
        )
    data = json.loads(report.read_text())
    assert data["geometry_passed"] is True
    assert data["manifest_sha256"] == sha(output / "manifest.json")
    print(
        f"PASS: {data['native_solids']} native solids and clearance controls; physical fit remains unverified"
    )


if __name__ == "__main__":
    main()
