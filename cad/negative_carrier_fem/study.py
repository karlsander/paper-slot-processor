"""Run reusable, hashed B1 flexure and jaw-contact studies.

No yield curve, temperature curve, creep law or friction measurements are
invented: constitutive limitations and sensitivity inputs accompany every run.
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np

from .cases import NOTES, geometry, mating_geometry
from .solver import (
    CCX,
    cached_mesh,
    contact_deck,
    elastic_deck,
    frd_fields,
    read_dat,
    sha,
    solve,
    stress_metrics,
)

ROOT = Path(__file__).resolve().parents[2]


def run(
    name,
    size,
    scale=1,
    mu=0.3,
    penalty=100000,
    interference=0.1,
    executable=CCX,
    side=1,
    elastic_mates=False,
    mate_cut=20,
):
    tag = f"{name}-{size:g}"
    if name == "clip-contact":
        tag = f"contact-{size:g}-{mu:g}-side{side}"
    if scale != 1:
        tag += f"-E{scale:g}"
    if penalty != 100000:
        tag += f"-K{penalty:g}"
    if interference != 0.1:
        tag += f"-gap{interference:g}"
    if elastic_mates:
        tag += f"-mates{mate_cut:g}-mortar"
    folder = ROOT / "build/negative-carrier-fem" / tag
    xyz, conn, info = cached_mesh(geometry(name), folder, size)
    if name == "clip-contact":
        mates = None
        if elastic_mates:
            mates = {
                key: cached_mesh(shape, folder / key.lower(), size)
                for key, shape in mating_geometry(side, mate_cut).items()
            }
        deck, bc = contact_deck(
            xyz, conn, scale, mu, penalty, interference, side, mates
        )
        bc["mate_cut_y_mm"] = mate_cut if elastic_mates else None
    else:
        deck, bc = elastic_deck(name, xyz, conn, scale, isotropic=name == "benchmark")
    prior = folder / "job.inp"
    cached = (
        prior.exists()
        and prior.read_text() == deck
        and (folder / "solver.log").exists()
    )
    if cached:
        log = (folder / "solver.log").read_text()
        cached = "Job finished" in log and "*ERROR" not in log
    print(f"{'Reusing' if cached else 'Solving'} {tag}: {len(xyz)} nodes", flush=True)
    if not cached:
        solve(folder, deck, executable)
    results = read_dat(folder / "job.dat")
    expected = 3 if name == "clip-contact" else (1 if name == "benchmark" else 4)
    assert len(results) == expected and results[-1]["time"] == expected
    # Support reactions must balance applied displacement reactions. Rigid-body
    # support references are separate nodes, as required by the CCX manual.
    history = []
    mortar_fields = (
        [r["CONTACT"] for r in frd_fields(folder / "job.frd") if "CONTACT" in r]
        if elastic_mates
        else []
    )
    if elastic_mates:
        assert len(mortar_fields) == expected, "Missing solved mortar contact fields"
    catch_fields = (
        [r["DISP"] for r in frd_fields(folder / "job.frd") if "DISP" in r]
        if name == "clip-catch"
        else []
    )
    for i, r in enumerate(results):
        stress = r["stress"]
        metrics = stress_metrics(stress)
        error = float(
            np.linalg.norm(np.array(r["fix_force"]) + np.array(r["load_force"]))
        )
        force = float(np.linalg.norm(r["load_force"]))
        assert error < max(1e-5, force * 0.005), (tag, error, force)
        row = {
            "step": i + 1,
            "reaction_load_n": r["load_force"],
            "reaction_support_n": r["fix_force"],
            "equilibrium_error_n": error,
            **metrics,
        }
        if name == "clip-contact":
            centers = xyz[conn[r["integration_elements"] - 1, :4] - 1].mean(axis=1)
            jaw = centers[:, 1] < 24.5
            row["jaw_region_stress"] = stress_metrics(stress[jaw])
            row["jaw_region_definition"] = (
                "element corner centroid Y < 24.5 mm; excludes concentrated back supports"
            )
            row.update(
                top_force_n=r["top_force"],
                bottom_force_n=r["bottom_force"],
                normal_force_per_jaw_n=(
                    abs(r["top_force"][2]) + abs(r["bottom_force"][2])
                )
                / 2,
                pull_force_n=abs(r["load_force"][1]),
            )
        else:
            row["displacement_mm"] = bc["travel_mm"] * (i + 1) / expected
            row["actuation_force_n"] = abs(r["load_force"][bc["axis"] - 1])
        if mortar_fields:
            values = np.array(list(mortar_fields[i].values()))
            assert values.shape[1] == 6
            r["contact_displacement"] = values[:, :3]
            r["contact_stress"] = values[:, 3:6]
            row["contact_metrics_location"] = "mortar slave nodes; unweighted fractions"
        if "contact_stress" in r:
            c = r["contact_stress"]
            active = c[:, 0] > 1e-3
            ratio = np.linalg.norm(c[active, 1:3], axis=1) / c[active, 0]
            row.update(
                contact_pressure_max_mpa=float(c[:, 0].max()),
                contact_penetration_max_mm=float(
                    max(0, -r["contact_displacement"][:, 0].min())
                ),
                contact_points_at_coulomb_fraction=float(np.mean(ratio >= mu * 0.98))
                if mu
                else None,
                friction_ratio_max=float(ratio.max()) if len(ratio) else 0,
                slide_mm=[0, 0.05, 0.15][i],
            )
        if catch_fields:
            top = np.flatnonzero(
                (xyz[:, 0] >= 1.6 - 1e-6)
                & (xyz[:, 0] <= 3.2 + 1e-6)
                & (xyz[:, 1] >= 22.5 - 1e-6)
                & (xyz[:, 1] <= 23.1 + 1e-6)
                & (np.abs(xyz[:, 2] + 0.25) < 1e-6)
            )
            assert len(top)
            z = xyz[top, 2] + np.array([catch_fields[i][int(n + 1)][2] for n in top])
            row["catch_top_max_z_mm"] = float(z.max())
            row["catch_clearance_to_nominal_base_mm"] = float(-0.45 - z.max())
            row["catch_clearance_scope"] = (
                "isolated release fixture; excludes simultaneous jaw/frame deformation"
            )
        strain = r.get("strain")
        if strain is not None:
            row["max_abs_strain_component"] = float(np.abs(strain).max())
        history.append(row)
    result = {
        "id": tag,
        "case": name,
        "notes": NOTES[name]
        + (
            f" Elastic local frame slices with clamped remote cut at Y={mate_cut} mm; full film/frame compliance is not solved."
            if elastic_mates
            else ""
        ),
        "mesh": info,
        "boundary": bc,
        "material_scale": scale,
        "temperature_c_requested": 35,
        "temperature_calibrated": False,
        "plasticity_calibrated": False,
        "creep_calibrated": False,
        "cad_source_sha256": sha(ROOT / "cad/negative_carrier_b/model.py"),
        "solver": "CalculiX; NLGEOM; C3D10; engineering-constants elasticity",
        "solver_version": re.search(
            r"CalculiX Version ([^,\n]+)", (folder / "solver.log").read_text()
        )[1],
        "history": history,
        "input_sha256": sha(prior),
        "frd_sha256": sha(folder / "job.frd"),
        "dat_sha256": sha(folder / "job.dat"),
        "log_sha256": sha(folder / "solver.log"),
    }
    if name == "benchmark":
        analytic = 2780 * scale * 0.01 / (4 * 10**3)
        result["analytical_force_n"] = analytic
        result["relative_force_error"] = abs(
            history[-1]["actuation_force_n"] / analytic - 1
        )
        assert result["relative_force_error"] < 0.03
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"id": tag, "last": history[-1]}), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("case", choices=list(NOTES))
    p.add_argument("--size", type=float, required=True)
    p.add_argument("--scale", type=float, default=1)
    p.add_argument("--mu", type=float, default=0.3)
    p.add_argument("--penalty", type=float, default=100000)
    p.add_argument("--interference", type=float, default=0.1)
    p.add_argument("--elastic-mates", action="store_true")
    p.add_argument("--mate-cut", type=float, default=20)
    p.add_argument("--side", type=int, choices=[-1, 1], default=1)
    p.add_argument("--ccx", default=CCX)
    args = p.parse_args()
    assert (
        18 <= args.mate_cut <= 21.8
        and (not args.elastic_mates or args.case == "clip-contact")
        and 0.01 <= args.size <= 1
        and 0 < args.scale <= 2
        and 0 <= args.mu <= 1
        and args.penalty > 0
        and args.interference > 0
    )
    run(
        args.case,
        args.size,
        args.scale,
        args.mu,
        args.penalty,
        args.interference,
        args.ccx,
        args.side,
        args.elastic_mates,
        args.mate_cut,
    )


if __name__ == "__main__":
    main()
