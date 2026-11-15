"""Sample nominal small-feature points against slicer deposition footprints.

The footprint model uses the reported line width and rectangular layer height;
this checks intended deposition, not physical bead shape or bond strength.
"""

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from build123d import Pos, Rot

from cad import parts
from cad.parameters import parameters


def transform(p, kind):
    shape = parts.vessel(p) if kind == "vessel" else parts.guide(p)
    rotation = Rot(p["print_tilt"], 0, 0) if kind == "vessel" else Rot(180, 0, 0)
    s = rotation * shape
    if kind == "vessel":
        s += Pos(1, -3, 0) * parts.rounded_box(p["body_width"] - 2, 6, 0.4, 1)
    b = s.bounding_box()
    shift = np.array(
        [(180 - b.size.X) / 2 - b.min.X, (180 - b.size.Y) / 2 - b.min.Y, -b.min.Z]
    )
    a = math.radians(p["print_tilt"] if kind == "vessel" else 180)
    matrix = np.array(
        [[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]]
    )
    return lambda pts: np.array(pts) @ matrix.T + shift


def probes(p, kind):
    if kind == "vessel":
        x = np.linspace(7, p["body_width"] - 7, 240)
        y = np.linspace(5, p["body_depth"] - 5, 50)
        z = p["empty_level"] - p["ridge_height"] / 2
        t = p["ridge_projection"] / 2
        ridge = (
            [(v, p["wall"] + t, z) for v in x]
            + [(v, p["body_depth"] - p["wall"] - t, z) for v in x]
            + [(p["wall"] + t, v, z) for v in y]
            + [(p["body_width"] - p["wall"] - t, v, z) for v in y]
        )
        z = p["guide_seat"] + p["rim_height"] / 2
        rim = [
            (v, -1 + p["rim_wall"] / 2, z)
            for v in np.linspace(
                -p["end_ledge"] + 3, p["body_width"] + p["end_ledge"] - 3, 240
            )
        ] + [(v, p["body_depth"] - p["rim_wall"] / 2, z) for v in x]
        corners = []
        radius = p["inside_radius"]
        for cx, cy, start in [
            (p["wall"] + radius, p["wall"] + radius, 180),
            (p["body_width"] - p["wall"] - radius, p["wall"] + radius, 270),
            (
                p["body_width"] - p["wall"] - radius,
                p["body_depth"] - p["wall"] - radius,
                0,
            ),
            (p["wall"] + radius, p["body_depth"] - p["wall"] - radius, 90),
        ]:
            for angle in np.linspace(start, start + 90, 40):
                a = math.radians(angle)
                corners.append(
                    (
                        cx + (radius - t) * math.cos(a),
                        cy + (radius - t) * math.sin(a),
                        p["empty_level"] - p["ridge_height"] / 2,
                    )
                )
        return {
            "ridge_straights": ridge,
            "ridge_corners": corners,
            "locating_rim_straights": rim,
        }
    x = p["magnet_x"][1]
    right = p["body_width"] + p["end_ledge"] - p["rim_wall"] - p["guide_fit"]
    near = x + p["pocket_diameter"] / 2
    return {
        "slot_wiping_land": [
            (
                v,
                p["body_depth"] / 2 + side * (p["guide_gap"] / 2 + 0.2),
                p["guide_thickness"] - p["drip_depth"] - p["wiping_land"] / 2,
            )
            for v in np.linspace(
                (p["body_width"] - p["slit_length"]) / 2 + 3,
                (p["body_width"] + p["slit_length"]) / 2 - 3,
                120,
            )
            for side in (-1, 1)
        ],
        "magnet_edge_ligament": [
            (v, p["body_depth"] / 2, z)
            for v in np.linspace(near + 0.15, right - 0.15, 10)
            for z in np.linspace(0.4, p["pocket_depth"] - 0.4, 12)
        ],
        "magnet_pocket_floor": [
            (
                x + dx,
                p["body_depth"] / 2 + dy,
                p["pocket_depth"] + (p["guide_thickness"] - p["pocket_depth"]) / 2,
            )
            for dx in np.linspace(-2, 2, 12)
            for dy in np.linspace(-2, 2, 12)
        ],
    }


