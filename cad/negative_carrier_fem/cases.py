"""Explicit submodel cuts and fixture assumptions, in the CAD's mm axes."""

from itertools import pairwise

import build123d as bd
import numpy as np

from cad.negative_carrier_b.model import (
    Config,
    closure_clip,
    collar,
    holder_halves,
    index_latch,
)
from cad.negative_carrier_concepts.model import box


def geometry(name):
    if name in ("index", "index-pinned", "index-tip"):
        shape = index_latch(free_pad=1)
        if name == "index-tip":
            shape &= box(1.825, 27.25, -0.1, 1.25, 4.7, 1.4)
        return shape
    if name == "guide":
        shape = collar(Config("135", frame_count=4), guide_free=1)["collar-base"]
        return shape & box(-1, -19.4, -1.5, 26, 2.2, 0.81)
    if name == "roof":
        shape = collar(Config("135", frame_count=4), roof_free=1)["collar-cap"]
        return shape & box(-11.35, 20, 1.0, 25.3, 1.6, 1.7)
    if name in ("clip-catch", "clip-contact"):
        return closure_clip(0, 1, jaw_free=1)
    if name == "benchmark":
        return box(5, 0, -0.5, 10, 1, 1)
    raise ValueError(name)


def conditions(name, xyz):
    x, y, z = xyz.T
    if name in ("index", "index-pinned"):
        fixed = np.abs(x) >= 17.5 - 1e-6
        load = y >= 40
        return fixed, load, 2, 2.0 if name == "index-pinned" else 4.0
    if name == "index-tip":
        return x <= 1.6 + 1e-6, (np.abs(y - 25) < 1e-6) & (x > 2), 1, -0.2
    if name == "guide":
        return x <= -10.5 + 1e-6, np.abs(x - 11) < 1e-6, 2, -0.2
    if name == "roof":
        return (
            x <= -21.5 + 1e-6,
            (np.abs(x + 0.4) < 1e-6) & (np.abs(z - 1.1) < 1e-6),
            3,
            0.2,
        )
    if name == "clip-catch":
        return (
            y >= 24.5,
            (np.abs(x - 3.8) < 1e-6) & (y >= 22.19) & (y <= 23.41) & (z < -0.44),
            3,
            -0.3,
        )
    if name == "clip-contact":
        return y >= 26.6 - 1e-6, np.zeros(len(x), dtype=bool), 3, 0.1
    if name == "benchmark":
        return x < 1e-6, x > 10 - 1e-6, 3, 0.01
    raise ValueError(name)


NOTES = {
    "index": "Full relaxed latch. Anchor pads fully clamped; paddle guided in X/Z, displaced 4 mm in Y. Actual anchor friction/rotation is not calibrated.",
    "index-pinned": "Support sensitivity through 2 mm of the planned 4 mm stroke: rigid anchor pads rotate freely about their actual post centers in Z; X/Y/Z translations fixed. Nonlinear rigid-body MPCs, not a clamped support. The elastic strength screen is already exceeded by 2 mm.",
    "index-tip": "Opposing leaf cut from relaxed latch; rigid adjacent tooth/body, 0.2 mm lateral tip take-up.",
    "guide": "Guide leaf with its CAD root, cut above the lower mask. Root clamped; tip pushed 0.2 mm laterally. One leaf.",
    "roof": "One roof tongue and CAD root strip. Root clamped; low toe edge pushed 0.2 mm upwards, free to rotate. Two per collar.",
    "clip-catch": "Whole relaxed clip. Back spine held; catch tongue tip pressed 0.3 mm down. Jaw preload is a separate contact case.",
    "clip-contact": "Whole relaxed clip with the actual holder contact footprint. Contact excludes the positive catch: this isolates friction with the catch disengaged. Two back-corner nodes remove X/Y rigid-body motion; the C spine remains free to bend and normal seating is solved by contact.",
    "benchmark": "10 x 1 x 1 mm cantilever; 0.01 mm end translation; Euler-Bernoulli small-deflection reference.",
}


def coupon_cells(side=1):
    """Rigid contact footprint sampled from the actual central holder station.

    Grid lines follow every pocket/rail boundary in this region. The front
    lower rail ends at 23.7 mm, front lid at 23.6; the rear rails end at 24.
    The catch pocket is absent from the bottom contact plane. Only planar jaw
    friction is included: catch breakout is deliberately not part of this case.
    """
    parts = holder_halves(Config("135", frame_count=4))
    xs = [-5, -3.5, 1.2, 3.6, 3.8, 4.5, 5]
    ys = [22, 22.3, 23.3, 23.6, 23.7, 23.75, 24, 24.2, 24.4]
    cells = {"TOP": [], "BOTTOM": []}
    for name, part, z in [
        ("TOP", parts["lid"], 0.65 - 1e-5),
        ("BOTTOM", parts["base"], -0.45 + 1e-5),
    ]:
        for x0, x1 in pairwise(xs):
            for y0, y1 in pairwise(ys):
                if part.is_inside(((x0 + x1) / 2, side * (y0 + y1) / 2, z)):
                    cells[name].append((x0, x1, y0, y1))
    return cells


def mating_geometry(side=1, cut_y=20):
    """Local actual frame material; cut edge is a remote displacement fixture.

    This is a compliance sensitivity, not the full film/frame assembly. The
    source holder is in its nominal assembled state; move the lid down 0.1 mm
    for initial contact with the printed clip, then restore it in the solver.
    """
    parts = holder_halves(Config("135", frame_count=4))
    result = {}
    for name, key in [("TOP", "lid"), ("BOTTOM", "base")]:
        part = parts[key]
        if side == -1:
            part = part.mirror(bd.Plane.XZ)
        part = part & box(0, (cut_y + 24.4) / 2, -1.2, 12, 24.4 - cut_y, 2.6)
        if name == "TOP":
            part = bd.Pos(0, 0, -0.1) * part
        result[name] = part
    return result
