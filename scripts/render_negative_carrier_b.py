#!/usr/bin/env python3
"""Render checked B1 solids along the same prescribed paths used by FreeCAD."""

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import build123d as bd
import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cad.negative_carrier_b.model import Config
from cad.negative_carrier_b.motion import interpolate, placement
from cad.negative_carrier_concepts.model import box

COLORS = {
    "base": "#315776",
    "lid": "#6f9ab6",
    "film": "#c89959",
    "collar-base": "#237f72",
    "collar-cap": "#48a28e",
    "index-latch": "#e8a94c",
    "receiver": "#8d9da7",
    "fixture-head": "#abb6bd",
    "fixture-stage": "#b6bfc3",
    "fixture-stop": "#b6bfc3",
}
BACKGROUND = "#edf1f3"
INK = "#213b4b"
MUTED = "#536a77"


def font(size):
    return ImageFont.truetype(str(ROOT / "cad/fonts/LiberationSans-Bold.ttf"), size)


def poly(shape):
    vertices, triangles = shape.tessellate(0.05)
    return pv.PolyData(
        np.array([list(v) for v in vertices]),
        np.column_stack([np.full(len(triangles), 3), triangles]).ravel(),
    )


def matrix(translation, pivot, angle):
    t = math.radians(angle)
    c, s = math.cos(t), math.sin(t)
    r = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    p = np.array([*pivot, 0])
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = np.array(translation) + p - r @ p
    return m


