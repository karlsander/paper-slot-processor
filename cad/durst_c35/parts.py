"""Native carrier geometry. Z=0 is each half's film face; exterior is +Z locally.

The sheet, upturned edges, and local window rim are separate features. Never use
the edge/rim height as the panel extrusion. A is mirrored below the film plane.
"""

import build123d as bd

MIN = (bd.Align.MIN,) * 3
BASE = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)


def box(x, y, z, dx, dy, dz):
    return bd.Pos(x, y, z) * bd.Box(dx, dy, dz, align=MIN)


def outline(p, rear, width=None, front=None, radius=None):
    width = p["body_width"] if width is None else width
    front = p["body_front_y"] if front is None else front
    radius = p["body_corner_radius"] if radius is None else radius
    return bd.Pos(0, (rear + front) / 2) * bd.RectangleRounded(
        width, front - rear, radius
    )


def window(p, relief=0, flare=0):
    # A rectilinear offset preserves B's four small corner insets during lofting.
    x, y = p["window_x"] / 2, p["window_y"] / 2
    k = p["b_corner_inset_length"]
    if not relief:
        profile = bd.Rectangle(2 * (x + flare), 2 * (y + flare))
    else:
        points = [
            (-x - flare, -y - flare),
            (-x + k - flare, -y - flare),
            (-x + k - flare, -y - relief - flare),
            (x - k + flare, -y - relief - flare),
            (x - k + flare, -y - flare),
            (x + flare, -y - flare),
            (x + flare, -y + k - flare),
            (x + relief + flare, -y + k - flare),
            (x + relief + flare, y - k + flare),
            (x + flare, y - k + flare),
            (x + flare, y + flare),
            (x - k + flare, y + flare),
            (x - k + flare, y + relief + flare),
            (-x + k - flare, y + relief + flare),
            (-x + k - flare, y + flare),
            (-x - flare, y + flare),
            (-x - flare, y - k + flare),
            (-x - relief - flare, y - k + flare),
            (-x - relief - flare, -y + k - flare),
            (-x - flare, -y + k - flare),
        ]
        profile = bd.Polygon(*points, align=None)
    return bd.Pos(0, p["window_center_y"]) * profile


def window_void(p, relief=0):
    land, height = p["aperture_land"], p["window_rim_height"]
    return (
        bd.Pos(0, 0, -0.1) * bd.extrude(window(p, relief), amount=land + 0.1)
        + bd.loft(
            [
                bd.Pos(0, 0, land) * window(p, relief),
                bd.Pos(0, 0, height) * window(p, relief, p["aperture_flare"]),
            ],
            ruled=True,
        )
        + bd.Pos(0, 0, height)
        * bd.extrude(window(p, relief, p["aperture_flare"]), amount=0.1)
    )


def shell(p, half):
    t, w, f = p["sheet_thickness"], p["side_wall"], p["body_front_y"]
    rear = -p["hinge_ear_width"] if half == "a" else 0
    plate_rear = p["a_plate_rear_y"] if half == "a" else 0
    height = p[f"outer_height_{half}"]
    # One open-ended U wall. Its inset rounded profile makes the planar walls
    # w thick, including the curved front corners; the hinge end stays open.
    outer = outline(p, rear)
    inner = outline(
        p,
        rear - 2 * w,
        width=p["body_width"] - 2 * w,
        front=f - w,
        radius=p["body_corner_radius"] - w,
    )
    walls = bd.extrude(outer - inner, amount=height)
    sheet = bd.extrude(outer, amount=t)
    sheet -= box(
        -p["body_width"],
        rear - 1,
        -1,
        2 * p["body_width"],
        plate_rear - rear + 1,
        t + 2,
    )
    shape = walls + sheet
    relief = p["b_aperture_relief"] if half == "b" else 0
    rim_profile = window(p, relief, p["aperture_flare"] + p["window_rim_width"])
    shape += bd.extrude(rim_profile, amount=p["window_rim_height"])
    shape -= window_void(p, relief)
    if half == "a":
        shape += bd.Pos(0, 0, height - p["lip_thickness"]) * bd.extrude(
            outline(
                p,
                f - 2 * w,
                width=p["body_width"] - 0.2,
                front=f + p["front_lip"],
                radius=1.0,
            ),
            amount=p["lip_thickness"],
        )
    # Grip grooves remain on the front ends of the side edges only.
    for side in (-1, 1):
        for y in range(int(f - 17), int(f - 4), 2):
            shape -= box(
                p["body_width"] / 2 - 0.3 if side > 0 else -p["body_width"] / 2 - 0.1,
                y,
                height - 5,
                0.4,
                0.8,
                5.1,
            )
    return shape


