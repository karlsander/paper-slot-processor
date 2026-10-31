#!/usr/bin/env python3
"""Build estimated C35 mating envelopes and check a prescribed insertion in FreeCAD."""

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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", type=Path, default=ROOT / "build/durst-c35-native")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/durst-c35-insertion"
    )
    parser.add_argument(
        "--config", type=Path, help="JSON overrides for estimated enlarger dimensions"
    )
    parser.add_argument(
        "--freecad",
        default=os.environ.get("FREECAD_CMD")
        or shutil.which("freecadcmd")
        or shutil.which("FreeCADCmd")
        or "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
    )
    args = parser.parse_args()
    from cad.durst_c35_insertion.model import export, parameters, sequence

    carrier, out = args.carrier.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = out / "insertion-validation.json"
    report.unlink(missing_ok=True)
    model = json.loads((carrier / "model-report.json").read_text())
    validation = json.loads((carrier / "validation.json").read_text())
    if (
        model.get("passed") is not True
        or validation.get("passed") is not True
        or validation["model_report_sha256"] != sha(carrier / "model-report.json")
    ):
        raise ValueError(
            "A matching, passing carrier export and FreeCAD study are required"
        )
    for name, expected in model["files_sha256"].items():
        if sha(carrier / name) != expected:
            raise ValueError(f"Carrier export changed: {name}")
    # Keep this study self-contained while preserving the verified carrier solids.
    for name in (
        "a.step",
        "b.step",
        "parameters.json",
        "model-report.json",
        "validation.json",
    ):
        shutil.copy2(carrier / name, out / ("carrier-" + name))
    q = parameters(**(json.loads(args.config.read_text()) if args.config else {}))
    export(out, q)
    (out / "fixture-parameters.json").write_text(json.dumps(q, indent=2) + "\n")
    (out / "motion.json").write_text(json.dumps(sequence(q), indent=2) + "\n")
    source = ROOT / "cad/durst_c35_insertion"
    manifest = {
        "schema_version": 1,
        "evidence_level": "provisional, unmeasured contact envelopes",
        "physical_fit_verified": False,
        "files_sha256": {p.name: sha(p) for p in sorted(out.glob("*.step"))},
        "source_sha256": {p.name: sha(p) for p in sorted(source.glob("*.py"))},
        "runner_sha256": sha(Path(__file__)),
    }
    for name in (
        "fixture-parameters.json",
        "motion.json",
        "carrier-parameters.json",
        "carrier-model-report.json",
        "carrier-validation.json",
    ):
        manifest["files_sha256"][name] = sha(out / name)
    (out / "study-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    script = source / "verify_freecad.py"
    result = subprocess.run(
        [args.freecad],
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=600,
        env=os.environ | {"DURST_INSERTION_OUTPUT": str(out)},
    )
    (out / "freecad-insertion.log").write_text(result.stdout + result.stderr)
    if (
        result.returncode
        or not report.exists()
        or json.loads(report.read_text()).get("verification_completed") is not True
    ):
        raise RuntimeError(
            f"No fresh completed study: inspect {out / 'freecad-insertion.log'}"
        )
    r = json.loads(report.read_text())
    if args.config is None and not all(
        c["detected"] for c in r["negative_controls"].values()
    ):
        raise RuntimeError("A default negative control failed to detect interference")
    print(
        f"Completed {len(r['samples'])} provisional poses; nominal path clear: {r['nominal_path_clear']}; physical fit: unverified"
    )
    if not r["nominal_path_clear"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
