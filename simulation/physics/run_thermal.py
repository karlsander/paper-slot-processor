"""Resolve the initial hot-water/cold-wall transient before the long cooling run."""

import argparse
import json
import re
import subprocess
from pathlib import Path

from cases import command, thermal


def solve(folder, name):
    with (folder / name).open("w") as log:
        subprocess.run(
            command("chtMultiRegionFoam", "-case", str(folder)),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )


def run(
    folder,
    hot=38,
    power=5,
    end=3600,
    spacing=6,
    air_h=5,
    solid_initial=20,
    dt=0.5,
    surface_h=3,
):
    if (folder / "scenario.json").exists():
        raise FileExistsError(f"Refusing to overwrite existing case {folder}")
    thermal(folder, hot, power, end, spacing, air_h, solid_initial, dt, surface_h)
    ctrl = folder / "system/controlDict"
    full = ctrl.read_text()
    startup = re.sub(r"endTime [^;]+;", f"endTime {min(30, end)};", full)
    startup = re.sub(r"deltaT [^;]+;", "deltaT 0.005;", startup)
    ctrl.write_text(startup)
    fv = folder / "system/fvSolution"
    normal = fv.read_text()
    fv.write_text(normal.replace("nOuterCorrectors 2", "nOuterCorrectors 8"))
    solve(folder, "log.startup")
    if end > 30:
        ctrl.write_text(full.replace("startFrom startTime", "startFrom latestTime"))
        fv.write_text(normal)
        solve(folder, "log.solver")
    else:
        (folder / "log.solver").write_text((folder / "log.startup").read_text())
    scenario = json.loads((folder / "scenario.json").read_text())
    scenario["startup"] = {
        "initial_dt_s": 0.005,
        "outer_correctors": 8,
        "duration_s": min(30, end),
        "later_outer_correctors": 2,
    }
    (folder / "scenario.json").write_text(json.dumps(scenario, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    for key, default in [
        ("hot", 38),
        ("power", 5),
        ("end", 3600),
        ("spacing", 6),
        ("air-h", 5),
        ("solid-initial", 20),
        ("dt", 0.5),
        ("surface-h", 3),
    ]:
        p.add_argument("--" + key, type=float, default=default)
    a = vars(p.parse_args())
    folder = a.pop("output")
    run(folder.resolve(), **a)
