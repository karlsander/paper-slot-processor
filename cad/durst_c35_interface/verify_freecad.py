"""Run in FreeCAD's console; require independent import and collision controls."""

import hashlib
import json
import os
from itertools import combinations
from pathlib import Path

import FreeCAD as App
import Part

out = Path(os.environ["DURST_INTERFACE_OUTPUT"])
manifest_path = out / "manifest.json"
data = json.loads(manifest_path.read_text())
assert data["geometry_passed"] is True and data["physical_fit_accepted"] is False


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(out / "measurements.json") == data["measurement_sha256"]
measured = json.loads((out / "measurements.json").read_text())
p = {key: entry["value"] for key, entry in measured["parameters"].items()}


def overlap(a, b):
    return abs(a.common(b).Volume) if a.BoundBox.intersect(b.BoundBox) else 0.0


def probe(x, y, bottom, width, depth, height):
    return Part.makeBox(
        width, depth, height, App.Vector(x - width / 2, y - depth / 2, bottom)
    )


shapes = {}
volume_errors = {}
for name, record in data["parts"].items():
    path = out / record["file"]
    assert sha(path) == record["sha256"]
    shape = Part.read(str(path))
    assert shape.isValid() and len(shape.Solids) == 1, name
    error = abs(shape.Volume / record["volume_mm3"] - 1)
    assert error < 1e-7, (name, error)
    shapes[name] = shape
    volume_errors[name] = error
max_overlap = max(overlap(a, b) for a, b in combinations(shapes.values(), 2))
assert max_overlap < 1e-6
# Head width is measured at the narrow band, not at the larger upper shell.
neck_section = shapes["head-shell"].common(
    probe(0, -p["neck_depth"] / 2, 2, 200, 200, 1)
)
assert abs(neck_section.BoundBox.XLength - p["neck_width"]) < 1e-6
assert abs(neck_section.BoundBox.YLength - p["neck_depth"]) < 1e-6
lower_section = shapes["lower-support"].common(
    probe(
        0,
        p["lower_front_offset"] - p["lower_depth"] / 2,
        -p["slot_gap"] - p["lower_height"] / 2,
        200,
        200,
        0.1,
    )
)
assert abs(lower_section.BoundBox.YLength - p["lower_depth"]) < 1e-6
rear_difference = lower_section.BoundBox.YMin - neck_section.BoundBox.YMin
if measured["observations"].get("neck_and_lower_rear_faces_coincide", {}).get("value"):
    assert abs(rear_difference) < 1e-6, rear_difference
assert (
    abs(
        shapes["lower-support"].BoundBox.YMax
        - lower_section.BoundBox.YMax
        - p["flange_front_overhang"]
    )
    < 1e-6
)
assert (
    abs(
        shapes["lower-support"].BoundBox.ZLength
        - p["lower_height"]
        - p["flange_thickness"]
    )
    < 1e-6
)
assert abs(shapes["lower-support"].BoundBox.ZMax + p["slot_gap"]) < 1e-6
# Recover the clear opening from imported solid geometry, independently of its builder.
opening = probe(
    0,
    p["lower_front_offset"] - p["lower_depth"] / 2,
    -p["slot_gap"] - p["lower_bevel_drop"] - 0.2,
    p["lower_width"] - 2 * p["corner_radius"],
    p["lower_depth"] - 2 * p["corner_radius"],
    0.1,
).cut(shapes["lower-support"])
assert len(opening.Solids) == 1
ob = opening.BoundBox
opening_profile = {
    "width": ob.XLength,
    "depth": ob.YLength,
    "left_margin": lower_section.BoundBox.XMax - ob.XMax,
    "right_margin": ob.XMin - lower_section.BoundBox.XMin,
    "front_margin": lower_section.BoundBox.YMax - ob.YMax,
    "rear_margin": ob.YMin - lower_section.BoundBox.YMin,
    "centre_x": (ob.XMin + ob.XMax) / 2,
    "centre_y": (ob.YMin + ob.YMax) / 2,
}
for actual, expected in [
    (opening_profile["width"], p["lower_opening_width"]),
    (opening_profile["depth"], p["lower_opening_depth"]),
    (opening_profile["left_margin"], p["lower_opening_left_offset"]),
    (opening_profile["front_margin"], p["lower_opening_front_offset"]),
]:
    assert abs(actual - expected) < 1e-6, (actual, expected)
# Check the sloping mouth in imported STEP geometry, including its transition
# to the unchanged clear walls. A thin slab ends at each reported depth.
bevel_sections = []
for fraction in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25):
    depth = fraction * p["lower_bevel_drop"]
    void = probe(
        0,
        p["lower_front_offset"] - p["lower_depth"] / 2,
        -p["slot_gap"] - depth - 0.02,
        p["lower_width"] - 2 * p["corner_radius"],
        p["lower_depth"] - 2 * p["corner_radius"],
        0.02,
    ).cut(shapes["lower-support"])
    assert len(void.Solids) == 1
    # STEP lofts may retain a larger underlying spline surface after trimming.
    # BoundBox encloses that surface; optimalBoundingBox measures the trimmed slab.
    bounds = void.optimalBoundingBox()
    extra = 2 * p["lower_bevel_run"] * max(0.0, 1 - fraction)
    assert abs(bounds.XLength - p["lower_opening_width"] - extra) < 1e-6
    assert abs(bounds.YLength - p["lower_opening_depth"] - extra) < 1e-6
    assert abs((bounds.XMin + bounds.XMax) / 2 - opening_profile["centre_x"]) < 1e-6
    assert abs((bounds.YMin + bounds.YMax) / 2 - opening_profile["centre_y"]) < 1e-6
    bevel_sections.append(
        {
            "depth_below_top": depth,
            "width": bounds.XLength,
            "depth": bounds.YLength,
        }
    )
