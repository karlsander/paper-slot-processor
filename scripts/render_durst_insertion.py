#!/usr/bin/env python3
"""Show the provisional C35 insertion sequence using the FreeCAD-checked poses."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import build123d as bd
import numpy as np
import pyvista as pv
import trimesh
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.render_durst_videos import font

FPS, WIDTH, HEIGHT = 24, 1280, 720
LABELS = {
    "depress_stage": "1  Depress the carrier stage",
    "align_carrier": "2  Align the closed carrier with the released gap",
    "insert": "3  Slide the carrier in, hinge end first",
    "release_stage": "4  Release the stage and seat the carrier",
    "depress_for_removal": "5  Depress the stage for removal",
    "withdraw": "6  Withdraw the closed carrier",
    "reset": "7  Release the empty stage",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(folder):
    out = folder / "video"
    out.mkdir(exist_ok=True)
    report_path = out / "video-report.json"
    report_path.unlink(missing_ok=True)
    validation_path = folder / "insertion-validation.json"
    validation = json.loads(validation_path.read_text())
    manifest_path = folder / "study-manifest.json"
    if not validation["verification_completed"] or validation[
        "study_manifest_sha256"
    ] != sha(manifest_path):
        raise ValueError("Missing or stale FreeCAD insertion study")
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest["files_sha256"].items():
        if sha(folder / name) != expected:
            raise ValueError(f"Study input changed: {name}")
    p = json.loads((folder / "carrier-parameters.json").read_text())
    view = pv.Plotter(off_screen=True, window_size=(WIDTH, 540))
    view.set_background("#e8edf0", top="#fbfaf7")
    colors = {
        "carrier-a": "#375f78",
        "carrier-b": "#6d9293",
        "mixing-box": "#d0b987",
        "stage": "#ab774b",
        "back-stop": "#535e67",
    }
    actors = {}
    bounds = {}
    for name, color in colors.items():
        shape = bd.import_step(folder / f"{name}.step")
        if name == "mixing-box":
            # Display-only cut: remove the upper half on the camera side. The
            # complete box, underside and all walls were checked in FreeCAD.
            shape -= bd.Pos(0, -100, 18) * bd.Box(
                200, 400, 300, align=(bd.Align.MIN,) * 3
            )
        path = out / f"{name}.stl"
        bd.export_stl(shape, path, tolerance=0.02, angular_tolerance=0.08)
        mesh = trimesh.load_mesh(path)
        bounds[name] = np.array(
            [
                [x, y, z]
                for x in mesh.bounds[:, 0]
                for y in mesh.bounds[:, 1]
                for z in mesh.bounds[:, 2]
            ]
        )
        faces = np.column_stack([np.full(len(mesh.faces), 3), mesh.faces]).ravel()
        actors[name] = view.add_mesh(
            pv.PolyData(mesh.vertices, faces), color=color, ambient=0.3, specular=0.12
        )
    direction = np.array([280, 330, 210], dtype=float)
    direction /= np.linalg.norm(direction)
    right = np.cross([0, 0, 1], direction)
    right /= np.linalg.norm(right)
    up = np.cross(direction, right)
    basis = np.stack([right, up, direction], axis=1)
    sweep = [bounds["mixing-box"], bounds["back-stop"]]
    for s in validation["samples"]:
        sweep += [bounds["stage"] + [0, 0, s["stage_z"]]]
        for name in ("carrier-a", "carrier-b"):
            sweep += [
                bounds[name]
                + [
                    0,
                    s["carrier_y"],
                    s["carrier_z"] + (p["film_gap"] if name == "carrier-b" else 0),
                ]
            ]
    projected = np.concatenate(sweep) @ basis
    target = ((projected.min(axis=0) + projected.max(axis=0)) / 2) @ basis.T
    view.camera_position = (target + 480 * direction, target, (0, 0, 1))
    view.camera.parallel_projection = True
    view.camera.parallel_scale = 0.55 * max(
        np.ptp(projected[:, 1]), np.ptp(projected[:, 0]) * 540 / WIDTH
    )
    view.enable_anti_aliasing("ssaa")
    timeline = []
    for phase, seconds in zip(LABELS, (1, 1, 5, 2, 1, 5, 1)):
        indexes = [
            i for i, s in enumerate(validation["samples"]) if s["phase"] == phase
        ]
        timeline += [
            indexes[round(t)] for t in np.linspace(0, len(indexes) - 1, seconds * FPS)
        ]
    video = out / "Durst-C35-provisional-insertion.mp4"
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
        str(video),
    ]
    snapshots = {}
    with (out / "encoding.log").open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for frame, sample_index in enumerate(timeline):
                s = validation["samples"][sample_index]
                for name in ("carrier-a", "carrier-b"):
                    matrix = np.eye(4)
                    matrix[:3, 3] = (
                        0,
                        s["carrier_y"],
                        s["carrier_z"] + (p["film_gap"] if name == "carrier-b" else 0),
                    )
                    actors[name].user_matrix = matrix
                    actors[name].prop.color = colors[name] if s["clear"] else "#d23e3e"
                matrix = np.eye(4)
                matrix[2, 3] = s["stage_z"]
                actors["stage"].user_matrix = matrix
                view.reset_camera_clipping_range()
                view.render()
                viewport = view.screenshot()
                image = Image.new("RGB", (WIDTH, HEIGHT), "#fbfaf7")
                image.paste(Image.fromarray(viewport), (0, 94))
                draw = ImageDraw.Draw(image)
                draw.text(
                    (32, 12),
                    "DURST C35  /  PROVISIONAL INSERTION STUDY",
                    font=font(18),
                    fill="#617380",
                )
                draw.text((30, 42), LABELS[s["phase"]], font=font(27), fill="#203747")
                draw.rectangle((0, 634, WIDTH, HEIGHT), fill="#203747")
                draw.text(
                    (30, 647),
                    f"Travel remaining: {s['carrier_y']:.0f} mm     Stage depression: {-s['stage_z']:.1f} mm",
                    font=font(23),
                    fill="white",
                )
                draw.text(
                    (30, 684),
                    "Estimated mating geometry · mixing box cut away for visibility · actual fit unverified",
                    font=font(18),
                    fill="#d7e1e7",
                )
                if frame in (24, 105, 190, 212, 250):
                    image.save(out / f"frame-{frame:04d}.png")
                    snapshots[frame] = hashlib.sha256(viewport.tobytes()).hexdigest()
                process.stdin.write(image.tobytes())
                if frame % 48 == 0:
                    print(f"Insertion video: {frame}/{len(timeline)}", flush=True)
        finally:
            process.stdin.close()
            view.close()
        if process.wait():
            raise RuntimeError(f"Video encoding failed: {log.name}")
    if len(set(snapshots.values())) < 3:
        raise ValueError("The inspection frames do not show geometry motion")
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
                str(video),
            ],
            text=True,
        )
    )
    stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    assert (int(stream["nb_read_frames"]), stream["width"], stream["height"]) == (
        len(timeline),
        WIDTH,
        HEIGHT,
    )
    report_path.write_text(
        json.dumps(
            {
                "passed": True,
                "video": video.name,
                "sha256": sha(video),
                "fps": FPS,
                "frames": len(timeline),
                "duration_seconds": len(timeline) / FPS,
                "validation_sha256": sha(validation_path),
                "renderer_sha256": sha(Path(__file__)),
                "frame_sample_indexes": timeline,
                "inspection_viewport_sha256": snapshots,
                "fixture_measured": False,
                "physical_fit_verified": False,
                "display_cutaway_only": "mixing-box material at X>=0, Z>=18 removed from render, retained in collision checks",
                "encoding": metadata,
            },
            indent=2,
        )
        + "\n"
    )
    print(video)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", type=Path)
    render(parser.parse_args().study.resolve())
