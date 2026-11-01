"""Insertion-area B-rep reference. Coordinates and evidence live in measurements.json.

The lower frame can be placed lower as a rigid body. This is a prescribed
clearance scenario, NOT an elastic solution or a calibrated spring model.
"""

import json
import math
from pathlib import Path

import build123d as bd

DEFAULT_MEASUREMENTS = Path(__file__).with_name("measurements.json")
STATUSES = {
    "user_measured",
    "user_approximate",
    "derived_from_user",
    "provisional",
    "display_extent",
}


def load_measurements(path=DEFAULT_MEASUREMENTS):
    data = json.loads(Path(path).read_text())
    defaults = json.loads(DEFAULT_MEASUREMENTS.read_text())
    if data.get("schema_version") != 1 or data.get("units") != "mm":
        raise ValueError("Expected schema 1 with mm units")
    if data["parameters"].keys() != defaults["parameters"].keys():
        raise ValueError("Parameter names differ from the fixture schema")
    for key, entry in data["parameters"].items():
        value = entry["value"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"Non-finite/non-numeric dimension: {key}")
        if entry["status"] not in STATUSES or not entry.get("source"):
            raise ValueError(f"Missing evidence/status: {key}")
    p = values(data)
    if data["observations"].get("neck_and_lower_rear_faces_coincide", {}).get(
        "value"
    ) and not math.isclose(
        p["lower_front_offset"] - p["lower_depth"],
        -p["neck_depth"],
        abs_tol=1e-6,
    ):
        raise ValueError(
            "Head neck and raised support must share the observed rear plane"
        )
    for key, value in p.items():
        if key not in {"lower_front_offset", "screw_protrusion"} and value <= 0:
            raise ValueError(f"Dimension must be positive: {key}")
    if p["screw_protrusion"] < 0 or p["screw_protrusion"] >= p["slot_gap"]:
        raise ValueError("Screw protrusion must be nonnegative and below rest gap")
    w = p["shell_wall"]
    if min(p["neck_width"], p["neck_depth"]) <= 2 * w:
        raise ValueError("Head wall consumes cavity")
    if p["body_width"] <= p["neck_width"] or p["body_depth"] <= p["neck_depth"]:
        raise ValueError("Upper body must enclose the neck")
    if not 0 < p["body_front_overhang"] < p["body_depth"] - p["neck_depth"]:
        raise ValueError("Upper body must enclose front and back of neck")
    if p["cover_thickness"] >= p["neck_height"] or w >= p["body_height_shown"]:
        raise ValueError("Head heights too small")
    if p["flange_width"] < p["lower_width"] or p["flange_depth"] < p["lower_depth"]:
        raise ValueError("Flange must enclose raised support")
    if not 0 < p["flange_front_overhang"] < p["flange_depth"] - p["lower_depth"]:
        raise ValueError("Flange must enclose front and back of support")
    if min(lower_opening_margins(p).values()) <= p["corner_radius"]:
        raise ValueError("Offset lower opening consumes frame or rounded perimeter")
    if p["corner_radius"] * 2 >= min(
        p["neck_width"], p["neck_depth"], p["lower_width"], p["lower_depth"]
    ):
        raise ValueError("Corner radius too large")
    if p["optical_width"] >= p["neck_width"] - 2 * w:
        raise ValueError("Optical opening crosses head wall")
    a, b = (
        p["optical_centre_depth"] - p["optical_depth"] / 2,
        p["optical_centre_depth"] + p["optical_depth"] / 2,
    )
    if not w < a < b < p["neck_depth"] - w:
        raise ValueError("Optical opening crosses head ends")
    if p["front_tab_width"] >= p["neck_width"] - 2 * w:
        raise ValueError("Front tab consumes head width")
    r = p["screw_head_diameter"] / 2
    for x, y in screw_centres(p):
        if (
            abs(x) + r >= p["neck_width"] / 2 - w
            or not w + r < -y < p["neck_depth"] - w - r
        ):
            raise ValueError("Screw envelope crosses plate perimeter")
        if abs(x) < p["optical_width"] / 2 + r and a - r < -y < b + r:
            raise ValueError("Screw envelope crosses optical opening")
    return data


def values(data):
    return {key: entry["value"] for key, entry in data["parameters"].items()}


def lower_opening_centre(p):
    # +X is operator-left in our right-handed X/Y/Z coordinates.
    return (
        p["lower_width"] / 2
        - p["lower_opening_left_offset"]
        - p["lower_opening_width"] / 2,
        p["lower_front_offset"]
        - p["lower_opening_front_offset"]
        - p["lower_opening_depth"] / 2,
    )


def lower_opening_margins(p):
    return {
        "front": p["lower_opening_front_offset"],
        "rear": p["lower_depth"]
        - p["lower_opening_front_offset"]
        - p["lower_opening_depth"],
        "left": p["lower_opening_left_offset"],
        "right": p["lower_width"]
        - p["lower_opening_left_offset"]
        - p["lower_opening_width"],
    }


