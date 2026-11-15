#!/usr/bin/env python3
"""Validate B2 against the measured C35 fixture under explicit placement assumptions."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad.durst_c35_interface.export import sha
from cad.negative_carrier_b2.interface import export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/negative-carrier-interface"
    )
    parser.add_argument("--formats", nargs="+", default=["135", "half", "aps", "110"])
    parser.add_argument("--release-drop", type=float, default=0.4)
    parser.add_argument(
        "--freecad",
        default=os.environ.get(
            "FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
        ),
    )
    args = parser.parse_args()
    out = args.output.resolve()
    export(out, args.formats, args.release_drop)
    script = ROOT / "cad/negative_carrier_b2/verify_interface.py"
    result = subprocess.run(
        [args.freecad],
        check=False,
        text=True,
        capture_output=True,
        timeout=1800,
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        env=os.environ | {"CARRIER_INTERFACE_OUTPUT": str(out)},
    )
    (out / "interface-validation.log").write_text(result.stdout + result.stderr)
    path = out / "interface-validation.json"
    if result.returncode or not path.exists():
        raise RuntimeError(
            f"No fresh interface result; inspect {out}/interface-validation.log"
        )
    data = json.loads(path.read_text())
    assert data["passed"] and data["manifest_sha256"] == sha(
        out / "interface-manifest.json"
    )
    print(
        f"PASS: {len(data['models'])} measured-interface scenarios; physical fit and registration remain provisional"
    )


if __name__ == "__main__":
    main()
