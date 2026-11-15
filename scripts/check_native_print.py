"""Slice all five native plates with the installed A1 mini PETG nozzle profiles."""

import argparse
import json
import subprocess
from pathlib import Path

import build_openscad as build


def check(
    source, output, nozzle, names=("guide_a", "guide_b", "vessel_a", "vessel_b", "base")
):
    output.mkdir(parents=True, exist_ok=True)
    system = Path(build.BAMBU_SYSTEM_DIR)
    machine = system / "machine" / f"Bambu Lab A1 mini {nozzle:g} nozzle.json"
    process = (
        system
        / "process"
        / (
            "0.10mm Standard @BBL A1M 0.2 nozzle.json"
            if nozzle == 0.2
            else "0.20mm Standard @BBL A1M.json"
        )
    )
    filament = (
        system
        / "filament"
        / (
            "Generic PETG @BBL A1M 0.2 nozzle.json"
            if nozzle == 0.2
            else "Generic PETG @BBL A1M.json"
        )
    )
    report = []
    for name in names:
        folder = output / name
        folder.mkdir(exist_ok=True)
        presets = {}
        for kind, path in [
            ("machine", machine),
            ("process", process),
            ("filament", filament),
        ]:
            data = build.resolve_preset(path)
            data.pop("inherits", None)
            if kind == "process":
                data.update(
                    wall_loops="4",
                    top_shell_layers="12" if nozzle == 0.2 else "6",
                    bottom_shell_layers="12" if nozzle == 0.2 else "6",
                    sparse_infill_density="15%",
                    curr_bed_type="Textured PEI Plate",
                )
                data.update(
                    enable_support="1" if name.startswith("vessel") else "0",
                    brim_type="outer_only" if name.startswith("vessel") else "no_brim",
                )
                if name.startswith("vessel"):
                    data.update(
                        support_type="tree(auto)",
                        support_on_build_plate_only="1",
                        support_threshold_angle="30",
                        brim_width="3",
                    )
            dest = folder / f"{kind}.json"
            dest.write_text(json.dumps(data, indent=2))
            presets[kind] = dest
        cmd = [
            build.BAMBU,
            *build.bambu_settings_args(presets, arrange=False),
            "--slice",
            "0",
            "--outputdir",
            str(folder),
            str(source / "plates" / f"{name}.stl"),
        ]
        with (folder / "slice.log").open("w") as log:
            result = subprocess.run(
                cmd,
                cwd=folder,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=1200,
                check=False,
            )
        assert result.returncode == 0, (name, result.returncode)
        result = json.loads((folder / "result.json").read_text())
        warnings = [
            p["warning_message"]
            for p in result.get("sliced_plates", [])
            if p.get("warning_message")
        ]
        assert result["return_code"] == 0 and not warnings, (name, result)
        stats = build.parse_gcode(folder / "plate_1.gcode")["stats"]
        report.append(
            {"part": name, "nozzle_mm": nozzle, "stats": stats, "warnings": warnings}
        )
        print(nozzle, name, "sliced", flush=True)
    (output / "slice-report.json").write_text(
        json.dumps({"passed": True, "plates": report}, indent=2)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--nozzle", type=float, choices=[0.2, 0.4], required=True)
    parser.add_argument(
        "--parts",
        nargs="+",
        choices=["guide_a", "guide_b", "vessel_a", "vessel_b", "base"],
        default=["guide_a", "guide_b", "vessel_a", "vessel_b", "base"],
    )
    a = parser.parse_args()
    check(a.source.resolve(), a.output.resolve(), a.nozzle, a.parts)
