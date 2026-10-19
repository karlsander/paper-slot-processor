#!/usr/bin/env python3
"""Export checked enlarger STLs, A1 mini Bambu projects, slices, previews and a ZIP.

Uses the existing Processor 0.20mm @BBL A1M profile and Generic PETG preset.
Does not send a job to a printer. Run from any directory with the repo's venv.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

import build_openscad as build
import check_enlarger as checks

ROOT = checks.ROOT
OUT = checks.OUT


def render_previews():
    images = ROOT / "enlarger/images"
    images.mkdir(exist_ok=True)
    for name, settings, camera in (
        ("holder-16x9", [], "0,0,0,50,0,25,450"),
        ("holder-4x3", ['format="4:3"'], "0,0,0,50,0,25,450"),
        ("test-covers", ["cover_count=4", "exploded=16"], "0,0,0,55,0,25,450"),
        ("five-bands", ["cover_count=4"], "0,0,0,0,0,0,450"),
    ):
        command = [build.OPENSCAD, "--backend", "Manifold", "--hardwarnings",
                   "-o", str(images / f"{name}.png"), "--imgsize", "1600,1100",
                   "--autocenter", "--viewall", "--render", "--camera", camera, "--projection", "o"]
        for setting in settings:
            command += ["-D", setting]
        build.run([*command, str(ROOT / "enlarger/model.scad")])


def slice_plate(name: str):
    folder = OUT / "plates" / name
    generated = folder / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    presets = build.resolved_bambu_presets(generated)
    mesh = OUT / "meshes" / f"{name}.stl"
    source_mesh = generated / f"{name}.openscad.3mf"
    build.run([build.OPENSCAD, "--backend", "Manifold", "--hardwarnings", "-o", str(source_mesh),
               str(ROOT / f"enlarger/plates/{name}.scad")])
    slices = build.bambu_slice(source_mesh, generated, name, presets)
    result = build.read_json(slices["bambu_result"])
    assert result.get("return_code") == 0, result
    assert len(result.get("sliced_plates", [])) == 1, f"Expected one A1 mini plate: {name}"
    warnings = [plate["warning_message"] for plate in result["sliced_plates"] if plate.get("warning_message")]
    if warnings:
        raise RuntimeError(f"Slicer warnings for {name}: {warnings}")
    project = build.bambu_project(source_mesh, folder, generated, name, presets)
    assert build.zip_ok(project), f"Invalid Bambu project: {name}"
    # Render the actual arranged/sliced project as a separate review artifact.
    build.run([build.BAMBU, "--camera-view", "1", "--export-png", "0",
               "--outputdir", str(generated), str(project)], cwd=generated)
    build.capture_sidecar_json(generated, generated / f"{name}.preview-result.json")
    preview = generated / "plate_1_1.png"
    assert build.png_ok(preview), f"Missing Bambu plate preview: {name}"
    return {"name": name, "stl": str(mesh.relative_to(ROOT)),
            "bambu_project": str(project.relative_to(ROOT)),
            "preview": str(preview.relative_to(ROOT)),
            "print": build.parse_gcode(slices["gcode"])["stats"], "warnings": warnings}


def package(report):
    destination = OUT / "fuji-102-enlarger-holder.zip"
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted((ROOT / "enlarger").rglob("*")):
            if source.is_file():
                archive.write(source, source.relative_to(ROOT))
        for item in report["plates"]:
            for key, target in (("stl", "STL"), ("bambu_project", "Bambu-A1-mini"), ("preview", "plate-previews")):
                source = ROOT / item[key]
                suffix = source.suffix
                archive.write(source, f"{target}/{item['name']}{suffix}")
        for name in ("geometry-summary.json", "print-summary.json"):
            archive.write(OUT / name, name)
        profile = ROOT / "profiles/Processor 0.20mm @BBL A1M.json"
        archive.write(profile, f"profiles/{profile.name}")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry-only", action="store_true", help="Check meshes and render previews without Bambu Studio.")
    args = parser.parse_args()
    checks.main()
    render_previews()
    if args.geometry_only:
        return
    report = {"profile": str(Path(build.BAMBU_PROCESS).relative_to(ROOT))
              if Path(build.BAMBU_PROCESS).is_relative_to(ROOT) else build.BAMBU_PROCESS,
              "filament_preset": build.BAMBU_FILAMENT, "plates": []}
    for name in checks.PLATES:
        report["plates"].append(slice_plate(name))
        print(f"PASS sliced {name}", flush=True)
    report["limits"] = "Projects need the user's actual opaque black filament selected and reslicing. No print was sent. Physical fit and opacity are unverified."
    (OUT / "print-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Ready: {package(report)}")


if __name__ == "__main__":
    main()
