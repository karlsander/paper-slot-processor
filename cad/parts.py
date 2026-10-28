"""Complete native v1.8 parts, in millimetres. Algebra-mode build123d."""

from copy import deepcopy
from pathlib import Path

from build123d import (
    Align,
    Box,
    Compound,
    Cylinder,
    FontStyle,
    Pos,
    RectangleRounded,
    Rot,
    Sphere,
    Text,
    extrude,
    fillet,
    loft,
)

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
    taper_top = floor + p["base_taper_height"]
    shape = rounded_box(p["base_width"], p["base_depth"], floor, 6)
    shape += loft(
        [
            Pos(0, 0, floor - 0.02)
            * rounded_profile(p["base_width"], p["base_depth"], 6),
            Pos(
                (p["base_width"] - p["base_top_width"]) / 2,
                (p["base_depth"] - p["base_top_depth"]) / 2,
                taper_top,
            )
            * rounded_profile(p["base_top_width"], p["base_top_depth"], 4.8),
        ],
        ruled=True,
    )
    # Separate straight sleeves project above the half-height tapered plinth.
    for chamber in (0, 1):
        outer = p["cradle_clearance"] + p["socket_wall"]
        shape += Pos(
            p["vessel_x"] - outer,
            p["vessel_y"] + chamber * p["vessel_pitch"] - outer,
            taper_top - 0.02,
        ) * rounded_box(
            p["body_width"] + 2 * outer,
            p["body_depth"] + 2 * outer,
            p["socket_height"] - p["base_taper_height"] + 0.02,
            1.2 + outer,
        )
    for chamber in (0, 1):
        clearance = p["cradle_clearance"]
        width, depth, height = p["body_width"], p["body_depth"], p["socket_height"]
        shape -= Pos(
            p["vessel_x"] - clearance,
            p["vessel_y"] + chamber * p["vessel_pitch"] - clearance,
            floor,
        ) * rounded_box(
            width + 2 * clearance, depth + 2 * clearance, height + 0.1, 1.2 + clearance
        )
    for chamber in (0, 1):
        label_y = p["base_depth"] / 2 + (-6 if chamber == 0 else 6)
        shape += Pos(p["vessel_x"] + 8, label_y - 4, taper_top) * tactile(chamber + 1)
        if labels:
            shape -= Pos(p["base_width"] / 2, label_y, taper_top - 0.6) * lettering(
                f"{'AB'[chamber]}  {p['working_ml']} ml", 5
            )
    return shape


def flange(p, height):
    return Pos(-p["end_ledge"], -1, 0) * rounded_box(
        p["flange_width"], p["flange_depth"], height, 2.4
    )


