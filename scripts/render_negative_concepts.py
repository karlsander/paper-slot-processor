#!/usr/bin/env python3
"""Render the checked layout solids; colors and transparent covers explain parts."""

import argparse
import hashlib
import json
from pathlib import Path

import build123d as bd
import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont

COLORS = {
    "receiver": "#ccd3d7",
    "gate": "#2b8c88",
    "sled": "#346781",
    "lid": "#6b97a8",
    "film": "#d4a05f",
    "case": "#79aaa5",
    "control": "#346781",
}


def font(size):
    return ImageFont.truetype(
        str(Path(__file__).resolve().parents[1] / "cad/fonts/LiberationSans-Bold.ttf"),
        size,
    )


def mesh(shape):
    vertices, triangles = shape.tessellate(0.06)
    return pv.PolyData(
        np.array([list(v) for v in vertices]),
        np.column_stack([np.full(len(triangles), 3), triangles]).ravel(),
    )


def view(out, model, exploded=False):
    plotter = pv.Plotter(off_screen=True, window_size=(1440, 390))
    plotter.set_background("#f3f5f4")
    manifest = json.loads((out / "manifest.json").read_text())
    fmt = manifest["formats"][model["format"]]
    dx = -fmt["centers"][(fmt["frames"] - 1) // 2]
    for record in model["parts"]:
        path = out / record["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
        shape = bd.import_step(path)
        dz = 22 if exploded and record["name"] == "lid" else 0
        actor = plotter.add_mesh(
            mesh(shape),
            color=COLORS[record["role"]],
            opacity=0.28
            if record["role"] == "case"
            else (0.65 if record["role"] == "gate" and not exploded else 1),
            smooth_shading=False,
            ambient=0.4,
            specular=0.1,
        )
        actor.position = (dx if record["motion"] == "moving" else 0, 0, dz)
    # Surface markings represent image areas only, never extra plastic.
    for i, x in enumerate(fmt["centers"]):
        face = bd.Pos(x + dx, 0, 0.081) * bd.Rectangle(
            fmt["image_width"], fmt["image_height"]
        )
        plotter.add_mesh(mesh(face), color="#815e43", ambient=0.7)
    plotter.camera_position = [(140, -230, 250), (0, 0, 0), (0, 0, 1)]
    plotter.enable_parallel_projection()
    plotter.camera.parallel_scale = 87 if model["variant"] != "cassette" else 136
    plotter.reset_camera_clipping_range()
    plotter.render()
    result = Image.fromarray(plotter.screenshot(return_img=True))
    plotter.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=Path("build/negative-carrier-concepts")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("docs/negative-carrier-concepts")
    )
    args = parser.parse_args()
    out, dest = args.input, args.output
    dest.mkdir(exist_ok=True, parents=True)
    manifest = json.loads((out / "manifest.json").read_text())
    checks = json.loads((out / "freecad-validation.json").read_text())
    assert (
        checks["passed"]
        and checks["manifest_sha256"]
        == hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest()
    )
    board = Image.new("RGB", (1440, 1640), "#f3f5f4")
    draw = ImageDraw.Draw(board)
    draw.text((44, 22), "A new negative carrier system", font=font(34), fill="#233d4b")
    draw.text(
        (44, 67),
        "Three native CAD layout concepts · printed parts · six-frame 35 mm holder",
        font=font(22),
        fill="#526572",
    )
    rows = [
        (
            "drawer-135",
            "A  /  Separate mask drawer",
            "Simplest build. Swap one mask when changing format; slide the loaded holder.",
            "Mask and holder are separate items. A wrong mask can expose neighbouring frames.",
        ),
        (
            "collar-135",
            "B  /  Captive mask collar",
            "The mask docks and stays put. The loaded holder slides through it. Preferred concept.",
            "Exploded lid view. Open the collar cap before the holder; closure details remain to design.",
        ),
        (
            "cassette-135",
            "C  /  Enclosed translating cassette",
            "Thumbwheel moves the holder inside a protective case; an independent latch locates it.",
            "About 450 mm case length for six frames. Transparent cover; wheel is an allowance only.",
        ),
    ]
    for row, (name, title, subtitle, detail) in enumerate(rows):
        y = 125 + row * 480
        model = next(m for m in manifest["models"] if m["name"] == name)
        board.paste(view(out, model, exploded=row == 1), (0, y + 70))
        draw.text((44, y), title, font=font(29), fill="#233d4b")
        draw.text((44, y + 39), subtitle, font=font(21), fill="#526572")
        draw.text((44, y + 442), detail, font=font(19), fill="#526572")
    draw.rectangle((0, 1575, 1440, 1640), fill="#233d4b")
    draw.text(
        (44, 1593),
        "Blue: holder   Amber: film   Teal: mask/case   Grey: receiver   |   Layouts only - C35 fit and precision unverified",
        font=font(20),
        fill="#ffffff",
    )
    board.save(dest / "concepts.png")
    print(dest / "concepts.png")


if __name__ == "__main__":
    main()
