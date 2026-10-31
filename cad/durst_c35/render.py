"""Render actual exported carrier surfaces and a transverse material section."""

import argparse
import json
from pathlib import Path

import build123d as bd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh


def raster(mesh):
    """Orthographic depth-buffer rendering avoids mplot3d's triangle-sort artifacts."""
    width, height = 1100, 700
    eye = np.array([0.424, -0.734, 0.530])
    eye /= np.linalg.norm(eye)
    right = np.cross([0, 0, 1], eye)
    right /= np.linalg.norm(right)
    up = np.cross(eye, right)
    points = mesh.vertices @ np.stack([right, up, eye], axis=1)
    center = (points.min(axis=0) + points.max(axis=0)) / 2
    points -= center
    scale = min(
        (width - 70) / np.ptp(points[:, 0]), (height - 70) / np.ptp(points[:, 1])
    )
    points[:, :2] *= scale
    points[:, 0] += width / 2
    points[:, 1] = height / 2 - points[:, 1]
    image = np.full((height, width, 3), np.array([243, 241, 234]) / 255.0)
    depth = np.full((height, width), -np.inf)
    light = np.array([-0.4, -0.5, 0.8])
    light /= np.linalg.norm(light)
    for face, normal in zip(mesh.faces, mesh.face_normals):
        if normal @ eye <= 0:
            continue
        tri = points[face]
        xmin, ymin = np.maximum(np.floor(tri[:, :2].min(axis=0)).astype(int), [0, 0])
        xmax, ymax = np.minimum(
            np.ceil(tri[:, :2].max(axis=0)).astype(int), [width - 1, height - 1]
        )
        x, y = np.meshgrid(
            np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5
        )
        a, b, c = tri
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-10:
            continue
        u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / den
        v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / den
        w = 1 - u - v
        z = u * a[2] + v * b[2] + w * c[2]
        region = depth[ymin : ymax + 1, xmin : xmax + 1]
        mask = (u >= -1e-8) & (v >= -1e-8) & (w >= -1e-8) & (z > region)
        region[mask] = z[mask]
        color = np.array([0.42, 0.54, 0.59]) * (0.48 + 0.52 * max(0, normal @ light))
        image[ymin : ymax + 1, xmin : xmax + 1][mask] = color
    return image


def render(out):
    p = json.loads((out / "parameters.json").read_text())
    meshes = {}
    for half in "ab":
        shape = bd.import_step(out / f"{half}.step")
        path = out / f"view-{half}.stl"
        bd.export_stl(shape, path, tolerance=0.03, angular_tolerance=0.1)
        meshes[half] = trimesh.load_mesh(path)
    fig = plt.figure(figsize=(13, 6), facecolor="#f3f1ea")
    for i, half in enumerate("ab", 1):
        ax = fig.add_subplot(1, 2, i, facecolor="#f3f1ea")
        mesh = meshes[half].copy()
        if half == "a":
            mesh.apply_transform(np.diag([1, 1, -1, 1]))
        ax.imshow(raster(mesh))
        ax.set_axis_off()
        ax.set_title(f"{half.upper()} — exterior facing up", fontsize=14)
    fig.suptitle("Durst C35 · V0.2 thin formed panels", fontsize=20, y=0.97)
    fig.text(
        0.5,
        0.05,
        f"{p['sheet_thickness']:g} mm provisional sheet · raised window rim stays local · no enlarger fit claim",
        ha="center",
        fontsize=12,
    )
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.1, wspace=0.03)
    fig.savefig(out / "preview-shells.png", dpi=160)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(13, 4), facecolor="#f3f1ea")
    ax.set_facecolor("#f3f1ea")
    for half, color in [("a", "#385464"), ("b", "#6f9299")]:
        mesh = meshes[half].copy()
        if half == "b":
            mesh.apply_translation([0, 0, p["film_gap"]])
        section = mesh.section(
            plane_origin=[0, p["window_center_y"], 0], plane_normal=[0, 1, 0]
        )
        for entity in section.entities:
            assert entity.closed
            loop = entity.discrete(section.vertices)
            ax.fill(loop[:, 0], loop[:, 2], color=color)
    ax.set(
        xlim=(-50, 50),
        ylim=(-16, 17),
        xlabel="Across carrier X (mm)",
        ylabel="Height Z (mm)",
    )
    ax.set_aspect("equal")
    ax.set_title(
        "Closed carrier · actual transverse section through the aperture",
        fontsize=17,
        pad=14,
    )
    ax.annotate(
        f"{p['sheet_thickness']:g} mm sheet per half\n{2 * p['sheet_thickness'] + p['film_gap']:g} mm closed sheet stack",
        xy=(32, -0.6),
        xytext=(23, -10),
        arrowprops={"arrowstyle": "->"},
        fontsize=11,
    )
    ax.annotate(
        f"Local window rim\n{p['window_rim_height']:g} mm per half",
        xy=(-20, 2),
        xytext=(-15, 9),
        arrowprops={"arrowstyle": "->"},
        fontsize=11,
    )
    ax.text(0, -14, f"{p['window_x']:g} mm clear opening", ha="center", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out / "section.png", dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    render(parser.parse_args().output.resolve())
