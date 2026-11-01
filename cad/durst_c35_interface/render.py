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
    measured = json.loads((folder / "measurements.json").read_text())
    p = {k: entry["value"] for k, entry in measured["parameters"].items()}
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
        ("SIDE / MEASURED PROFILE", list(meshes), (-250, -49, 9), (0, -49, 9), 81),
        (
            "HEAD UNDERSIDE",
            [n for n in meshes if n != "lower-support"],
            (115, 140, -155),
            (0, -49, 10),
            110,
        ),
        (
            "LOWER SUPPORT / FRONT AT BOTTOM",
            ["lower-support"],
            (0, -49, 200),
            (0, -49, -12),
            75,
        ),
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
            if i == 2:
                # Show the raised support boundary separately from the wider flange.
                edges = (
                    meshes[name]
                    .clean()
                    .extract_feature_edges(
                        feature_angle=20,
                        boundary_edges=True,
                        feature_edges=True,
                        non_manifold_edges=False,
                        manifold_edges=False,
                    )
                )
                plot.add_mesh(edges, color="#9eafba", line_width=1.5)
        if i == 0:
            # Foreground datum markers, using the measured neck and raised support.
            for y in (0, -p["neck_depth"]):
                plot.add_lines(
                    np.array(
                        [
                            [-60, y, -p["slot_gap"] - p["lower_height"]],
                            [-60, y, p["neck_height"]],
                        ]
                    ),
                    color="#00869b",
                    width=2,
                )
        plot.camera_position = [eye, centre, (0, -1, 0) if i == 2 else (0, 0, 1)]
        plot.enable_parallel_projection()
        plot.camera.parallel_scale = scale
        plot.add_text(title, position=(12, 805), font_size=12, color="#17394e")
        note = [
            f"P = Q = {p['neck_depth']:g} mm; cyan = shared end planes\nR = {p['flange_thickness']:g} mm; S = {p['flange_front_overhang']:g} mm; front at left\nOuter housing / rear flange extent provisional",
            "Six visible heads: sizes/positions provisional\nLight opening and optical position unmeasured",
            f"T = {p['lower_opening_width']:g} mm; U = {p['lower_opening_depth']:g} mm\nV = {p['lower_opening_front_offset']:g} mm; W = {p['lower_opening_left_offset']:g} mm\nBevel: {p['lower_bevel_drop']:g} mm drop / {p['lower_bevel_run']:g} mm run per side",
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
