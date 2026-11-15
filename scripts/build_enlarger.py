#!/usr/bin/env python3
"""Build native CAD, previews and saved/reopened Bambu projects; never print."""

import argparse
import json
import sys
import zipfile
from pathlib import Path

from check_enlarger import ROOT, check

sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/enlarger-native")
    parser.add_argument("--config", type=Path)
    parser.add_argument(
        "--freecad",
        default="/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
    )
    parser.add_argument("--geometry-only", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    p = check(output, args.config, args.freecad)
    from cad.enlarger.render import render

    render(p, output / "images")
    if args.geometry_only:
        return
    # This native Bambu importer consumes our STL plates, checks settings and
    # source vertices after saving, then reopens and slices each saved project.
    # No OpenSCAD model, executable or mesh is used anywhere in this pipeline.
    from build_native_bambu import export as bambu_export

    model = json.loads((output / "model-report.json").read_text())
    reports = []
    for name in model["plates"]:
        folder = output / "bambu" / name
        bambu_export(output, folder, 0.4, name, selected_part=name)
        reports.append(json.loads((folder / "project-report.json").read_text()))
    (output / "print-summary.json").write_text(
        json.dumps(
            {
                "plates": reports,
                "physical_fit_accepted": False,
                "printer_job_sent": False,
            },
            indent=2,
        )
        + "\n"
    )
    print(package(output))


def package(output):
    """Package checked geometry and its complete native build sources."""
    from cad.enlarger.export import sha

    manifest = json.loads((output / "model-report.json").read_text())
    assert all(
        sha(ROOT / name) == digest for name, digest in manifest["sources"].items()
    )
    destination = output / "fuji-102-enlarger-holder.zip"
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for pattern in (
            "plates/*.step",
            "plates/*.stl",
            "assembly-*.step",
            "assembly-*.FCStd",
            "*.json",
            "images/*.png",
            "bambu/*/*.3mf",
            "bambu/*/project-report.json",
        ):
            for source in sorted(output.glob(pattern)):
                relative = source.relative_to(output)
                if relative.parts[0] == "images":
                    relative = Path("enlarger") / relative
                archive.write(source, relative)
        for source in sorted((ROOT / "cad/enlarger").glob("*.py")):
            archive.write(source, source.relative_to(ROOT))
        for relative in (
            "cad/__init__.py",
            "scripts/build_enlarger.py",
            "scripts/check_enlarger.py",
            "scripts/build_native_bambu.py",
            "scripts/bambu_common.py",
            "cad/fonts/LiberationSans-Bold.ttf",
            "cad/fonts/LICENSE",
            "cad/requirements.txt",
            "cad/enlarger/requirements-render.txt",
            "enlarger/README.md",
        ):
            archive.write(ROOT / relative, relative)
    return destination


if __name__ == "__main__":
    main()
