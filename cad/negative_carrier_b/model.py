"""Native B1 parts. Coordinates are mm; the optical axis is at (0,0,0)."""

from dataclasses import dataclass, replace
from functools import lru_cache
from math import isfinite

import build123d as bd

from cad.negative_carrier_concepts.model import box, ring
from cad.negative_carrier_concepts.spec import FORMATS


@dataclass(frozen=True)
class Config:
    format: str = "135"
    film_thickness: float = 0.15
    frame_pitch: float | None = None
    frame_count: int | None = None
    image_width: float | None = None
    film_tail_frames: int = 2  # demonstration film only; never changes printed parts

    def __post_init__(self):
        if self.format not in FORMATS or not 0 < self.film_thickness < 0.2:
            raise ValueError("Unknown format or film thickness outside (0, 0.2) mm")
        if (
            not isinstance(self.fmt.frames, int)
            or isinstance(self.fmt.frames, bool)
            or self.fmt.frames < 2
            or not isfinite(self.fmt.demo_pitch)
            or not isfinite(self.fmt.image_width)
            or not 0.4 < self.fmt.image_width <= 36
            or self.fmt.demo_pitch < 15
            or self.fmt.demo_pitch - self.fmt.image_width < 1.0
            or not isinstance(self.film_tail_frames, int)
            or isinstance(self.film_tail_frames, bool)
            or self.film_tail_frames < 0
        ):
            raise ValueError(
                "Need two or more frames, at least 1 mm between images, and nonnegative integer tail frames"
            )

    @property
    def fmt(self):
        f = FORMATS[self.format]
        return replace(
            f,
            demo_pitch=f.demo_pitch if self.frame_pitch is None else self.frame_pitch,
            frames=f.frames if self.frame_count is None else self.frame_count,
            image_width=f.image_width if self.image_width is None else self.image_width,
        )

    @property
    def length(self):
        return max(self.fmt.length, self.fmt.travel + 54)

    @property
    def image_span(self):
        return self.fmt.travel + self.fmt.image_width

    @property
    def film_length(self):
        return self.image_span + 4 + 2 * self.film_tail_frames * self.fmt.demo_pitch

    @property
    def film_centers(self):
        return tuple(
            self.fmt.centers[0] + i * self.fmt.demo_pitch
            for i in range(
                -self.film_tail_frames, self.fmt.frames + self.film_tail_frames
            )
        )


def prism(points, z, height):
    if (
        sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(points, points[1:] + points[:1]))
        < 0
    ):
        points = list(reversed(points))
    return bd.Pos(0, 0, z) * bd.extrude(bd.Polygon(*points, align=None), amount=height)


