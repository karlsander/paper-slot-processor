"""All dimensions in mm. X advances film; +Y faces operator; Z is optical.

Thin moving geometry ends at Y=42. Thick clamps and screw are outside the
independent, unmeasured enlarger envelope. No prescribed flexure shapes.
"""

from functools import lru_cache

import build123d as bd

from cad.negative_carrier_b.model import Config
from cad.negative_carrier_concepts.model import box

PITCH = 3.0
WEDGE_SLOPE = 0.05
DEFAULT = Config("135", frame_count=4)


def cylinder(x, y, z, radius, height):
    return bd.Pos(x, y, z) * bd.Cylinder(
        radius, height, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )


@lru_cache(maxsize=4)
def thread(clearance=False):
    """Real trapezoidal helix, D12 x 3; female has radial/axial allowance.

    Custom printed thread, not a certified metric or Acme standard.
    """
    r = 0.25 if clearance else 0
    a = 0.15 if clearance else 0
    core = cylinder(0, 0, 0, 4.6 + r, 16)
    profile = bd.Plane.XZ * bd.Polygon(
        (4.45 + r, -1.15 - a),
        (6 + r, -0.6 - a),
        (6 + r, 0.6 + a),
        (4.45 + r, 1.15 + a),
        align=None,
    )
    helix = bd.Helix(PITCH, 22, 4.45 + r)
    ridge = bd.Pos(0, 0, -3) * bd.sweep(profile, path=helix, is_frenet=True)
    return (core + ridge) & box(0, 0, 0, 20, 20, 16)


def notch(x=0, z0=3.5, z1=8.5, front=65):
    """Three inclined contact faces: two locate X, rear face biases -Y.

    All faces transmit a downward component to the support pads. The tip is
    relieved so its bottom cannot determine the working position.
    """
    sections = []
    for z in (z0, z1):
        half = z - 3
        sections.append(
            bd.Pos(x, 0, z)
            * bd.Polygon(
                (-half, 59 - z),
                (half, 59 - z),
                (half, front),
                (-half, front),
                align=None,
            )
        )
    return bd.loft(sections, ruled=True)


def stations(p):
    return (-p.length / 2 + 14, 0, p.length / 2 - 14)


def edge_offset(p):
    """Keep each clamp and side datum the same distance from the film margin."""
    return p.fmt.film_width / 2 - 17.5


def ramp(x, low, high, y0=43, y1=47.5, half=11):
    poly = bd.Plane.XZ * bd.Polygon(
        (x - half, low),
        (x + half, low),
        (x + half, high + half * WEDGE_SLOPE),
        (x - half, high - half * WEDGE_SLOPE),
        align=None,
    )
    return bd.Pos(0, y0, 0) * bd.extrude(poly, amount=y1 - y0, dir=(0, 1, 0))


