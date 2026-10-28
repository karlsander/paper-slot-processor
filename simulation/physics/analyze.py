"""Reduce OpenFOAM function output, including restarted runs, to auditable results."""

import argparse
import json
import re
from pathlib import Path

import numpy as np


def table(paths):
    """Join numeric function tables; newer restart data wins at duplicate times."""
    rows = {}
    for path in sorted(paths, key=lambda p: float(p.parent.name)):
        for line in path.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                values = list(map(float, line.split()))
                rows[values[0]] = values
    if not rows:
        raise ValueError("No function output")
    return np.array([rows[t] for t in sorted(rows)])


def liquid_flux(phi, rho_phi, rho_water=1000, rho_air=1):
    """Recover water volume flux from mixture mass and total volume flux."""
    return (rho_phi - rho_air * phi) / (rho_water - rho_air)


def check_complete(case, end):
    logs = list(case.glob("log.*"))
    texts = [
        p.read_text()
        for p in logs
        if p.name
        in ("log.solver", "log.parallel", "log.chtMultiRegionFoam", "log.interFoam")
    ]
    for text in texts:
        times = re.findall(r"^Time = ([\d.e+-]+)", text, re.MULTILINE)
        if (
            times
            and float(times[-1]) >= end - 1e-3
            and re.search(r"^End$", text, re.MULTILINE)
        ):
            return
    raise ValueError(f"{case}: no completed solver log through {end} s")


def fill(case):
    s = json.loads((case / "scenario.json").read_text())
    end = s["pour_seconds"] + 2
    check_complete(case, end)
    volume = table(case.glob("postProcessing/volume/*/*.dat"))
    fluxes = {}
    for patch in ("inlet", "outlet"):
        data = table(case.glob(f"postProcessing/{patch}Flux/*/*.dat"))
        flux = liquid_flux(data[:, 1], data[:, 2])
        # Include the prescribed t=0 boundary value in the quadrature.
        initial = -s["target_ml"] * 1e-6 / s["pour_seconds"] if patch == "inlet" else 0
        fluxes[patch] = float(
            np.trapezoid(np.r_[initial, flux], np.r_[0, data[:, 0]]) * 1e6
        )
    stored = float(volume[-1, 1] * 1e6)
    return {
        "case": case.name,
        "spacing_mm": s["mesh_spacing_mm"],
        "pour_seconds": s["pour_seconds"],
        "last_volume_time_s": float(volume[-1, 0]),
        "injected_ml": -fluxes["inlet"],
        "escaped_ml": fluxes["outlet"],
        "stored_ml": stored,
        "balance_residual_ml": -fluxes["inlet"] - fluxes["outlet"] - stored,
    }


def mean(case, region="water"):
    return table(case.glob(f"postProcessing/{region}/{region}Mean/*/*.dat"))


def extrema(case, region):
    rows = {}
    for path in sorted(
        case.glob(f"postProcessing/{region}/{region}Extrema/*/*.dat"),
        key=lambda p: float(p.parent.name),
    ):
        for line in path.read_text().splitlines():
            a = line.split()
            if len(a) > 6 and a[1] == "T":
                rows[float(a[0])] = [
                    float(a[0]),
                    float(a[2]) - 273.15,
                    float(a[6]) - 273.15,
                ]
    return np.array([rows[t] for t in sorted(rows)])


