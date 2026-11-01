#!/usr/bin/env python3
"""Export concept assemblies, then independently verify them in FreeCAD."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/negative-carrier-concepts"
    )
    parser.add_argument(
        "--freecad",
        default=os.environ.get("FREECAD_CMD")
        or shutil.which("freecadcmd")
        or "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
    )
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = out / "freecad-validation.json"
    report.unlink(missing_ok=True)
    from cad.negative_carrier_concepts.model import export

    export(out)
    script = ROOT / "cad/negative_carrier_concepts/verify_freecad.py"
    result = subprocess.run(
        [args.freecad],
        check=False,
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        text=True,
        capture_output=True,
        env=os.environ | {"NEGATIVE_CONCEPT_OUTPUT": str(out)},
        timeout=600,
    )
    (out / "freecad.log").write_text(result.stdout + result.stderr)
    if (
        result.returncode
        or not report.exists()
        or json.loads(report.read_text()).get("passed") is not True
    ):
        raise RuntimeError(f"Concept checks did not pass: {out / 'freecad.log'}")
    print(
        "Six concept assemblies passed sampled rigid checks; real fit and registration remain unverified"
    )


if __name__ == "__main__":
    main()