@lru_cache(maxsize=8)
def holder(p=DEFAULT):
    delta = edge_offset(p)
    h = p.fmt.image_height / 2 + 0.4
    # Continuous open image passage, with supports in the interframe gaps.
    base = box(0, 10, -1.2, p.length, 68, 1.2)
    base -= box(0, 0, -1.3, p.length + 2, 2 * h, 1.5)
    lid = box(0, 0, 0.2, p.length, 48, 1.0)
    lid -= box(0, 0, 0, p.length + 2, 2 * h, 2)
    # Keep clamping lands at the chosen film thickness; never touch image areas.
    for y in (-1, 1):
        width = p.fmt.film_width / 2 - h
        lid += box(
            0,
            y * (h + width / 2),
            p.film_thickness,
            p.length,
            width,
            0.21 - p.film_thickness,
        )
    for a, b in zip(p.fmt.centers, p.fmt.centers[1:]):
        width = b - a - p.fmt.image_width - 0.4
        base += box((a + b) / 2, 0, -1.2, width, 2 * h + 0.1, 1.2)
        lid += box(
            (a + b) / 2, 0, p.film_thickness, width, 2 * h + 0.1, 1.2 - p.film_thickness
        )
    # Continuous underside datum groove avoids the moving edge clamps.
    base -= box(0, -19.4 - delta, -1.3, p.length + 2, 1.2, 0.7)
    # Thicker front spine and index features are fully outside Y=42.
    base += box(0, 53.5, -1.2, p.length, 21, 9.2)
    for x in p.fmt.centers:
        base -= notch(x)
    for x in stations(p):
        for side in (-1, 1):
            base -= box(x, side * (23 + delta), -1.3, 20.4, 2.4, 0.85)
            cut = bd.Pos(x - 10.2, delta, 0) * bd.extrude(
                bd.Plane.YZ
                * bd.Polygon(
                    (21.8, 0.66), (24.2, 0.54), (24.2, 2), (21.8, 2), align=None
                ),
                amount=20.4,
                dir=(1, 0, 0),
            )
            if side < 0:
                cut = cut.mirror(bd.Plane.XZ)
            lid -= cut
            # Narrow formats use open pockets so clamps still enter directly
            # from outside. The continuous datum groove moves inward too.
            inner = 24 + delta
            lid -= box(x, side * (inner + 25) / 2, -0.1, 20.4, 25 - inner, 2)
        inner = 24 + delta
        base -= box(x, (inner + 34) / 2, -1.3, 20.4, 34 - inner, 2.6)
        base -= box(x, -(inner + 25) / 2, -1.3, 20.4, 25 - inner, 2.6)
    return {"base": base, "lid": lid}


def closure_wedge(x=0, side=1):
    """Broad push-on wedge with no catch or release tongue.

    The 1:20 top ramp matches the lid's edge. Nominal pose has zero preload;
    contact analysis, not intersecting CAD, establishes force for extra travel.
    """
    outer = box(x, 24.5, -1.2, 20, 5.4, 2.5)
    gap = bd.Pos(x - 11, 0, 0) * bd.extrude(
        bd.Plane.YZ
        * bd.Polygon((20, -0.45), (25.4, -0.45), (25.4, 0.48), (20, 0.75), align=None),
        amount=22,
        dir=(1, 0, 0),
    )
    outer -= gap
    return outer if side > 0 else outer.mirror(bd.Plane.XZ)


def shoe():
    s = notch(0, 4.5, 8, front=60)
    s += box(0, 57, 8, 12, 8, 4.4)
    # Open-front tapered bearing centers X under preload. A flat floor with
    # radial clearance allowed the shoe to float sideways around the screw.
    s -= bearing_cone()
    s -= cylinder(0, 57, 10.3, 3.3, 1.1)
    s -= box(0, 61, 9, 6.6, 8, 2.4)
    s -= cylinder(0, 57, 11.3, 1.95, 2)
    s -= box(0, 61, 11.3, 3.9, 8, 2)
    return s


def bearing_cone():
    return bd.Pos(0, 57, 9) * bd.Cone(
        1.7, 3.0, 1.3, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )


def bearing_head():
    s = bearing_cone() + cylinder(0, 57, 10.3, 3, 0.7)
    s += cylinder(0, 57, 10.8, 1.7, 2.4)
    return s


def dock_side_bevel():
    return bd.Pos(0, -60, 0) * bd.extrude(
        bd.Plane.XZ * bd.Polygon((23.2, -2.4), (24.1, -2.4), (24.1, -1.5), align=None),
        amount=180,
        dir=(0, 1, 0),
    )


def screw():
    s = bd.Pos(0, 57, 13) * thread()
    s += bearing_head()
    s += cylinder(0, 57, 28.8, 4.6, 0.6)
    s += cylinder(0, 57, 29.2, 11, 4.2)
    for x in (-1, 1):
        s += box(x * 10, 57, 29.2, 4, 9, 4.2)
    return s