class Scene:
    def __init__(self, out, manifest, model, size, mode, detail=None):
        self.out, self.manifest, self.model = out, manifest, model
        self.p = Config(**model["config"])
        self.mode = mode
        self.detail = detail
        self.plot = pv.Plotter(off_screen=True, window_size=size)
        self.plot.set_background(BACKGROUND)
        self.cache = {}
        self.actors = {}
        self.active = {}
        self.markings = []
        self.parts = {n: r["asset"] for n, r in model["parts"].items()}
        self.parts.update(
            {
                k.split("/")[-1]: k
                for k in manifest["assets"]
                if k.startswith("fixture/")
            }
        )
        for name, key in self.parts.items():
            opacity = (
                0.16
                if name == "fixture-head"
                else (0.32 if name == "collar-cap" and detail else 1)
            )
            self.actors[name] = self.plot.add_mesh(
                self.mesh(key),
                color=COLORS.get(name, "#d8ad70"),
                opacity=opacity,
                smooth_shading=False,
                ambient=0.25,
                diffuse=0.65,
                specular=0.12,
                specular_power=18,
            )
            self.active[name] = key
        for i, x in enumerate(self.p.film_centers):
            face = pv.Plane(
                center=(x, 0, self.p.film_thickness + 0.002),
                direction=(0, 0, 1),
                i_size=self.p.fmt.image_width,
                j_size=self.p.fmt.image_height,
                i_resolution=1,
                j_resolution=1,
            )
            self.markings.append(
                self.plot.add_mesh(face, color="#75583f", ambient=0.5, diffuse=0.4)
            )
            number_in_holder = i - self.p.film_tail_frames + 1
            if not 1 <= number_in_holder <= self.p.fmt.frames:
                continue  # tail images stay visible without misleading slot numbers
            number = pv.Text3D(
                str(number_in_holder),
                depth=0.002,
                height=5,
                center=(x, 0, self.p.film_thickness + 0.006),
            )
            number.rotate_z(
                180, point=(x, 0, self.p.film_thickness + 0.006), inplace=True
            )
            self.markings.append(
                self.plot.add_mesh(number, color="#efd7a1", ambient=0.8, diffuse=0.1)
            )
        if detail == "exit":
            x = -self.p.fmt.centers[0] - self.p.length / 2
            self.plot.camera_position = [(x - 36, 65, 52), (x + 3, 0, 0), (0, 0, 1)]
            scale = 25
        elif detail == "index":
            self.plot.camera_position = [(0, 91, 73), (0, 31, 0), (0, 0, 1)]
            scale = 20
        elif detail == "clip":
            x = -self.p.fmt.centers[0]
            self.plot.camera_position = [(x + 6, 53, -28), (x, 23, -0.4), (0, 0, 1)]
            scale = 8
        elif mode in ("load", "reposition"):
            x = -self.p.fmt.centers[0]
            self.plot.camera_position = [(x + 25, 350, 275), (x, 0, 19), (0, 0, 1)]
            scale = max(100, (self.p.film_length + self.p.fmt.demo_pitch) / 3.6)
        elif mode == "dock":
            self.plot.camera_position = [(190, 420, 285), (65, 35, 0), (0, 0, 1)]
            scale = max(111, self.p.film_length / 3.4)
        else:
            self.plot.camera_position = [(0, 350, 285), (0, 0, 0), (0, 0, 1)]
            scale = max(79, (self.p.film_length + self.p.fmt.travel) / 3.6)
        self.plot.enable_parallel_projection()
        self.plot.camera.parallel_scale = scale

    def mesh(self, key):
        if key not in self.cache:
            record = self.manifest["assets"][key]
            path = self.out / record["file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]
            shape = bd.import_step(path)
            if key == "fixture/fixture-head":
                shape = shape & box(0, 0, -20, 300, 300, 28)
            self.cache[key] = poly(shape)
        return self.cache[key]

    def draw(self, state):
        for name, actor in self.actors.items():
            fixture = name.startswith("fixture")
            visible = (
                state.machine if fixture or name == "receiver" else state.cartridge
            )
            if self.detail and (fixture or name == "receiver"):
                visible = False
            actor.visibility = visible
            key = self.parts[name]
            if name == "index-latch":
                key = self.model["variants"][f"index-{round(state.index_release)}"]
            elif name.startswith("closure-"):
                key = self.model["variants"][
                    f"{name}-{round(state.clips_release / 0.075)}"
                ]
            if self.active[name] != key:
                actor.mapper.dataset = self.mesh(key)
                self.active[name] = key
            d, p, a = placement(name, self.p, state)
            actor.user_matrix = matrix(d, p, a)
        for actor in self.markings:
            actor.visibility = state.cartridge
            actor.position = (
                state.holder_x + state.film_x,
                state.assembly_y,
                state.film_z,
            )
        self.plot.reset_camera_clipping_range()
        self.plot.render()
        return Image.fromarray(self.plot.screenshot(return_img=True))

    def close(self):
        self.plot.close()


def duration(phase):
    a, b = phase["start"], phase["end"]
    g = phase["group"]
    if g == "advance":
        if a["holder_x"] != b["holder_x"]:
            return 2.6 if abs(a["holder_x"] - b["holder_x"]) > 50 else 1.5
        if a["index_release"] != b["index_release"]:
            return 0.65
        return 1.2
    if g == "install":
        return 3 if a["receiver_y"] != b["receiver_y"] else 1.2
    if g == "dock":
        return 3.5 if a["assembly_y"] != b["assembly_y"] else 1.5
    if a["clips_release"] != b["clips_release"]:
        return 0.8
    return 2.2


def render(out, dest, manifest, model, mode, fps=24, quick=False):
    groups = {
        "load": ("load",),
        "dock": ("install", "dock"),
        "advance": ("advance",),
        "reposition": ("reposition",),
    }[mode]
    phases = [p for p in model["phases"] if p["group"] in groups]
    scene = Scene(out, manifest, model, (1440, 700), mode)
    detail = (
        Scene(
            out,
            manifest,
            model,
            (420, 280),
            mode,
            detail={"load": "clip", "advance": "index", "reposition": "exit"}[mode],
        )
        if mode != "dock"
        else None
    )
    titles = {
        "load": f"Clamp {model['format_data']['frames']} positions - film exits both ends",
        "reposition": "Reposition a longer strip at the workbench",
        "dock": "Install the receiver, then dock the cartridge",
        "advance": (
            "Slide, click, and return to the same frame"
            if model["format"] == "135"
            else "110: one small frame at a time"
        ),
    }
    name = f"{model['format']}-{mode}"
    path = dest / (name + ".mp4")
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            "1440x900",
            "-r",
            str(fps),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(path),
        ],
        stdin=subprocess.PIPE,
    )
    count = 0
    stills = []
    measurements = []
    for index, phase in enumerate(phases):
        frames = 8 if quick else max(2, round(duration(phase) * fps))
        hold = 2 if quick else round(0.45 * fps)
        for j in range(frames + hold):
            t = min(1, j / (frames - 1))
            ease = t * t * (3 - 2 * t)
            state = interpolate(phase, ease)
            frame = Image.new("RGB", (1440, 900), BACKGROUND)
            frame.paste(scene.draw(state), (0, 100))
            draw = ImageDraw.Draw(frame)
            draw.text((36, 20), titles[mode], font=font(31), fill=INK)
            draw.text(
                (36, 64),
                f"{index + 1:02d}  {phase['label']}",
                font=font(23),
                fill=MUTED,
            )
            show_detail = detail is not None and (
                mode in ("advance", "reposition")
                or phase["label"]
                in (
                    "Flex the six clip catches",
                    "Slide the six closure clips home",
                    "Release the catches into their recesses",
                )
            )
            if show_detail:
                image = detail.draw(state)
                left = 36 if mode == "load" else 996
                frame.paste(image, (left, 110))
                draw.rectangle((left, 110, left + 420, 144), fill=BACKGROUND)
                draw.rectangle((left, 110, left + 420, 390), outline="#c5d0d6", width=1)
                text = {
                    "advance": "Index tooth - cap transparent",
                    "load": "Clip catch - underside view",
                    "reposition": "Open film exit + retaining ears",
                }[mode]
                draw.text((left + 10, 120), text, font=font(18), fill=INK)
                if mode == "advance":
                    status = (
                        "RELEASED"
                        if state.index_release > 3.5
                        else (
                            "SEATED"
                            if state.index_release < 0.1
                            else "RETRACTING / RETURNING"
                        )
                    )
                    draw.rectangle((left + 1, 356, left + 419, 389), fill=BACKGROUND)
                    draw.text((left + 10, 361), status, font=font(17), fill=MUTED)
            elif mode == "dock":
                draw.text(
                    (1008, 121),
                    "Enlarger: translucent cutaway",
                    font=font(18),
                    fill=MUTED,
                )
            draw.line((36, 809, 1404, 809), fill="#c5d0d6", width=1)
            x = 36
            for text, color in [
                ("Holder", "#315776"),
                ("Film", "#c89959"),
                ("Format collar", "#237f72"),
                ("Printed locks", "#d8ad70"),
                ("Receiver", "#8d9da7"),
            ]:
                draw.rectangle((x, 831, x + 14, 845), fill=color)
                draw.text((x + 23, 825), text, font=font(20), fill=INK)
                x += len(text) * 12 + 70
            draw.text(
                (36, 866),
                "B1 geometry simulation  |  Dimensions provisional; spring force, film grip and real fit await testing.",
                font=font(18),
                fill=MUTED,
            )
            proc.stdin.write(frame.tobytes())
            count += 1
            if j == frames - 1:
                still = dest / (name + f"-step-{index + 1:02d}.jpg")
                frame.save(still, quality=87)
                stills.append(still.name)
                if index == len(phases) - 1:
                    frame.save(dest / (name + "-poster.jpg"), quality=92)
                measurements.append(
                    {"phase": phase["label"], "frame": count - 1, "state": state.data()}
                )
        print(name, index + 1, "/", len(phases), flush=True)
    proc.stdin.close()
    assert proc.wait() == 0
    scene.close()
    if detail:
        detail.close()
    metadata = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-count_frames",
                "-show_entries",
                "stream=codec_name,width,height,nb_read_frames,r_frame_rate,duration",
                "-of",
                "json",
                str(path),
            ],
            text=True,
        )
    )["streams"][0]
    assert (
        int(metadata["nb_read_frames"]) == count
        and metadata["width"] == 1440
        and metadata["height"] == 900
    )
    return {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "frames": count,
        "probe": metadata,
        "stills": stills,
        "phase_endpoints": measurements,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "build/negative-carrier-b")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/negative-carrier-b/videos"
    )
    parser.add_argument("--quick", action="store_true")
    parser.add_argument(
        "--only", choices=("load", "dock", "advance", "110", "reposition")
    )
    args = parser.parse_args()
    out = args.input
    dest = args.output
    dest.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((out / "manifest.json").read_text())
    check = json.loads((out / "freecad-validation.json").read_text())
    digest = hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest()
    assert check["passed"] and check["manifest_sha256"] == digest, (
        "Refusing to render unverified geometry"
    )
    result = {
        "manifest_sha256": digest,
        "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "freecad_report_sha256": hashlib.sha256(
            (out / "freecad-validation.json").read_bytes()
        ).hexdigest(),
        "quick_preview": args.quick,
        "videos": [],
    }
    for fmt, mode in [
        ("135", "load"),
        ("135", "dock"),
        ("135", "advance"),
        ("110", "advance"),
        ("135", "reposition"),
    ]:
        if args.only and (("110" if fmt == "110" else mode) != args.only):
            continue
        model = next(m for m in manifest["models"] if m["format"] == fmt)
        if mode == "reposition" and not any(
            p["group"] == mode for p in model["phases"]
        ):
            continue
        result["videos"].append(
            render(out, dest, manifest, model, mode, quick=args.quick)
        )
    (dest / "render-validation.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
