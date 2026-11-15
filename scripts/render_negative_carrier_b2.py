#!/usr/bin/env python3
"""Slow paired-angle B2 mechanism chapters from checked native STEP assets."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import build123d as bd
import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad.negative_carrier_b2.workflow import blend, transform
from cad.negative_carrier_fem.solver import sha

BUILD = ROOT / "build/negative-carrier-b2"
DOCS = ROOT / "docs/negative-carrier-b2/videos"
FPS = 20
SIZE = (1600, 900)
PANEL = (780, 710)
COLORS = {
    "base": "#315776",
    "lid": "#8aaec3",
    "film": "#c89d62",
    "sleeve": "#2b8c7f",
    "shoe": "#ed9f35",
    "screw": "#e9b552",
    "receiver": "#81919a",
    "dock-wedge": "#d7704e",
}


def font(size):
    return ImageFont.truetype(str(ROOT / "cad/fonts/LiberationSans-Bold.ttf"), size)


def mesh(shape):
    v, t = shape.tessellate(0.04)
    return pv.PolyData(
        np.array([list(x) for x in v]), np.column_stack([np.full(len(t), 3), t]).ravel()
    )


class View:
    def __init__(self, meshes, target, eye, scale, visible, alpha=None):
        self.plot = pv.Plotter(off_screen=True, window_size=PANEL)
        self.plot.set_background("#edf1f3")
        self.actors = {}
        for n, m in meshes.items():
            if n not in visible and not (n.startswith("mark-") and "film" in visible):
                continue
            self.actors[n] = self.plot.add_mesh(
                m,
                color=("#f5e4c9" if n.startswith("mark-number") else "#6d5138")
                if n.startswith("mark-")
                else COLORS.get(n, "#d7704e"),
                opacity=(alpha or {}).get(n, 1),
                smooth_shading=False,
                ambient=0.25,
                diffuse=0.65,
                specular=0.12,
            )
        self.plot.camera_position = [eye, target, (0, 0, 1)]
        self.plot.enable_parallel_projection()
        self.plot.camera.parallel_scale = scale

    def frame(self, pose):
        for n, a in self.actors.items():
            a.user_matrix = transform("film" if n.startswith("mark-") else n, pose)
        # screenshot() can return the previous framebuffer after actor changes.
        # Explicitly render every new pose before reading its pixels.
        self.plot.render()
        return Image.fromarray(self.plot.screenshot(return_img=True))


def chapters(m):
    m["phases"]
    names = list(m["parts"])
    carrier = [n for n in names if n not in ("receiver", "dock-wedge")]
    bench = ["base", "lid", "film"] + [n for n in names if n.startswith("wedge-")]

    def view(target, eye, scale, show, alpha=None):
        return (target, eye, scale, show, alpha)

    return [
        (
            "01-load",
            "Load the film and fit the lid",
            "Open film exits | supports touch margins and frame gaps",
            [(0, 1), (1, 1)],
            [
                view((0, 3, 3), (150, 200, 155), 105, bench),
                view((0, 17, 1), (18, 60, 30), 16, bench, {"lid": 0.35}),
            ],
        ),
        (
            "02-wedges",
            "Broad push-on wedges secure the film margins",
            "No snap catches or release tongues | pull straight off to release",
            [(2, 1), (2, -1), (2, 1)],
            [
                view((0, 24, 0), (22, 55, 23), 15, bench, {"lid": 0.3}),
                view((0, 24, 0), (-22, 48, -16), 15, bench, {"base": 0.3}),
            ],
        ),
        (
            "03-mask",
            "Pass the loaded holder through its format mask",
            "The mask stays at the optical axis while the frames move",
            [(3, 1)],
            [
                view((45, 15, 3), (200, 250, 170), 115, carrier),
                view(
                    (0, 1, 0), (0, -40, 100), 37, carrier, {"sleeve": 0.25, "lid": 0.45}
                ),
            ],
        ),
        (
            "04-dock",
            "Dock the sleeve and seat its broad wedge",
            "The rear stop and bevelled rails locate the sleeve; the wedge clamps it",
            [(4, 1), (5, 1), (6, 1)],
            [
                view((25, 25, 2), (180, 230, 140), 110, names),
                view(
                    (0, 78, -3),
                    (35, 115, -20),
                    20,
                    ["receiver", "sleeve", "dock-wedge"],
                    {"sleeve": 0.35, "receiver": 0.65},
                ),
            ],
        ),
        (
            "05-index",
            "Turn the screw to seat the rigid indexing shoe",
            "The tapered screw seat centers the shoe; three notch faces locate the frame",
            [(7, 1), (8, 1), (9, 1)],
            [
                view((0, 57, 15), (35, 98, 34), 26, names, {"sleeve": 0.18}),
                view(
                    (0, 57, 10),
                    (-18, 78, 7),
                    9,
                    names,
                    {"sleeve": 0.1, "shoe": 0.35, "base": 0.2},
                ),
            ],
        ),
        (
            "06-advance",
            "Lift clear, slide one frame, and seat again",
            "Coarse screw capture lifts the shoe; film remains clamped in its holder",
            # Use the actual two-stage release at frame 2 before returning.
            # Reversing the seating pose would skip capture-clearance take-up.
            [(10, 1), (11, 1), (12, 1), (13, 1), (10, -1), (7, 1)],
            [
                view((25, 18, 7), (190, 240, 180), 110, names),
                view((0, 56, 9), (27, 93, 34), 24, names, {"sleeve": 0.2}),
            ],
        ),
    ]


def run(preview=False):
    data = json.loads((BUILD / "manifest.json").read_text())
    if not preview:
        assert data["passed"], "Geometry check has not passed"
    assert data["source_sha256"] == sha(ROOT / "cad/negative_carrier_b2/model.py")
    m = next(m for m in data["formats"] if m["config"]["format"] == "135")
    meshes = {}
    for n, r in m["parts"].items():
        path = BUILD / r["file"]
        assert sha(path) == r["sha256"]
        meshes[n] = mesh(bd.import_step(path))
    fmt = m["format_data"]
    for i, x in enumerate(fmt["centers"]):
        meshes[f"mark-image-{i}"] = pv.Plane(
            center=(x, 0, 0.151),
            direction=(0, 0, 1),
            i_size=fmt["image_width"],
            j_size=fmt["image_height"],
            i_resolution=1,
            j_resolution=1,
        )
        meshes[f"mark-number-{i}"] = pv.Text3D(
            str(i + 1), depth=0.002, height=5, center=(x, 0, 0.154)
        )
    DOCS.mkdir(parents=True, exist_ok=True)
    records = []
    for slug, title, note, sequence, views in chapters(m):
        displays = [View(meshes, *v) for v in views]
        view_frames = [set() for _ in displays]
        target = DOCS / f"{slug}.mp4"
        if not preview:
            proc = subprocess.Popen(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgb24",
                    "-s",
                    f"{SIZE[0]}x{SIZE[1]}",
                    "-r",
                    str(FPS),
                    "-i",
                    "-",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "20",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(target),
                ],
                stdin=subprocess.PIPE,
            )
        count = 0
        for idx, direction in sequence:
            step = m["phases"][idx]
            samples = (
                [0.5] if preview else np.linspace(0, 1, round(step["seconds"] * FPS))
            )
            for t in samples:
                t = float(t)
                t = t * t * (3 - 2 * t)
                if direction < 0:
                    t = 1 - t
                pose = blend(step["start"], step["end"], t)
                canvas = Image.new("RGB", SIZE, "#edf1f3")
                draw = ImageDraw.Draw(canvas)
                draw.text((24, 20), title, font=font(34), fill="#213b4b")
                draw.text((24, 66), note, font=font(21), fill="#536a77")
                for i, v in enumerate(displays):
                    panel = v.frame(pose)
                    view_frames[i].add(hashlib.sha256(panel.tobytes()).hexdigest())
                    canvas.paste(panel, (10 + i * 800, 108))
                label = step["label"]
                if direction < 0:
                    label = (
                        "Return to the previous frame with the shoe raised"
                        if idx == 10
                        else "Pull the broad wedges straight off to release the lid"
                    )
                draw.text((24, 829), label, font=font(23), fill="#213b4b")
                draw.text(
                    (24, 865),
                    "Native CAD motion | translucent parts reveal contacts | preload deformation is assessed separately",
                    font=font(17),
                    fill="#536a77",
                )
                if preview:
                    canvas.save(DOCS / f"{slug}-preview.png")
                else:
                    proc.stdin.write(canvas.tobytes())
                count += 1
        for d in displays:
            d.plot.close()
        if not preview:
            assert all(len(frames) > 2 for frames in view_frames), (
                slug,
                "A geometry viewport did not animate",
            )
            proc.stdin.close()
            assert proc.wait() == 0
            subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(target), "-f", "null", "-"],
                check=True,
            )
            records.append(
                {
                    "file": target.name,
                    "frames": count,
                    "fps": FPS,
                    "sha256": sha(target),
                    "unique_geometry_frames_per_view": [len(s) for s in view_frames],
                }
            )
        print(slug, count, "frames", flush=True)
    if not preview:
        listing = DOCS / "chapters.txt"
        listing.write_text(
            "\n".join("file '" + r["file"] + "'" for r in records) + "\n"
        )
        target = DOCS / "B2-mechanisms-slow-multiple-angles.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-c",
                "copy",
                "-movflags",
                "+faststart",
                str(target),
            ],
            check=True,
        )
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(target), "-f", "null", "-"], check=True
        )
        (DOCS / "render-validation.json").write_text(
            json.dumps(
                {
                    "source_sha256": data["source_sha256"],
                    "manifest_sha256": sha(BUILD / "manifest.json"),
                    "chapters": records,
                    "combined_sha256": sha(target),
                    "decoded_all_frames": True,
                    "motion_is_prescribed": True,
                },
                indent=2,
            )
            + "\n"
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preview", action="store_true")
    run(p.parse_args().preview)
