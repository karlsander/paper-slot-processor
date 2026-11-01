"""Build123d layout solids: deliberately omit unvalidated latches and drive teeth."""

import argparse
import hashlib
import json
from pathlib import Path

import build123d as bd

from .spec import FORMATS, VARIANTS, summary


def box(x, y, z, dx, dy, dz):
    return bd.Pos(x, y, z) * bd.Box(
        dx, dy, dz, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )


def ring(length, width, opening_length, opening_width, z, height):
    return box(0, 0, z, length, width, height) - box(
        0, 0, z - 1, opening_length, opening_width, height + 2
    )


def components(fmt, variant):
    if variant not in VARIANTS:
        raise ValueError(variant)
    length = fmt.length
    opening_length = fmt.centers[-1] - fmt.centers[0] + fmt.image_width + 2
    lower = ring(length, 52, opening_length, fmt.image_height + 0.8, -1.3, 1.2)
    lid = ring(length, 52, opening_length, fmt.image_height + 0.8, 0.1, 1.2)
    # Index rail is outside the film. The rectangular pockets visualize station
    # locations only; detailed spring/ramp contact geometry is intentionally TBD.
    lower += box(0, -26, -1.3, length, 4, 1.2)
    for x in fmt.centers:
        lower -= box(x, -28, -2, 2.4, 2.4, 3)
    aw, ah = fmt.aperture
    upper_mask = ring(70, 66, aw, ah, 1.55, 0.8)
    lower_mask = ring(70, 66, aw, ah, -2.35, 0.8)
    # Connections are beyond the translating frame, not across its path.
    gate = upper_mask + lower_mask
    for y in (-32, 32):
        gate += box(0, y, -2.35, 70, 2, 4.7)
    # A rearward neck supplies a keyed docking silhouette; fit features TBD.
    gate += box(0, 37, -2.35, 18, 10, 0.8)
    receiver = ring(94.6, 100, 70.8, 84.8, -3.55, 1.2)
    result = {
        "receiver": (receiver, "fixed", "receiver"),
        "gate": (gate, "fixed", "gate"),
        "sled": (lower, "moving", "sled"),
        "lid": (lid, "moving", "lid"),
        "film": (
            box(0, 0, -0.075, length - 16, fmt.film_width, 0.15),
            "moving",
            "film",
        ),
    }
    if variant == "drawer":
        # Separate, deliberately visible pull handle for the manual mask exchange.
        result["gate"] = (gate + box(0, -40, 1.55, 18, 16, 0.8), "fixed", "gate")
    elif variant == "cassette":
        result["receiver"] = (
            receiver.moved(bd.Location((0, 0, -1.2))),
            "fixed",
            "receiver",
        )
        case_length = length + fmt.travel + 16
        case = box(0, 0, -3.55, case_length, 66, 7.1)
        case -= box(0, 0, -1.55, case_length - 4, 60, 3.1)
        case -= box(0, 0, -5, aw, ah, 10)
        result["gate"] = (case, "fixed", "case")
        # A spatial allowance only, not a functional gear or printable drive.
        wheel = bd.Pos(0, -44, -2) * bd.Cylinder(
            10, 4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        result["wheel-envelope"] = (wheel, "fixed", "control")
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(out):
    out.mkdir(parents=True, exist_ok=True)
    report = summary() | {"build123d_version": bd.__version__, "models": []}
    choices = [(v, FORMATS["135"]) for v in VARIANTS] + [
        ("collar", FORMATS[k]) for k in ("half", "aps", "110")
    ]
    for variant, fmt in choices:
        name = f"{variant}-{fmt.key}"
        folder = out / name
        folder.mkdir(exist_ok=True)
        records = []
        for part_name, (shape, motion, role) in components(fmt, variant).items():
            if not shape.is_valid or len(shape.solids()) != 1:
                raise ValueError(f"Invalid layout solid {name}/{part_name}")
            step = folder / f"{part_name}.step"
            bd.export_step(shape, step)
            bounds = shape.bounding_box()
            records.append(
                {
                    "name": part_name,
                    "motion": motion,
                    "role": role,
                    "volume_mm3": shape.volume,
                    "dimensions_mm": list(bounds.size),
                    "file": str(step.relative_to(out)),
                    "sha256": sha(step),
                }
            )
        report["models"].append(
            {"name": name, "variant": variant, "format": fmt.key, "parts": records}
        )
    report["source_sha256"] = {
        p.name: sha(p) for p in Path(__file__).parent.glob("*.py")
    }
    (out / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Exported {len(report['models'])} concept assemblies to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("build/negative-carrier-concepts")
    )
    export(parser.parse_args().output)
