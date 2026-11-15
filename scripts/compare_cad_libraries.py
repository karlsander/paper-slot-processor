#!/usr/bin/env python3
"""Compare pinned build123d and CadQuery clip implementations and their STEP files."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "simulation/comparison"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build123d-python", default=str(ROOT / ".venv-cad/bin/python")
    )
    parser.add_argument("--cadquery-python", default=str(ROOT / ".venv-cq/bin/python"))
    parser.add_argument("--output", type=Path, default=ROOT / "build/clip-comparison")
    parser.add_argument(
        "--freecad",
        default=os.environ.get("FREECAD_CMD")
        or shutil.which("FreeCADCmd")
        or shutil.which("freecadcmd")
        or "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = output / "comparison.json"
    report.unlink(missing_ok=True)

    def run(command, log, **kwargs):
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=300, **kwargs
        )
        (output / log).write_text(result.stdout + result.stderr)
        result.check_returncode()

    # Run sequentially so the timed builds do not compete with another backend.
    for backend, python in (
        ("build123d", args.build123d_python),
        ("cadquery", args.cadquery_python),
        ("cadquery_func", args.cadquery_python),
    ):
        run(
            [python, str(SOURCE / "run_backend.py"), backend, str(output)],
            f"{backend}.log",
        )
    for backend, python in (
        ("build123d", args.build123d_python),
        ("cadquery", args.cadquery_python),
    ):
        run(
            [python, str(SOURCE / "edit_step.py"), backend, str(output)],
            f"{backend}-step-edit.log",
        )
    openscad = (
        os.environ.get("OPENSCAD_BIN")
        or shutil.which("openscad")
        or "/opt/homebrew/bin/openscad"
    )
    run(
        [
            openscad,
            "--backend",
            "Manifold",
            "--hardwarnings",
            "--export-format",
            "asciistl",
            "-o",
            str(output / "openscad-reference.stl"),
            str(SOURCE / "reference.scad"),
        ],
        "openscad.log",
    )
    script = SOURCE / "verify_freecad.py"
    run(
        [args.freecad],
        "freecad.log",
        input=f"exec(compile(open({str(script)!r}).read(), {str(script)!r}, 'exec'))\n",
        env=os.environ | {"CLIP_COMPARISON_OUTPUT": str(output)},
    )
    # The FreeCAD console may exit zero after a Python exception.
    if not report.exists() or json.loads(report.read_text()).get("passed") is not True:
        raise RuntimeError(
            f"No fresh passing comparison report; inspect {output / 'freecad.log'}"
        )
    sources = [
        *SOURCE.glob("*.py"),
        *SOURCE.glob("*.scad"),
        ROOT / "v2/guide.scad",
        ROOT / "v2/parameters.scad",
        ROOT / "v2/geometry.scad",
    ]
    (output / "source-hashes.json").write_text(
        json.dumps(
            {
                str(path.relative_to(ROOT)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in sorted(sources)
            },
            indent=2,
        )
        + "\n"
    )
    print(f"PASS: {report}")


if __name__ == "__main__":
    main()
