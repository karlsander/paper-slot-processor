#!/usr/bin/env python3
"""Export the B1 prototype and independently check its sampled workflows."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check_bed(out, size, brim):
    """Conservative flat-part footprints, one part per plate, with a brim."""
    if (
        not math.isfinite(size)
        or not math.isfinite(brim)
        or brim < 0
        or size <= 2 * brim
    ):
        raise ValueError("Bed size must be finite and larger than two brim widths")
    manifest = out / "manifest.json"
    data = json.loads(manifest.read_text())
    report = {
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "bed_xy_mm": [size, size],
        "brim_mm": brim,
        "one_part_per_plate": True,
        "sliced": False,
        "parts": [],
    }
    for key, asset in data["assets"].items():
        if "print" not in asset:
            continue
        record = asset["print"]
        assert (
            hashlib.sha256((out / record["file"]).read_bytes()).hexdigest()
            == record["sha256"]
        )
        x, y, _ = record["extents_mm"]
        axis, diagonal = max(x, y), (x + y) / math.sqrt(2)
        extent = min(axis, diagonal) + 2 * brim
        report["parts"].append(
            {
                "asset": key,
                "stl_sha256": record["sha256"],
                "z_rotation_degrees": 45 if diagonal < axis else 0,
                "square_footprint_with_brim_mm": extent,
                "passed": extent <= size,
            }
        )
    report["passed"] = bool(report["parts"]) and all(
        p["passed"] for p in report["parts"]
    )
    (out / "bed-fit.json").write_text(json.dumps(report, indent=2) + "\n")
    assert report["passed"], (
        "Print footprint exceeds the requested bed; see bed-fit.json"
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/negative-carrier-b"
    )
    parser.add_argument("--formats", nargs="+", default=["135", "half", "aps", "110"])
    parser.add_argument(
        "--freecad",
        default=os.environ.get(
            "FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
        ),
    )
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument(
        "--bed-size", type=float, help="Optional square XY bed size in mm"
    )
    parser.add_argument(
        "--brim", type=float, default=5, help="Brim allowance for bed check, mm"
    )
    parser.add_argument(
        "--config", type=Path, help="JSON object keyed by format with Config overrides"
    )
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not args.reuse:
        from cad.negative_carrier_b.export import export

        export(
            out,
            args.formats,
            json.loads(args.config.read_text()) if args.config else None,
        )
    if args.bed_size is not None:
        check_bed(out, args.bed_size, args.brim)
    report = out / "freecad-validation.json"
    report.unlink(missing_ok=True)
    script = ROOT / "cad/negative_carrier_b/verify_freecad.py"
    result = subprocess.run(
        [args.freecad],
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=1800,
        env=os.environ | {"NEGATIVE_B_OUTPUT": str(out)},
    )
    (out / "freecad.log").write_text(result.stdout + result.stderr)
    if result.returncode or not report.exists():
        raise RuntimeError(f"FreeCAD did not produce a report: {out / 'freecad.log'}")
    data = json.loads(report.read_text())
    assert (
        data["manifest_sha256"]
        == hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest()
    )
    for model in data["models"]:
        print(
            model["format"],
            model["passed"],
            "poses:",
            len(model["samples"]),
            "failures:",
            model["failures"][:12],
            flush=True,
        )
    if not data["passed"]:
        raise RuntimeError(f"B1 geometry checks failed: {report}")
    print(
        "Sampled geometry passed. Real fit, optical performance and spring forces remain unverified."
    )


if __name__ == "__main__":
    main()
