"""Render solved nodal fields, not prescribed animation geometry."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv

from .solver import frd_fields

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/negative-carrier-fem"
DOC = ROOT / "docs/negative-carrier-b/forces"


def field_image(case, filename, magnification, view, scalar_max=None):
    folder = OUT / case
    archive = np.load(folder / "mesh.npz")
    xyz, conn = archive["xyz"], archive["conn"]
    fields = frd_fields(folder / "job.frd")
    step = 0 if case.startswith("contact") else -1
    displacement = [r["DISP"] for r in fields if "DISP" in r][step]
    stresses = [r["STRESS"] for r in fields if "STRESS" in r][step]
    u = np.array([displacement[i] for i in range(1, len(xyz) + 1)])
    s = np.array([stresses[i] for i in range(1, len(xyz) + 1)])
    xx, yy, zz, xy, yz, zx = s[:, :6].T  # FRD order differs from DAT
    mises = np.sqrt(
        0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2)
        + 3 * (xy**2 + yz**2 + zx**2)
    )
    cells = np.column_stack([np.full(len(conn), 10), conn - 1]).ravel()
    grid = pv.UnstructuredGrid(
        cells, np.full(len(conn), pv.CellType.QUADRATIC_TETRA), xyz
    )
    plotter = pv.Plotter(off_screen=True, window_size=(1000, 560))
    plotter.set_background("#f5f3ee")
    plotter.add_mesh(grid, color="#525c69", opacity=0.18)
    deformed = grid.copy()
    deformed.points = xyz + u[:, :3] * magnification
    deformed["Mises MPa"] = mises
    plotter.add_mesh(
        deformed,
        scalars="Mises MPa",
        cmap="turbo",
        clim=(0, scalar_max) if scalar_max else None,
        ambient=0.35,
        smooth_shading=False,
        scalar_bar_args={
            "title": "Nodal averaged Mises (MPa)",
            "color": "#18272b",
            "width": 0.65,
            "height": 0.08,
            "position_x": 0.18,
            "position_y": 0.04,
        },
    )
    node_offset = len(xyz)
    if "mates" in case:
        for name in ["top", "bottom"]:
            mate = np.load(folder / name / "mesh.npz")
            mp, mc = mate["xyz"], mate["conn"]
            mu = np.array(
                [
                    displacement[i]
                    for i in range(node_offset + 1, node_offset + len(mp) + 1)
                ]
            )
            mg = pv.UnstructuredGrid(
                np.column_stack([np.full(len(mc), 10), mc - 1]).ravel(),
                np.full(len(mc), pv.CellType.QUADRATIC_TETRA),
                mp + mu[:, :3] * magnification,
            )
            plotter.add_mesh(mg, color="#78939c", opacity=0.23)
            node_offset += len(mp)
    if view == "xy":
        plotter.view_xy()
    elif view == "xz":
        plotter.view_xz()
    else:
        center = np.mean(xyz, axis=0)
        offset = (18, -18, -12 if case.startswith("clip-catch") else 12)
        plotter.camera_position = [tuple(center + offset), tuple(center), (0, 0, 1)]
    plotter.enable_parallel_projection()
    plotter.reset_camera()
    plotter.camera.zoom(0.9 if case.startswith("index-tip") else 1.05)
    plotter.screenshot(str(filename))
    plotter.close()


def main():
    DOC.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor="#f5f3ee")
    for ax, case, label in zip(
        axes,
        ["contact-0.4-0.3-side1", "contact-0.55-0.3-side1-mates20-mortar"],
        ["Rigid mating frame", "Elastic local frame"],
    ):
        image_path = DOC / f"{case}-compare.png"
        field_image(case, image_path, 3, "iso", scalar_max=120)
        r = json.loads((OUT / case / "result.json").read_text())["history"][0]
        ax.imshow(plt.imread(image_path))
        ax.axis("off")
        ax.set_title(
            f"{label}: {r['normal_force_per_jaw_n']:.2f} N per jaw at seating",
            loc="left",
            fontsize=13,
        )
    fig.suptitle(
        "Frame flexibility changes clip preload — same 0.1 mm imposed interference",
        fontsize=17,
    )
    fig.text(
        0.025,
        0.025,
        "Shared stress scale; deformation ×3. Local frame slices have held inner cut faces. These are fixture-dependent elastic results, not a complete-holder grip rating.",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    fig.savefig(DOC / "jaw-compliance.png", dpi=160)
    plt.close(fig)
    panels = [
        (
            "index-0.4",
            "Main index latch",
            1,
            "xy",
            "4 mm travel: elastic model exceeds strength",
        ),
        (
            "index-tip-0.085",
            "Index clearance leaf",
            4,
            "xy",
            "0.2 mm take-up: root stress concern",
        ),
        ("guide-0.2", "Lateral guide spring", 8, "xy", "0.2 mm take-up: only 0.70 mN"),
        ("roof-0.2", "One roof spring", 8, "xz", "0.2 mm lift: only 3.08 mN"),
        (
            "clip-catch-0.22",
            "Clip release tongue",
            3,
            "iso",
            "Low stress; catch still ~0.022 mm proud",
        ),
        (
            "contact-0.55-0.3-side1-mates20-mortar",
            "Front clip with local frame",
            3,
            "iso",
            "0.1 mm interference; frame compliance included",
        ),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(16, 13), facecolor="#f5f3ee")
    for ax, (case, title, factor, view, subtitle) in zip(axes.flat, panels):
        path = DOC / f"{case}.png"
        field_image(case, path, factor, view)
        ax.imshow(plt.imread(path))
        ax.axis("off")
        ax.set_title(
            f"{title}  |  deformation ×{factor}\n{subtitle}",
            fontsize=12,
            loc="left",
            color="#18272b",
        )
    fig.suptitle(
        "PETG force study — solved finite-element deformation",
        fontsize=22,
        color="#18272b",
        y=0.985,
    )
    fig.text(
        0.025,
        0.012,
        "Grey: relaxed geometry. Each colour scale is independent.\n"
        "Requested service: 35 °C. Baseline uses published tensile moduli; no calibrated temperature, plasticity or creep law.\n"
        "Above-strength fields show elastic demand, not stresses the printed part can sustain.",
        fontsize=11,
        color="#18272b",
    )
    fig.tight_layout(rect=(0.01, 0.07, 0.99, 0.95))
    fig.savefig(DOC / "stress-overview.png", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), facecolor="#f5f3ee")
    for ax, (case, title, _, _, _) in zip(axes.flat, panels):
        if case.startswith("contact"):
            continue
        data = json.loads((OUT / case / "result.json").read_text())
        history = data["history"]
        d = [0] + [abs(r["displacement_mm"]) for r in history]
        f = [0] + [r["actuation_force_n"] for r in history]
        ax.plot(d, f, "o-", color="#176e79", label="Published-modulus baseline")
        ax.set_title(title, loc="left")
        ax.set_xlabel("Prescribed travel (mm)")
        ax.set_ylabel("Reaction (N)")
        ax.grid(alpha=0.2)
        ax.set_facecolor("#faf9f6")
        if case.startswith("index-") and not case.startswith("index-tip"):
            ax.text(
                0.03,
                0.83,
                "Large-stroke values are\ninvalid elastic extrapolation",
                transform=ax.transAxes,
                color="#a02c32",
                fontsize=9,
            )
    axes.flat[-1].axis("off")
    axes.flat[-1].text(
        0,
        0.85,
        "Interpretation\n\nNonlinear geometry; elastic material.\nNo plastic flow or damage model.\nNo calibrated 35 °C modulus.\nNo creep or lifetime prediction.\n\nFriction is analysed separately\nagainst actual frame contact areas.",
        va="top",
        fontsize=13,
    )
    fig.suptitle("Reaction force versus imposed travel", fontsize=20)
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    fig.savefig(DOC / "force-curves.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
