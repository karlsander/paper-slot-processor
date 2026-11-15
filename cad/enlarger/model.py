"""Exact B-reps. X follows roll, Y spans paper, Z=0 is baseboard."""

from pathlib import Path

import build123d as bd

from .parameters import image_length

FONT = Path(__file__).resolve().parents[1] / "fonts/LiberationSans-Bold.ttf"
EPS = 0.01


def box(x, y, z, dx, dy, dz):
    return bd.Pos(x, y, z) * bd.Box(dx, dy, dz, align=(bd.Align.MIN,) * 3)


def cylinder(x, y, z, d, h):
    return bd.Pos(x, y, z) * bd.Cylinder(
        d / 2, h, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )


def prism(points, height):
    return bd.extrude(bd.Polygon(*points, align=None), amount=height)


def label(text, size, depth):
    return bd.extrude(
        bd.Text(
            text, size, font_path=str(FONT), align=(bd.Align.CENTER, bd.Align.CENTER)
        ),
        amount=depth,
    )


def deck(p):
    length, width, z = p["base_length"], p["base_width"], p["deck_thickness"]
    s = box(-length / 2, -width / 2, 0, length, width, z)
    for side in (-1, 1):
        y = p["channel_width"] / 2 if side > 0 else -p["channel_width"] / 2 - 2
        s += box(-length / 2, y, z, length, 2, p["guide_height"])
        y = p["rail_inner"] if side > 0 else -width / 2
        s += box(
            -length / 2, y, z, length, p["outer_rail_width"], p["outer_rail_height"]
        )
        for t in (-1, 1):
            s += bd.Pos(
                side * p["locator_x"], t * p["attachment_y"], z - EPS
            ) * bd.Cone(
                p["locator_diameter"] / 2,
                (p["locator_diameter"] - 0.4) / 2,
                p["locator_height"] + EPS,
                align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN),
            )
            s -= cylinder(
                side * p["magnet_x"],
                t * p["attachment_y"],
                z - p["magnet_thickness"] - p["magnet_depth_clearance"],
                p["magnet_diameter"] + p["magnet_diameter_clearance"],
                p["magnet_thickness"] + p["magnet_depth_clearance"] + EPS,
            )
    return s


def base_halves(p):
    length, width = p["base_length"], p["base_width"]
    tongues = bd.Sketch()
    for y in (-width / 4, width / 4):
        tongues += bd.Pos(0, y) * bd.Polygon(
            (-1, -7),
            (0, -7),
            (p["joint_depth"], -10),
            (p["joint_depth"], 10),
            (0, 7),
            (-1, 7),
            align=None,
        )
    left = bd.Pos(-length / 4, 0) * bd.Rectangle(length / 2, width) + tongues
    right = bd.Pos((p["joint_clearance"] + length / 2) / 2, 0) * bd.Rectangle(
        length / 2 - p["joint_clearance"], width
    )
    right -= bd.offset(tongues, amount=p["joint_clearance"], kind=bd.Kind.INTERSECTION)
    full = deck(p)
    return {
        name: full
        & (
            bd.Pos(0, 0, -EPS)
            * bd.extrude(
                outline, amount=p["deck_thickness"] + p["locator_height"] + 2 * EPS
            )
        )
        for name, outline in [("base_left", left), ("base_right", right)]
    }


def mask(p, fmt, side):
    if side not in (-1, 1):
        raise ValueError("Mask side must be -1 or 1")
    length = image_length(p, fmt)
    s = box(
        length / 2,
        -p["mask_width"] / 2,
        p["paper_z"],
        (p["base_length"] - length) / 2,
        p["mask_width"],
        p["mask_thickness"],
    )
    # XY polygon maps to XZ; extrude toward -Y through the paper channel.
    cut = bd.Plane.XZ * bd.Polygon(
        (-EPS, p["mask_edge_land"]),
        (p["mask_bevel"], p["mask_thickness"] + EPS),
        (-EPS, p["mask_thickness"] + EPS),
        align=None,
    )
    s -= bd.Pos(length / 2, p["channel_width"] / 2, p["paper_z"]) * bd.extrude(
        cut, amount=p["channel_width"], dir=(0, -1, 0)
    )
    for t in (-1, 1):
        s -= cylinder(
            p["magnet_x"],
            t * p["attachment_y"],
            p["paper_z"] - EPS,
            p["magnet_diameter"] + p["magnet_diameter_clearance"],
            p["magnet_thickness"] + p["magnet_depth_clearance"] + EPS,
        )
        s -= cylinder(
            p["locator_x"],
            t * p["attachment_y"],
            p["paper_z"] - EPS,
            p["locator_diameter"] + p["locator_clearance"],
            p["locator_height"] + 0.3 + EPS,
        )
    s -= (
        bd.Pos(p["base_length"] / 2 - 10, 0, p["mask_top"] - 0.4)
        * bd.Rot(0, 0, 90)
        * label(fmt + (" L" if side < 0 else " R"), 3, 0.4 + EPS)
    )
    return bd.Rot(0, 0, 180 if side < 0 else 0) * s


