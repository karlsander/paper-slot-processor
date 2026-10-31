"""Reproduce or collect the fixed verification matrix; exclude abandoned pilots."""

import argparse
import json
import os
import re
import subprocess

from .solver import CCX, sha
from .study import ROOT, run

MATRIX = (
    [
        ("benchmark", 0.35, {}),
        ("index", 0.55, {}),
        ("index", 0.4, {}),
        ("index-pinned", 0.55, {}),
        ("index-tip", 0.12, {}),
        ("index-tip", 0.085, {}),
        ("guide", 0.3, {}),
        ("guide", 0.2, {}),
        ("roof", 0.3, {}),
        ("roof", 0.2, {}),
        ("clip-catch", 0.3, {}),
        ("clip-catch", 0.22, {}),
    ]
    + [
        (name, size, {"scale": 0.7})
        for name, size in [
            ("index", 0.55),
            ("index-tip", 0.12),
            ("guide", 0.3),
            ("roof", 0.3),
            ("clip-catch", 0.3),
        ]
    ]
    + [
        ("clip-contact", size, {"side": side})
        for side in [1, -1]
        for size in [0.55, 0.4]
    ]
    + [
        ("clip-contact", 0.55, {"mu": 0}),
        ("clip-contact", 0.55, {"mu": 0.6}),
        ("clip-contact", 0.55, {"penalty": 200000}),
        ("clip-contact", 0.55, {"scale": 0.7}),
        ("clip-contact", 0.55, {"scale": 0.7, "side": -1}),
    ]
)

MATRIX += [
    ("clip-contact", 0.55, {"elastic_mates": True}),
    ("clip-contact", 0.4, {"elastic_mates": True}),
    ("clip-contact", 0.55, {"elastic_mates": True, "side": -1}),
    ("clip-contact", 0.55, {"elastic_mates": True, "scale": 0.7}),
]


