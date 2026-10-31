"""Estimated contact envelopes informed by the C35 manual, not factory drawings."""

import math

import build123d as bd

from cad.durst_c35.parts import box

# Independent fixture dimensions: deliberately not recomputed to fit a changed
# carrier. These are hypotheses to replace with measurements, not OEM dimensions.
DEFAULTS = {
    "mixing_width": 90.0,
    "mixing_rear_y": 10.0,
    "mixing_front_y": 96.0,
    "mixing_height": 110.0,
    "mixing_wall": 2.5,
    "upper_contact_z": 1.4,
    "upper_contact_width": 7.0,
    "upper_relief_depth": 2.0,
    "optical_width": 40.0,
    "optical_length": 28.0,
    "optical_center_y": 54.0,
    "stage_width": 84.0,
    "stage_rail_width": 6.0,
    "stage_rear_y": 14.0,
    "stage_front_y": 96.0,
    "stage_crossbar_depth": 6.0,
    "stage_contact_z": -1.2,
    "stage_height": 10.8,
    "stage_depression": 3.0,
    "stop_front_y": -7.0,
    "stop_depth": 4.0,
    "stop_width": 104.0,
    "stop_bottom_z": -16.0,
    "stop_height": 32.0,
    "withdrawal": 120.0,
}


def parameters(**overrides):
    if overrides.keys() - DEFAULTS.keys():
        raise ValueError(
            f"Unknown fixture dimensions: {overrides.keys() - DEFAULTS.keys()}"
        )
    q = DEFAULTS | overrides
    for name, value in q.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{name} must be a finite number")
        if not name.endswith(("_y", "_z")) and value <= 0:
            raise ValueError(f"{name} must be positive")
    if not (
        q["mixing_rear_y"] < q["mixing_front_y"]
        and q["stage_rear_y"] + q["stage_crossbar_depth"] < q["stage_front_y"]
        and 2 * q["stage_rail_width"] < q["stage_width"]
        and 2 * q["upper_contact_width"] < q["mixing_width"]
        and q["optical_width"] < q["mixing_width"] - 2 * q["upper_contact_width"]
        and q["mixing_height"] > 2 * q["mixing_wall"]
        and q["upper_contact_z"] > q["stage_contact_z"]
    ):
        raise ValueError("Inconsistent contact-envelope dimensions")
    return q


def fixtures(q):
    w, wall = q["mixing_width"], q["mixing_wall"]
    rear, front = q["mixing_rear_y"], q["mixing_front_y"]
    bottom = q["upper_contact_z"] + q["upper_relief_depth"]
    mixing = box(-w / 2, rear, bottom, w, front - rear, q["mixing_height"])
    mixing -= box(
        -w / 2 + wall,
        rear + wall,
        bottom + wall,
        w - 2 * wall,
        front - rear - 2 * wall,
        q["mixing_height"],
    )
    mixing -= box(
        -q["optical_width"] / 2,
        q["optical_center_y"] - q["optical_length"] / 2,
        bottom - 0.1,
        q["optical_width"],
        q["optical_length"],
        wall + 0.2,
    )
    for x in (-w / 2, w / 2 - q["upper_contact_width"]):
        mixing += box(
            x,
            rear,
            q["upper_contact_z"],
            q["upper_contact_width"],
            front - rear,
            q["upper_relief_depth"],
        )
    w, rail = q["stage_width"], q["stage_rail_width"]
    rear, front = q["stage_rear_y"], q["stage_front_y"]
    bottom = q["stage_contact_z"] - q["stage_height"]
    stage = box(-w / 2, rear, bottom, w, q["stage_crossbar_depth"], q["stage_height"])
    for x in (-w / 2, w / 2 - rail):
        stage += box(x, rear, bottom, rail, front - rear, q["stage_height"])
    stop = box(
        -q["stop_width"] / 2,
        q["stop_front_y"] - q["stop_depth"],
        q["stop_bottom_z"],
        q["stop_width"],
        q["stop_depth"],
        q["stop_height"],
    )
    return {"mixing-box": mixing, "stage": stage, "back-stop": stop}


def sequence(q):
    """Hand-guided closed carrier, hinge first along -Y; stage release is prescribed."""
    travel, depression = q["withdrawal"], q["stage_depression"]
    phases = [
        ("depress_stage", 13, (travel, 0, 0), (travel, 0, -depression)),
        (
            "align_carrier",
            7,
            (travel, 0, -depression),
            (travel, -depression / 2, -depression),
        ),
        (
            "insert",
            61,
            (travel, -depression / 2, -depression),
            (0, -depression / 2, -depression),
        ),
        ("release_stage", 13, (0, -depression / 2, -depression), (0, 0, 0)),
        ("depress_for_removal", 13, (0, 0, 0), (0, -depression / 2, -depression)),
        (
            "withdraw",
            61,
            (0, -depression / 2, -depression),
            (travel, -depression / 2, -depression),
        ),
        ("reset", 13, (travel, -depression / 2, -depression), (travel, 0, 0)),
    ]
    result = []
    for phase, count, start, end in phases:
        for i in range(count):
            t = i / (count - 1)
            y, z, stage_z = [a + (b - a) * t for a, b in zip(start, end)]
            result.append(
                {"phase": phase, "carrier_y": y, "carrier_z": z, "stage_z": stage_z}
            )
    return result


def export(folder, q):
    folder.mkdir(parents=True, exist_ok=True)
    for name, shape in fixtures(q).items():
        if not shape.is_valid or len(shape.solids()) != 1:
            raise ValueError(f"Invalid fixture: {name}")
        bd.export_step(shape, folder / f"{name}.step")
