"""Independent unmeasured C35 envelope, copied from the earlier insertion study.

Dimensions are unchanged; only Y was translated by -54 mm to put the optical
axis at the origin. This is not an OEM drawing or a measured machine.
"""

from cad.negative_carrier_concepts.model import box

PARAMETERS = {
    "mixing_width": 90,
    "mixing_rear_y": -44,
    "mixing_front_y": 42,
    "mixing_height": 110,
    "wall": 2.5,
    "upper_contact_z": 1.4,
    "upper_land_width": 7,
    "relief": 2,
    "optical_width": 40,
    "optical_length": 28,
    "stage_width": 84,
    "stage_rail": 6,
    "stage_rear_y": -40,
    "stage_front_y": 42,
    "stage_crossbar": 6,
    "stage_contact_z": -1.2,
    "stage_height": 10.8,
    "stop_front_y": -61,
    "stop_depth": 4,
    "stop_width": 104,
    "stop_bottom_z": -16,
    "stop_height": 32,
}


def fixtures():
    q = PARAMETERS
    w, wall = q["mixing_width"], q["wall"]
    length = q["mixing_front_y"] - q["mixing_rear_y"]
    cy = (q["mixing_rear_y"] + q["mixing_front_y"]) / 2
    bottom = q["upper_contact_z"] + q["relief"]
    head = box(0, cy, bottom, w, length, q["mixing_height"])
    head -= box(
        0, cy, bottom + wall, w - 2 * wall, length - 2 * wall, q["mixing_height"]
    )
    head -= box(0, 0, bottom - 0.1, q["optical_width"], q["optical_length"], wall + 0.2)
    for side in (-1, 1):
        head += box(
            side * (w - q["upper_land_width"]) / 2,
            cy,
            q["upper_contact_z"],
            q["upper_land_width"],
            length,
            q["relief"],
        )
    w, rail = q["stage_width"], q["stage_rail"]
    bottom = q["stage_contact_z"] - q["stage_height"]
    rear, front = q["stage_rear_y"], q["stage_front_y"]
    stage = box(
        0,
        rear + q["stage_crossbar"] / 2,
        bottom,
        w,
        q["stage_crossbar"],
        q["stage_height"],
    )
    for side in (-1, 1):
        stage += box(
            side * (w - rail) / 2,
            (rear + front) / 2,
            bottom,
            rail,
            front - rear,
            q["stage_height"],
        )
    stop = box(
        0,
        q["stop_front_y"] - q["stop_depth"] / 2,
        q["stop_bottom_z"],
        q["stop_width"],
        q["stop_depth"],
        q["stop_height"],
    )
    return {"fixture-head": head, "fixture-stage": stage, "fixture-stop": stop}
