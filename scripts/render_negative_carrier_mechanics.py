#!/usr/bin/env python3
"""Parts atlas and mechanism close-ups from the verified compact B1 STEP set.

Display cuts/transparency never alter the checked CAD. Every animation segment
references an existing manifest phase (sometimes only its final few mm).
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import build123d as bd
import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw
from render_negative_carrier_b import (
    BACKGROUND,
    COLORS,
    INK,
    MUTED,
    ROOT,
    Scene,
    font,
    interpolate,
    poly,
)

FPS = 24
SIZE = (1920, 1080)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def view(
    target,
    eye,
    scale,
    *,
    show=None,
    opacity=None,
    marks=False,
    up=(0, 0, 1),
    labels=(),
    section=None,
):
    return {
        "target": target,
        "eye": eye,
        "scale": scale,
        "show": show,
        "opacity": opacity or {},
        "marks": marks,
        "up": up,
        "labels": labels,
        "section": section,
    }


def chapters(model):
    phases = model["phases"]

    def phase(label, seconds=2.2, start=0, end=1):
        i = next(i for i, p in enumerate(phases) if p["label"] == label)
        return {"phase": i, "seconds": seconds, "start": start, "end": end}

    holder = ["base", "lid", "film"]
    clip = "closure-0-1"
    x = -model["format_data"]["centers"][0]
    all_parts = [n for n in model["parts"] if n != "film"]
    overview = view((30, 0, 0), (210, 310, 300), 165, marks=True, up=(1, 0, 0))
    advance = [
        phase("Retract the index tooth before frame 2", 1.5),
        phase("Slide to frame 2", 3),
        phase("Frame 2: release to register", 1.5),
    ]
    # Reverse exactly the same checked phases to return to the first pocket.
    back = [dict(p, start=1, end=0) for p in reversed(advance)]
    for step, label in zip(
        back,
        (
            "Retract the tooth to return",
            "Slide back to frame 1",
            "Frame 1: release to register",
        ),
    ):
        step["label"] = label
    return [
        {
            "slug": "01-film-clamp",
            "title": "Place the film and lower the lid",
            "number": "01",
            "left": "Clamping lands at the film margins",
            "right": "Whole holder",
            "note": "The lid meets the film margins and the gaps between images.",
            "sub": "Lift-off lid; six separate C clips secure it in the next step.",
            "views": [
                view((x, 13, 1), (x + 15, 70, 38), 24, show=holder, marks=True),
                view((x, 0, 4), (x + 25, 200, 155), 110, show=holder, marks=True),
            ],
            "steps": [
                phase("Place the strip against the frame lands", 2.5, 0.75),
                phase("Lower the full-length lid", 3, 0.83),
            ],
        },
        {
            "slug": "02-closure-clip",
            "title": "Flex, slide, then release the clip catch",
            "number": "02",
            "left": "One of six C clips - underside",
            "right": "Catch and its recess",
            "note": "The long tongue bends down; the clip slides 7 mm onto the frame edge.",
            "sub": "The catch returns into its recess. Release the tongue again before removal.",
            "views": [
                view((x, 24, -0.3), (x + 10, 57, -24), 10, show=holder + [clip]),
                view(
                    (x + 2.4, 24, -0.4),
                    (x + 2.4, 42, -18),
                    5.6,
                    show=["base", "lid", clip],
                    opacity={"base": 0.3},
                    labels=[("Catch", (x + 2.4, 22.8, -0.3))],
                ),
            ],
            "steps": [
                phase("Flex the six clip catches", 2),
                phase("Slide the six closure clips home", 3),
                phase("Release the catches into their recesses", 2),
            ],
        },
        {
            "slug": "03-cap-lock",
            "title": "Quarter-turn keys retain the mask cap",
            "number": "03",
            "left": "One of four cap keys",
            "right": "Lower crossbar - underside",
            "note": "Lower the cap over the aligned keys, then turn the keys 90 degrees.",
            "sub": "The lower crossbars bridge the slots and prevent the cap lifting off.",
            "views": [
                view(
                    (18, 31, 1),
                    (43, 69, 31),
                    11,
                    show=["collar-base", "collar-cap", "cap-lock-18-31"],
                    opacity={"collar-base": 0.3, "collar-cap": 0.3},
                ),
                view(
                    (18, 31, -2),
                    (25, 50, -27),
                    6.8,
                    show=["collar-base", "collar-cap", "cap-lock-18-31"],
                    opacity={"collar-base": 0.4, "collar-cap": 0.18},
                ),
            ],
            "steps": [
                phase("Lower the matching mask cap", 2.5, 0.91),
                phase("Turn the four cap locks", 3),
            ],
        },
        {
            "slug": "04-docking-lock",
            "title": "Dock the collar; lower and turn the two pins",
            "number": "04",
            "left": "Right-hand dock pin and receiver rail",
            "right": "Cartridge seating in the receiver",
            "note": "The crossbars retain the collar vertically; eccentric shoulders locate it.",
            "sub": "The receiver stays in the enlarger. Its rear stop and left pads are the references.",
            "views": [
                view(
                    (18, 48, -0.5),
                    (48, 85, 24),
                    15,
                    show=["receiver", "collar-base", "dock-lock-18"],
                    opacity={"receiver": 0.3, "collar-base": 0.4},
                ),
                view(
                    (0, 12, 0),
                    (100, 230, 230),
                    78,
                    show=all_parts,
                    opacity={"base": 0.3, "lid": 0.2, "collar-cap": 0.3},
                ),
            ],
            "steps": [
                phase("Slide the prepared cartridge into the receiver", 3, 0.85),
                phase("Lower the two front dock pins", 2.5),
                phase("Turn the pins to retain the collar", 3),
            ],
        },
        {
            "slug": "05-index-latch",
            "title": "Release, advance one frame, then register again",
            "number": "05",
            "left": "Paddle and its two flexure arms",
            "right": "Hard tooth and opposing spring tip",
            "note": "Pull the paddle 4 mm before sliding. Release it into the next frame pocket.",
            "sub": "The hard tooth defines X; the small opposing leaf takes up pocket clearance.",
            "views": [
                view(
                    (0, 34, 0),
                    (0, 78, 100),
                    18,
                    show=["base", "collar-base", "index-latch"],
                    opacity={"collar-base": 0.4},
                ),
                view(
                    (0, 27.5, 0.6),
                    (0, 27.5, 75),
                    6.5,
                    up=(0, 1, 0),
                    show=["base", "index-latch"],
                ),
            ],
            "steps": advance + back,
        },
        {
            "slug": "06-guides",
            "title": "Guides control sideways motion and height",
            "number": "06",
            "left": "Underside groove: two hard pads + guide leaf",
            "right": "Section: roof tongue and lower support",
            "note": "The groove slides along two pads while the guide leaf takes up the opposite wall.",
            "sub": "Three lower supports set height; two roof tongues keep the holder seated as it slides.",
            "views": [
                view(
                    (0, -19.5, -1),
                    (12, -70, 55),
                    24,
                    show=["base", "collar-base"],
                    opacity={"base": 0.22},
                    labels=[
                        ("Guide leaf", (8, -19.2, -0.8)),
                        ("Hard guide pad", (-18, -19.7, -0.9)),
                    ],
                ),
                view(
                    (-10, 20, 0),
                    (-10, 90, 15),
                    14,
                    show=["base", "lid", "collar-base", "collar-cap"],
                    section=(-1000, 1000, 19.1, 20.9, -1000, 1000),
                    labels=[
                        ("Roof tongue", (-3, 20, 1.6)),
                        ("Lower support", (0, 20.5, -1.3)),
                    ],
                ),
            ],
            "steps": [advance[1], dict(advance[1], start=1, end=0)],
        },
        {
            "slug": "07-end-retention",
            "title": "Open film exits; outer ears retain the collar",
            "number": "07",
            "left": "First-frame end of travel",
            "right": "Film extending beyond both ends",
            "note": "Film passes through the open center. The retaining ears sit outside the film path.",
            "sub": "This shows the first indexed position, before the ears reach their overtravel stops.",
            "views": [
                view(
                    (-28, 0, 0),
                    (-75, 65, 48),
                    37,
                    show=["base", "lid", "film", "collar-base", "collar-cap"],
                    opacity={"collar-cap": 0.3},
                    marks=True,
                ),
                overview,
            ],
            "steps": [
                phase("Slide back to the original frame", 4, 0.8),
                phase("Frame 1 registered again", 1.5),
            ],
        },
        {
            "slug": "08-fixed-mask",
            "title": "The masks stay at the optical axis",
            "number": "08",
            "left": "One exposure opening; film advances behind it",
            "right": "The holder moves through the fixed collar",
            "note": "Each cartridge carries masks matched to its format; every indexed frame is accessible.",
            "sub": "Keep the enlarger lamp off while moving: B1 has no shutter.",
            "views": [
                view((0, 0, 0), (0, 0, 120), 28, up=(0, -1, 0), marks=True),
                overview,
            ],
            "steps": advance,
        },
        {
            "slug": "09-strip-reposition",
            "title": "For the next group, reopen the clamp at the workbench",
            "number": "09",
            "left": "Film clears the margin ledges before shifting",
            "right": "Collar separated; lid and clips released",
            "note": "Lift the film, shift it one pitch, then realign and reclose the holder.",
            "sub": "This is open-clamp reloading, not continuous transport through a closed cartridge.",
            "views": [
                view((-27, 0, 0.5), (-65, 65, 30), 29, show=holder, marks=True),
                view((x, 0, 10), (x + 50, 230, 160), 125, show=holder, marks=True),
            ],
            "steps": [
                phase("Lift the film clear of all clamping lands", 2),
                phase("Move the strip one pitch; align the next image group", 3.5),
                phase("Lower the film onto the margin supports", 2),
            ],
        },
    ]


class Detail(Scene):
    def set_view(self, spec):
        self.spec = spec
        self.plot.camera_position = [spec["eye"], spec["target"], spec["up"]]
        self.plot.camera.parallel_scale = spec["scale"]
        for n, actor in self.actors.items():
            actor.prop.opacity = spec["opacity"].get(n, 1)
            mesh = self.mesh(self.active[n])
            if spec["section"] is not None:
                mesh = mesh.clip_box(spec["section"], invert=False)
            actor.mapper.dataset = mesh

    def draw(self, state):
        # Reuse the exact transform and variant selection of the workflow movie.
        super().draw(state)
        for n, actor in self.actors.items():
            if n.startswith("fixture") or (
                self.spec["show"] is not None and n not in self.spec["show"]
            ):
                actor.visibility = False
        for actor in self.markings:
            actor.visibility = self.spec["marks"]
        self.plot.reset_camera_clipping_range()
        self.plot.render()
        frame = Image.fromarray(self.plot.screenshot(return_img=True))
        d = ImageDraw.Draw(frame)
        for i, (label, point) in enumerate(self.spec["labels"]):
            if label == "Catch":
                point = (
                    point[0],
                    point[1] + state.clips_out,
                    point[2] - state.clips_release * (6.4 / 7.8) ** 2,
                )
            renderer = self.plot.renderer
            renderer.SetWorldPoint(*point, 1)
            renderer.WorldToDisplay()
            px, py, _ = renderer.GetDisplayPoint()
            px, py = int(px), frame.height - int(py)
            tx, ty = 22, 26 + 52 * i
            d.line((tx, ty + 26, px, py), fill=INK, width=2)
            d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=INK)
            bounds = d.textbbox((tx, ty), label, font=font(22))
            d.rectangle(
                (bounds[0] - 5, bounds[1] - 3, bounds[2] + 5, bounds[3] + 3),
                fill=BACKGROUND,
            )
            d.text((tx, ty), label, font=font(22), fill=INK)
        return frame


def parts_atlas(out, dest, manifest, model):
    groups = [
        (
            "Holder base",
            ["base"],
            (32, 150, 952, 260),
            "168 mm long; four frame positions",
        ),
        ("Lift-off lid", ["lid"], (1016, 150, 952, 260), "One piece; open film exits"),
        ("Shared receiver", ["receiver"], (32, 434, 630, 420), "Stays in the enlarger"),
        (
            "Lower format collar",
            ["collar-base"],
            (685, 434, 630, 420),
            "Mask, guide leaf and support pads",
        ),
        (
            "Upper mask cap",
            ["collar-cap"],
            (1338, 434, 630, 420),
            "Mask and two roof tongues",
        ),
        (
            "Closure clips",
            [n for n in model["parts"] if n.startswith("closure-")],
            (32, 878, 466, 410),
            "Six clips; flex catches to remove",
        ),
        (
            "Cap keys",
            [n for n in model["parts"] if n.startswith("cap-lock-")],
            (522, 878, 466, 410),
            "Four quarter-turn locks",
        ),
        (
            "Dock pins",
            [n for n in model["parts"] if n.startswith("dock-lock-")],
            (1012, 878, 466, 410),
            "Two different eccentric pins",
        ),
        (
            "Index latch",
            ["index-latch"],
            (1502, 878, 466, 410),
            "Replaceable printed flexure",
        ),
    ]
    shown = [n for _, names, _, _ in groups for n in names]
    assert len(shown) == len(set(shown)) == 18
    assert set(shown) == set(model["parts"]) - {"film"}
    canvas = Image.new("RGB", (2000, 1400), BACKGROUND)
    d = ImageDraw.Draw(canvas)
    d.text((32, 27), "All 18 printed pieces", font=font(52), fill=INK)
    d.text(
        (34, 94),
        "Compact 35 mm B1  /  17 cartridge parts + 1 shared receiver  /  A1 mini size",
        font=font(27),
        fill=MUTED,
    )
    records = []
    for title, names, (x, y, w, h), note in groups:
        card = Image.new("RGB", (w, h), "#f8fafb")
        draw = ImageDraw.Draw(card)
        plot = pv.Plotter(off_screen=True, window_size=(w - 20, h - 105))
        plot.set_background("#f8fafb")
        for j, name in enumerate(names):
            record = manifest["assets"][model["parts"][name]["asset"]]
            record = record.get("relaxed_native", record)
            path = out / record["file"]
            assert sha(path) == record["sha256"]
            mesh = poly(bd.import_step(path))
            center = mesh.center
            mesh.translate(-np.array(center), inplace=True)
            if len(names) > 1:
                columns = 3 if len(names) == 6 else 2
                mesh.translate(
                    ((j % columns) * 15, (j // columns) * 12, 0), inplace=True
                )
            plot.add_mesh(
                mesh,
                color=COLORS.get(name, "#d8ad70"),
                ambient=0.3,
                diffuse=0.65,
                specular=0.15,
                smooth_shading=False,
            )
            records.append(
                {"part": name, "file": record["file"], "sha256": record["sha256"]}
            )
        direction = np.array(
            (0, -1, 0.45)
            if title in ("Holder base", "Lift-off lid")
            else (0.25, -1, 1.5)
        )
        plot.view_vector(direction, viewup=(0, 0, 1))
        plot.enable_parallel_projection()
        plot.reset_camera()
        # Fit projected extents; reset_camera alone wastes wide card viewports.
        right = np.cross((0, 0, 1), direction)
        right /= np.linalg.norm(right)
        up = np.cross(direction, right)
        up /= np.linalg.norm(up)
        b = plot.bounds
        corners = np.array([(a, b1, c) for a in b[:2] for b1 in b[2:4] for c in b[4:]])
        extent_x = np.ptp(corners @ right)
        extent_y = np.ptp(corners @ up)
        plot.camera.parallel_scale = (
            max(extent_y / 2, extent_x / 2 / ((w - 20) / (h - 105))) * 1.12
        )
        card.paste(Image.fromarray(plot.screenshot(return_img=True)), (10, 58))
        plot.close()
        draw.text((20, 14), title, font=font(28), fill=INK)
        count = f"x{len(names)}"
        draw.text((w - 70, 14), count, font=font(28), fill=INK)
        draw.text((20, h - 38), note, font=font(20), fill=MUTED)
        canvas.paste(card, (x, y))
    d.text(
        (34, 1322),
        "Actual relaxed print geometry. Views use different scales; this is an inventory, not a packed print plate.",
        font=font(25),
        fill=INK,
    )
    d.text(
        (34, 1360),
        "Film and the enlarger are reference objects and are not included. Dimensions and mechanical forces remain provisional.",
        font=font(23),
        fill=MUTED,
    )
    path = dest / "all-parts.png"
    canvas.save(path)
    return {"file": path.name, "sha256": sha(path), "parts": records}


def compose(scenes, chapter, phase, state, progress):
    frame = Image.new("RGB", SIZE, BACKGROUND)
    d = ImageDraw.Draw(frame)
    d.text(
        (30, 20),
        f"{chapter['number']} / 09   {chapter['title']}",
        font=font(38),
        fill=INK,
    )
    d.text((32, 76), phase["label"], font=font(26), fill=MUTED)
    for scene, x, label in zip(scenes, (20, 1240), (chapter["left"], chapter["right"])):
        frame.paste(scene.draw(state), (x, 164))
        d.text((x + 12, 128), label, font=font(24), fill=INK)
    d.line((32, 942, 1888, 942), fill="#c5d0d6", width=2)
    d.text((32, 960), chapter["note"], font=font(29), fill=INK)
    d.text((32, 1002), chapter["sub"], font=font(25), fill=MUTED)
    d.text(
        (32, 1044),
        "Checked CAD paths / transparent or omitted covers for visibility / prescribed flexures, not a force simulation",
        font=font(20),
        fill=MUTED,
    )
    d.rectangle((0, 1076, int(SIZE[0] * progress), 1079), fill="#237f72")
    return frame


def probe(path):
    result = json.loads(
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
    subprocess.run(
        ["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
        check=True,
    )
    return result


def render(out, dest, manifest, model, preview):
    scenes = [
        Detail(out, manifest, model, size, "advance")
        for size in [(1200, 760), (660, 760)]
    ]
    results = []
    for chapter in chapters(model):
        for scene, spec in zip(scenes, chapter["views"]):
            scene.set_view(spec)
        movie = dest / (chapter["slug"] + ".mp4")
        proc = (
            None
            if preview
            else subprocess.Popen(
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
                    "1920x1080",
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
                    str(movie),
                ],
                stdin=subprocess.PIPE,
            )
        )
        count = 0
        endpoints = []
        for i, step in enumerate(chapter["steps"]):
            phase = model["phases"][step["phase"]]
            frames = round(step["seconds"] * FPS)
            samples = [0, frames // 2, frames - 1] if preview else range(frames + 18)
            for j in samples:
                t = min(1, j / (frames - 1))
                t = t * t * (3 - 2 * t)
                t = step["start"] + (step["end"] - step["start"]) * t
                state = interpolate(phase, t)
                frame = compose(
                    scenes,
                    chapter,
                    phase | {"label": step.get("label", phase["label"])},
                    state,
                    (i + min(1, j / frames)) / len(chapter["steps"]),
                )
                if proc:
                    proc.stdin.write(frame.tobytes())
                if preview and j in (0, frames // 2, frames - 1):
                    suffix = (
                        "start" if j == 0 else ("end" if j == frames - 1 else "mid")
                    )
                    file = f"{chapter['slug']}-{i + 1:02d}-{suffix}.jpg"
                    # Disposable preview contacts; final state records stay in JSON.
                    frame.save(dest / file, quality=88)
                if j == frames - 1:
                    endpoints.append(
                        {
                            "phase": step["phase"],
                            "t": t,
                            "state": state.data(),
                            "frame": count,
                        }
                    )
                    if i == len(chapter["steps"]) - 1:
                        frame.save(dest / (chapter["slug"] + "-poster.jpg"), quality=92)
                count += 1
            print(chapter["slug"], i + 1, "/", len(chapter["steps"]), flush=True)
        if proc:
            proc.stdin.close()
            assert proc.wait() == 0
            metadata = probe(movie)
            assert int(metadata["nb_read_frames"]) == count
            results.append(
                {
                    "file": movie.name,
                    "title": chapter["title"],
                    "sha256": sha(movie),
                    "frames": count,
                    "probe": metadata,
                    "steps": chapter["steps"],
                    "endpoints": endpoints,
                }
            )
    for scene in scenes:
        scene.close()
    return results


def combine(dest, videos):
    listing = dest / "concat.txt"
    listing.write_text("".join(f"file '{r['file']}'\n" for r in videos))
    metadata = dest / "chapters.ffmeta"
    lines = [";FFMETADATA1"]
    frame = 0
    for v in videos:
        lines.extend(
            [
                "[CHAPTER]",
                f"TIMEBASE=1/{FPS}",
                f"START={frame}",
                f"END={frame + v['frames']}",
                f"title={v['title']}",
            ]
        )
        v["start_seconds"] = frame / FPS
        frame += v["frames"]
    metadata.write_text("\n".join(lines) + "\n")
    path = dest / "mechanisms-close-up.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-i",
            str(metadata),
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(path),
        ],
        check=True,
    )
    listing.unlink()
    metadata.unlink()
    result = probe(path)
    assert int(result["nb_read_frames"]) == frame
    return {"file": path.name, "sha256": sha(path), "frames": frame, "probe": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=ROOT / "build/negative-carrier-b-a1-mini"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/negative-carrier-b/mechanics"
    )
    parser.add_argument(
        "--preview", action="store_true", help="Render atlas and selected poses only"
    )
    args = parser.parse_args()
    out, dest = args.input, args.output
    dest.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((out / "manifest.json").read_text())
    validation = json.loads((out / "freecad-validation.json").read_text())
    assert validation["passed"] and validation["manifest_sha256"] == sha(
        out / "manifest.json"
    )
    # A stale export is not silently accepted as the current CAD.
    for file, digest in manifest["source_hashes"].items():
        assert sha(ROOT / file) == digest, file
    model = next(m for m in manifest["models"] if m["format"] == "135")
    assert model["config"]["frame_count"] == 4
    result = {
        "manifest_sha256": sha(out / "manifest.json"),
        "freecad_report_sha256": sha(out / "freecad-validation.json"),
        "source_hashes": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [Path(__file__), ROOT / "scripts/render_negative_carrier_b.py"]
        },
        "format": "135",
        "indexed_frames": 4,
        "preview": args.preview,
        "evidence": "Existing checked paths; prescribed flexures, no force or physical-fit claim",
    }
    result["atlas"] = parts_atlas(out, dest, manifest, model)
    result["videos"] = render(out, dest, manifest, model, args.preview)
    if not args.preview:
        result["combined"] = combine(dest, result["videos"])
    (dest / "render-validation.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
