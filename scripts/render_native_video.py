#!/usr/bin/env python3
"""Launch FreeCAD GUI rendering and encode a verified frame sequence with ffmpeg."""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--freecad",
        default=os.environ.get("FREECAD_GUI")
        or shutil.which("FreeCAD")
        or "/Applications/FreeCAD.app/Contents/Resources/bin/freecad",
    )
    args = parser.parse_args()
    folder = args.output.resolve()
    report = folder / "video-report.json"
    report.unlink(missing_ok=True)
    macro = folder / "render-native.FCMacro"
    macro.write_text(
        f"import sys\nsys.path.insert(0,{str(ROOT)!r})\nfrom cad.video import start\nstart({str(folder)!r})\n"
    )
    with (folder / "video-render.log").open("w") as log:
        process = subprocess.Popen(
            [args.freecad, str(macro)], stdout=log, stderr=subprocess.STDOUT
        )
        deadline = time.monotonic() + 1800
        while not report.exists():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError(f"No completed video report; inspect {log.name}")
            time.sleep(1)
    result = json.loads(report.read_text())
    if result.get("passed") is not True:
        raise RuntimeError(result)
    frames = folder / "video-frames"
    assert all(
        (frames / f"frame-{i:04d}.png").exists() for i in range(result["frames"])
    )
    video = folder / "processor-build123d.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(result["fps"]),
            "-i",
            str(frames / "frame-%04d.png"),
            "-frames:v",
            str(result["frames"]),
            "-c:v",
            "libx264",
            "-crf",
            "19",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(video),
        ],
        check=True,
        capture_output=True,
    )
    metadata = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(video),
            ],
            text=True,
        )
    )
    stream = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    assert int(stream["nb_frames"]) == result["frames"] and (
        stream["width"],
        stream["height"],
    ) == (1280, 720)
    (folder / "video-encoding.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(video)


if __name__ == "__main__":
    main()
