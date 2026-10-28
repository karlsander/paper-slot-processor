#!/usr/bin/env python3
"""Build the heater-free v1.8: unchanged v2 wet parts and one shared base."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from build_v2 import PARTS as V2_PARTS, export_plate

ROOT = Path(__file__).resolve().parents[1]
PARTS = {name: V2_PARTS[name] for name in
         ("vessel_a", "vessel_b", "guide_a", "guide_b", "clips", "cover_a", "cover_b", "fit")}
PARTS["base"] = ("Shared two-bath base", "base", {}, 1)
STANDARD_PARTS = ("vessel_a", "vessel_b", "guide_a", "guide_b", "clips", "base")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parts", nargs="*", choices=list(PARTS))
    parser.add_argument("--aspect", type=float, default=16/9)
    parser.add_argument("--covers", action="store_true", help="Include two optional resting covers")
    parser.add_argument("--fit", action="store_true", help="Include the optional guide/clip fit sample")
    parser.add_argument("--mesh-only", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "build/v1.8-print")
    args = parser.parse_args()
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    names = list(args.parts or STANDARD_PARTS)
    names += [name for name in ("cover_a", "cover_b") if args.covers and name not in names]
    if args.fit and "fit" not in names:
        names.append("fit")
    parameters = {"image_aspect": args.aspect}
    reports = [export_plate(name, folder / name, parameters, not args.mesh_only,
               source=ROOT / "v1_8/processor.scad", definition=PARTS[name],
               optional=name not in STANDARD_PARTS) for name in names]
    (folder / "summary.json").write_text(json.dumps(reports, indent=2) + "\n")
    sources = sorted([*(ROOT / "v2").glob("*.scad"), *(ROOT / "v1_8").glob("*.scad")])
    digest = hashlib.sha256()
    for path in sources:
        digest.update(str(path.relative_to(ROOT)).encode() + path.read_bytes())
    (folder / "configuration.json").write_text(json.dumps(parameters | {
        "variant": "v1.8", "cad_sha256": digest.hexdigest(),
        "printed_pieces": sum(report["mesh"]["body_count"] for report in reports),
    }, indent=2) + "\n")
    with zipfile.ZipFile(folder / "processor-v1.8-print-files.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for report in reports:
            for key in ("stl", "project"):
                if key in report:
                    path = Path(report[key])
                    archive.write(path, path.relative_to(folder))
        for name in ("summary.json", "configuration.json"):
            archive.write(folder / name, name)
        archive.write(ROOT / "docs/v1.8.md", "README.md")
        for path in sorted((ROOT / "docs/images").glob("v1.8-*.png")):
            archive.write(path, Path("images") / path.name)
        for path in sources:
            archive.write(path, Path("source") / path.relative_to(ROOT))
    print(f"Built {len(reports)} v1.8 plates in {folder}")


if __name__ == "__main__":
    main()