def holder_halves(p):
    """Monolithic lower and upper frames; a larger printer is user-approved."""
    opening = p.image_span + 0.8
    base = ring(p.length, 48, opening, p.fmt.image_height + 0.8, -1.1, 1.1)
    lid = ring(p.length, 48, opening, p.fmt.image_height + 0.8, 0.2, 1.1)
    # Local 0.05 mm fingers/contact lands close the nominal film space to 0.15.
    contact = ring(
        opening + 3,
        p.fmt.film_width,
        opening,
        p.fmt.image_height + 0.8,
        p.film_thickness,
        0.25 - p.film_thickness,
    )
    lid += contact
    # Narrow lands support the nominal gaps between images on both sides.
    for a, b in zip(p.fmt.centers, p.fmt.centers[1:]):
        width = b - a - p.fmt.image_width - 0.4
        base += box((a + b) / 2, 0, -1.1, width, 48, 1.1)
        lid += box((a + b) / 2, 0, p.film_thickness, width, 48, 1.3 - p.film_thickness)
    # Film side datums are outside image areas; they cannot act as sprocket teeth.
    for x in (-p.length / 2 + 15, p.length / 2 - 15):
        base += box(x, p.fmt.film_width / 2 + 0.4, 0, 6, 0.8, 0.15)
    # The index rail is only on the lower frame. All pockets face the operator.
    base += box(0, 26, -1.1, p.length - 4, 4.4, 2.4)
    for x in p.fmt.centers:
        base -= box(x, 27, -1.3, 4.4, 4.4, 3)
    lid -= box(0, 24, 0, p.length + 1, 0.8, 3)
    # Retaining ears keep the closed collar captive outside the film path.
    for x in (-p.length / 2 + 1, p.length / 2 - 1):
        base += box(x, 0, -1.1, 2, 62, 2.4)
        base -= box(x, 0, 0, 2.2, p.fmt.film_width + 0.8, 1.5)
        lid -= box(x, 0, 0, 2.4, 70, 3)
    # Continue the image clearance through BOTH ends. A longer strip's image
    # areas must not be squeezed between the former solid end lands. Only the
    # film margins remain supported here; the interframe bars stay unchanged.
    for side in (-1, 1):
        inner = opening / 2
        outer = p.length / 2 + 0.5
        relief = box(
            side * (inner + outer) / 2,
            0,
            -1.2,
            outer - inner,
            p.fmt.image_height + 0.8,
            3,
        )
        base -= relief
        lid -= relief
        # Planar lead-outs on the margin ledges avoid a square edge at the exit.
        # These are geometric chamfers; printed edge finish still needs checking.
        edge = p.length / 2
        points = [
            (side * (edge - 1), 0),
            (side * (edge + 0.1), -0.33),
            (side * (edge + 0.1), 1.5),
            (side * (edge - 1), 1.5),
        ]
        cut = bd.extrude(
            bd.Plane.XZ * bd.Polygon(*points, align=None),
            amount=p.fmt.film_width + 0.8,
            dir=(0, 1, 0),
        )
        base -= bd.Pos(0, -(p.fmt.film_width + 0.8) / 2, 0) * cut
        edge -= 2.2  # the lid is set back from the retaining ears
        points = [
            (side * (edge - 1), -0.1),
            (side * (edge + 0.1), -0.1),
            (side * (edge + 0.1), p.film_thickness + 0.33),
            (side * (edge - 1), p.film_thickness),
        ]
        cut = bd.extrude(
            bd.Plane.XZ * bd.Polygon(*points, align=None),
            amount=p.fmt.film_width + 0.8,
            dir=(0, 1, 0),
        )
        lid -= bd.Pos(0, -(p.fmt.film_width + 0.8) / 2, 0) * cut
    # Continuous underside channel provides two Y datums without obstructing
    # the closure clips or the film. It also prevents yaw during frame advance.
    base -= box(0, -19.5, -1.2, p.length + 1, 1.4, 0.55)
    # Recesses let the C clips capture BOTH halves without increasing the moving
    # envelope above 2.4 mm. The central pair helps clamp a long strip evenly.
    stations = closure_stations(p)
    for x in stations:
        width = 10
        for side in (-1, 1):
            base -= box(x, side * 23.1, -1.2, width + 0.4, 2.2, 0.75)
            lid -= box(x, side * 23.1, 0.65, width + 0.4, 2.2, 1)
            base -= box(x + 2.4, side * 22.8, -0.6, 2.4, 1.0, 0.45)
    pieces = {}
    for x in stations:
        width = 10
        for side in (-1, 1):
            # Open side faces the film, and the channel captures recessed rails.
            clip = closure_clip(x, side)
            # Index rail relief on the front clips prevents the clip crossing it.
            if side == 1:
                base -= box(x, 26.0, -1.2, width + 0.4, 4.6, 3)
            pieces[f"closure-{x:g}-{side}"] = clip
    pieces["base"] = base
    pieces["lid"] = lid
    return pieces


def closure_stations(p):
    middle = 0 if p.fmt.frames % 2 == 0 else p.fmt.demo_pitch / 2
    return (-p.length / 2 + 8, middle, p.length / 2 - 8)


def closure_clip(x, side, release=0, jaw_free=0):
    """C clip with a positive underside catch; prescribed lip deflection in mm."""
    # The printed free jaw is 0.1 mm narrower than the imposed seated gap.
    # Spreading it during assembly supplies the intended film-clamping preload.
    # Forces and creep are not solved by this geometric representation.
    squeeze = 0.1 * jaw_free
    clip = box(x, side * 24.3, -1.1, 10, 4.6, 2.4 - squeeze)
    clip -= box(x, side * 22.2, -0.45, 11, 4.4, 1.1 - squeeze)
    # A lengthwise spring tongue (7.8 mm), isolated from the short C-channel lip.
    clip -= box(x + 0.5, side * 22.8, -1.2, 8, 1.9, 0.76)
    points = []
    for i in range(17):
        t = i / 16
        points.append((x - 4 + 7.8 * t, -0.45 - release * t * t))
    outline = points + [(px, pz - 0.4) for px, pz in reversed(points)]
    profile = bd.Plane.XZ * bd.Polygon(*outline, align=None)
    tongue = bd.extrude(profile, amount=1.2, dir=(0, 1, 0))
    clip += bd.Pos(0, side * 22.8 - 0.6, 0) * tongue
    # The catch sits near the free end; deflection is prescribed, not FEA.
    dz = release * (6.4 / 7.8) ** 2
    clip += box(x + 2.4, side * 22.8, -0.46 - dz, 1.6, 0.6, 0.21)
    return clip