def magnet_pockets(p, z):
    return Compound(
        children=[
            Pos(x, p["body_depth"] / 2, z)
            * Cylinder(
                p["pocket_diameter"] / 2,
                p["pocket_depth"] + 0.02,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            for x in p["magnet_x"]
        ]
    )


def fill_ridge(p):
    w, d, r, t = (
        p["inner_width"],
        p["bath_gap"],
        p["inside_radius"],
        p["ridge_projection"],
    )
    outer = rounded_box(w + 0.04, d + 0.04, p["ridge_height"], r + 0.02)
    inner = Pos(t + 0.02, t + 0.02, -0.01) * rounded_box(
        w - 2 * t, d - 2 * t, p["ridge_height"] + 0.02, r - t
    )
    return Pos(
        p["wall"] - 0.02, p["wall"] - 0.02, p["empty_level"] - p["ridge_height"]
    ) * (outer - inner)


def vessel(p, chamber=0, labels=True):
    width, depth, height = p["body_width"], p["body_depth"], p["body_height"]
    shape = rounded_box(width, depth, height, 1.2)
    seat = p["guide_seat"]
    shape += Pos(0, 0, seat - p["ledge_thickness"]) * flange(
        p, p["ledge_thickness"] + p["rim_height"]
    )
    # Recess the top inside a thin outer rim. The left notch clears its pull tab.
    rw = p["rim_wall"]
    recess = Pos(-p["end_ledge"] + rw, -1 + rw, seat) * rounded_box(
        p["flange_width"] - 2 * rw,
        p["flange_depth"] - 2 * rw,
        p["rim_height"] + 1,
        2.4 - rw,
    )
    notch = Pos(
        -p["end_ledge"] - 1, (depth - p["tab_width"]) / 2 - p["guide_fit"], seat
    ) * Box(rw + 2, p["tab_width"] + 2 * p["guide_fit"], p["rim_height"] + 1, align=MIN)
    shape -= recess + notch
    shape += (
        Pos(width / 2 - 2 * chamber, 0.3, height - 30)
        * Rot(90, 0, 0)
        * tactile(chamber + 1)
    )
    shape -= liquid_void(p, chamber)
    shape -= magnet_pockets(p, seat - p["pocket_depth"])
    if labels:
        shape -= (
            Pos(width / 2, 0.6, height * 0.45)
            * Rot(90, 0, 0)
            * lettering("AB"[chamber], 26)
        )
    return shape


def liquid_void(p, chamber=0):
    """Wet cavity excluding the continuous fill ridge and bottom stops."""
    width, depth, height = p["body_width"], p["body_depth"], p["body_height"]
    # Spherical corner/edge rounding corresponds to the SCAD hull of spheres.
    cavity = Box(p["inner_width"], p["bath_gap"], height + 12 - p["floor"], align=MIN)
    cavity = fillet(cavity.edges(), radius=p["inside_radius"])
    cavity = Pos(p["wall"], p["wall"], p["floor"]) * cavity
    cavity -= fill_ridge(p)
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


def guide(p, chamber=0, labels=True):
    gap = p["guide_gap"]
    width, depth, thick = p["body_width"], p["body_depth"], p["guide_thickness"]
    inset = p["rim_wall"] + p["guide_fit"]
    x = -p["end_ledge"] + inset
    shape = Pos(x, -1 + inset, 0) * rounded_box(
        p["guide_width"], p["guide_depth"], thick, 2.4 - inset
    )
    shape += Pos(
        -p["end_ledge"] - p["tab_length"], (depth - p["tab_width"]) / 2, 0
    ) * rounded_box(p["tab_length"] + inset + 1, p["tab_width"], thick, 2)
    shape -= magnet_pockets(p, -0.02)

    def section(g, z):
        return Pos(
            (width - p["slit_length"]) / 2, depth / 2 - g / 2, z
        ) * rounded_profile(p["slit_length"], g, min(g / 2, 0.6))

    low = thick - p["drip_depth"] - p["wiping_land"]
    shape -= loft([section(gap + 4, -0.02), section(gap, low + 0.02)], ruled=True)
    shape -= extrude(section(gap, low - 0.02), amount=p["wiping_land"] + 0.06)
    shape -= loft(
        [section(gap, thick - p["drip_depth"]), section(gap + 4, thick + 0.04)],
        ruled=True,
    )
    if labels:
        shape -= Pos(
            -p["end_ledge"] - p["tab_length"] / 2, depth / 2, thick - 0.6
        ) * lettering("AB"[chamber], 5)
    return shape


def centered_plate(shape):
    box = shape.bounding_box()
    return (
        Pos(
            (180 - box.size.X) / 2 - box.min.X,
            (180 - box.size.Y) / 2 - box.min.Y,
            -box.min.Z,
        )
        * shape
    )


def print_vessel(p, shape, chamber):
    result = Rot(p["print_tilt"], 0, 0) * shape
    result += Pos(1, -3, 0) * rounded_box(p["body_width"] - 2, 6, 0.4, 1)
    return centered_plate(result)


def print_guide(p, shape):
    return centered_plate(Rot(180, 0, 0) * shape)


def assembly_parts(p, shapes):
    """Named local shapes and explicit mating locations; no constraint solver."""
    parts = {"base": deepcopy(shapes["base"])}
    for i, letter in enumerate("ab"):
        origin = Pos(
            p["vessel_x"], p["vessel_y"] + i * p["vessel_pitch"], p["cradle_floor"]
        )
        parts[f"vessel_{letter}"] = origin * shapes[f"vessel_{letter}"]
        parts[f"guide_{letter}"] = (
            origin * Pos(0, 0, p["guide_seat"]) * shapes[f"guide_{letter}"]
        )
    return parts
