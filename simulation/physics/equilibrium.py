"""Steady 3-D solid conduction with a well-mixed bulk-liquid node.

This is a separate heater-sizing approximation, not a steady CFD flow solution.
SI units throughout; conforming cells share harmonic face conductances.
"""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import spsolve

try:
    from .cases import thermal_geometry
except ImportError:
    from cases import thermal_geometry

K = {"petg": 0.2, "pad": 1.0, "aluminium": 205.0, "heater": 0.2}
SIGMA = 5.670374419e-8


class Model:
    def __init__(self, spacing=6, width=100, thickness=1.4, liquid_h=300):
        axes, material = thermal_geometry(width, thickness)
        axes = [
            np.unique(
                np.concatenate(
                    [
                        np.linspace(a, b, max(1, int(np.ceil((b - a) / step))) + 1)
                        for a, b in itertools.pairwise(axis)
                    ]
                )
            )
            for axis, step in zip(axes, [spacing / 1000, 0.002, spacing / 1000])
        ]
        centers = [(a[:-1] + a[1:]) / 2 for a in axes]
        sizes = [np.diff(a) for a in axes]
        cells = {}
        count = 1
        for ijk in itertools.product(*(range(len(c)) for c in centers)):
            mat = material(*[c[i] for c, i in zip(centers, ijk)])
            if mat:
                node = 0 if mat == "water" else count
                if node:
                    count += 1
                cells[ijk] = (mat, node, np.array([s[i] for s, i in zip(sizes, ijk)]))
        rows = []
        cols = []
        values = []
        external = []
        source = np.zeros(count)
        self.regions = {r: [] for r in K}
        for ijk, (mat, node, dims) in cells.items():
            if mat != "water":
                self.regions[mat].append(node)
            if mat == "heater":
                source[node] = np.prod(dims)
            for axis in range(3):
                area = np.prod(np.delete(dims, axis))
                for sign in [-1, 1]:
                    neighbor = list(ijk)
                    neighbor[axis] += sign
                    adj = cells.get(tuple(neighbor))
                    if adj:
                        other, j, dd = adj
                        if j == node or sign < 0:
                            continue
                        resistance = (
                            1 / liquid_h if mat == "water" else dims[axis] / 2 / K[mat]
                        )
                        resistance += (
                            1 / liquid_h
                            if other == "water"
                            else dd[axis] / 2 / K[other]
                        )
                        g = area / resistance
                        rows.extend([node, j, node, j])
                        cols.extend([node, j, j, node])
                        values.extend([g, g, -g, -g])
                    else:
                        r = 0 if mat == "water" else dims[axis] / 2 / K[mat]
                        external.append(
                            (
                                node,
                                area,
                                r,
                                0.15 if mat == "aluminium" else 0.9,
                                mat == "water",
                            )
                        )
        self.matrix = coo_matrix((values, (rows, cols)), shape=(count, count)).tocsr()
        self.source = source / source.sum()
        e = np.array(external)
        self.ext_nodes = e[:, 0].astype(int)
        self.area = e[:, 1]
        self.resistance = e[:, 2]
        self.epsilon = e[:, 3]
        self.water = e[:, 4].astype(bool)
        self.count = count
        self.cells = len(cells)

    def solve(self, power=15, air_h=5, room=20, surface_h=3):
        ambient = room + 273.15
        t = np.full(self.count, ambient + power)
        ts = t[self.ext_nodes].copy()
        h = np.where(self.water, surface_h, air_h)
        for iteration in range(100):
            hr = self.epsilon * SIGMA * (ts + ambient) * (ts * ts + ambient * ambient)
            ht = h + hr
            g = self.area / (self.resistance + 1 / ht)
            diagonal = np.bincount(self.ext_nodes, weights=g, minlength=self.count)
            new = spsolve(
                self.matrix + diags(diagonal), power * self.source + diagonal * ambient
            )
            surface = ambient + (new[self.ext_nodes] - ambient) / (
                1 + ht * self.resistance
            )
            error = np.max(np.abs(new - t))
            t = new
            ts = surface
            if error < 1e-8:
                break
        else:
            raise RuntimeError("Radiation iteration did not converge")
        loss = float(np.sum(g * (t[self.ext_nodes] - ambient)))
        residual = loss - power
        if abs(residual) > 1e-6:
            raise RuntimeError(f"Energy imbalance {residual} W")
        return {
            "power_W": power,
            "room_C": room,
            "air_h": air_h,
            "surface_h": surface_h,
            "liquid_C": float(t[0] - 273.15),
            "region_max_C": {
                r: float(max(t[nodes]) - 273.15) for r, nodes in self.regions.items()
            },
            "energy_residual_W": residual,
            "iterations": iteration + 1,
            "cells": self.cells,
            "solid_nodes": self.count - 1,
        }

    def required(self, target=35, **conditions):
        power = brentq(
            lambda p: self.solve(p, **conditions)["liquid_C"] - target, 0, 60, xtol=1e-7
        )
        return self.solve(power, **conditions)


def study(output):
    output.mkdir(parents=True, exist_ok=True)
    result = {
        "model": "3-D finite-volume solid conduction; one well-mixed liquid node",
        "assumptions": {
            "liquid_film_W_m2K": 300,
            "perfect_solid_contacts": True,
            "radiation": True,
            "evaporation_resolved": False,
            "base_neighbor_top_mass_omitted": True,
        },
        "cases": {},
    }
    cases = result["cases"]
    model = Model()
    for h in [3, 5, 8]:
        for power in [10, 15]:
            cases[f"RS-{power}W-h{h}"] = model.solve(power, air_h=h)
        for target in [30, 35, 38]:
            cases[f"required-{target}C-h{h}"] = model.required(target, air_h=h)
    cases["RS-15W-room18"] = model.solve(15, room=18)
    cases["RS-15W-high-surface-loss"] = model.solve(15, surface_h=30)
    cases["required-35C-high-surface-loss"] = model.required(35, surface_h=30)
    cases["original-5W"] = Model(width=140, thickness=3).solve(5)
    cases["mesh-3mm-15W"] = Model(spacing=3).solve(15)
    cases["film-100-15W"] = Model(liquid_h=100).solve(15)
    cases["film-500-15W"] = Model(liquid_h=500).solve(15)
    cases["zero-power"] = model.solve(0)
    result["heater_size_mm"] = [100, 150, 1.4]
    (output / "equilibrium.json").write_text(json.dumps(result, indent=2) + "\n")
    for name, row in cases.items():
        print(
            name,
            round(row["power_W"], 3),
            round(row["liquid_C"], 3),
            round(row["region_max_C"]["heater"], 3),
            flush=True,
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    study(p.parse_args().output)
