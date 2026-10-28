"""Render actual OpenFOAM fields as annotated section movies, not CAD fill animation."""

import argparse
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from analyze import mean


def reader(case):
    marker = case / "case.foam"
    marker.touch()
    result = pv.OpenFOAMReader(marker)
    result.skip_zero_time = False
    return result


def sample(mesh, points, field):
    data = pv.PolyData(points).sample(mesh)
    values = np.array(data[field], dtype=float)
    values[data["vtkValidPointMask"] == 0] = np.nan
    return values


def plane(xs, zs, y):
    x, z = np.meshgrid(xs, zs)
    return np.column_stack([x.ravel(), np.full(x.size, y), z.ravel()])


def encode(frames, output, fps):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            str(frames / "%04d.png"),
            "-vf",
            "fps=30",
            "-c:v",
            "libx264",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )


def thermal(root, output):
    output.mkdir(parents=True, exist_ok=True)
    frames = output / "thermal-frames"
    frames.mkdir(exist_ok=True)
    cases = ["hot-38C-0W", "hot-38C-5W", "cold-20C-5W"]
    readers = [reader(root / case) for case in cases]
    xs = np.linspace(0.00305, 0.12495, 90)
    zs = np.linspace(0.00405, 0.19366, 140)
    points = plane(xs, zs, 0.010)
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor="#f7f7f5")
    gs = fig.add_gridspec(
        1,
        4,
        left=0.065,
        right=0.95,
        bottom=0.2,
        top=0.84,
        wspace=0.42,
        width_ratios=[1, 1, 1, 1.7],
    )
    axes = [fig.add_subplot(gs[0, i]) for i in range(3)]
    curve = fig.add_subplot(gs[0, 3])
    images = []
    texts = []
    for ax, title in zip(
        axes, ["38°C fill · heater off", "38°C fill · 5 W", "20°C fill · 5 W"]
    ):
        images.append(
            ax.imshow(
                np.zeros((len(zs), len(xs))),
                origin="lower",
                extent=[3, 125, 4, 193.7],
                vmin=20,
                vmax=38,
                cmap="inferno",
                aspect="equal",
            )
        )
        ax.set(title=title, xlabel="Width (mm)")
        ax.set_ylim(0, 205)
        texts.append(
            ax.text(0.5, -0.18, "", transform=ax.transAxes, ha="center", fontsize=10)
        )
    axes[0].set_ylabel("Height (mm)")
    colors = ["#407cad", "#d26923", "#32856b"]
    for case, color, label in zip(
        cases, colors, ["38°C / off", "38°C / 5 W", "20°C / 5 W"]
    ):
        data = mean(root / case)
        curve.plot(data[:, 0] / 60, data[:, 1] - 273.15, color=color, lw=2, label=label)
    curve.legend(fontsize=8, loc="upper right")
    curve.set(
        xlim=(0, 60),
        ylim=(19, 39),
        xlabel="Minutes",
        ylabel="Mean liquid temperature (°C)",
    )
    curve.grid(alpha=0.2)
    cursor = curve.axvline(0, color="#333", lw=1)
    cax = fig.add_axes([0.12, 0.135, 0.40, 0.022])
    fig.colorbar(
        images[0],
        cax=cax,
        orientation="horizontal",
        label="Liquid temperature (°C) · common scale",
    )
    title = fig.suptitle("", fontsize=17, y=0.96)
    fig.text(
        0.065,
        0.025,
        "3D conjugate heat transfer · front section through water · room and vessel initially 20°C\nComputed fields; water proxy, assumed PETG/contact/air losses. Physical measurements still needed.",
        fontsize=10,
        color="#444",
    )
    for index, time in enumerate(range(0, 3601, 30)):
        title.set_text(f"Heating the bath with a 5 W pad  |  {time / 60:04.1f} min")
        for r, im, txt, case in zip(readers, images, texts, cases):
            r.set_active_time_value(time)
            mesh = r.read()["water"]["internalMesh"]
            values = sample(mesh, points, "T").reshape(len(zs), len(xs)) - 273.15
            im.set_data(values)
            cell = mesh.cell_data["T"] - 273.15
            txt.set_text(f"Cells: {cell.min():.1f}–{cell.max():.1f}°C")
        cursor.set_xdata([time / 60, time / 60])
        fig.savefig(frames / f"{index:04d}.png")
    plt.close(fig)
    encode(frames, output / "thermal-simulation.mp4", 6)


