"""Render the native B-reps for the assembly guide."""

import numpy as np
import pyvista as pv

from .model import assembly


def render(p, output):
    output.mkdir(parents=True, exist_ok=True)
    for name, fmt, count, exploded, top in [
        ("holder-16x9", "16:9", 0, 0, False),
        ("holder-4x3", "4:3", 0, 0, False),
        ("test-covers", "16:9", 4, 16, False),
        ("five-bands", "16:9", 4, 0, True),
        ("five-bands-4x3", "4:3", 4, 0, True),
    ]:
        plot = pv.Plotter(off_screen=True, window_size=(1600, 1100))
        plot.set_background("#edf1f3")
        for key, shape in assembly(p, fmt, count, exploded).items():
            vertices, triangles = shape.tessellate(0.06)
            mesh = pv.PolyData(
                np.asarray([list(v) for v in vertices]),
                np.column_stack([np.full(len(triangles), 3), triangles]).ravel(),
            )
            color = (
                "#fff3d6"
                if key == "paper"
                else "#327a94"
                if key.startswith("mask")
                else ["#dfa144", "#d08a35", "#bd752c", "#a95f24"][
                    int(key.split("_")[1]) - 1
                ]
                if key.startswith("cover")
                else "#454e55"
            )
            plot.add_mesh(
                mesh, color=color, smooth_shading=False, ambient=0.35, specular=0.1
            )
        plot.camera_position = (
            [(0, 0, 350), (0, 0, 0), (0, 1, 0)]
            if top
            else [(210, -285, 300), (0, 0, 5), (0, 0, 1)]
        )
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = 135 if top else 145
        plot.screenshot(str(output / f"{name}.png"))
        plot.close()