@lru_cache(maxsize=8)
def sleeve(p=DEFAULT):
    delta = edge_offset(p)
    aw, ah = p.fmt.aperture
    low = box(0, 19.5, -2.4, 48, 103, 0.8)
    low -= box(0, 0, -3, aw, ah, 3)
    top = box(0, -3, 1.5, 48, 58, 0.8)
    top -= box(0, 0, 1, aw, ah, 3)
    s = low + top + box(0, -30, -2.4, 48, 4, 4.7)
    # Three support pads. Two rear side references set Y/yaw under clamp load.
    for x, y in ((-18, 39), (18, 39), (0, -21 - delta)):
        s += box(x, y, -1.6, 6, 0.8 if x == 0 else 3, 0.4)
    for x in (-18, 18):
        s += box(x, -19.3 - delta, -1.6, 6, 1, 0.9)
    # Front bridge spans above moving index spine and all closure wedges.
    s += box(0, 68, -2.4, 48, 6, 22.4)
    s += box(0, 60.5, 17, 30, 15, 12)
    s -= bd.Pos(0, 57, 13) * thread(True)
    # Shoe guide cheeks only begin above the moving spine.
    for x in (-7.5, 7.5):
        s += box(x, 57, 8.4, 2.4, 9, 9)
    # Dock tongue and flange: no four cap keys or little dock pins.
    s += box(0, -32.55, -2.4, 32, 1.5, 1.2)
    s += ramp(0, -2.4, 1.2, 71, 75, half=16)
    # Broad V rails locate the sleeve in X/yaw under the docking clamp.
    bevel = dock_side_bevel()
    s -= bevel
    s -= bevel.mirror(bd.Plane.YZ)
    return s


def receiver():
    s = box(0, -47, -1.2, 94.6, 28, 2.6)
    for x in (-46.5, 46.5):
        s += box(x, 15, -3.4, 1.6, 122, 1.4)
        s += box(x, -34, -3.4, 1.6, 2, 4.8)
    s += box(0, 74, -6.4, 94.6, 6, 4)
    # Integral broad stop limits positive docking-wedge travel to 2 mm.
    s += box(15, 81, -6.4, 6, 14, 4)
    for x in (-22.5, 22.5):
        s += box(x, 20, -3.4, 3, 108, 1)
    rail = bd.Pos(0, -34, 0) * bd.extrude(
        bd.Plane.XZ * bd.Polygon((23.2, -2.4), (24, -2.4), (24, -1.6), align=None),
        amount=108,
        dir=(0, 1, 0),
    )
    s += rail
    s += rail.mirror(bd.Plane.YZ)
    # Rear pocket captures the format sleeve tongue after forward docking.
    s += box(0, -33.65, -3.4, 36, 0.7, 3)
    s += box(0, -32.9, -0.4, 36, 1.6, 0.8)
    # Broad front C wedge holds the sleeve flange; matching 1:20 ramp.
    return s


def dock_wedge():
    # Broad 1.2 mm lower / >=1.3 mm upper jaws with a longer free span.
    # Thick short jaws needed ~40 N at 0.5 mm; thinner short jaws still ~20 N.
    s = box(0, 79.5, -7.6, 20, 17, 10.6)
    s -= ramp(0, -6.4, 1.2, 70.9, 82.5, half=12)
    return s


@lru_cache(maxsize=8)
def parts(p=DEFAULT):
    result = holder(p)
    result.update(
        {
            f"wedge-{i}-{side}": bd.Pos(0, side * edge_offset(p), 0)
            * closure_wedge(x, side)
            for i, x in enumerate(stations(p))
            for side in (-1, 1)
        }
    )
    result.update(
        sleeve=sleeve(p),
        shoe=shoe(),
        screw=screw(),
        receiver=receiver(),
        **{"dock-wedge": dock_wedge()},
    )
    result["film"] = box(0, 0, 0, p.film_length, p.fmt.film_width, p.film_thickness)
    return result
