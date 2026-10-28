"""Complete native v1.8 parts, in millimetres. Algebra-mode build123d."""

from copy import deepcopy
from pathlib import Path

from build123d import (
    Align,
    Box,
    Circle,
    Compound,
    Cylinder,
    FontStyle,
    Plane,
    Pos,
    RectangleRounded,
    Rot,
    Sphere,
    Text,
    extrude,
    fillet,
    loft,
    mirror,
)

from .parameters import well_at

MIN = (Align.MIN, Align.MIN, Align.MIN)


def rounded_profile(width, depth, radius):
    # Keep all four corner arcs for loft correspondence at the capsule limit.
    # A 0.001 mm straight segment avoids a topology change at radius=depth/2.
    return RectangleRounded(
        width, depth, min(radius, depth / 2 - 0.001), align=(Align.MIN, Align.MIN)
    )


def rounded_box(width, depth, height, radius):
    return extrude(rounded_profile(width, depth, radius), amount=height)


def base(p, labels=True):
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
    for chamber in (0, 1):
        shape += Pos(12, chamber * p["vessel_pitch"] + 9, floor) * tactile(chamber + 1)
        if labels:
            shape -= Pos(
                p["base_width"] / 2, chamber * p["vessel_pitch"] + 11, floor - 0.6
            ) * lettering(f"{'AB'[chamber]}  {p['working_ml']} ml", 5)
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