def write_summary(results):
    out = ROOT / "build/negative-carrier-fem"
    docs = ROOT / "docs/negative-carrier-b/forces"
    docs.mkdir(parents=True, exist_ok=True)
    for result in results:
        folder = out / result["id"]
        for file, key in [
            ("job.inp", "input_sha256"),
            ("job.frd", "frd_sha256"),
            ("job.dat", "dat_sha256"),
            ("solver.log", "log_sha256"),
        ]:
            assert sha(folder / file) == result[key], (result["id"], file)
        log = (folder / "solver.log").read_text()
        assert "Job finished" in log and "*ERROR" not in log
        result["solver_version"] = re.search(r"CalculiX Version ([^,\n]+)", log)[1]
    by_id = {r["id"]: r for r in results}
    mesh_pairs = [
        ("index-0.55", "index-0.4"),
        ("index-tip-0.12", "index-tip-0.085"),
        ("guide-0.3", "guide-0.2"),
        ("roof-0.3", "roof-0.2"),
        ("clip-catch-0.3", "clip-catch-0.22"),
    ]
    convergence = []
    for coarse, fine in mesh_pairs:
        a, b = [by_id[k]["history"][-1]["actuation_force_n"] for k in (coarse, fine)]
        convergence.append(
            {
                "coarse": coarse,
                "fine": fine,
                "force_change_percent": 100 * abs(b / a - 1),
            }
        )
    for side in [1, -1]:
        coarse, fine = f"contact-0.55-0.3-side{side}", f"contact-0.4-0.3-side{side}"
        for step in [0, 2]:
            for key in ["normal_force_per_jaw_n", "pull_force_n"]:
                a, b = [by_id[k]["history"][step][key] for k in (coarse, fine)]
                convergence.append(
                    {
                        "coarse": coarse,
                        "fine": fine,
                        "step": step + 1,
                        "quantity": key,
                        "force_change_percent": 100 * abs(b / a - 1) if a else None,
                    }
                )
    if "contact-0.55-0.3-side1-mates20-mortar" in by_id:
        coarse, fine = (
            "contact-0.55-0.3-side1-mates20-mortar",
            "contact-0.4-0.3-side1-mates20-mortar",
        )
        for step in [0, 2]:
            for key in ["normal_force_per_jaw_n", "pull_force_n"]:
                a, b = [by_id[k]["history"][step][key] for k in (coarse, fine)]
                convergence.append(
                    {
                        "coarse": coarse,
                        "fine": fine,
                        "step": step + 1,
                        "quantity": key,
                        "force_change_percent": 100 * abs(b / a - 1) if a else None,
                    }
                )
    summary = {
        "scope": "nonlinear geometry and friction contact, elastic constitutive screening",
        "requested_service_temperature_c": 35,
        "temperature_calibrated": False,
        "material": "Bambu PETG Basic V3; XY E=2780 MPa, Z E=2550 MPa; estimated nu=0.38 and shear moduli",
        "source": "https://store.bblcdn.com/s1/default/cb94589bf7994fdcbfa833badefae9cd/Bambu_PETG_Basic_Technical_Data_Sheet.pdf",
        "temperature_sensitivity": "E and G multiplied by 0.7; uncalibrated scenario, not a 35 C property or guaranteed bound",
        "cad_source_sha256": sha(ROOT / "cad/negative_carrier_b/model.py"),
        "strength_screen": "51 MPa XY and 35 MPa Z tensile UTS; not yield stresses or an anisotropic failure criterion",
        "mesh_convergence": convergence,
        "studies": results,
    }
    for path in [out / "summary.json", docs / "results.json"]:
        path.write_text(json.dumps(summary, indent=2) + "\n")
    lines = [
        "# Numerical force-study summary",
        "",
        "These are elastic model results, not measured holding capacities. Read the material, fixture and strength limits in [the study report](README.md).",
        "",
        "## Contact cases",
        "",
        "Normal is the mean absolute vertical reaction of the two jaws. Pull is the reaction at 0.15 mm outward movement, not a demonstrated steady sliding limit. Peak jaw stresses exclude elements whose corner centroid is at Y >= 24.5 mm, avoiding the concentrated back-support singularities.",
        "",
        "| Case | Seated normal N/jaw | Pull at 0.15 mm N | Seated jaw XY tension MPa | Seated jaw Z tension MPa | Max penetration at final step mm |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        if r["case"] != "clip-contact":
            continue
        first, last = r["history"][0], r["history"][-1]
        stress = first["jaw_region_stress"]
        lines.append(
            f"| {r['id']} | {first['normal_force_per_jaw_n']:.4g} | {last['pull_force_n']:.4g} | {stress['xy_tension_max_mpa']:.4g} | {stress['z_tension_max_mpa']:.4g} | {last.get('contact_penetration_max_mm', 0):.4g} |"
        )
    lines += [
        "",
        "The 51 MPa XY and 35 MPa Z reference values are ultimate tensile strengths, not permissible service stresses. Rigid-frame contact cases exceed those references; their forces are elastic demand only. Numerical friction and pressure parameters are uncalibrated.",
        "",
        "## Refinement",
        "",
        "| Coarse → fine | Quantity | Step | Relative change |",
        "|---|---|---:|---:|",
    ]
    for c in convergence:
        lines.append(
            f"| {c['coarse']} → {c['fine']} | {c.get('quantity', 'actuation force')} | {c.get('step', 4)} | {c['force_change_percent']:.3g}% |"
        )
    lines += [
        "",
        "Force refinement does not establish peak-stress convergence at sharp roots, edges or point supports. Contact pull reactions retain greater mesh/penalty sensitivity than spring reactions, so no precise holding-force rating is assigned.",
        "",
        "## Run integrity",
        "",
        f"{len(results)} accepted studies. Every listed run completed every requested step and passed the reaction-balance check. Input, FRD, DAT, log and mesh hashes are retained in results.json. Failed development runs are excluded.",
        "",
    ]
    (docs / "numerical-summary.md").write_text("\n".join(lines))
    return summary


def freecad_export(ids, executable):
    out = ROOT / "build/negative-carrier-fem"
    report = out / "freecad-results.json"
    report.unlink(missing_ok=True)
    script = ROOT / "cad/negative_carrier_fem/freecad_results.py"
    env = os.environ | {
        "CARRIER_FEM_OUTPUT": str(out),
        "CARRIER_FEM_CASES": json.dumps(ids),
    }
    result = subprocess.run(
        [executable],
        check=False,
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        text=True,
        capture_output=True,
        env=env,
        timeout=600,
    )
    (out / "freecad-results.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0 and report.exists(), (
        result.stdout[-4000:] + result.stderr[-4000:]
    )
    assert json.loads(report.read_text())["passed"] is True
    (ROOT / "docs/negative-carrier-b/forces/freecad-results.json").write_text(
        report.read_text()
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ccx", default=CCX)
    parser.add_argument(
        "--freecad", help="Optional FreeCAD console executable for native result export"
    )
    args = parser.parse_args()
    results = [
        run(name, size, executable=args.ccx, **kwargs) for name, size, kwargs in MATRIX
    ]
    write_summary(results)
    if args.freecad:
        freecad_export(
            [
                "index-0.4",
                "index-pinned-0.55",
                "index-tip-0.085",
                "guide-0.2",
                "roof-0.2",
                "clip-catch-0.22",
                "contact-0.4-0.3-side1",
                "contact-0.4-0.3-side-1",
                "contact-0.4-0.3-side1-mates20-mortar",
            ],
            args.freecad,
        )


if __name__ == "__main__":
    main()
