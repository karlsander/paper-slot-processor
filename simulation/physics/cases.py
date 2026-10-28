"""Generate reproducible finite-volume OpenFOAM cases in SI units."""

import argparse
import itertools
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cad.parameters import parameters


def tutorial_root():
    """Use a sourced Linux installation or the native OpenFOAM.app launcher."""
    if os.environ.get("FOAM_TUTORIALS"):
        return Path(os.environ["FOAM_TUTORIALS"])
    return (
        Path(subprocess.check_output(["openfoam", "-show-prefix"], text=True).strip())
        / "tutorials"
    )


def command(*args):
    return (["openfoam"] if shutil.which("openfoam") else []) + list(args)


def write(path, text, cls="dictionary"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"FoamFile {{ version 2.0; format ascii; class {cls}; object {path.name}; }}\n"
        + text
        + "\n"
    )


def run(folder, *args):
    with (folder / ("log." + args[0])).open("w") as log:
        r = subprocess.run(
            command(*args, "-case", str(folder)),
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if r.returncode:
        raise RuntimeError((args, (folder / ("log." + args[0])).read_text()[-2500:]))


# Hex faces, outward ordering; x-, x+, y-, y+, z-, z+.
FACE = [
    (0, 4, 7, 3),
    (1, 2, 6, 5),
    (0, 1, 5, 4),
    (3, 7, 6, 2),
    (0, 3, 2, 1),
    (4, 5, 6, 7),
]
DELTAS = [(-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)]


def grid(folder, axes, material, spacing):
    blocks = {}
    vertices = {}
    points = []
    for ijk in itertools.product(*(range(len(a) - 1) for a in axes)):
        lo = [axes[d][i] for d, i in enumerate(ijk)]
        hi = [axes[d][i + 1] for d, i in enumerate(ijk)]
        region = material(*[(l + h) / 2 for l, h in zip(lo, hi)])
        if not region:
            continue
        coords = [
            (lo[0], lo[1], lo[2]),
            (hi[0], lo[1], lo[2]),
            (hi[0], hi[1], lo[2]),
            (lo[0], hi[1], lo[2]),
            (lo[0], lo[1], hi[2]),
            (hi[0], lo[1], hi[2]),
            (hi[0], hi[1], hi[2]),
            (lo[0], hi[1], hi[2]),
        ]
        ids = []
        for c in coords:
            if c not in vertices:
                vertices[c] = len(points)
                points.append(c)
            ids.append(vertices[c])
        n = [max(1, math.ceil((h - l) / s)) for l, h, s in zip(lo, hi, spacing)]
        blocks[ijk] = (region, ids, n, lo, hi)
    boundary = {}
    volumes = {}
    for ijk, (region, ids, n, lo, hi) in blocks.items():
        volumes[region] = volumes.get(region, 0) + math.prod(
            h - l for l, h in zip(lo, hi)
        )
        for d, delta in enumerate(DELTAS):
            neighbor = tuple(i + v for i, v in zip(ijk, delta))
            if neighbor in blocks:
                continue
            name = "freeSurface" if region == "water" else "ambient_" + region
            boundary.setdefault(name, []).append(tuple(ids[i] for i in FACE[d]))
    text = (
        "scale 1;\nvertices (\n"
        + "\n".join("({:g} {:g} {:g})".format(*v) for v in points)
        + "\n);\nblocks (\n"
    )
    text += (
        "\n".join(
            "hex ({}) {} ({}) simpleGrading (1 1 1)".format(
                " ".join(map(str, ids)), region, " ".join(map(str, n))
            )
            for region, ids, n, _, _ in blocks.values()
        )
        + "\n);\nedges ();\nboundary (\n"
    )
    text += (
        "\n".join(
            name
            + " { type wall; faces ("
            + " ".join("({})".format(" ".join(map(str, f))) for f in faces)
            + "); }"
            for name, faces in boundary.items()
        )
        + "\n);\nmergePatchPairs ();"
    )
    write(folder / "system/blockMeshDict", text)
    return volumes


def control(folder, solver, end, dt, functions="", interval=30):
    write(
        folder / "system/controlDict",
        f"""application {solver}; startFrom startTime; startTime 0; stopAt endTime; endTime {end}; deltaT {dt};
writeControl adjustableRunTime; writeInterval {interval}; writeFormat ascii; writePrecision 10; writeCompression off; timeFormat general; timePrecision 10;
runTimeModifiable true; adjustTimeStep yes; maxCo 1; maxDi 100000; maxDeltaT {dt}; functions {{ {functions} }}""",
    )


def field(folder, region, name, dims, value, bc, vector=False):
    write(
        folder / "0" / region / name,
        f"dimensions [{dims}];\ninternalField uniform {value};\nboundaryField {{\n{bc}\n}}",
        "volVectorField" if vector else "volScalarField",
    )


def thermal(
    folder,
    hot=38,
    power=5,
    end=3600,
    spacing=6,
    air_h=5,
    solid_initial=20,
    dt=0.5,
    surface_h=3,
    pad_k=1,
):
    p = parameters()
    height = p["body_height"] / 1000
    fill = p["empty_level"] / 1000
    x = [-0.014, -0.006, 0, 0.002, 0.003, 0.125, 0.126, 0.128, 0.134, 0.142]
    y = [0, 0.003, 0.017, 0.020, 0.0205, 0.022, 0.025]
    z = sorted({0, 0.003, 0.004, 0.006, 0.024, 0.174, 0.185, fill, height})

    def material(x, y, z):
        if 0 < x < 0.128 and 0 < y < 0.020 and z < height:
            if x < 0.003 or x > 0.125 or y < 0.003 or y > 0.017 or z < 0.004:
                return "petg"
            if z < fill:
                return "water"
        if 0.002 < x < 0.126 and 0.020 < y < 0.0205 and 0.006 < z < 0.185:
            return "pad"
        if -0.014 < x < 0.142 and 0.0205 < y < 0.022 and 0.003 < z < 0.185:
            return "aluminium"
        if -0.006 < x < 0.134 and 0.022 < y < 0.025 and 0.024 < z < 0.174:
            return "heater"

    folder.mkdir(parents=True, exist_ok=True)
    volumes = grid(folder, [x, y, z], material, [spacing / 1000, 0.002, spacing / 1000])
    control(folder, "chtMultiRegionFoam", end, dt)
    write(
        folder / "system/fvSchemes",
        "ddtSchemes {} gradSchemes {} divSchemes {} laplacianSchemes {} interpolationSchemes {} snGradSchemes {}",
    )
    write(folder / "system/fvSolution", "PIMPLE { nOuterCorrectors 2; }")
    write(
        folder / "constant/regionProperties",
        "regions (fluid (water) solid (petg pad aluminium heater));",
    )
    write(
        folder / "constant/g",
        "dimensions [0 1 -2 0 0 0 0]; value (0 0 -9.81);",
        "uniformDimensionedVectorField",
    )
    run(folder, "blockMesh")
    run(folder, "splitMeshRegions", "-cellZones", "-overwrite")
    base = tutorial_root() / "heatTransfer/chtMultiRegionFoam/multiRegionHeater"
    materials = {
        "water": (998, 4180, 0.6),
        "petg": (1270, 1200, 0.2),
        "pad": (1800, 1000, pad_k),
        "aluminium": (2700, 900, 205),
        "heater": (1400, 1200, 0.2),
    }
    functions = []
    for region, (rho, cp, k) in materials.items():
        fluid = region == "water"
        temp = hot + 273.15 if fluid else solid_initial + 273.15
        method = "fluidThermo" if fluid else "solidThermo"
        boundary = (folder / "constant" / region / "polyMesh/boundary").read_text()
        patches = re.findall(r"(\w+)\s*\{\s*type\s+\w+;", boundary)
        tbc = []
        ubc = []
        pbc = []
        for patch in patches:
            coupled = "_to_" in patch
            if coupled:
                bc = f"type compressible::turbulentTemperatureRadCoupledMixed; Tnbr T; kappaMethod {method}; value uniform {temp};"
            else:
                emissivity = 0.15 if region == "aluminium" else 0.9
                # Effective top loss includes the slotted cover/headspace; evaporation is a sensitivity, not resolved transport.
                h = surface_h if fluid else air_h
                bc = f"type externalWallHeatFluxTemperature; mode coefficient; Ta constant 293.15; h uniform {h}; emissivity {emissivity}; kappaMethod {method}; value uniform {temp};"
            tbc.append(patch + " { " + bc + " }")
            ubc.append(
                patch
                + " { type "
                + (
                    "slip;"
                    if patch == "freeSurface"
                    else "fixedValue; value uniform (0 0 0);"
                )
                + " }"
            )
            pbc.append(
                patch + " { type " + "fixedFluxPressure; value uniform 100000;" + " }"
            )
        field(folder, region, "T", "0 0 0 1 0 0 0", temp, "\n".join(tbc))
        field(
            folder,
            region,
            "p",
            "1 -1 -2 0 0 0 0",
            100000,
            '".*" { type calculated; value uniform 100000; }',
        )
        eos = "Boussinesq" if fluid else "rhoConst"
        eosdata = "rho0 998; T0 293.15; beta 0.0003;" if fluid else f"rho {rho};"
        transport = f"mu 0.0008; Pr {cp * 0.0008 / k};" if fluid else f"kappa {k};"
        write(
            folder / "constant" / region / "thermophysicalProperties",
            f"""thermoType {{ type {"heRhoThermo" if fluid else "heSolidThermo"}; mixture pureMixture; transport {"const" if fluid else "constIso"}; thermo hConst; equationOfState {eos}; specie specie; energy sensibleEnthalpy; }}
mixture {{ specie {{ molWeight 18; }} equationOfState {{ {eosdata} }} thermodynamics {{ Cp {cp}; Hf 0; }} transport {{ {transport} }} }}""",
        )
        for name in ["fvSchemes", "fvSolution"]:
            dest = folder / "system" / region / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(
                base / "system" / ("bottomWater" if fluid else "heater") / name, dest
            )
        if fluid:
            f = folder / "system" / region / "fvSolution"
            f.write_text(
                f.read_text()
                .replace(
                    "momentumPredictor   yes;",
                    "momentumPredictor yes; pRefCell 0; pRefValue 100000;",
                )
                .replace(
                    "solver           GAMG;", "solver           GAMG; maxIter 100;"
                )
            )
            field(
                folder, region, "U", "0 1 -1 0 0 0 0", "(0 0 0)", "\n".join(ubc), True
            )
            field(folder, region, "p_rgh", "1 -1 -2 0 0 0 0", 100000, "\n".join(pbc))
            field(
                folder,
                region,
                "p",
                "1 -1 -2 0 0 0 0",
                100000,
                '".*" { type calculated; value uniform 100000; }',
            )
            write(
                folder / "constant" / region / "turbulenceProperties",
                "simulationType laminar;",
            )
            field(
                folder,
                region,
                "alphat",
                "1 -1 -1 0 0 0 0",
                0,
                '".*" { type calculated; value uniform 0; }',
            )
        functions.append(
            f"{region}Mean {{ type volFieldValue; libs (fieldFunctionObjects); region {region}; writeControl timeStep; writeInterval 10; log false; fields (T); writeFields false; operation volAverage; regionType all; }}"
        )
        functions.append(
            f"{region}Extrema {{ type fieldMinMax; libs (fieldFunctionObjects); region {region}; writeControl timeStep; writeInterval 10; log false; fields (T"
            + (" U" if fluid else "")
            + "); }"
        )
        functions.append(
            f"{region}HeatFlux {{ type wallHeatFlux; libs (fieldFunctionObjects); region {region}; writeControl writeTime; log false; }}"
        )
    write(
        folder / "constant/heater/fvOptions",
        f"heat {{ type scalarSemiImplicitSource; active true; selectionMode all; volumeMode absolute; sources {{ h ({power} 0); }} }}",
    )
    control(folder, "chtMultiRegionFoam", end, dt, "\n".join(functions))
    (folder / "scenario.json").write_text(
        json.dumps(
            {
                "kind": "3D conjugate transient heat transfer with laminar buoyant water",
                "liquid_initial_c": hot,
                "solid_initial_c": solid_initial,
                "room_c": 20,
                "power_w": power,
                "air_h": air_h,
                "surface_h": surface_h,
                "mesh_spacing_mm": spacing,
                "max_dt": dt,
                "end_seconds": end,
                "volumes_m3": volumes,
                "materials": materials,
                "cavity_volume_error_percent": 100
                * (volumes["water"] * 1e6 / p["working_ml"] - 1),
                "approximations": [
                    "Rectangularized bath; rounded corners, stops and fill ridge omitted.",
                    "Dry headspace and slotted top represented by effective free-surface heat transfer; top mass omitted.",
                    "Isolated module; base/straps and neighboring air flow omitted.",
                    "Water proxy for chemistry; isotropic PETG and assumed pad/heater properties.",
                    "No evaporation mass transfer; effective surface heat-transfer sensitivity only.",
                ],
            },
            indent=2,
        )
    )
    print(folder, volumes, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--hot", type=float, default=38)
    parser.add_argument("--power", type=float, default=5)
    parser.add_argument("--end", type=float, default=3600)
    parser.add_argument("--spacing", type=float, default=6)
    parser.add_argument("--air-h", type=float, default=5)
    parser.add_argument("--solid-initial", type=float, default=20)
    parser.add_argument("--dt", type=float, default=0.5)
    parser.add_argument("--surface-h", type=float, default=3)
    parser.add_argument("--pad-k", type=float, default=1)
    a = parser.parse_args()
    thermal(
        a.output.resolve(),
        a.hot,
        a.power,
        a.end,
        a.spacing,
        a.air_h,
        a.solid_initial,
        a.dt,
        a.surface_h,
        a.pad_k,
    )