def collar(p, guide_free=0, roof_free=0):
    aw, ah = p.fmt.aperture
    lower = ring(48, 66, aw, ah, -2.3, 0.8)
    cap = ring(48, 66, aw, ah, 1.8, 0.8)
    # Two roof tongues keep the holder on its three lower support pads. They
    # press the lid outside the film and prevent lifting out of the guide groove.
    # The relaxed print has 0.2 mm extra deflection; assembly shapes are imposed.
    for y in (-20, 20):
        cap -= box(-9.5, y, 1.7, 23, 2.2, 1)
        points = []
        for i in range(17):
            t = i / 16
            points.append((-22 + 22 * t, 1.8 - (0.5 + 0.2 * roof_free) * t * t))
        outline = points + [(x, z + 0.5) for x, z in reversed(points)]
        profile = bd.Plane.XZ * bd.Polygon(*outline, align=None)
        cap += bd.Pos(0, y - 0.8, 0) * bd.extrude(profile, amount=1.6, dir=(0, 1, 0))
        cap += box(0.4, y, 1.3 - 0.2 * roof_free, 1.6, 1.6, 0.6)
    # Outside the frame travel envelope: wall rails and keyed cap seating.
    for y in (-32, 32):
        lower += box(0, y, -2.3, 48, 2, 4.1)
    lower -= box(0, 32, -0.2, 9.0, 5, 1.6)
    # Three lower hard pads define the film plane; upper surfaces remain clear.
    for x, y in ((-18, -21), (18, -21), (0, 21)):
        lower += box(x, y, -1.5, 3, 2, 0.4)
    for x in (-18, 18):
        lower += box(x, -19.7, -1.5, 3, 1, 0.8)
    # A long, thin guide leaf takes up the opposite groove wall. guide_free=1
    # is the printable relaxed shape; 0 is the nominal seated deformation.
    lower += box(-12, -19.6, -1.5, 3, 0.5, 0.8)
    points = []
    for i in range(17):
        t = i / 16
        points.append((-12 + 23 * t, -19.6 + (0.55 + 0.2 * guide_free) * t * t))
    outline = [(x, y - 0.25) for x, y in points] + [
        (x, y + 0.25) for x, y in reversed(points)
    ]
    lower += prism(outline, -1.1, 0.4)
    # Dock feet engage the receiver below the moving holder.
    for x in (-22.5, 22.5):
        lower += box(x, 0, -2.7, 3, 61, 0.5)
    # Front shelf supports the separate printed index flexure and release paddle.
    lower += box(0, 38.5, -2.3, 46, 15, 1.8)
    cap += box(0, 36, 1.8, 46, 8, 0.8)
    # Four printed quarter-turn locks capture the cap. Their shafts locate only
    # loosely: the planar ledges, rear stop and side pad are the working datums.
    keys = {}
    for x in (-18, 18):
        for y in (-31, 31):
            lower += box(x, y, -2.3, 7.4, 3.2, 4.1)
            lower -= keyhole(x, y, -3, 6.3, 1.9, 6)
            cap -= keyhole(x, y, 1.5, 6.3, 3.3, 2)
            keys[f"cap-lock-{x:g}-{y:g}"] = quarter_lock(x, y, -2.8, 2.6)
    for x in (-20, 20):
        lower += box(x, 36, -0.5, 5, 5, 0.45)
        lower += bd.Pos(x, 36, -0.1) * bd.Cylinder(
            1, 1.4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        cap += box(x, 36, 1.2, 5, 5, 0.7)
        cap -= bd.Pos(x, 36, 1.1) * bd.Cylinder(
            1.2, 2, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
    for x in (-18, 18):
        lower += box(x, 46, -2.3, 9, 8, 1.8)
        hole = keyhole(x, 48, -3, 6.3, 3.3, 4)
        if x > 0:
            hole = hole.rotate(bd.Axis((x, 48, 0), (0, 0, 1)), 90)
        lower -= hole
        pin = quarter_lock(x, 48, -4.9, -0.4)
        # Eccentric shoulders seat the collar against the rear and left datums.
        # They model nominal contact, not torque or elastic clamping preload.
        pin += bd.Pos(x + (-0.2 if x < 0 else 0.2), 48, -2.3) * bd.Cylinder(
            1.45, 1.8, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
        keys[f"dock-lock-{x:g}"] = pin
    return {"collar-base": lower, "collar-cap": cap} | keys


def keyhole(x, y, z, length, width, height):
    return box(x, y, z, length, width, height) + bd.Pos(x, y, z) * bd.Cylinder(
        1.2, height, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )


def quarter_lock(x, y, bottom, top):
    shape = bd.Pos(x, y, bottom) * bd.Cylinder(
        1, top + 0.6 - bottom, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
    )
    shape += box(x, y, bottom, 5.6, 1.6, 0.5)
    shape += box(x, y, top, 5.6, 3, 0.6)
    return shape


def index_latch(release=0, free_pad=0):
    """Prescribed planar flexure displacement, not a solved elastic deformation."""
    body = box(-0.3, 31.2 + release, -0.05, 3.8, 12.4, 1.2)
    body += box(0, 41 + release, -0.05, 14, 8, 1.2)
    # Hard tooth face at X=-2.2; a thin opposing leaf takes up nominal clearance.
    tip = 2.2 + 0.2 * free_pad
    body += prism(
        [
            (1.25, 28.5 + release),
            (1.6, 28.5 + release),
            (tip, 25.0 + release),
            (tip - 0.35, 25.0 + release),
        ],
        -0.05,
        1.2,
    )
    for side in (-1, 1):
        points = []
        for i in range(17):
            t = i / 16
            x = side * (20 - 18.5 * t)
            y = 36 + release * (t * t * (3 - 2 * t))
            points.append((x, y))
        outline = [(x, y - 0.35) for x, y in points] + [
            (x, y + 0.35) for x, y in reversed(points)
        ]
        body += prism(outline, 0, 0.8)
        body += box(side * 20, 36, -0.05, 5, 5, 1.2)
        body -= bd.Pos(side * 20, 36, -1) * bd.Cylinder(
            1.15, 4, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)
        )
    return body


def receiver():
    # The low side bridges pass outside the 90 mm hypothetical mixing box.
    rear = box(0, -47, -1.2, 94.6, 28, 2.6)
    shape = rear + box(0, 48, -4.4, 94.6, 6, 1.2)
    for x in (-46.5, 46.5):
        shape += box(x, 3, -3.2, 1.6, 90, 1.2)
        shape += box(x, -34, -3.2, 1.6, 2, 4.6)
    for x in (-22.5, 22.5):
        shape += box(x, 7, -3.2, 3.8, 82, 0.5)
        shape += box(x, -33.4, -3.2, 3.8, 0.8, 2)
    for x in (-24.6, 24.6):
        shape += box(x, 7, -3.2, 0.6, 82, 1.3)
    # Rear station references and a side datum, kept below the moving holder.
    for y in (-26, 26):
        shape += box(-24.2, y, -2.7, 0.4, 6, 0.4)
    for x in (-18, 18):
        hole = keyhole(x, 48, -5, 6.3, 1.9, 3)
        if x > 0:
            hole = hole.rotate(bd.Axis((x, 48, 0), (0, 0, 1)), 90)
        shape -= hole
    return shape


DEFAULT_CONFIG = Config()


@lru_cache(maxsize=8)
def parts(p=DEFAULT_CONFIG):
    result = holder_halves(p) | collar(p)
    result["index-latch"] = index_latch()
    result["receiver"] = receiver()
    result["film"] = box(0, 0, 0, p.film_length, p.fmt.film_width, p.film_thickness)
    return result


def role(name):
    if name.startswith("base"):
        return "holder-base"
    if name.startswith("lid"):
        return "holder-lid"
    if name.startswith("closure"):
        return "closure"
    if name == "film":
        return "film"
    if name == "receiver":
        return "receiver"
    return "collar"
