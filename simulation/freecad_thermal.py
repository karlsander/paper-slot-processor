"""Headless FreeCAD FEM + Gmsh + CalculiX conduction benchmark.

A flat section of the vessel wall, with a prescribed liquid-side temperature
and air-side convection. Edges are adiabatic. This verifies the FEM pipeline;
it is not a full-bath cooling, fluid-flow or heater-performance prediction.
"""

import json
import os
from pathlib import Path

import FreeCAD as App
import ObjectsFem
from femmesh.gmshtools import GmshTools
from femtools.ccxtools import FemToolsCcx

OUT = Path(os.environ["PROCESSOR_STUDY_OUTPUT"])
P = json.loads((OUT / "parameters.json").read_text())
BIN = Path(os.environ.get("FREECAD_SOLVER_BIN", App.getHomePath() + "bin"))
REPORT = OUT / "thermal-report.json"
REPORT.unlink(missing_ok=True)
App.ParamGet("User parameter:BaseApp/Preferences/Mod/Fem/Gmsh").SetString(
    "gmshBinaryPath", str(BIN / "gmsh")
)


def solve(h, mesh_size):
    name = f"wall-h{h}-mesh{mesh_size}"
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument(name.replace("-", "_"))
    wall = doc.addObject("Part::Box", "WallSection")
    # A 20 x 20 mm section avoids wasting elements on an analytically 1D problem.
    wall.Length = 20
    wall.Width = P["wall"]
    wall.Height = 20
    doc.recompute()
    analysis = ObjectsFem.makeAnalysis(doc, "ThermalAnalysis")
    solver = ObjectsFem.makeSolverCalculiXCcxTools(doc, "CalculiX")
    solver.AnalysisType = "thermomech"
    solver.ThermoMechType = "pure heat transfer"
    solver.ThermoMechSteadyState = True
    solver.WorkingDir = str(folder)
    analysis.addObject(solver)
    material = ObjectsFem.makeMaterialSolid(doc, "AssumedPETG")
    material.Material = {
        "Name": "PETG assumed isotropic",
        "ThermalConductivity": "0.20 W/m/K",
        "Density": "1270 kg/m^3",
        "SpecificHeat": "1200 J/kg/K",
        "YoungsModulus": "2000 MPa",
        "PoissonRatio": "0.38",
        "ThermalExpansionCoefficient": "0 m/m/K",
    }
    analysis.addObject(material)

    def face_at_y(y):
        return next(
            f"Face{i}"
            for i, face in enumerate(wall.Shape.Faces, 1)
            if abs(face.CenterOfMass.y - y) < 1e-7 and abs(face.Area - 400) < 1e-7
        )

    hot = ObjectsFem.makeConstraintTemperature(doc, "LiquidSide35C")
    hot.References = [(wall, face_at_y(0))]
    hot.Temperature = 308.15
    analysis.addObject(hot)
    cold = ObjectsFem.makeConstraintHeatflux(doc, "Air22C")
    cold.References = [(wall, face_at_y(P["wall"]))]
    cold.ConstraintType = "Convection"
    cold.AmbientTemp = "295.15 K"
    cold.FilmCoef = f"{h} W/m^2/K"
    analysis.addObject(cold)
    initial = ObjectsFem.makeConstraintInitialTemperature(doc, "InitialTemperature")
    initial.initialTemperature = 295.15
    analysis.addObject(initial)
    mesh = ObjectsFem.makeMeshGmsh(doc, "Mesh")
    mesh.Shape = wall
    mesh.CharacteristicLengthMax = f"{mesh_size} mm"
    mesh.CharacteristicLengthMin = f"{mesh_size / 2} mm"
    mesh.SecondOrderLinear = False
    analysis.addObject(mesh)
    doc.recompute()
    mesher = GmshTools(mesh)
    error = mesher.create_mesh()
    assert not error, error
    assert mesh.FemMesh.VolumeCount > 0, "Gmsh did not produce volume elements"
    fem = FemToolsCcx(analysis, solver)
    fem.setup_ccx(str(BIN / "ccx"))
    fem.update_objects()
    fem.setup_working_dir(str(folder))
    missing = fem.check_prerequisites()
    assert not missing, missing
    fem.write_inp_file()
    assert fem.ccx_run() == 0, "CalculiX solve failed"
    (folder / "calculix.log").write_text(fem.ccx_stdout)
    fem.load_results()
    results = [
        obj
        for obj in doc.Objects
        if hasattr(obj, "Temperature") and hasattr(obj, "NodeNumbers")
    ]
    assert results, "No temperature result imported"
    result = results[-1]
    values = list(result.Temperature)
    assert values, "No nodal temperatures"
    outer_c = min(values) - 273.15
    hot_c = max(values) - 273.15
    flux = (35 - 22) / (P["wall"] / 1000 / 0.20 + 1 / h)
    expected_outer_c = 22 + flux / h
    assert abs(outer_c - expected_outer_c) < 0.02, (outer_c, expected_outer_c)
    assert abs(hot_c - 35) < 0.02, hot_c
    doc.recompute()
    doc.saveAs(str(folder / "wall-thermal.FCStd"))
    report = {
        "h_w_m2k": h,
        "mesh_size_mm": mesh_size,
        "nodes": mesh.FemMesh.NodeCount,
        "elements": mesh.FemMesh.VolumeCount,
        "min_c": outer_c,
        "max_c": hot_c,
        "analytical_outer_c": expected_outer_c,
        "outer_error_c": abs(outer_c - expected_outer_c),
        "analytical_flux_w_m2": flux,
        "document": str(folder / "wall-thermal.FCStd"),
    }
    App.closeDocument(doc.Name)
    return report


cases = [solve(5, 3), solve(5, 1.5), solve(3, 3), solve(8, 3)]
report = {
    "passed": True,
    "kind": "Steady conduction/convection FEM benchmark",
    "wall_mm": P["wall"],
    "assumed_petg_k_w_mk": 0.20,
    "liquid_side_c": 35,
    "room_c": 22,
    "cases": cases,
    "mesh_refinement_delta_c": abs(cases[0]["min_c"] - cases[1]["min_c"]),
    "limitations": [
        "Prescribed uniform liquid-side temperature; no liquid flow or cooling transient.",
        "Assumed isotropic PETG conductivity and air-side film coefficients, not measured material properties.",
        "No radiation, evaporation, base contact, infill microstructure or neighboring bath.",
        "Validates solver operation and units; does not validate the physical processor.",
    ],
}
REPORT.write_text(json.dumps(report, indent=2) + "\n")
print("PASS: FreeCAD/Gmsh/CalculiX thermal benchmark")
