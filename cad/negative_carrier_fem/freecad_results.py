"""Run inside FreeCAD's console; import solved FRD fields and verify a reopen."""

import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App
import ObjectsFem
import Part
from feminout.importCcxFrdResults import importFrd


def export_case(folder):
    data = json.loads((folder / "result.json").read_text())
    assert (
        hashlib.sha256((folder / "job.frd").read_bytes()).hexdigest()
        == data["frd_sha256"]
    )
    doc = App.newDocument("PETG_Force_Study")
    source = doc.addObject("PartDesign::Feature", "RelaxedGeometry")
    source.Shape = Part.read(str(folder / "part.step"))
    source.addProperty("App::PropertyString", "StudyNotes").StudyNotes = data["notes"]
    source.addProperty(
        "App::PropertyString", "MaterialLimitations"
    ).MaterialLimitations = (
        "Bambu PETG Basic V3 tensile moduli; assumed shear/Poisson constants. "
        "35 C requested but no calibrated temperature law. No plasticity or creep. "
        "Above-strength elastic results are demand only."
    )
    source.addProperty("App::PropertyString", "InputSHA256").InputSHA256 = data[
        "input_sha256"
    ]
    if data["boundary"].get("elastic_mates"):
        for name in ["top", "bottom"]:
            mate = doc.addObject(
                "PartDesign::Feature", name.title() + "InitialGeometry"
            )
            mate.Shape = Part.read(str(folder / name / "part.step"))
    analysis = ObjectsFem.makeAnalysis(doc, "Analysis")
    importFrd(str(folder / "job.frd"), analysis, "Solved_")
    doc.recompute()
    results = [o for o in doc.Objects if o.isDerivedFrom("Fem::FemResultObject")]
    assert len(results) == len(data["history"])
    for result in results:
        assert result.NodeNumbers and result.DisplacementVectors and result.vonMises
        assert (
            len(result.NodeNumbers)
            == len(result.DisplacementVectors)
            == len(result.vonMises)
        )
    path = folder / "solved.FCStd"
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(path))
    restored = [o for o in reopened.Objects if o.isDerivedFrom("Fem::FemResultObject")]
    assert len(restored) == len(results)
    counts = [len(o.NodeNumbers) for o in restored]
    assert all(counts)
    App.closeDocument(reopened.Name)
    return {
        "id": data["id"],
        "passed": True,
        "result_steps": len(counts),
        "nodes_per_step": counts,
        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "freecad_version": App.Version(),
    }


root = Path(os.environ["CARRIER_FEM_OUTPUT"])
report_path = root / "freecad-results.json"
report_path.unlink(missing_ok=True)
ids = json.loads(os.environ["CARRIER_FEM_CASES"])
reports = [export_case(root / case) for case in ids]
report_path.write_text(json.dumps({"passed": True, "cases": reports}, indent=2) + "\n")
