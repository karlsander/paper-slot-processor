"""Run inside FreeCADCmd: verify native exchange, thin sections and rigid motion."""

import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

out = Path(os.environ["DURST_C35_OUTPUT"])
report_path = out / "validation.json"
report_path.unlink(missing_ok=True)
p = json.loads((out / "parameters.json").read_text())
model = json.loads((out / "model-report.json").read_text())


def box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, App.Vector(x, y, z))


def overlap(a, b):
    return max(0, a.common(b).Volume)


def move(shape, x=0, y=0, z=0):
    shape = shape.copy()
    shape.translate(App.Vector(x, y, z))
    return shape


def opened(shape, angle):
    shape = move(shape, z=p["film_gap"])
    shape.rotate(App.Vector(0, p["hinge_y"], p["hinge_z"]), App.Vector(1, 0, 0), angle)
    return shape


shapes, roundtrips, plates, sections = {}, [], [], []
for entry in model["parts"]:
    half = entry["name"]
    s = Part.read(str(out / f"{half}.step"))
    assert s.isValid() and len(s.Solids) == 1, half
    error = abs(s.Volume - entry["volume_mm3"])
    assert error < 0.01, (half, error)
    shapes[half] = s
    roundtrips.append({"part": half, "volume_error_mm3": error})
    plate = Part.read(str(out / "plates" / f"{half}.step"))
    mesh = Mesh.Mesh(str(out / "plates" / f"{half}.stl"))
    b = mesh.BoundBox
    assert plate.isValid() and len(plate.Solids) == 1 and mesh.isSolid(), half
    assert abs(plate.Volume - s.Volume) < 0.01
    assert abs(b.ZMin) < 1e-4 and b.XMin >= 3 and b.YMin >= 3
    assert b.XMax <= 177 and b.YMax <= 177 and b.ZMax <= 178
    plates.append(
        {"part": half, "size_mm": [b.XLength, b.YLength, b.ZLength], "mesh_solid": True}
    )
    # Full-height columns measure the actual sheet, independently of authoring.
    # Side edges, window rim, pin bosses and hinge tabs are intentionally excluded.
    for x, y in [
        (-35, 25),
        (35, 25),
        (-35, 54),
        (35, 54),
        (-35, 80),
        (35, 80),
        (0, 20),
        (0, 85),
    ]:
        start = -p["outer_height_a"] - 1 if half == "a" else 0
        sample = box(x - 1, y - 1, start, 2, 2, p[f"outer_height_{half}"] + 1)
        section = s.common(sample)
        assert abs(section.Volume / 4 - p["sheet_thickness"]) < 1e-6, (
            half,
            x,
            y,
            section.Volume,
        )
        assert abs(section.BoundBox.ZLength - p["sheet_thickness"]) < 1e-6
        sections.append(
            {"part": half, "xy_mm": [x, y], "thickness_mm": section.BoundBox.ZLength}
        )
    sign = -1 if half == "a" else 1
    for side in (-1, 1):
        # Thin vertical wall at a straight middle section.
        sample = box(
            side * p["body_width"] / 2 - 2 * p["side_wall"]
            if side > 0
            else -p["body_width"] / 2 - 1,
            53,
            sign * 7 - 0.5,
            2 * p["side_wall"] + 1,
            2,
            1,
        )
        assert abs(overlap(s, sample) - 2 * p["side_wall"]) < 1e-6, (half, "side wall")
    start = -p["outer_height_a"] + 0.1 if half == "a" else p["window_rim_height"] + 0.1
    cavity = box(
        -40, 16, start, 80, 75, p[f"outer_height_{half}"] - p["window_rim_height"] - 0.2
    )
    assert overlap(s, cavity) < 1e-6, (half, "hollow exterior")
    # This point lies within the local window reinforcement, outside its flare.
    x = (
        p["window_x"] / 2
        + (p["b_aperture_relief"] if half == "b" else 0)
        + p["aperture_flare"]
        + p["window_rim_width"] / 2
    )
    sample = box(
        x - 0.1,
        p["window_center_y"] - 0.1,
        -p["outer_height_a"] if half == "a" else 0,
        0.2,
        0.2,
        p[f"outer_height_{half}"],
    )
    assert abs(overlap(s, sample) / 0.04 - p["window_rim_height"]) < 1e-6, (
        half,
        "local window rim",
    )
print("STEP, print meshes and thin-sheet sections passed", flush=True)