def fill(case, output):
    output.mkdir(parents=True, exist_ok=True)
    frames = output / (case.name + "-frames")
    frames.mkdir(exist_ok=True)
    r = reader(case)
    times = r.time_values
    xs = np.linspace(0.00005, 0.12195, 122)
    zs = np.linspace(0.00005, 0.20028, 200)
    points = plane(xs, zs, 0.007)
    ys = np.linspace(0.00005, 0.01395, 28)
    y, z = np.meshgrid(ys, zs)
    side = np.column_stack([np.full(y.size, 0.061), y.ravel(), z.ravel()])
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor="#f7f7f5")
    ax = fig.add_axes([0.08, 0.19, 0.44, 0.66])
    sideax = fig.add_axes([0.59, 0.19, 0.17, 0.66])
    note = fig.add_axes([0.8, 0.25, 0.19, 0.5])
    note.axis("off")
    a = ax.imshow(
        np.zeros((len(zs), len(xs))),
        origin="lower",
        extent=[0, 122, 0, 200.33],
        cmap="Blues",
        vmin=0,
        vmax=1,
        aspect="equal",
    )
    b = sideax.imshow(
        np.zeros((len(zs), len(ys))),
        origin="lower",
        extent=[0, 14, 0, 200.33],
        cmap="Blues",
        vmin=0,
        vmax=1,
        aspect="auto",
    )
    ax.set(
        xlabel="Width (mm)",
        ylabel="Height above bath floor (mm)",
        title="Front section · mid-depth",
    )
    sideax.set(xlabel="Depth (mm)", title="Side section\n(depth enlarged)")
    for item in (ax, sideax):
        item.axhline(189.71, ls="--", color="#d26923", lw=1)
    cax = fig.add_axes([0.80, 0.17, 0.16, 0.025])
    fig.colorbar(
        a, cax=cax, orientation="horizontal", ticks=[0, 0.5, 1], label="Water fraction"
    )
    title = fig.suptitle("", fontsize=18, y=0.95)
    import json

    s = json.loads((case / "scenario.json").read_text())
    note.text(
        0,
        0.95,
        f"{s['target_ml']} ml in {s['pour_seconds']:g} s\n\n12 × 6 mm jet\n\n{s['mesh_spacing_mm']:g} mm mesh target\n\nDashed line:\nCAD fill mark",
        va="top",
        fontsize=12,
    )
    fig.text(
        0.07,
        0.06,
        "OpenFOAM interFoam · 3D water/air volume-of-fluid calculation · playback 3× slower\nRectangularized cavity; prescribed jet. Splash quantities are mesh-sensitive and require testing.",
        fontsize=11,
        color="#444",
    )
    for index, time in enumerate(times):
        r.set_active_time_value(time)
        mesh = r.read()["internalMesh"]
        a.set_data(sample(mesh, points, "alpha.water").reshape(len(zs), len(xs)))
        b.set_data(sample(mesh, side, "alpha.water").reshape(len(zs), len(ys)))
        title.set_text(f"Filling the open bath  |  {time:.1f} s")
        fig.savefig(frames / f"{index:04d}.png")
    plt.close(fig)
    encode(frames, output / (case.name + ".mp4"), 10 / 3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["fill", "thermal"])
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    a = parser.parse_args()
    globals()[a.kind](a.source, a.output)
