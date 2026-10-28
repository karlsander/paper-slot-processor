"""Run inside FreeCADCmd: STEP round-trip, clearance, tolerance and motion probes."""

import json
import os
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

OUT = Path(os.environ["PROCESSOR_STUDY_OUTPUT"])
P = json.loads((OUT / "parameters.json").read_text())
MODEL = json.loads((OUT / "model-report.json").read_text())
REPORT = OUT / "fit-report.json"
REPORT.unlink(missing_ok=True)
doc = App.newDocument("ProcessorFitStudy")
shapes = {}
roundtrip = []
for expected in MODEL["parts"]:
    name = expected["name"]
    shape = Part.read(str(OUT / f"{name}.step"))
    assert shape.isValid() and len(shape.Solids) == 1, name
    difference = abs(shape.Volume - expected["volume_mm3"])
    assert difference < 0.01, (name, difference)
    roundtrip.append(
        {"part": name, "volume_difference_mm3": difference, "valid_solid": True}
    )
    shapes[name] = shape

# Compare sampled boundary points on real OpenSCAD sections against native CAD.
# This catches translation/dimension drift while allowing analytic circular arcs.
parity = []
slice_box = Part.makeBox(500, 500, 1, App.Vector(-100, -100, 20))
for name, shape_name in [("base", "base"), ("vessel", "vessel_a")]:
    section = shapes[shape_name].common(slice_box)
    boundary = Part.makeCompound(section.Shells)
    mesh = Mesh.Mesh(str(OUT / f"reference-{name}.stl"))
    points = [point.Vector for point in mesh.Points]
    points += [
        App.Vector(*facet.Points[0])
        .add(App.Vector(*facet.Points[1]))
        .add(App.Vector(*facet.Points[2]))
        .multiply(1 / 3)
        for facet in mesh.Facets
    ]
    deviation = max(Part.Vertex(point).distToShape(boundary)[0] for point in points)
    relative_volume_error = abs(section.Volume - mesh.Volume) / mesh.Volume
    assert deviation < 0.01, (name, deviation)
    assert relative_volume_error < 0.001, (name, relative_volume_error)
    parity.append(
        {
            "part": name,
            "sampled_boundary_deviation_mm": deviation,
            "relative_section_volume_error": relative_volume_error,
            "sample_points": len(points),
        }
    )


def positioned(shape, chamber=0, lift=0):
    result = shape.copy()
    result.translate(
        App.Vector(
            P["vessel_x"],
            P["vessel_y"] + chamber * P["vessel_pitch"],
            P["cradle_floor"] + lift,
        )
    )
    return result


def collision(a, b):
    return max(0, a.common(b).Volume)


base = shapes["base"]
baths = [positioned(shapes[f"vessel_{letter}"], i) for i, letter in enumerate("ab")]
for name, shape in [("Base", base), ("BathA", baths[0]), ("BathB", baths[1])]:
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Shape = shape
    obj.addProperty(
        "App::PropertyString", "StudyScope"
    ).StudyScope = "Defeatured fit geometry; not a print replacement"

# Exclude the deliberate bottom seating contact when measuring lateral clearance.
sides = base.common(
    Part.makeBox(
        P["base_width"] + 2,
        P["base_depth"] + 2,
        P["socket_height"],
        App.Vector(-1, -1, P["cradle_floor"] + 0.01),
    )
)
clearances = [sides.distToShape(bath)[0] for bath in baths]
assert all(abs(value - P["cradle_clearance"]) < 1e-5 for value in clearances), (
    clearances
)
motion = []
for chamber in (0, 1):
    for lift in [0, 0.5, 4, 16, 31, 32, 36, 60]:
        moving = positioned(shapes[f"vessel_{'ab'[chamber]}"], chamber, lift)
        base_overlap = collision(base, moving)
        neighbor_overlap = collision(baths[1 - chamber], moving)
        assert base_overlap < 1e-5 and neighbor_overlap < 1e-5, (
            chamber,
            lift,
            base_overlap,
            neighbor_overlap,
        )
        motion.append(
            {
                "chamber": "AB"[chamber],
                "lift_mm": lift,
                "base_overlap_mm3": base_overlap,
                "neighbor_overlap_mm3": neighbor_overlap,
            }
        )


def rounded_envelope(growth):
    width = P["body_width"] + 2 * growth
    depth = P["body_depth"] + 2 * growth
    height = P["socket_height"]
    solid = Part.makeBox(width, depth, height)
    vertical = [
        edge
        for edge in solid.Edges
        if abs(edge.Length - height) < 1e-8
        and abs(edge.Vertexes[1].Point.z - edge.Vertexes[0].Point.z) > height - 1e-8
    ]
    solid = solid.makeFillet(1.2 + growth, vertical)
    solid.translate(
        App.Vector(
            P["vessel_x"] - growth, P["vessel_y"] - growth, P["cradle_floor"] + 0.01
        )
    )
    return solid


tolerances = []
# Each number is the sum of outward vessel error and inward socket error per side.
for error in [0, 0.2, 0.4, 0.6, 0.7]:
    envelope = rounded_envelope(error)
    overlap = collision(sides, envelope)
    expected_margin = P["cradle_clearance"] - error
    if expected_margin > 0:
        assert overlap < 1e-5
    elif expected_margin < 0:
        assert overlap > 1
    tolerances.append(
        {
            "combined_error_per_side_mm": error,
            "nominal_remaining_clearance_mm": expected_margin,
            "overlap_mm3": overlap,
            "classification": "interference"
            if overlap > 1e-5
            else "contact"
            if abs(expected_margin) < 1e-8
            else "clear",
        }
    )

tilts = []
for angle in [0, 0.5, 1, 1.5, 2]:
    moving = baths[0].copy()
    # Rock around the front lower edge; the opposite bottom edge rises off the floor.
    moving.rotate(
        App.Vector(
            P["vessel_x"] + P["body_width"] / 2, P["vessel_y"], P["cradle_floor"]
        ),
        App.Vector(1, 0, 0),
        angle,
    )
    overlap = collision(sides, moving)
    tilts.append(
        {
            "angle_degrees": angle,
            "socket_overlap_mm3": overlap,
            "classification": "interference" if overlap > 1e-5 else "clear",
        }
    )
assert (
    tilts[0]["classification"] == "clear"
    and tilts[-1]["classification"] == "interference"
)

report = {
    "passed": True,
    "freecad_version": App.Version(),
    "roundtrip": roundtrip,
    "openscad_section_comparison": parity,
    "lateral_clearance_mm": clearances,
    "sampled_vertical_motion": motion,
    "tolerance_sweep": tolerances,
    "tilt_sweep": tilts,
    "limitations": [
        "Rigid geometric tests, not friction, insertion force, deformation or printer calibration.",
        "Vertical removal checked at listed samples; the existing OpenSCAD suite checks a continuous envelope.",
        "STEP import and build123d both use Open Cascade; this is interoperability evidence, not an independent physics solver.",
        "Tolerance values are hypothetical dimensional errors, not measured A1 mini accuracy.",
    ],
}
doc.recompute()
doc.saveAs(str(OUT / "processor-fit.FCStd"))
REPORT.write_text(json.dumps(report, indent=2) + "\n")
print("PASS: FreeCAD headless fit study")
