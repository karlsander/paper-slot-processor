"""Native build123d solids for a defeatured v1.8 fit study, in millimetres.

Dimensions come from evaluated OpenSCAD, not a second set of defaults. Text,
tactile marks and the fill-cue engraving are omitted. Curves are analytic rather
than 64-sided polygons. This study does not replace the production print files.
"""

from build123d import (
    Align,
    Box,
    Circle,
    Cylinder,
    Plane,
    Pos,
    RectangleRounded,
    Sphere,
    extrude,
    fillet,
    loft,
    mirror,
)

MIN = (Align.MIN, Align.MIN, Align.MIN)


def rounded_box(width, depth, height, radius):
    return extrude(
        RectangleRounded(width, depth, radius, align=(Align.MIN, Align.MIN)),
        amount=height,
    )


def base(p):
    floor = p["cradle_floor"]
    shape = rounded_box(p["base_width"], p["base_depth"], floor, 3)
    for chamber in (0, 1):
        clearance, wall = p["cradle_clearance"], p["socket_wall"]
        width, depth, height = p["body_width"], p["body_depth"], p["socket_height"]
        outer = rounded_box(
            width + 2 * (clearance + wall),
            depth + 2 * (clearance + wall),
            height + 0.02,
            1.2 + clearance + wall,
        )
        inner = Pos(wall, wall, -0.02) * rounded_box(
            width + 2 * clearance, depth + 2 * clearance, height + 0.06, 1.2 + clearance
        )
        socket = outer - inner
        shape += (
            Pos(
                p["vessel_x"] - clearance - wall,
                chamber * p["vessel_pitch"] + p["vessel_y"] - clearance - wall,
                floor - 0.02,
            )
            * socket
        )
    return shape


def well(p, extra=0, extend=0, chamber=0):
    sections = [
        Pos(x, p["well_cy"], z + (extend if z == p["well_top"] else 0))
        * Circle(radius + extra)
        for z, x, radius in p["well_stations"]
    ]
    shape = loft(sections, ruled=True)
    shape &= Pos(-p["vessel_xmax"], -100, -1) * Box(
        3 * p["vessel_xmax"],
        p["body_depth"] + 100,
        p["body_height"] + extend + 3,
        align=MIN,
    )
    if chamber == 0:
        shape = Pos(p["body_width"], 0, 0) * mirror(shape, about=Plane.YZ)
    return shape


def vessel(p, chamber=0):
    width, depth, height = p["body_width"], p["body_depth"], p["body_height"]
    shape = rounded_box(width, depth, height, 1.2)
    rim = p["rim_overhang"]
    shape += Pos(-rim, -rim, height - p["rim_height"]) * rounded_box(
        width + 2 * rim, depth + rim - 0.1, p["rim_height"], 1.5
    )
    shape += well(p, p["well_wall"], chamber=chamber)
    return shape - liquid_void(p, chamber)


def liquid_void(p, chamber=0):
    """Wet cavity, including the connected filling well and bottom stops."""
    width, depth, height = p["body_width"], p["body_depth"], p["body_height"]
    # Spherical corner/edge rounding corresponds to the SCAD hull of spheres.
    cavity = Box(p["inner_width"], p["bath_gap"], height + 12 - p["floor"], align=MIN)
    cavity = fillet(cavity.edges(), radius=p["inside_radius"])
    cavity = Pos(p["wall"], p["wall"], p["floor"]) * cavity
    cavity += well(p, extend=2, chamber=chamber)
    for x in (width / 3, 2 * width / 3):
        stop = Pos(x, depth / 2, p["floor"] - 0.02) * Cylinder(
            2,
            p["bottom_clearance"] - 2 + 0.02,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        stop += Pos(
            x, depth / 2, p["floor"] + p["bottom_clearance"] - 2 + 0.02
        ) * Sphere(2)
        cavity -= stop
    return cavity


def placed_vessel(p, shape, chamber=0):
    return (
        Pos(
            p["vessel_x"],
            p["vessel_y"] + chamber * p["vessel_pitch"],
            p["cradle_floor"],
        )
        * shape
    )