def box(x, y, z, width, depth, height):
    return bd.Pos(x, y, z) * bd.Box(
        width, depth, height, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )


def rounded(x, y, z, width, depth, height, radius):
    return bd.Pos(x, y, z) * bd.extrude(
        bd.RectangleRounded(width, depth, radius), amount=height
    )


def screw_centres(p):
    x = p["neck_width"] / 2 - p["screw_side_inset"]
    ys = (-p["screw_end_inset"], -p["neck_depth"] + p["screw_end_inset"])
    return [(side * x, y) for side in (-1, 1) for y in ys] + [
        (0, -p["screw_middle_end_inset"]),
        (0, -p["neck_depth"] + p["screw_middle_end_inset"]),
    ]


def parts(data=None, lower_drop_mm=0.0):
    data = load_measurements() if data is None else data
    if not math.isfinite(lower_drop_mm) or lower_drop_mm < 0:
        raise ValueError("Lower drop must be finite and nonnegative")
    p = values(data)
    nw, nd, nh, w = (
        p[k] for k in ("neck_width", "neck_depth", "neck_height", "shell_wall")
    )
    neck = rounded(0, -nd / 2, 0, nw, nd, nh, p["corner_radius"])
    neck -= box(0, -nd / 2, -1, nw - 2 * w, nd - 2 * w, nh + 2)
    cy = p["body_front_overhang"] - p["body_depth"] / 2
    body = rounded(
        0,
        cy,
        nh,
        p["body_width"],
        p["body_depth"],
        p["body_height_shown"],
        p["corner_radius"],
    )
    body -= box(
        0,
        cy,
        nh + w,
        p["body_width"] - 2 * w,
        p["body_depth"] - 2 * w,
        p["body_height_shown"],
    )
    body -= box(0, -nd / 2, nh - 1, nw - 2 * w, nd - 2 * w, w + 2)
    head = neck + body
    plate = box(0, -nd / 2, 0, nw - 2 * w, nd - 2 * w, p["cover_thickness"])
    plate -= box(
        0,
        -p["optical_centre_depth"],
        -1,
        p["optical_width"],
        p["optical_depth"],
        p["cover_thickness"] + 2,
    )
    # The small front tab is observed, but its function is not assigned.
    plate += box(
        0,
        (p["front_tab_projection"] - w) / 2,
        0,
        p["front_tab_width"],
        p["front_tab_projection"] + w,
        p["cover_thickness"],
    )
    # White surround clears the visible black tab; no duplicated solid material.
    head -= box(
        0,
        (p["front_tab_projection"] - w) / 2,
        -0.01,
        p["front_tab_width"],
        p["front_tab_projection"] + w,
        p["cover_thickness"] + 0.01,
    )
    top = -p["slot_gap"] - lower_drop_mm
    lower_cy = p["lower_front_offset"] - p["lower_depth"] / 2
    flange_cy = (
        p["lower_front_offset"] + p["flange_front_overhang"] - p["flange_depth"] / 2
    )
    bottom = top - p["lower_height"] - p["flange_thickness"]
    lower = rounded(
        0,
        lower_cy,
        top - p["lower_height"],
        p["lower_width"],
        p["lower_depth"],
        p["lower_height"],
        p["corner_radius"],
    )
    lower += rounded(
        0,
        flange_cy,
        bottom,
        p["flange_width"],
        p["flange_depth"],
        p["flange_thickness"],
        p["corner_radius"],
    )
    opening_x, opening_y = lower_opening_centre(p)
    lower -= box(
        opening_x,
        opening_y,
        bottom - 1,
        p["lower_opening_width"],
        p["lower_opening_depth"],
        p["lower_height"] + p["flange_thickness"] + 2,
    )
    result = {"head-shell": head, "underside-plate": plate, "lower-support": lower}
    # Cylinders are collision envelopes, not detailed screw/drive geometry.
    if p["screw_protrusion"] > 0:
        for i, (x, y) in enumerate(screw_centres(p), 1):
            result[f"screw-head-{i}"] = bd.Pos(
                x, y, -p["screw_protrusion"]
            ) * bd.Cylinder(
                p["screw_head_diameter"] / 2,
                p["screw_protrusion"],
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
    return result


def clearance_scenario(data, lower_drop_mm=0.0):
    """Plane separations only; force, real contacts and carrier acceptance unknown."""
    p = values(data)
    return {
        "kind": "prescribed rigid placement; not force simulation",
        "lower_drop_mm": lower_drop_mm,
        "flat_gap_mm": p["slot_gap"] + lower_drop_mm,
        "local_gap_at_screw_envelope_mm": p["slot_gap"]
        + lower_drop_mm
        - p["screw_protrusion"],
        "force_N": None,
        "physical_fit_accepted": False,
    }