# The optical tunnel remains clear through both halves. Independently check the
# A aperture at its film land, and the four B insets and relieved midsections.
a, b = shapes["a"], opened(shapes["b"], 0)
assembly = a.fuse(b)
optical = box(
    -p["window_x"] / 2, p["b_rear_margin"], -20, p["window_x"], p["window_y"], 40
)
assert overlap(assembly, optical) < 1e-6
land = box(
    -p["window_x"] / 2 - 2,
    p["b_rear_margin"] - 2,
    -p["aperture_land"] / 2,
    p["window_x"] + 4,
    p["window_y"] + 4,
    0.1,
).cut(a)
assert abs(land.BoundBox.XLength - p["window_x"]) < 1e-6
assert abs(land.BoundBox.YLength - p["window_y"]) < 1e-6
for x in (-p["window_x"] / 2 - 0.4, p["window_x"] / 2 + 0.2):
    for y in (p["b_rear_margin"] - 0.4, p["b_rear_margin"] + p["window_y"] + 0.2):
        probe = box(x, y, 0.05, 0.2, 0.2, 0.2)
        assert abs(overlap(shapes["b"], probe) - probe.Volume) < 1e-6
for x, y, dx, dy in [
    (-p["window_x"] / 2 - 0.5, p["window_center_y"] - 1, 0.2, 2),
    (p["window_x"] / 2 + 0.3, p["window_center_y"] - 1, 0.2, 2),
    (-1, p["b_rear_margin"] - 0.5, 2, 0.2),
    (-1, p["b_rear_margin"] + p["window_y"] + 0.3, 2, 0.2),
]:
    assert overlap(shapes["b"], box(x, y, 0.05, dx, dy, 0.2)) < 1e-6
film_thickness = 0.14
assert p["film_gap"] > film_thickness
film = box(
    -45,
    p["window_center_y"] - p["film_width"] / 2,
    (p["film_gap"] - film_thickness) / 2,
    90,
    p["film_width"],
    film_thickness,
)
assert overlap(assembly, film) < 1e-6
# Blind recesses have a local closed floor, without thickening the panel.
floors = []
for x in (-p["film_pin_spacing"] / 2, p["film_pin_spacing"] / 2):
    floor = Part.makeCylinder(
        p["b_pin_recess_bottom"] / 2 - 0.1,
        p["b_pin_boss_height"] - p["b_pin_recess_depth"],
        App.Vector(x, p["film_pin_y"], p["b_pin_recess_depth"]),
    )
    assert abs(overlap(shapes["b"], floor) - floor.Volume) < 1e-6
    floors.append(p["b_pin_boss_height"] - p["b_pin_recess_depth"])
print("Optical opening, film path and blind recess floors passed", flush=True)

motion = []
for angle in range(181):
    moving = opened(shapes["b"], angle)
    volume = overlap(a, moving)
    assert volume < 1e-4, (angle, volume)
    motion.append({"angle_deg": angle, "overlap_mm3": volume})
print("181 rigid hinge positions passed", flush=True)

# Save two separate documents to avoid duplicating open and closed solids in an
# ambiguous assembly. Reopen the saved documents before declaring success.
for angle, name in [(0, "carrier"), (110, "carrier-open")]:
    doc = App.newDocument("DurstCarrier")
    for half, shape in [("a", a), ("b", opened(shapes["b"], angle))]:
        obj = doc.addObject("PartDesign::Feature", half.upper())
        obj.Label = f"{half.upper()} — thin formed carrier"
        obj.Shape = shape
        obj.addProperty(
            "App::PropertyLength", "SheetThickness", "Prototype"
        ).SheetThickness = p["sheet_thickness"]
        obj.addProperty(
            "App::PropertyString", "Evidence", "Prototype"
        ).Evidence = f"Provisional {p['sheet_thickness']:g} mm sheet; enlarger slot unmodeled; physical fit unverified"
    doc.recompute()
    path = out / f"{name}.FCStd"
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(path))
    assert len(reopened.Objects) == 2
    for obj in reopened.Objects:
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1
    App.closeDocument(reopened.Name)

report_path.write_text(
    json.dumps(
        {
            "passed": True,
            "freecad_version": App.Version(),
            "roundtrips": roundtrips,
            "plates": plates,
            "model_report_sha256": hashlib.sha256(
                (out / "model-report.json").read_bytes()
            ).hexdigest(),
            "sheet_sections": sections,
            "blind_floor_mm": floors,
            "hinge_samples": motion,
            "optical_opening_mm": [p["window_x"], p["window_y"]],
            "film_probe_mm": [90, 35, film_thickness],
            "nominal_closed_sheet_stack_mm": 2 * p["sheet_thickness"] + p["film_gap"],
            "nominal_window_rim_stack_mm": 2 * p["window_rim_height"] + p["film_gap"],
            "physical_fit_verified": False,
            "enlarger_slot_modeled": False,
            "limitations": [
                "Rigid hinge samples at 1 degree intervals, not a continuous swept-volume proof.",
                "No elastic snap-fit, friction, print warp, film grip, light leaks or thermal performance solved.",
                "The enlarger mating slot has not been modeled; no insertion-fit claim.",
                "build123d and FreeCAD both use Open Cascade.",
            ],
        },
        indent=2,
    )
    + "\n"
)
print("PASS: saved and reopened both FreeCAD carrier documents", flush=True)