def cover(p, i, fmt="16:9"):
    if isinstance(i, bool) or i not in range(4):
        raise ValueError("Cover index must be 0–3")
    lo = -image_length(p, fmt) / 2 + i * p["band_width"]
    hi = lo + p["band_width"]
    c = (lo + hi) / 2
    end, z, t = p["cover_end"], p["cover_bottom"], p["cover_thickness"]
    s = box(lo, -end, z, p["band_width"], 2 * end, t)
    if i < 3:
        s += box(
            hi - EPS, -end, z, p["cover_lap"] + EPS, 2 * end, p["cover_lap_height"]
        )
    # Ruled grip taper matches the old hull's exterior.
    s += bd.loft(
        [
            bd.Pos(c, end - 3, z + t - EPS) * bd.Rectangle(14, 4),
            bd.Pos(c, end - 3, z + t + 4) * bd.Rectangle(13, 3),
        ],
        ruled=True,
    )
    if i > 0:
        lap, gap, h = p["cover_lap"], p["cover_clearance"], p["cover_lap_height"]
        cut = bd.Plane.XZ * bd.Polygon(
            (-EPS, -EPS),
            (lap + gap, -EPS),
            (lap + gap, h + gap),
            (-EPS, h + lap + 2 * gap),
            align=None,
        )
        s -= bd.Pos(lo, end + EPS, z) * bd.extrude(
            cut, amount=2 * end + 2 * EPS, dir=(0, -1, 0)
        )
    s -= bd.Pos(c, -end + 3.5, z + t - 0.4) * label(str(i + 1), 4, 0.4 + EPS)
    for n in range(i + 1):
        s -= cylinder(c + (n - i / 2) * 3, end - 3, z + t + 4 - 0.6, 1.6, 0.6 + EPS)
    return s


def paper(p):
    return box(
        -p["base_length"] / 2 - 10,
        -p["paper_width"] / 2,
        p["deck_thickness"],
        p["base_length"] + 20,
        p["paper_width"],
        p["paper_thickness"],
    )


def assembly(p, fmt="16:9", count=0, exploded=0):
    if isinstance(count, bool) or count not in range(5):
        raise ValueError("Cover count must be 0–4")
    shapes = base_halves(p) | {"paper": paper(p)}
    for side in (-1, 1):
        shapes[f"mask_{side}"] = bd.Pos(0, 0, exploded) * mask(p, fmt, side)
    for i in range(count):
        shapes[f"cover_{i + 1}"] = bd.Pos(0, 0, 2 * exploded) * cover(p, i, fmt)
    return shapes


def plates(p):
    bases = base_halves(p)
    length, width = p["base_length"], p["base_width"]
    result = {
        "base_left": bd.Pos(length / 2, width / 2, 0) * bases["base_left"],
        "base_right": bd.Pos(0, width / 2, 0) * bases["base_right"],
    }
    for fmt, key in [("16:9", "masks_16x9"), ("4:3", "masks_4x3")]:
        depth = (length - image_length(p, fmt)) / 2
        result[key] = bd.Compound(
            children=[
                bd.Pos(
                    length / 2 if side < 0 else depth + 6 - image_length(p, fmt) / 2,
                    p["mask_width"] / 2,
                    -p["paper_z"],
                )
                * mask(p, fmt, side)
                for side in (-1, 1)
            ]
        )
    for i in range(4):
        result[f"cover_{i + 1}"] = bd.Pos(
            image_length(p, "16:9") / 2 - i * p["band_width"],
            p["cover_end"],
            -p["cover_bottom"],
        ) * cover(p, i)
    crop = box(
        -length / 2,
        p["paper_width"] / 2 - 6,
        -EPS,
        42,
        p["cover_end"] - p["paper_width"] / 2 + 6,
        30,
    )
    coupon = [
        bd.Pos(length / 2, -p["paper_width"] / 2 + 6, 0) * (bases["base_left"] & crop),
        bd.Pos(52 + length / 2, -p["paper_width"] / 2 + 6, -p["paper_z"])
        * (mask(p, "16:9", -1) & crop),
        bd.Pos(82 + p["image_169"] / 2, -p["paper_width"] / 2 + 6, -p["cover_bottom"])
        * (cover(p, 0) & crop),
    ]
    result["fit_coupon"] = bd.Compound(children=coupon)
    return result