controls = {}
for label, thickness in (
    ("below", p["slot_gap"] - 0.1),
    ("at", p["slot_gap"]),
    ("above", p["slot_gap"] + 0.1),
):
    s = probe(0, -4, -p["slot_gap"], 8, 2, thickness)
    controls[label] = {
        "thickness_mm": thickness,
        "overlap_mm3": overlap(s, shapes["underside-plate"]),
    }
assert (
    controls["below"]["overlap_mm3"] < 1e-6
    and controls["at"]["overlap_mm3"] < 1e-6
    and controls["above"]["overlap_mm3"] > 0.1
)
screw_overlap = None
if "screw-head-1" in shapes:
    screw = shapes["screw-head-1"]
    c = screw.Solids[0].CenterOfMass
    s = probe(c.x, c.y, -p["slot_gap"], 2, 2, p["slot_gap"])
    screw_overlap = overlap(s, screw)
    assert screw_overlap > 1e-6
# Independent straight optical-path check through both openings.
beam = probe(
    0,
    -p["optical_centre_depth"],
    -100,
    p["optical_width"] - 0.1,
    p["optical_depth"] - 0.1,
    200,
)
beam_overlap = sum(overlap(beam, s) for s in shapes.values())
assert beam_overlap < 1e-6, beam_overlap

doc = App.newDocument("Durst_C35_Insertion_Area")
parameters = doc.addObject("App::FeaturePython", "InterfaceParameters")
for name, value, group, description in [
    (
        "HeadWidth",
        p["neck_width"],
        "User measurements",
        "B-head: external neck width; user measured",
    ),
    (
        "RestGap",
        p["slot_gap"],
        "User measurements",
        "A: approximate unloaded gap; excludes local screw protrusion",
    ),
    (
        "LowerDrop",
        0.0,
        "Prescribed placement",
        "Positive downward displacement. NOT a spring-force or deformation solution",
    ),
]:
    parameters.addProperty("App::PropertyLength", name, group, description)
    setattr(parameters, name, value)
parameters.addProperty("App::PropertyString", "EvidenceJSON", "Evidence")
parameters.EvidenceJSON = json.dumps(measured)
parameters.addProperty("App::PropertyBool", "PhysicalFitAccepted", "Evidence")
parameters.PhysicalFitAccepted = False
parameters.addProperty("App::PropertyString", "Scope", "Evidence")
parameters.Scope = data["scope"]
for name, shape in shapes.items():
    obj = doc.addObject("Part::Feature", name.replace("-", "_"))
    obj.Label = name + (
        " (unmeasured screw envelope)" if name.startswith("screw") else ""
    )
    obj.Shape = shape
    if name == "lower-support":
        obj.setExpression("Placement.Base.z", "-InterfaceParameters.LowerDrop")
doc.recompute()
fixed_bounds = shapes["underside-plate"].BoundBox.ZMin
parameters.LowerDrop = 0.15
doc.recompute()
assert (
    abs(doc.getObject("lower_support").Shape.BoundBox.ZMax + p["slot_gap"] + 0.15)
    < 1e-6
)
assert abs(doc.getObject("underside_plate").Shape.BoundBox.ZMin - fixed_bounds) < 1e-6
parameters.LowerDrop = 0
doc.recompute()
path = out / "insertion-area.FCStd"
doc.saveAs(str(path))
App.closeDocument(doc.Name)
reopened = App.openDocument(str(path))
assert len(reopened.Objects) == len(shapes) + 1
reopened.getObject("InterfaceParameters").LowerDrop = 0.1
reopened.recompute()
assert (
    abs(reopened.getObject("lower_support").Shape.BoundBox.ZMax + p["slot_gap"] + 0.1)
    < 1e-6
)
App.closeDocument(reopened.Name)
(out / "freecad-validation.json").write_text(
    json.dumps(
        {
            "geometry_passed": True,
            "physical_fit_accepted": False,
            "freecad_version": App.Version(),
            "manifest_sha256": sha(manifest_path),
            "native_document_sha256": sha(path),
            "native_solids": len(shapes),
            "lower_opening_mm": opening_profile,
            "lower_bevel_sections_mm": bevel_sections,
            "side_profile_mm": {
                "neck_depth": neck_section.BoundBox.YLength,
                "raised_support_depth": lower_section.BoundBox.YLength,
                "rear_plane_difference": rear_difference,
                "flange_front_overhang": shapes["lower-support"].BoundBox.YMax
                - lower_section.BoundBox.YMax,
                "flange_thickness": shapes["lower-support"].BoundBox.ZLength
                - p["lower_height"],
            },
            "relative_import_volume_errors": volume_errors,
            "maximum_part_overlap_mm3": max_overlap,
            "optical_path_intersection_mm3": beam_overlap,
            "negative_controls": {
                "flat_plate_probe_overlap_mm3": controls,
                "screw_probe_overlap_mm3": screw_overlap,
            },
            "saved_lower_drop_expression_reopened_and_checked": True,
            "force_simulation_performed": False,
        },
        indent=2,
    )
    + "\n"
)