def tapered_pin(diameter, length, tip):
    return bd.Cylinder(diameter / 2, length - tip, align=BASE) + bd.Pos(
        0, 0, length - tip
    ) * bd.Cone(diameter / 2, (diameter - 0.5) / 2, tip, align=BASE)


def lower(p):
    shape = bd.mirror(shell(p, "a"), about=bd.Plane.XY)
    for side in (-1, 1):
        shape += (
            bd.Pos(side * p["skirt_inner_x"], p["hinge_y"], p["hinge_z"])
            * bd.Rot(0, -side * 90, 0)
            * tapered_pin(
                p["hinge_pin_diameter"],
                p["hinge_pin_length"],
                p["hinge_pin_tip_length"],
            )
        )
    for x in (-p["film_pin_spacing"] / 2, p["film_pin_spacing"] / 2):
        shape += bd.Pos(x, p["film_pin_y"], 0) * tapered_pin(
            p["film_pin_diameter"], p["film_pin_height"], p["film_pin_tip_height"]
        )
    for x in (-p["body_width"] / 2 + 6, p["body_width"] / 2 - 6):
        for y in (p["a_plate_rear_y"] + 12, p["body_front_y"] - 12):
            shape += bd.Pos(x, y, 0) * bd.Cylinder(1, p["film_gap"], align=BASE)
    return shape


def upper(p):
    shape = shell(p, "b")
    # Hole-bearing tabs retain the original estimated pin-and-ear arrangement.
    for side in (-1, 1):
        x = p["ear_inner_x"] if side > 0 else -p["ear_outer_x"]
        profile = bd.Pos(
            -p["hinge_ear_width"] / 2,
            (p["sheet_thickness"] - p["hinge_ear_height"]) / 2,
        ) * bd.RectangleRounded(
            p["hinge_ear_width"], p["hinge_ear_height"] + p["sheet_thickness"], 1.5
        )
        ear = bd.Pos(x, 0, 0) * (
            bd.Plane.YZ * bd.extrude(profile, amount=p["hinge_ear_thickness"])
        )
        ear += box(
            x,
            -p["hinge_ear_width"],
            -0.6,
            p["hinge_ear_thickness"],
            p["hinge_ear_width"] + 2.2,
            p["sheet_thickness"] + 0.6,
        )
        ear -= (
            bd.Pos(x - 0.1, p["hinge_y"], -p["hinge_hole_from_root"])
            * bd.Rot(0, 90, 0)
            * bd.Cylinder(
                p["hinge_hole_diameter"] / 2, p["hinge_ear_thickness"] + 0.2, align=BASE
            )
        )
        shape += ear
    for x in (-p["film_pin_spacing"] / 2, p["film_pin_spacing"] / 2):
        at = bd.Pos(x, p["film_pin_y"], 0)
        shape += at * bd.Cylinder(
            p["b_pin_recess_mouth"] / 2 + p["b_pin_boss_wall"],
            p["b_pin_boss_height"],
            align=BASE,
        )
        shape -= at * bd.Cone(
            p["b_pin_recess_mouth"] / 2,
            p["b_pin_recess_bottom"] / 2,
            p["b_pin_recess_depth"],
            align=BASE,
        )
    return shape


def opened(p, shape, angle=0):
    return (
        bd.Pos(0, p["hinge_y"], p["hinge_z"])
        * bd.Rot(angle, 0, 0)
        * bd.Pos(0, -p["hinge_y"], p["film_gap"] - p["hinge_z"])
        * shape
    )


def print_part(shape, half):
    if half == "b":
        shape = bd.Rot(0, 180, 0) * shape
    bounds = shape.bounding_box()
    return (
        bd.Pos(
            90 - (bounds.min.X + bounds.max.X) / 2,
            90 - (bounds.min.Y + bounds.max.Y) / 2,
            -bounds.min.Z,
        )
        * shape
    )
