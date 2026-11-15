"""Reproduce the explicit B2 study matrix, native results and compact report.

Development directories are deliberately excluded. A completed solver run is
not a material/temperature or physical-manufacture acceptance result.
"""

import argparse
import json
import os
import subprocess
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from cad.negative_carrier_fem.solver import sha

from .forces import OUT, ROOT, run

MATRIX = [
    ("index", 1.8, 1, 0),
    ("index", 1.2, 1, 0),
    ("wedge", 1.2, 1, 0.3),
    ("wedge", 0.8, 1, 0.3),
    ("wedge", 1.2, 1, 0.1),
    ("wedge", 1.2, 0.7, 0.3),
    ("dock", 1.8, 1, 0),
    ("dock", 1.8, 1, 0.3),
    ("dock", 1.2, 1, 0.3),
    ("screw-load", 1.4, 1, 0.3),
    ("screw-load", 1, 1, 0.3),
    ("nut-load", 1.4, 1, 0.3),
    ("nut-load", 1, 1, 0.3),
    ("wedge-110", 1.2, 1, 0.3),
    ("dock-stop", 1.2, 1, 0.3),
]
DOCS = ROOT / "docs/negative-carrier-b2/forces"


def tag(case, size, scale, mu):
    return f"{case}-h{size:g}-E{scale:g}-mu{mu:g}-K100000"


def collect():
    results = []
    for args in MATRIX:
        folder = OUT / tag(*args)
        r = json.loads((folder / "result.json").read_text())
        assert r["cad_source_sha256"] == sha(Path(__file__).with_name("model.py"))
        assert r["input_sha256"] == sha(folder / "job.inp")
        assert r["frd_sha256"] == sha(folder / "job.frd")
        assert "Job finished" in (folder / "solver.log").read_text()
        results.append(r)
    return results


def comparison(a, b):
    rows = []
    for x, y in zip(a["history"], b["history"]):
        body = (
            "WEDGE"
            if a["case"] == "dock"
            else "LID"
            if a["case"] == "wedge"
            else "CAP"
            if a["case"] == "index"
            else "SCREW"
            if a["case"] == "screw-load"
            else "NUT"
        )
        key = (
            "fixture_reaction_n"
            if a["case"] in ("wedge", "dock")
            else "load_patch_displacement_mm"
        )
        component = 0 if a["case"] == "dock" else 2
        c, f = x["parts"][body][key][component], y["parts"][body][key][component]
        floor = 1e-6 if key == "fixture_reaction_n" else 1e-9
        rows.append(
            {
                "label": x["label"],
                "quantity": f"{body}.{key}[{component}]",
                "coarse": c,
                "fine": f,
                "absolute_difference": abs(c - f),
                "relative_difference": abs(c - f) / abs(f) if abs(f) > floor else None,
                "coarse_peak_mises_mpa": x["vm_max_mpa"],
                "fine_peak_mises_mpa": y["vm_max_mpa"],
            }
        )
    return {"coarse": a["id"], "fine": b["id"], "steps": rows}


def report(results):
    DOCS.mkdir(parents=True, exist_ok=True)
    comparisons = [
        comparison(results[a], results[b])
        for a, b in [(0, 1), (2, 3), (7, 8), (9, 10), (11, 12)]
    ]
    data = {
        "cases": results,
        "mesh_comparisons": comparisons,
        "physical_acceptance": False,
        "temperature_calibrated": False,
        "index_contact_compliance_converged": False,
        "force_source": "FRD FORC at constrained DOFs; mortar correction included",
        "source_sha256": sha(Path(__file__).with_name("model.py")),
    }
    (DOCS / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    for ix, name in enumerate(("wedge", "dock")):
        ax = axes[0, ix]
        for r in results:
            if r["case"] != name:
                continue
            x = [0.25, 0.5, 1, 0.5, 0]
            y = [
                s["parts"]["WEDGE"]["fixture_reaction_n"][0]
                if name == "dock"
                else abs(s["parts"]["LID"]["fixture_reaction_n"][2])
                for s in r["history"]
            ]
            ax.plot(x, y, "o-", label=r["id"].split("-K")[0])
        ax.set(
            xlabel="Wedge travel from zero-preload seat (mm)",
            ylabel="Drive force (N), signed"
            if name == "dock"
            else "Film-side cut reaction (N)",
            title="Film-edge wedge" if name == "wedge" else "Docking wedge",
        )
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)
    for i, style in ((0, "o--"), (1, "o-")):
        r = results[i]
        axes[1, 0].plot(
            range(1, 7),
            [
                s["parts"]["RAIL"]["mean_displacement_mm"][0] * 1000
                for s in r["history"]
            ],
            style,
            label=r["id"].split("-K")[0],
        )
    axes[1, 0].set(
        xticks=range(1, 7),
        xticklabels=["2 N", "5 N", "+2 N X", "−2 N X", "return", "10 N"],
        ylabel="Mean rail X displacement (µm)",
        title="Index contact: mesh-sensitive local screen",
    )
    axes[1, 0].legend(fontsize=7)
    for r in (results[10], results[12]):
        axes[1, 1].plot(
            [5, 15, 30], [s["vm_max_mpa"] for s in r["history"]], "o-", label=r["case"]
        )
    axes[1, 1].set(
        xlabel="Axial load (N)",
        ylabel="Peak integration-point von Mises (MPa)",
        title="Thread solids: prescribed-bearing structural screen",
    )
    axes[1, 1].legend()
    axes[1, 1].grid(alpha=0.25)
    fig.suptitle(
        "B2 elastic FEA — local fixtures, assumed friction; 35 °C not calibrated",
        fontsize=14,
    )
    fig.savefig(DOCS / "force-summary.png", dpi=160)
    plt.close(fig)
    return data