def check(gcode, p, kind):
    groups = probes(p, kind)
    convert = transform(p, kind)
    points = np.concatenate([convert(v) for v in groups.values()])
    need_z = (points[:, 2].min() - 0.3, points[:, 2].max() + 0.3)
    layers = defaultdict(list)
    position = np.zeros(3)
    width = 0.42
    h = 0.2
    feature = "Custom"
    e = 0.0
    relative = True
    for line in gcode.open():
        if line.startswith("; FEATURE:"):
            feature = line.split(":", 1)[1].strip()
        if line.startswith("; LINE_WIDTH:"):
            width = float(line.split(":")[1])
        if line.startswith("; LAYER_HEIGHT:"):
            h = float(line.split(":")[1])
        code = line.split(";")[0].strip()
        if code == "M83":
            relative = True
        if code == "M82":
            relative = False
        if code.startswith("G92 E"):
            e = float(code[5:])
        m = re.match(r"^(G[0123])\s", code)
        if not m:
            continue
        data = {k: float(v) for k, v in re.findall(r"([XYZEFIJ])(-?[\d.]+)", code)}
        q = np.array([data.get(k, position[i]) for i, k in enumerate("XYZ")])
        de = data.get("E", 0) if relative else data.get("E", e) - e
        if "E" in data:
            e = e + data["E"] if relative else data["E"]
        if (
            de > 0
            and ("X" in data or "Y" in data)
            and feature not in ["Custom", "Skirt", "Brim"]
            and not feature.startswith("Support")
            and need_z[0] < q[2] < need_z[1]
        ):
            if m[1] in ["G2", "G3"]:
                c = position[:2] + np.array([data.get("I", 0), data.get("J", 0)])
                r = np.linalg.norm(position[:2] - c)
                a = math.atan2(position[1] - c[1], position[0] - c[0])
                b = math.atan2(q[1] - c[1], q[0] - c[0])
                sweep = (
                    (b - a) % (2 * math.pi)
                    if m[1] == "G3"
                    else -((a - b) % (2 * math.pi))
                )
                theta = np.linspace(
                    a, a + sweep, max(2, math.ceil(abs(sweep) * r / 0.1))
                )
                xy = c + np.column_stack([np.cos(theta), np.sin(theta)]) * r
            else:
                xy = np.linspace(
                    position[:2],
                    q[:2],
                    max(2, math.ceil(np.linalg.norm(q[:2] - position[:2]) / 0.1)),
                )
            layers[(round(q[2], 5), round(h, 5))].append(
                np.column_stack([xy, np.full(len(xy), width)])
            )
        position = q
    coverage = np.zeros(len(points), dtype=bool)
    distances = np.full(len(points), np.inf)
    for (z, h), chunks in layers.items():
        selected = np.flatnonzero(
            (points[:, 2] >= z - h - 1e-5) & (points[:, 2] <= z + 1e-5)
        )
        if not len(selected):
            continue
        bead = np.concatenate(chunks)
        tree = cKDTree(bead[:, :2])
        dist, idx = tree.query(points[selected, :2], k=min(8, len(bead)))
        gap = (dist - bead[idx, 2] / 2).min(axis=1)
        distances[selected] = np.minimum(distances[selected], gap)
        coverage[selected] |= gap <= 0.055
    result = {}
    start = 0
    for name, pts in groups.items():
        end = start + len(pts)
        result[name] = {
            "points": len(pts),
            "covered_fraction": float(coverage[start:end].mean()),
            "worst_distance_beyond_bead_mm": float(max(0, distances[start:end].max())),
        }
        start = end
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--parameters", type=Path)
    a = parser.parse_args()
    p = json.loads(a.parameters.read_text()) if a.parameters else parameters()
    result = {
        k: check(a.folder / f"{k}_a/plate_1.gcode", p, k) for k in ["vessel", "guide"]
    }
    (a.folder / "feature-paths.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if any(
        v["covered_fraction"] < 1 for group in result.values() for v in group.values()
    ):
        raise RuntimeError(
            "At least one small-feature probe has no intended extrusion coverage"
        )
