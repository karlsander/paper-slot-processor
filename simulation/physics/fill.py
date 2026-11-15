"""Three-dimensional water/air VOF fill with gravity, viscosity and surface tension."""

import argparse
import json
import shutil
from pathlib import Path

from cases import control, field, grid, parameters, run, tutorial_root, write


def generate(folder, spacing=4, pour_seconds=5):
    p = parameters()
    folder.mkdir(parents=True, exist_ok=True)
    height = (p["body_height"] - p["floor"]) / 1000
    grid(
        folder,
        [[0, 0.055, 0.067, 0.122], [0, 0.004, 0.010, 0.014], [0, height]],
        lambda x, y, z: "fill",
        [spacing / 1000] * 3,
    )
    # Replace the generic external patch by explicitly classified block faces.
    path = folder / "system/blockMeshDict"
    text = path.read_text()
    start = text.index("boundary (")
    text = text[:start]
    import re

    vertices = [
        tuple(map(float, line.strip().strip("()").split()))
        for line in re.search(r"vertices \((.*?)\);", text, re.DOTALL)[1].splitlines()
        if line.strip()
    ]
    blocks = re.findall(r"hex \((.*?)\)", text)
    patches = {"walls": [], "inlet": [], "atmosphere": []}
    from cases import FACE

    seen = {}
    for block in blocks:
        ids = list(map(int, block.split()))
        for face in FACE:
            f = tuple(ids[i] for i in face)
            key = tuple(sorted(f))
            seen.setdefault(key, []).append(f)
    for faces in seen.values():
        if len(faces) > 1:
            continue
        f = faces[0]
        coords = [vertices[i] for i in f]
        if all(abs(v[2] - height) < 1e-6 for v in coords):
            cx = sum(v[0] for v in coords) / 4
            cy = sum(v[1] for v in coords) / 4
            name = (
                "inlet" if 0.055 < cx < 0.067 and 0.004 < cy < 0.010 else "atmosphere"
            )
        else:
            name = "walls"
        patches[name].append(f)
    text += (
        "boundary (\n"
        + "\n".join(
            name
            + " { type "
            + ("wall" if name == "walls" else "patch")
            + "; faces ("
            + " ".join("({})".format(" ".join(map(str, f))) for f in faces)
            + "); }"
            for name, faces in patches.items()
        )
        + ");\nmergePatchPairs ();"
    )
    # write() already supplies the FoamFile header.
    path.write_text(text)
    tutorial = tutorial_root() / "multiphase/interFoam/laminar/damBreak/damBreak"
    for item in [
        "system/fvSolution",
        "system/fvSchemes",
        "constant/transportProperties",
        "constant/turbulenceProperties",
    ]:
        dest = folder / item
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tutorial / item, dest)
    write(
        folder / "constant/g",
        "dimensions [0 1 -2 0 0 0 0]; value (0 0 -9.81);",
        "uniformDimensionedVectorField",
    )
    speed = p["working_ml"] * 1e-6 / pour_seconds / (0.012 * 0.006)
    field(
        folder,
        "",
        "U",
        "0 1 -1 0 0 0 0",
        "(0 0 0)",
        f"""walls {{ type noSlip; }}
inlet {{ type uniformFixedValue; uniformValue table ((0 (0 0 {-speed})) ({pour_seconds - 1e-6} (0 0 {-speed})) ({pour_seconds} (0 0 0)) ({pour_seconds + 2} (0 0 0))); value uniform (0 0 {-speed}); }}
atmosphere {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}""",
        True,
    )
    field(
        folder,
        "",
        "p_rgh",
        "1 -1 -2 0 0 0 0",
        0,
        "walls { type fixedFluxPressure; value uniform 0; } inlet { type fixedFluxPressure; value uniform 0; } atmosphere { type totalPressure; p0 uniform 0; value uniform 0; }",
    )
    field(
        folder,
        "",
        "alpha.water",
        "0 0 0 0 0 0 0",
        0,
        "walls { type zeroGradient; } inlet { type fixedValue; value uniform 1; } atmosphere { type inletOutlet; inletValue uniform 0; value uniform 0; }",
    )
    functions = """volume { type volFieldValue; libs (fieldFunctionObjects); writeControl timeStep; writeInterval 10; log false; fields (alpha.water); operation volIntegrate; regionType all; writeFields false; }
inletFlux { type surfaceFieldValue; libs (fieldFunctionObjects); writeControl timeStep; writeInterval 1; log false; fields (phi rhoPhi); operation sum; regionType patch; name inlet; writeFields false; }
outletFlux { type surfaceFieldValue; libs (fieldFunctionObjects); writeControl timeStep; writeInterval 1; log false; fields (phi rhoPhi); operation sum; regionType patch; name atmosphere; writeFields false; }
range { type fieldMinMax; libs (fieldFunctionObjects); writeControl timeStep; writeInterval 50; log false; fields (alpha.water U); }
"""
    control(folder, "interFoam", pour_seconds + 2, 0.002, functions, 0.1)
    file = folder / "system/controlDict"
    s = (
        file.read_text()
        .replace("deltaT 0.002", "deltaT 0.0001")
        .replace("maxCo 1;", "maxCo 0.3; maxAlphaCo 0.3;")
    )
    file.write_text(s)
    run(folder, "blockMesh")
    run(folder, "checkMesh")
    (folder / "scenario.json").write_text(
        json.dumps(
            {
                "solver": "interFoam",
                "mesh_spacing_mm": spacing,
                "pour_seconds": pour_seconds,
                "inlet_m_s": speed,
                "target_ml": p["working_ml"],
                "domain_mm": [122, 14, height * 1000],
                "initial_water_ml": 0,
                "inlet_mm": [12, 6],
                "approximations": [
                    "Rectangular cavity; sub-millimetre fill ridge, stops and rounded corners omitted.",
                    "Prescribed centered rectangular jet; no bottle geometry or user hand motion.",
                    "Laminar water-air, fixed water properties; chemistry and contact angle not calibrated.",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--spacing", type=float, default=4)
    parser.add_argument("--pour-seconds", type=float, default=5)
    a = parser.parse_args()
    generate(a.output.resolve(), a.spacing, a.pour_seconds)
