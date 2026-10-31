#!/usr/bin/env python3
"""Render the verified Durst STEP parts as a turntable and rigid hinge animation."""

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

import build123d as bd
import numpy as np
import pyvista as pv
import trimesh
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, VIEW_HEIGHT, FPS = 1280, 720, 550, 24
COLORS = {"a": "#375f78", "b": "#6d9293"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hinge_matrix(p, angle):
    """Same X-axis rigid placement as the independently checked FreeCAD study."""
    a = math.radians(angle)
    rotation = np.array(
        [[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]]
    )
    pivot = np.array([0, p["hinge_y"], p["hinge_z"]])
    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = pivot + rotation @ (np.array([0, 0, p["film_gap"]]) - pivot)
    return matrix


def posed(vertices, matrix):
    return vertices @ matrix[:3, :3].T + matrix[:3, 3]


def font(size):
    for name in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def caption(view, scene, angle, thickness):
    image = Image.new("RGB", (WIDTH, HEIGHT), "#fbfaf7")
    image.paste(Image.fromarray(view), (0, 84))
    draw = ImageDraw.Draw(image)
    draw.text((35, 16), "DURST C35  /  V0.2", font=font(18), fill="#617380")
    title = "360° assembly view" if scene == "rotation" else "Hinge opening and closing"
    draw.text((33, 42), title, font=font(30), fill="#203747")
    draw.text((WIDTH - 180, 44), f"{angle:03.0f}°", font=font(30), fill="#375f78")
    draw.rectangle((0, 634, WIDTH, HEIGHT), fill="#203747")
    for x, half, label in [(35, "a", "Lower A"), (210, "b", "Upper B")]:
        draw.rounded_rectangle((x, 653, x + 20, 673), radius=4, fill=COLORS[half])
        draw.text((x + 31, 650), label, font=font(22), fill="#ffffff")
    draw.text(
        (430, 650),
        f"{thickness:g} mm provisional sheet · upturned sides",
        font=font(22),
        fill="#ffffff",
    )
    detail = (
        "Actual STEP geometry · colours distinguish the two halves"
        if scene == "rotation"
        else "Prescribed rigid motion · FreeCAD checked at 1° intervals · physical fit unverified"
    )
    draw.text((35, 687), detail, font=font(17), fill="#c9d5dd")
    return image


def render(folder, destination):
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / "video-report.json"
    report_path.unlink(missing_ok=True)
    model_path, validation_path = (
        folder / "model-report.json",
        folder / "validation.json",
    )
    model = json.loads(model_path.read_text())
    validation = json.loads(validation_path.read_text())
    if model.get("passed") is not True or validation.get("passed") is not True:
        raise ValueError("A passing export and FreeCAD study are required")
    if validation["model_report_sha256"] != sha(model_path):
        raise ValueError("FreeCAD validation belongs to a different export")
    for name, expected in model["files_sha256"].items():
        if sha(folder / name) != expected:
            raise ValueError(f"Verified export changed: {name}")
    checked = {s["angle_deg"]: s["overlap_mm3"] for s in validation["hinge_samples"]}
    if set(checked) != set(range(181)) or max(checked.values()) >= 1e-4:
        raise ValueError("Expected all 181 passing FreeCAD hinge positions")
    p = json.loads((folder / "parameters.json").read_text())
    meshes = {}
    for half in "ab":
        path = destination / f"render-{half}.stl"
        bd.export_stl(
            bd.import_step(folder / f"{half}.step"),
            path,
            tolerance=0.01,
            angular_tolerance=0.05,
        )
        meshes[half] = trimesh.load_mesh(path)
    report = {
        "passed": False,
        "model_report_sha256": sha(model_path),
        "validation_sha256": sha(validation_path),
        "render_script_sha256": sha(Path(__file__)),
        "pyvista_version": pv.__version__,
        "method": "STEP tessellation rendered in VTK; motion uses FreeCAD-checked rigid poses",
        "physical_fit_verified": False,
        "videos": [],
    }
    for scene in ("rotation", "hinge"):
        frames = 12 * FPS if scene == "rotation" else 16 * FPS
        plotter = pv.Plotter(off_screen=True, window_size=(WIDTH, VIEW_HEIGHT))
        plotter.set_background("#e8edf0", top="#fbfaf7")
        actors = {}
        for half, mesh in meshes.items():
            faces = np.column_stack([np.full(len(mesh.faces), 3), mesh.faces]).ravel()
            actors[half] = plotter.add_mesh(
                pv.PolyData(mesh.vertices, faces),
                color=COLORS[half],
                smooth_shading=False,
                specular=0.15,
                ambient=0.28,
            )
        actors["b"].user_matrix = hinge_matrix(p, 0)
        direction = np.array([1.45, 1.8, 1.5])
        direction /= np.linalg.norm(direction)
        if scene == "rotation":
            target, scale = np.array([0, 48, 0]), 71
        else:
            # Fit the entire sweep once: the camera never zooms with the pose.
            points = np.concatenate(
                [meshes["a"].vertices]
                + [posed(meshes["b"].vertices, hinge_matrix(p, a)) for a in range(181)]
            )
            right = np.cross([0, 0, 1], direction)
            right /= np.linalg.norm(right)
            up = np.cross(direction, right)
            basis = np.stack([right, up, direction], axis=1)
            projected = points @ basis
            center = (projected.min(axis=0) + projected.max(axis=0)) / 2
            target = center @ basis.T
            scale = 0.56 * max(
                np.ptp(projected[:, 1]),
                np.ptp(projected[:, 0]) * VIEW_HEIGHT / WIDTH,
            )
        plotter.camera_position = (target + 350 * direction, target, (0, 0, 1))
        plotter.camera.parallel_projection = True
        plotter.camera.parallel_scale = scale
        plotter.enable_anti_aliasing("ssaa")
        path = destination / f"Durst-C35-v0.2-{scene}.mp4"
        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            f"{WIDTH}x{HEIGHT}",
            "-framerate",
            str(FPS),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(path),
        ]
        angles = []
        viewport_hashes = {}
        with (destination / f"{scene}-encoding.log").open("w") as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
            try:
                for index in range(frames):
                    if scene == "rotation":
                        angle = index * 360 / frames
                        r = math.radians(angle)
                        orbit = np.array(
                            [
                                [math.cos(r), -math.sin(r), 0],
                                [math.sin(r), math.cos(r), 0],
                                [0, 0, 1],
                            ]
                        )
                        plotter.camera_position = (
                            target + 350 * (orbit @ direction),
                            target,
                            (0, 0, 1),
                        )
                    else:
                        seconds = index / FPS
                        if seconds < 1:
                            angle = 0
                        elif seconds < 7:
                            angle = round(
                                90 * (1 - math.cos(math.pi * (seconds - 1) / 6))
                            )
                        elif seconds < 9:
                            angle = 180
                        elif seconds < 15:
                            angle = round(
                                90 * (1 + math.cos(math.pi * (seconds - 9) / 6))
                            )
                        else:
                            angle = 0
                        actors["b"].user_matrix = hinge_matrix(p, angle)
                    angles.append(angle)
                    plotter.reset_camera_clipping_range()
                    plotter.render()
                    viewport = plotter.screenshot()
                    image = caption(viewport, scene, angle, p["sheet_thickness"])
                    if index in (0, frames // 4, frames // 2, 3 * frames // 4):
                        image.save(destination / f"{scene}-{index:04d}.png")
                        viewport_hashes[index] = hashlib.sha256(
                            viewport.tobytes()
                        ).hexdigest()
                    process.stdin.write(image.tobytes())
                    if index % (FPS * 2) == 0:
                        print(f"{scene}: {index}/{frames} frames", flush=True)
            finally:
                process.stdin.close()
                plotter.close()
            if process.wait() != 0:
                raise RuntimeError(f"Encoding failed; inspect {log.name}")
        if len(set(viewport_hashes.values())) < 3:
            raise RuntimeError(
                "Rendered geometry did not move across inspection frames"
            )
        metadata = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-count_frames",
                    "-show_streams",
                    "-of",
                    "json",
                    str(path),
                ],
                text=True,
            )
        )
        stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        if (int(stream["nb_read_frames"]), stream["width"], stream["height"]) != (
            frames,
            WIDTH,
            HEIGHT,
        ):
            raise RuntimeError(
                "Encoded video does not match the requested frames/dimensions"
            )
        report["videos"].append(
            {
                "file": path.name,
                "sha256": sha(path),
                "frames": frames,
                "fps": FPS,
                "duration_seconds": frames / FPS,
                "frame_angles_deg": angles,
                "inspection_viewport_sha256": viewport_hashes,
                "encoding": metadata,
            }
        )
        print(path, flush=True)
    report["passed"] = True
    report_path.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe")):
        parser.error("ffmpeg and ffprobe must be installed")
    render(args.input.resolve(), (args.output or args.input / "videos").resolve())
