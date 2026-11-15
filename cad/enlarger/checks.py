"""Probe actual native parts for fits, light paths and exposed paper areas."""

import math

import build123d as bd

from .model import base_halves, box, cover, cylinder, mask
from .parameters import image_length, parameters


def volume(shape):
    return sum(s.volume for s in shape.solids()) if shape else 0


def overlap(a, b):
    return volume(a & b)


def check_scenario(p, fmt):
    checks = []
    bases = base_halves(p)
    masks = [mask(p, fmt, side) for side in (-1, 1)]
    covers = [cover(p, i, fmt) for i in range(4)]
    fixed = list(bases.values()) + masks

    def clear(name, pairs):
        for a, b in pairs:
            assert overlap(a, b) < 1e-6, (fmt, name, overlap(a, b))
        checks.append(name)

    clear("joint", [(bases["base_left"], bases["base_right"])])
    probes = [
        box(
            -p["base_length"] / 2 - 40,
            -p["paper_width"] / 2 + dy + 0.01,
            p["deck_thickness"] + 0.01,
            p["base_length"] + 80,
            p["paper_width"] - 0.02,
            p["paper_thickness"] - 0.02,
        )
        for dy in (-p["paper_side_clearance"], 0, p["paper_side_clearance"])
    ]
    clear("paper", [(s, q) for s in fixed for q in probes])
    clear("masks", [(s, m) for s in bases.values() for m in masks])
    clear(
        "covers",
        [(s, c) for s in fixed for c in covers]
        + [
            (covers[i], bd.Pos(0.01, 0, 0) * covers[j])
            for i in range(3)
            for j in range(i + 1, 4)
        ],
    )
    magnets = []
    for x in (-p["magnet_x"], p["magnet_x"]):
        for y in (-p["attachment_y"], p["attachment_y"]):
            magnets += [
                cylinder(
                    x,
                    y,
                    p["deck_thickness"]
                    - p["magnet_thickness"]
                    - p["magnet_depth_clearance"]
                    + 0.01,
                    p["magnet_diameter"],
                    p["magnet_thickness"] - 0.02,
                ),
                cylinder(
                    x,
                    y,
                    p["paper_z"] + p["magnet_depth_clearance"],
                    p["magnet_diameter"],
                    p["magnet_thickness"] - 0.01,
                ),
            ]
    clear("magnets", [(s, m) for s in fixed for m in magnets])
    length = image_length(p, fmt)
    for sign in (-1, 1):
        ray = bd.loft(
            [
                bd.Pos(0, 0, p["paper_z"] + 0.01)
                * bd.Rectangle(length - 10, p["paper_width"]),
                bd.Pos(0, sign * 15 * math.tan(math.radians(30)), p["paper_z"] + 15)
                * bd.Rectangle(length - 10, p["paper_width"]),
            ],
            ruled=True,
        )
        clear(f"light-{sign}", [(s, ray) for s in fixed])
    # Project the actual faces above the paper. Union their projections before
    # subtracting, so edge laps and bevels determine the exposed area.
    aperture = bd.Rectangle(length, p["paper_width"])
    above = box(-200, -200, p["paper_z"] + 0.01, 400, 400, 40)
    shadow = bd.Sketch()
    for shape in fixed:
        cut = shape & above
        if cut:
            for face in bd.project(
                [f for f in cut.faces() if abs(f.normal_at().Z) > 1e-7],
                workplane=bd.Plane.XY,
            ).faces():
                shadow += face
    for count in range(5):
        if count:
            for face in bd.project(
                [f for f in covers[count - 1].faces() if abs(f.normal_at().Z) > 1e-7],
                workplane=bd.Plane.XY,
            ).faces():
                shadow += face
        exposed = aperture - shadow
        expected_length = (
            length - count * p["band_width"] - (p["cover_lap"] if 0 < count < 4 else 0)
        )
        assert len(exposed.faces()) == 1, (fmt, count, "fragmented exposure")
        assert abs(exposed.area - expected_length * p["paper_width"]) < 0.01, (
            fmt,
            count,
            exposed.area,
        )
        size = exposed.bounding_box().size
        assert (
            abs(size.X - expected_length) < 1e-5
            and abs(size.Y - p["paper_width"]) < 1e-5
        ), (fmt, count, size)
        checks.append(f"exposure-{count}")
    return checks


def run_checks():
    report = []
    for name, overrides in [
        ("default", {}),
        ("thicker-paper", {"paper_thickness": 0.5}),
        ("narrower-roll", {"paper_width": 100}),
    ]:
        p = parameters(**overrides)
        for fmt in ("16:9", "4:3"):
            report += [f"{name}-{fmt}-{check}" for check in check_scenario(p, fmt)]
            print("PASS native fits and exposure", name, fmt, flush=True)
    for key, value in [
        ("guide_height", 0.4),
        ("paper_width", 120),
        ("deck_thickness", 3.2),
        ("magnet_diameter", 8),
        ("band_width", 34),
        ("joint_clearance", 0),
        ("outer_rail_height", 0.2),
    ]:
        try:
            parameters(**{key: value})
        except ValueError:
            report.append(f"rejects-{key}")
        else:
            raise AssertionError(f"Accepted invalid {key}")
    return report
