"""Nominal rigid-body operating paths shared by collision checks and movies."""

from copy import deepcopy

import build123d as bd
import numpy as np

from .model import PITCH, parts


def transform(name, pose):
    t = pose.get(name, [0, 0, 0, 0])
    a = np.radians(t[3])
    c, s = np.cos(a), np.sin(a)
    m = np.eye(4)
    m[:3, :3] = [[c, -s, 0], [s, c, 0], [0, 0, 1]]
    center = np.array([0, 57, 0]) if name == "screw" else np.zeros(3)
    m[:3, 3] = np.array(t[:3]) + center - m[:3, :3] @ center
    return m


def place(shape, name, pose):
    x, y, z, a = pose.get(name, [0, 0, 0, 0])
    if a:
        shape = shape.rotate(bd.Axis((0, 57, 0), (0, 0, 1)), a)
    return bd.Pos(x, y, z) * shape


def blend(a, b, t):
    return {n: [x + (y - x) * t for x, y in zip(a[n], b[n])] for n in a}


def phases(p):
    names = list(parts(p))
    pose = {n: [0, 0, 0, 0] for n in names}
    moving = ["base", "lid", "film"] + [n for n in names if n.startswith("wedge-")]
    cartridge = [n for n in names if n not in ("receiver", "dock-wedge")]
    bench = moving
    steps = []

    def step(label, change, show, seconds=6):
        before = deepcopy(pose)
        for n, v in change.items():
            pose[n] = v
        steps.append(
            {
                "label": label,
                "start": before,
                "end": deepcopy(pose),
                "show": show,
                "seconds": seconds,
            }
        )

    pose["film"][2] = 12
    pose["lid"] = [0, 0, 16, 0]
    for n in names:
        if n.startswith("wedge-"):
            pose[n] = [
                0,
                7 * int(n.rsplit("-", 1)[-1]) if not n.endswith("--1") else -7,
                0,
                0,
            ]
    step("Place film on the margin supports", {"film": [0, 0, 0, 0]}, bench)
    step("Lower the lid straight onto the film margins", {"lid": [0, 0, 0, 0]}, bench)
    step(
        "Push the broad wedges onto the recessed frame edges",
        {n: [0, 0, 0, 0] for n in names if n.startswith("wedge-")},
        bench,
        8,
    )
    # Reposition between chapters, not an undocumented installation motion.
    for n in moving:
        pose[n][0] += p.length / 2 + 28
    pose["screw"] = [0, 0, 4.8, 4.8 / PITCH * 360]
    pose["shoe"] = [0, 0, 4.4, 0]
    step(
        "Slide the loaded strip through its matching mask sleeve",
        {n: [-p.fmt.centers[0], 0, 0, 0] for n in moving},
        cartridge,
        10,
    )
    for n in cartridge:
        pose[n][1] += 35
    pose["dock-wedge"] = [-4, 60, 0, 0]
    step(
        "Slide the format sleeve into the receiver",
        {n: [*pose[n][:1], pose[n][1] - 35, *pose[n][2:]] for n in cartridge},
        names,
        9,
    )
    step("Fit the broad docking wedge", {"dock-wedge": [-4, 0, 0, 0]}, names, 6)
    step("Seat the docking wedge", {"dock-wedge": [0, 0, 0, 0]}, names, 4)
    step(
        "Turn the coarse screw to seat the indexing shoe",
        {"screw": [0, 0, 0, 0], "shoe": [0, 0, 0, 0]},
        names,
        10,
    )
    for frame in range(1, p.fmt.frames):
        step(
            "Loosen: flange first takes up its capture clearance",
            {"screw": [0, 0, 0.4, 0.4 / PITCH * 360]},
            names,
            3,
        )
        step(
            "Continue turning: lift the rigid shoe clear",
            {"screw": [0, 0, 4.8, 4.8 / PITCH * 360], "shoe": [0, 0, 4.4, 0]},
            names,
            8,
        )
        step(
            f"Slide to frame {frame + 1}",
            {n: [-p.fmt.centers[frame], 0, 0, 0] for n in moving},
            names,
            10,
        )
        step(
            f"Seat frame {frame + 1}",
            {"screw": [0, 0, 0, 0], "shoe": [0, 0, 0, 0]},
            names,
            10,
        )
    return steps
