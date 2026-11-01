"""Render the actual exported fixture geometry; no generated CAD illustration."""

import argparse
import json
from pathlib import Path

import build123d as bd
import numpy as np
import pyvista as pv

from .export import ROOT, sha


def render(folder, target):
    data = json.loads((folder / "manifest.json").read_text())
    native = json.loads((folder / "freecad-validation.json").read_text())
    assert native["geometry_passed"] and native["manifest_sha256"] == sha(
        folder / "manifest.json"
    )
    meshes = {}
    for name, record in data["parts"].items():
        path = folder / record["file"]
        assert sha(path) == record["sha256"]
        shape = bd.import_step(path)
        vertices, triangles = shape.tessellate(0.08)
        meshes[name] = pv.PolyData(
            np.asarray([list(v) for v in vertices]),
            np.column_stack([np.full(len(triangles), 3), triangles]).ravel(),
        )
    plot = pv.Plotter(
        shape=(1, 3), off_screen=True, window_size=(1920, 850), border=False
    )
    groups = [
        ("FRONT / RESTING STATE", list(meshes), (0, 250, -5), (0, -40, 8), 69),
        (
            "HEAD UNDERSIDE",
            [n for n in meshes if n != "lower-support"],
            (115, 140, -155),
            (0, -40, 10),
            98,
        ),
        ("LOWER SUPPORT / TOP", ["lower-support"], (125, 145, 145), (0, -40, -12), 98),
    ]
    for i, (title, names, eye, centre, scale) in enumerate(groups):
        plot.subplot(0, i)
        plot.set_background("#edf1f3")
        for name in names:
            color = (
                "#e4dfd4"
                if name == "head-shell"
                else "#bb7644"
                if name.startswith("screw-")
                else "#394651"
            )
            plot.add_mesh(
                meshes[name],
                color=color,
                smooth_shading=False,
                specular=0.15,
                ambient=0.3,
            )
        plot.camera_position = [eye, centre, (0, 0, 1)]
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = scale
        plot.add_text(title, position=(12, 805), font_size=12, color="#17394e")
        note = [
            "Head width 88.55 mm; rest gap about 6 mm\nL-O measured; depth/interior provisional\nHead cropped above shoulder",
            "Six visible heads: sizes/positions provisional\nLight opening and optical position unmeasured",
            "Outer form observed; interior unmeasured\nLowerDrop is prescribed movement, not FEA",
        ][i]
        plot.add_text(note, position=(12, 24), font_size=10, color="#17394e")
    target.parent.mkdir(parents=True, exist_ok=True)
    plot.screenshot(str(target))
    plot.close()
    (target.parent / "preview-provenance.json").write_text(
        json.dumps(
            {
                "renderer": "PyVista from verified build123d STEP solids",
                "manifest_sha256": sha(folder / "manifest.json"),
                "native_report_sha256": sha(folder / "freecad-validation.json"),
                "png_sha256": sha(target),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=ROOT / "build/durst-c35-interface"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs/durst-c35-interface/model-preview.png",
    )
    args = parser.parse_args()
    render(args.input, args.output)