def native_results(results, executable):
    script = ROOT / "cad/negative_carrier_fem/freecad_results.py"
    # Both refined contact cases plus the index and two thread solids.
    ids = [results[i]["id"] for i in (1, 3, 8, 10, 12)]
    p = OUT / "freecad-results.json"
    p.unlink(missing_ok=True)
    r = subprocess.run(
        [executable],
        check=False,
        text=True,
        capture_output=True,
        timeout=1800,
        input=f"exec(compile(open({str(script)!r}).read(),{str(script)!r},'exec'))\n",
        env=os.environ
        | {"CARRIER_FEM_OUTPUT": str(OUT), "CARRIER_FEM_CASES": json.dumps(ids)},
    )
    (OUT / "freecad-results.log").write_text(r.stdout + r.stderr)
    assert r.returncode == 0 and p.exists(), OUT / "freecad-results.log"
    data = json.loads(p.read_text())
    assert data["passed"]
    (DOCS / p.name).write_text(p.read_text())


def package(results):
    target = ROOT / "build/B2-CAD-and-force-evidence.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root in (
            ROOT / "build/negative-carrier-b2",
            ROOT / "build/negative-carrier-b2-full",
        ):
            manifest = json.loads((root / "manifest.json").read_text())
            native = json.loads((root / "freecad-validation.json").read_text())
            assert manifest["passed"] and native["passed"]
            assert manifest["source_sha256"] == sha(
                Path(__file__).with_name("model.py")
            )
            assert native["manifest_sha256"] == sha(root / "manifest.json")
            for fmt in ("135", "half", "aps", "110"):
                # The manifest is authoritative; omit stale development files.
                m = json.loads((root / fmt / "manifest.json").read_text())
                paths = [root / fmt / "manifest.json", root / fmt / "assembly.FCStd"]
                checked = next(
                    r for r in native["models"] if r["config"]["format"] == fmt
                )
                assert sha(paths[-1]) == checked["assembly_sha256"]
                for n, rec in m["parts"].items():
                    assert sha(root / rec["file"]) == rec["sha256"]
                    paths.append(root / rec["file"])
                    if n != "film":
                        stl = root / rec["print"]["file"]
                        assert sha(stl) == rec["print"]["sha256"]
                        paths.append(stl)
                for p in paths:
                    z.write(p, p.relative_to(ROOT / "build"))
            for name in ("manifest.json", "freecad-validation.json"):
                p = root / name
                z.write(p, p.relative_to(ROOT / "build"))
        for r in results:
            folder = OUT / r["id"]
            for body, info in r["mesh"].items():
                for name, hash_key in (
                    ("part.step", "native_sha256"),
                    ("mesh.npz", "mesh_sha256"),
                ):
                    p = folder / body.lower() / name
                    assert sha(p) == info[hash_key]
                    z.write(p, Path("forces") / r["id"] / body.lower() / name)
            for name in (
                "job.inp",
                "job.frd",
                "job.dat",
                "solver.log",
                "result.json",
                "part.step",
                "mesh.npz",
                "solved.FCStd",
            ):
                p = folder / name
                if p.exists():
                    z.write(p, Path("forces") / r["id"] / name)
        for p in DOCS.iterdir():
            if p.is_file():
                z.write(p, Path("report") / p.name)
    print(target, target.stat().st_size, "bytes")
    printable = ROOT / "build/B2-printable-parts.zip"
    with zipfile.ZipFile(printable, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr(
            "READ-ME.txt",
            "B2 prototype: choose ONE compact/full format folder.\n"
            "Each folder has 13 oriented STL parts for one complete assembly.\n"
            "Extra strip holders need base, lid and six identical edge wedges.\n"
            "The receiver and docking wedge are shared. Each format sleeve can\n"
            "have its own shoe and screw for quick swaps.\n\n"
            "Units: mm. Bambu PETG Basic, solid infill for comparison with FEA.\n"
            "Inspect supports, bridges, threads and bed/brim clearance in the slicer.\n"
            "These are not pre-sliced printer projects. Test wedge/thread coupons first.\n"
            "Actual enlarger fit, film retention and warm creep remain unverified.\n"
            "See DESIGN.md and FORCE-STUDY.md for operating steps and evidence limits.\n",
        )
        z.write(DOCS.parent / "README.md", "DESIGN.md")
        z.write(DOCS / "README.md", "FORCE-STUDY.md")
        for profile, folder in (
            ("compact", "negative-carrier-b2"),
            ("full", "negative-carrier-b2-full"),
        ):
            root = ROOT / "build" / folder
            for model in json.loads((root / "manifest.json").read_text())["formats"]:
                for name, rec in model["parts"].items():
                    if name == "film":
                        continue
                    p = root / rec["print"]["file"]
                    assert sha(p) == rec["print"]["sha256"]
                    z.write(p, Path(profile) / model["config"]["format"] / p.name)
    print(printable, printable.stat().st_size, "bytes")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--collect",
        action="store_true",
        help="Require completed matrix instead of solving",
    )
    p.add_argument("--native", action="store_true")
    p.add_argument("--package", action="store_true")
    p.add_argument(
        "--freecad",
        default=os.environ.get(
            "FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
        ),
    )
    a = p.parse_args()
    if not a.collect:
        for case, size, scale, mu in MATRIX:
            run(case, size, scale, mu)
    results = collect()
    report(results)
    if a.native:
        native_results(results, a.freecad)
    if a.package:
        package(results)


if __name__ == "__main__":
    main()