def thermal(case):
    s = json.loads((case / "scenario.json").read_text())
    check_complete(case, s["end_seconds"])
    end = min(mean(case, r)[-1, 0] for r in s["materials"])
    stored = loss = initial_excess = 0
    for r, (rho, cp, _) in s["materials"].items():
        ti = s["liquid_initial_c"] if r == "water" else s["solid_initial_c"]
        capacity = rho * cp * s["volumes_m3"][r]
        data = mean(case, r)
        stored += capacity * (np.interp(end, data[:, 0], data[:, 1]) - 273.15 - ti)
        initial_excess += capacity * abs(ti - s["room_c"])
        patches = {}
        for path in case.glob(f"postProcessing/{r}/{r}HeatFlux/*/*.dat"):
            for line in path.read_text().splitlines():
                if not line.strip() or line.startswith("#"):
                    continue
                a = line.split()
                if "_to_" not in a[1] and float(a[0]) <= end:
                    patches.setdefault(a[1], {})[float(a[0])] = float(a[-1])
        for values in patches.values():
            t = np.array(sorted(values))
            q = np.array([values[v] for v in t])
            loss -= np.trapezoid(q, t)
    supplied = s["power_w"] * end
    residual = stored + loss - supplied
    times = [t for t in (60, 300, 600, 1800, 3600) if t <= s["end_seconds"]]
    water_range = extrema(case, "water")
    # Use saved fields at exact reporting times, not the nearest function sample.
    import pyvista as pv

    marker = case / "case.foam"
    marker.touch()
    reader = pv.OpenFOAMReader(marker)
    field_means = {}
    cell_ranges = {}
    for t in times:
        reader.set_active_time_value(t)
        mesh = reader.read()["water"]["internalMesh"]
        volumes = mesh.compute_cell_sizes(length=False, area=False)["Volume"]
        temperatures = mesh.cell_data["T"] - 273.15
        field_means[str(t)] = float(np.average(temperatures, weights=volumes))
        cell_ranges[str(t)] = [float(temperatures.min()), float(temperatures.max())]
    return {
        "case": case.name,
        "mean_c": field_means,
        "cell_range_c": cell_ranges,
        "water_range_including_boundaries_c": {
            str(t): [
                float(np.interp(t, water_range[:, 0], water_range[:, i]))
                for i in (1, 2)
            ]
            for t in times
        },
        "all_time_water_range_c": [
            float(water_range[:, 1].min()),
            float(water_range[:, 2].max()),
        ],
        "balance_time_s": float(end),
        "stored_sensible_J": float(stored),
        "input_J": float(supplied),
        "external_loss_J": float(loss),
        "balance_residual_J": float(residual),
        "balance_residual_percent_of_energy_scale": float(
            100 * abs(residual) / max(initial_excess, supplied, 1)
        ),
        "balance_definition": "Constant reference density Cp sensible storage; initial excess or supplied heat is the scale. Boussinesq approximation, initial boundary transient and sampled flux quadrature contribute residual.",
    }


def main(root, output):
    output.mkdir(parents=True, exist_ok=True)
    results = {"thermal": [], "fill": []}
    for name in (
        "hot-38C-5W",
        "hot-38C-0W",
        "cold-20C-5W",
        "cold-20C-0W",
        "preheated-38C-5W",
        "hot-still-air",
        "hot-draft",
        "hot-surface-loss",
        "hot-smallstep",
        "hot-refined",
        "hot-startup-check",
    ):
        if (root / name).exists():
            results["thermal"].append(thermal(root / name))
    for name in ("fill-fast-budget", "fill-fine", "fill-finer", "fill-slow"):
        if (root / name).exists():
            results["fill"].append(fill(root / name))
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5.5), layout="constrained")
    for name, label, color in [
        ("hot-38C-5W", "38°C fill · 5 W", "#d26923"),
        ("hot-38C-0W", "38°C fill · heater off", "#407cad"),
        ("cold-20C-5W", "20°C fill · 5 W", "#32856b"),
        ("preheated-38C-5W", "Vessel + fill preheated to 38°C · 5 W", "#9765ac"),
    ]:
        data = mean(root / name)
        s = json.loads((root / name / "scenario.json").read_text())
        ax.plot(
            np.r_[0, data[:, 0]] / 60,
            np.r_[s["liquid_initial_c"], data[:, 1] - 273.15],
            label=label,
            color=color,
            lw=2,
        )
    ax.set(
        xlabel="Minutes after fill",
        ylabel="Mean liquid temperature (°C)",
        ylim=(19, 39),
        xlim=(0, 60),
        title="One bath in a 20°C room · OpenFOAM conjugate heat transfer",
    )
    ax.grid(alpha=0.2)
    ax.legend(loc="upper right", fontsize=9)
    fig.text(
        0.5,
        0.005,
        "Water proxy · assumed materials and air losses · predictions require measurement",
        ha="center",
        fontsize=9,
    )
    fig.savefig(output / "thermal-curves.png", dpi=160)
    plt.close(fig)
    with (output / "thermal-curves.csv").open("w") as file:
        file.write("case,time_s,mean_water_c\n")
        for entry in results["thermal"]:
            for t, temp in mean(root / entry["case"]):
                file.write(f"{entry['case']},{t:.8g},{temp - 273.15:.8g}\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.root, args.output)
