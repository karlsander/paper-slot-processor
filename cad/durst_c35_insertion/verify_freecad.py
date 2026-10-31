"""FreeCAD contact study; a passing estimated fixture is not physical fit evidence."""

import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App
import Part

out = Path(os.environ["DURST_INSERTION_OUTPUT"])
report = out / "insertion-validation.json"
report.unlink(missing_ok=True)
manifest = json.loads((out / "study-manifest.json").read_text())
for filename, expected in manifest["files_sha256"].items():
    assert hashlib.sha256((out / filename).read_bytes()).hexdigest() == expected, (
        filename
    )
p = json.loads((out / "carrier-parameters.json").read_text())
q = json.loads((out / "fixture-parameters.json").read_text())
motion = json.loads((out / "motion.json").read_text())
shapes = {
    name: Part.read(str(out / f"{name}.step"))
    for name in ("carrier-a", "carrier-b", "mixing-box", "stage", "back-stop")
}
for name, shape in shapes.items():
    assert shape.isValid() and len(shape.Solids) == 1, name


def moved(shape, x=0, y=0, z=0):
    shape = shape.copy()
    shape.translate(App.Vector(x, y, z))
    return shape


def measure(pose, x=0, carriers=None):
    carriers = carriers or (shapes["carrier-a"], shapes["carrier-b"])
    values = []
    for half, shape in zip("ab", carriers):
        moving = moved(
            shape,
            x=x,
            y=pose["carrier_y"],
            z=pose["carrier_z"] + (p["film_gap"] if half == "b" else 0),
        )
        for name in ("mixing-box", "stage", "back-stop"):
            fixed = moved(shapes[name], z=pose["stage_z"] if name == "stage" else 0)
            volume = max(0, moving.common(fixed).Volume)
            distance = moving.distToShape(fixed)[0]
            values.append(
                {
                    "carrier": half,
                    "fixture": name,
                    "overlap_mm3": volume,
                    "distance_mm": distance,
                }
            )
    return values


def total(values):
    return sum(v["overlap_mm3"] for v in values)


samples = []
for i, pose in enumerate(motion):
    values = measure(pose)
    samples.append(
        {**pose, "pairs": values, "clear": max(v["overlap_mm3"] for v in values) < 1e-4}
    )
    if i % 30 == 0:
        print(
            f"Insertion sample {i}/{len(motion)}: overlap {total(values):.6f} mm³",
            flush=True,
        )
nominal_clear = all(s["clear"] for s in samples)
seated = {"carrier_y": 0, "carrier_z": 0, "stage_z": 0}
controls = {}
controls["over_insert_2mm"] = measure(seated | {"carrier_y": -2})
controls["side_offset_3mm"] = measure(seated, x=3)
controls["stage_not_depressed_on_lowered_path"] = measure(
    seated | {"carrier_z": -q["stage_depression"] / 2}
)
# Extra material on ordinary panel areas, away from rim/pin/window details.
# This deliberately recreates the thickness regression against the same fixture.
bad_a = shapes["carrier-a"].fuse(Part.makeBox(10, 15, 2.5, App.Vector(30, 75, -2.5)))
bad_b = shapes["carrier-b"].fuse(Part.makeBox(10, 15, 2.5, App.Vector(30, 75, 0)))
assert bad_a.isValid() and bad_b.isValid()
controls["local_2_5mm_panel_regression"] = measure(seated, carriers=(bad_a, bad_b))
print(
    "Control overlaps:",
    {name: round(total(v), 4) for name, v in controls.items()},
    flush=True,
)

# Test a larger mixing-box footprint independently of the carrier; its full
# lower outline, including the uncut side walls, remains in collision checks.
width_sweep = []
original_mixing = shapes["mixing-box"]
for width in (88.0, 90.0, 92.0, 93.0, 94.0):
    matrix = App.Matrix()
    matrix.A11 = width / q["mixing_width"]
    shapes["mixing-box"] = original_mixing.transformGeometry(matrix)
    pairs = measure(seated)
    width_sweep.append({"mixing_width_mm": width, "overlap_mm3": total(pairs)})
shapes["mixing-box"] = original_mixing

# Store the complete solids; visual cutaways are generated only by the renderer.
doc = App.newDocument("DurstProvisionalInsertion")
for name, shape in shapes.items():
    shape = moved(shape, z=p["film_gap"] if name == "carrier-b" else 0)
    obj = doc.addObject("PartDesign::Feature", name.replace("-", "_"))
    obj.Shape = shape
    obj.Label = name.replace("-", " ").title()
    obj.addProperty("App::PropertyString", "Evidence", "Study")
    obj.Evidence = (
        f"Carrier: provisional {p['sheet_thickness']:g} mm sheet"
        if name.startswith("carrier")
        else "Estimated contact envelope; not measured or a factory drawing"
    )
doc.recompute()
path = out / "provisional-insertion.FCStd"
doc.saveAs(str(path))
App.closeDocument(doc.Name)
check = App.openDocument(str(path))
assert len(check.Objects) == 5 and all(obj.Shape.isValid() for obj in check.Objects)
App.closeDocument(check.Name)
report.write_text(
    json.dumps(
        {
            "verification_completed": True,
            "nominal_path_clear": nominal_clear,
            "evidence_level": "provisional fixture consistency only",
            "physical_fit_verified": False,
            "fixture_dimensions_measured": False,
            "freecad_version": App.Version(),
            "study_manifest_sha256": hashlib.sha256(
                (out / "study-manifest.json").read_bytes()
            ).hexdigest(),
            "samples": samples,
            "negative_controls": {
                name: {"detected": total(v) > 1e-4, "pairs": v}
                for name, v in controls.items()
            },
            "mixing_width_sweep": width_sweep,
            "limitations": [
                "Fixture contacts and dimensions are estimates; nominal clearance is not a prediction of real fit.",
                "Discrete prescribed rigid poses, not a continuous swept-volume or force simulation.",
                "The hand guides the carrier through the released gap; gravity, friction and spring force are not solved.",
                "Stage U rails, underside contact lands, relief and rear stop are hypotheses awaiting inspection.",
            ],
        },
        indent=2,
    )
    + "\n"
)
print("Completed provisional insertion study and reopened FreeCAD document", flush=True)