def vessel(p, chamber=0, labels=True):
    width, depth, height = p["body_width"], p["body_depth"], p["body_height"]
    shape = rounded_box(width, depth, height, 1.2)
    rim = p["rim_overhang"]
    shape += Pos(-rim, -rim, height - p["rim_height"]) * rounded_box(
        width + 2 * rim, depth + rim - 0.1, p["rim_height"], 1.5
    )
    shape += well(p, p["well_wall"], chamber=chamber)
    shape += (
        Pos(width / 2 - 2 * chamber, 0.3, height - 30)
        * Rot(90, 0, 0)
        * tactile(chamber + 1)
    )
    shape -= liquid_void(p, chamber)
    if labels:
        shape -= (
            Pos(width / 2, 0.6, height * 0.45)
            * Rot(90, 0, 0)
            * lettering("AB"[chamber], 26)
        )
    r = well_at(p, p["empty_level"])[1]
    ring = Cylinder(
        r + 0.4, 0.6, align=(Align.CENTER, Align.CENTER, Align.MIN)
    ) - Cylinder(r - 0.01, 0.6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ring = Pos(p["well_cx"], p["well_cy"], p["empty_level"] - 0.3) * ring
    if chamber == 0:
        ring = Pos(width, 0, 0) * mirror(ring, about=Plane.YZ)
    return shape - ring


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
        stop += Pos(x, depth / 2, p["floor"] + p["bottom_clearance"] - 2) * Sphere(2)
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


def tactile(n, size=8):
    return Compound(
        children=[Pos(i * 4, 0, 0) * rounded_box(2, size, 1, 0.9) for i in range(n)]
    )


def lettering(text, size):
    # OCCT and OpenSCAD use different font-size metrics. Lettering is verified
    # separately from fit surfaces, and never changes a mating dimension.
    return extrude(
        Text(
            text,
            font_size=size,
            font="Liberation Sans",
            font_style=FontStyle.BOLD,
            font_path=str(Path(__file__).parent / "fonts/LiberationSans-Bold.ttf"),
            align=(Align.CENTER, Align.CENTER),
        ),
        amount=0.7,
    )


def guide(p, chamber=0, gap=None, closed=False, labels=True):
    gap = p["guide_gap"] if gap is None else gap
    width, depth, thick, skirt = (
        p["body_width"],
        p["body_depth"],
        p["guide_thickness"],
        p["guide_skirt"],
    )
    over = p["rim_overhang"] + p["guide_fit"]
    shape = Pos(-over, -over, 0) * rounded_box(
        p["guide_width"], p["guide_depth"], thick, 1.5
    )
    outer = rounded_box(
        p["inner_width"] - 2 * p["guide_fit"],
        p["bath_gap"] - 2 * p["guide_fit"],
        skirt + 0.02,
        p["inside_radius"],
    )
    inner = Pos(1.5, 1.5, -0.02) * rounded_box(
        p["inner_width"] - 2 * p["guide_fit"] - 3,
        p["bath_gap"] - 2 * p["guide_fit"] - 3,
        skirt + 0.04,
        1,
    )
    shape += Pos(p["wall"] + p["guide_fit"], p["wall"] + p["guide_fit"], -skirt) * (
        outer - inner
    )
    shape += Pos(9, -over + 0.2, 0.6) * Rot(90, 0, 0) * tactile(chamber + 1, 1.8)
    if not closed:

        def section(g, z):
            return Pos(
                (width - p["slit_length"]) / 2, depth / 2 - g / 2, z
            ) * rounded_profile(p["slit_length"], g, min(g / 2, 0.6))

        low = thick - p["drip_depth"] - p["wiping_land"]
        shape -= loft(
            [section(gap + 4, -skirt - 0.02), section(gap, low + 0.02)], ruled=True
        )
        shape -= extrude(section(gap, low - 0.02), amount=p["wiping_land"] + 0.06)
        shape -= loft(
            [section(gap, thick - p["drip_depth"]), section(gap + 4, thick + 0.04)],
            ruled=True,
        )
    if labels:
        label = "AB"[chamber] + ("" if closed else f" {gap:g}")
        shape -= Pos(width - 12, depth / 2, thick - 0.6) * lettering(label, 3)
    return shape


def clip(p):
    w = p["clip_width"]
    return (
        rounded_box(w, 9, 9, 1)
        - Pos(-0.02, 2, 1.8) * Box(w + 0.04, 8, 5.4, align=MIN)
        - Pos(-0.02, 3.8, -0.02) * Box(w + 0.04, 6, 1.82, align=MIN)
    )


def fit_sample(p, bath):
    return Pos(
        p["vessel_xmax"] - p["body_width"], p["rim_overhang"], -p["body_height"] + 12
    ) * (
        bath
        & Pos(-p["vessel_xmax"], -5, p["body_height"] - 12)
        * Box(3 * p["vessel_xmax"], p["body_depth"] + 10, 13, align=MIN)
    )


def print_vessel(p, shape, chamber):
    import math

    tilt = math.radians(p["print_tilt"])
    dx = p["vessel_xmax"] - p["body_width"] if chamber == 0 else p["rim_overhang"]
    dy = p["body_height"] * math.sin(tilt) + p["rim_overhang"] * math.cos(tilt)
    result = Pos(dx, dy, 0) * Rot(p["print_tilt"], 0, 0) * shape
    result += Pos(dx + 1, dy - 3, 0) * rounded_box(p["body_width"] - 2, 6, 0.4, 1)
    return (
        Pos(
            (180 - p["vessel_print_bounds"][0]) / 2,
            (180 - p["vessel_print_bounds"][1]) / 2,
            0,
        )
        * result
    )


def print_guide(p, shape):
    return (
        Pos(p["rim_overhang"] + p["guide_fit"], p["body_depth"], p["guide_thickness"])
        * Rot(180, 0, 0)
        * shape
    )


def clip_plate(p, shape):
    one = Pos(0, 0, p["clip_width"]) * Rot(0, 90, 0) * shape
    return Compound(children=[Pos(x, y, 0) * one for x in (0, 14) for y in (0, 14)])


def assembly_parts(p, shapes):
    """Named local shapes and explicit mating locations; no constraint solver."""
    parts = {"base": deepcopy(shapes["base"])}
    for i, letter in enumerate("ab"):
        origin = Pos(
            p["vessel_x"], p["vessel_y"] + i * p["vessel_pitch"], p["cradle_floor"]
        )
        parts[f"vessel_{letter}"] = origin * shapes[f"vessel_{letter}"]
        parts[f"guide_{letter}"] = (
            origin * Pos(0, 0, p["body_height"]) * shapes[f"guide_{letter}"]
        )
        for j, x in enumerate((p["body_width"] / 4, 3 * p["body_width"] / 4)):
            parts[f"clip_{letter}{j}"] = (
                origin
                * Pos(x - p["clip_width"] / 2, -4.2, p["body_height"] - 4)
                * shapes["clip"]
            )
    return parts
