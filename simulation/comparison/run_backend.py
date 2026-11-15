"""Run one implementation in its own pinned Python environment."""

import argparse
import importlib
import json
import platform
import statistics
import time
from dataclasses import asdict
from pathlib import Path

from clip_spec import Clip, cases, invalid_cases

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("backend", choices=("build123d", "cadquery", "cadquery_func"))
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
report_path = args.output / f"{args.backend}.json"
report_path.unlink(missing_ok=True)
make_clip = importlib.import_module(f"clip_{args.backend}").make_clip
library = importlib.import_module(
    "build123d" if args.backend == "build123d" else "cadquery"
)
OCP = importlib.import_module("OCP")


def inspect_shape(shape):
    if args.backend == "build123d":
        return shape.is_valid, len(shape.solids()), shape.volume
    return shape.isValid(), len(shape.Solids()), shape.Volume()


def export(shape, path):
    if args.backend == "build123d":
        library.export_step(shape, path)
    else:
        library.exporters.export(shape, str(path))


regular, stress = cases()
results = []
for kind, group in (("regular", regular), ("exploratory", stress)):
    for name, params in group:
        row = {"name": name, "kind": kind, "parameters": asdict(params)}
        try:
            started = time.perf_counter()
            shape = make_clip(params)
            elapsed = time.perf_counter() - started
            valid, solids, volume = inspect_shape(shape)
            assert valid and solids == 1 and volume > 0, (valid, solids, volume)
            filename = f"{args.backend}-{name}.step"
            export(shape, args.output / filename)
            row.update(
                success=True, volume_mm3=volume, build_seconds=elapsed, step=filename
            )
        except Exception as exc:  # noqa: BLE001 - record comparative kernel failures
            row.update(success=False, error=f"{type(exc).__name__}: {exc}")
        results.append(row)

timings = {}
for name, params in (("original", Clip()), ("rounded_roots", Clip(root_radius=0.8))):
    make_clip(
        params
    )  # Warm up before timing; exclude import, shape validation and STEP I/O.
    elapsed = []
    for _ in range(9):
        started = time.perf_counter()
        shape = make_clip(params)
        elapsed.append(time.perf_counter() - started)
        assert inspect_shape(shape)[:2] == (True, 1)
    timings[name] = {
        "median_seconds": statistics.median(elapsed),
        "samples_seconds": elapsed,
    }

rejected = 0
for params in invalid_cases():
    try:
        make_clip(params)
    except ValueError:
        rejected += 1
assert rejected == len(invalid_cases()), "Shared parameter guard failed"
passed = all(row["success"] for row in results if row["kind"] == "regular")
report_path.write_text(
    json.dumps(
        {
            "backend": args.backend,
            "library_version": library.__version__,
            "ocp_version": OCP.__version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "passed": passed,
            "cases": results,
            "timings": timings,
            "invalid_inputs_rejected_by_shared_guard": rejected,
        },
        indent=2,
    )
    + "\n"
)
print(
    args.backend, "PASS" if passed else "FAIL", len(regular), "regular cases", timings
)
raise SystemExit(0 if passed else 1)
