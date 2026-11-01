#!/usr/bin/env python3
"""Export B2 and require a fresh, hash-linked native FreeCAD report."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--full-size", action="store_true")
    p.add_argument("--reuse", action="store_true")
    p.add_argument("--formats", nargs="+", default=["135", "half", "aps", "110"])
    p.add_argument(
        "--freecad",
        default=os.environ.get(
            "FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
        ),
    )
    a = p.parse_args()
    out = ROOT / (
        "build/negative-carrier-b2-full" if a.full_size else "build/negative-carrier-b2"
    )
    if not a.reuse:
        from cad.negative_carrier_b2 import export

        export.OUT = out
        assert export.export(a.formats, True, a.full_size)["passed"]
    manifest = out / "manifest.json"
    m = json.loads(manifest.read_text())
    assert (
        m["source_sha256"]
        == hashlib.sha256(
            (ROOT / "cad/negative_carrier_b2/model.py").read_bytes()
        ).hexdigest()
    )
    report = out / "freecad-validation.json"
    report.unlink(missing_ok=True)
    script = ROOT / "cad/negative_carrier_b2/verify_freecad.py"
    r = subprocess.run(
        [a.freecad],
        check=False,
        text=True,
        capture_output=True,
        timeout=1800,
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        env=os.environ | {"CARRIER_B2_OUTPUT": str(out)},
    )
    (out / "freecad-validation.log").write_text(r.stdout + r.stderr)
    assert r.returncode == 0 and report.exists(), out / "freecad-validation.log"
    data = json.loads(report.read_text())
    assert (
        data["passed"]
        and data["manifest_sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    )
    print(
        f"B2: {len(data['models'])} native assemblies and continuous frame sweeps passed."
    )


if __name__ == "__main__":
    main()
