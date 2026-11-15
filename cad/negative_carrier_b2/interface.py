"""Explicit, provisional carrier registration in the measured C35 datums."""

import json
from dataclasses import asdict
from pathlib import Path

import build123d as bd

from cad.durst_c35_interface.export import sha
from cad.durst_c35_interface.model import load_measurements, values
from cad.durst_c35_interface.model import parts as fixture_parts

from .model import Config, box, parts
from .workflow import phases, place

ROOT = Path(__file__).resolve().parents[2]


def registration(data, shapes):
    p = values(data)
    # Recover the underside of an inner receiver rail from actual geometry.
    # Its contact with the measured frame is a seating hypothesis, not a
    # measurement of the original film plane or a calibrated clamping force.
    rail = shapes["receiver"] & box(22.5, -32.5, -20, 2, 1, 40)
    assert rail and len(rail.solids()) == 1
    z = -p["slot_gap"] - rail.bounding_box().min.Z
    return (0.0, -p["optical_centre_depth"], z)


def export(output, formats=("135", "half", "aps", "110"), release_drop=0.4):
    if not 0 <= release_drop <= 3:
        raise ValueError(
            "Release scenario must be within 0–3 mm; range is not measured travel"
        )
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name in ("interface-manifest.json", "interface-validation.json"):
        (output / name).unlink(missing_ok=True)
    data = load_measurements()
    report = {
        "schema_version": 1,
        "physical_fit_accepted": False,
        "registration_measured": False,
        "release_drop_mm": release_drop,
        "release_travel_status": "prescribed scenario; available travel and force unmeasured",
        "measurements": data,
        "fixture": {},
        "models": [],
        "limitations": [
            "Head optical aperture/position, screw envelopes and outer housing are provisional.",
            "Film plane, receiver seating/retention, physical insertion stop and spring travel/force are unmeasured.",
            "Straight optical clearance is not an illumination, light-leak or photographic registration test.",
            "Printed fit, thread function, film retention, friction, warm creep and repeatability require physical trials.",
        ],
        "sources": {
            str(p.relative_to(ROOT)): sha(p)
            for folder in ("cad/durst_c35_interface", "cad/negative_carrier_b2")
            for p in sorted((ROOT / folder).glob("*.py"))
        },
    }

    def record(shape, path):
        assert shape.is_valid and len(shape.solids()) == 1, path
        bd.export_step(shape, path)
        return {
            "file": str(path.relative_to(output)),
            "sha256": sha(path),
            "volume_mm3": shape.volume,
        }

    for name, shape in fixture_parts(data).items():
        report["fixture"][name] = record(shape, output / f"{name}.step")
    for full in (False, True):
        for fmt in formats:
            p = (
                Config(fmt)
                if full
                else Config(
                    fmt, frame_count={"135": 4, "half": 7, "aps": 4, "110": 7}[fmt]
                )
            )
            shapes = parts(p)
            pose = phases(p)[7]["end"]
            offset = registration(data, shapes)
            name = f"{fmt}-" + ("full" if full else "compact")
            folder = output / name
            folder.mkdir(exist_ok=True)
            model = {
                "name": name,
                "config": asdict(p),
                "translation_mm": offset,
                "placement_status": "receiver rail seated on lower support; optical centre from provisional head aperture",
                "frame_travel_mm": p.fmt.travel,
                "aperture_mm": p.fmt.aperture,
                "moving": [
                    n
                    for n in shapes
                    if n in ("base", "lid", "film") or n.startswith("wedge-")
                ],
                "parts": {},
            }
            for n, s in shapes.items():
                model["parts"][n] = record(
                    bd.Pos(*offset) * place(s, n, pose), folder / f"{n}.step"
                )
            # Enough positive-Y translation to clear the entire head and support.
            model["withdrawal_mm"] = max(
                160,
                -min(
                    bd.import_step(folder / f"{n}.step").bounding_box().min.Y
                    for n in shapes
                )
                + 10,
            )
            report["models"].append(model)
            print("Exported measured-interface scenario", name, flush=True)
    report["measurement_sha256"] = sha(
        ROOT / "cad/durst_c35_interface/measurements.json"
    )
    (output / "interface-manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
