#!/usr/bin/env python3
"""Check the build123d holder; optionally require independent FreeCAD verification."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad.enlarger.checks import run_checks
from cad.enlarger.export import export, sha
from cad.enlarger.parameters import parameters


def check(output, config=None, freecad=None):
    output = Path(output).resolve()
    p = parameters(**(json.loads(Path(config).read_text()) if config else {}))
    # Invalidate earlier success evidence before any operation that can fail.
    output.mkdir(parents=True, exist_ok=True)
    for name in (
        "geometry-summary.json",
        "freecad-validation.json",
        "model-report.json",
    ):
        (output / name).unlink(missing_ok=True)
    export(output, p)
    checks = run_checks()
    if config:
        from cad.enlarger.checks import check_scenario

        for fmt in ("16:9", "4:3"):
            checks += [f"configured-{fmt}-{name}" for name in check_scenario(p, fmt)]
    if freecad:
        script = ROOT / "cad/enlarger/verify_freecad.py"
        result = subprocess.run(
            [str(freecad)],
            input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
            text=True,
            capture_output=True,
            check=False,
            timeout=300,
            env=os.environ | {"ENLARGER_OUTPUT": str(output)},
        )
        (output / "freecad-validation.log").write_text(result.stdout + result.stderr)
        path = output / "freecad-validation.json"
        if result.returncode or not path.exists():
            raise RuntimeError(
                f"No fresh FreeCAD validation: {output}/freecad-validation.log"
            )
        native = json.loads(path.read_text())
        assert native["passed"] and native["manifest_sha256"] == sha(
            output / "model-report.json"
        )
    report = {
        "status": "passed",
        "checks": checks,
        "plate_count": 9,
        "freecad_checked": bool(freecad),
        "physical_fit_accepted": False,
        "model_report_sha256": sha(output / "model-report.json"),
    }
    (output / "geometry-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"Passed nine native plates and {len(checks)} geometry cases; FreeCAD: {bool(freecad)}",
        flush=True,
    )
    return p


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/enlarger-native")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--freecad", default=os.environ.get("FREECAD_CMD"))
    args = parser.parse_args()
    check(args.output, args.config, args.freecad)
