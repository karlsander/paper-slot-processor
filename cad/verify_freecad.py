"""FreeCAD verification of native solids, assembly, print plates and wet geometry."""

import json
import os
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

out = Path(os.environ["PROCESSOR_NATIVE_OUTPUT"])
report_path = out / "validation.json"
report_path.unlink(missing_ok=True)
p = json.loads((out / "parameters.json").read_text())
model = json.loads((out / "model-report.json").read_text())
shapes = {}
roundtrip = []
for entry in model["parts"]:
    name = entry["name"]
    shape = Part.read(str(out / f"{name}.step"))
    assert shape.isValid() and len(shape.Solids) == 1, name
    error = abs(shape.Volume - entry["volume_mm3"])
    assert error < 0.01, (name, error)
    shapes[name] = shape
    roundtrip.append({"part": name, "volume_error_mm3": error, "valid": True})
print("STEP round trips passed", flush=True)
plates = []
for entry in model["plates"]:
    name = entry["name"]
    shape = Part.read(str(out / "plates" / f"{name}.step"))
    mesh = Mesh.Mesh(str(out / "plates" / f"{name}.stl"))
    assert shape.isValid() and len(shape.Solids) == entry["solid_count"], name
    assert mesh.isSolid(), name
    box = mesh.BoundBox
    assert abs(box.ZMin) < 0.001, (name, box.ZMin)
    assert (
        box.XMin >= -0.001
        and box.YMin >= -0.001
        and box.XMax <= 180.001
        and box.YMax <= 180.001
    ), name
    assert all(
        v <= limit + 0.001
        for v, limit in zip(
            (box.XLength, box.YLength, box.ZLength), p["usable_xy"] + [p["usable_z"]]
        )
    ), name
    plates.append(
        {
            "part": name,
            "watertight_mesh": True,
            "solid_count": len(shape.Solids),
            "bounds_mm": [box.XLength, box.YLength, box.ZLength],
        }
    )


def moved(shape, x=0, y=0, z=0):
    s = shape.copy()
    s.translate(App.Vector(x, y, z))
    return s


def overlap(a, b):
    return max(0, a.common(b).Volume)


def position(s, i=0, z=0):
    return moved(
        s, p["vessel_x"], p["vessel_y"] + i * p["vessel_pitch"], p["cradle_floor"] + z
    )


assembly = {"base": shapes["base"]}
for i, letter in enumerate("ab"):
    assembly[f"vessel_{letter}"] = position(shapes[f"vessel_{letter}"], i)
    assembly[f"guide_{letter}"] = position(
        shapes[f"guide_{letter}"], i, p["guide_seat"]
    )
collisions = []
for i, (name, a) in enumerate(assembly.items()):
    for other, b in list(assembly.items())[i + 1 :]:
        volume = overlap(a, b)
        assert volume < 1e-4, (name, other, volume)
        collisions.append({"parts": [name, other], "overlap_mm3": volume})
print("Assembly pairs clear", flush=True)
motion = []
for i, letter in enumerate("ab"):
    moving_names = [
        f"vessel_{letter}",
        f"guide_{letter}",
    ]
    # Move a complete bath module; include the neighboring module's top.
    for lift in (0, 0.5, 4, 16, 31, 32, 36, 60, p["body_height"]):
        for name in moving_names:
            moving = moved(assembly[name], z=lift)
            volume = sum(
                overlap(moving, fixed)
                for fixed_name, fixed in assembly.items()
                if fixed_name not in moving_names
            )
            assert volume < 1e-4, (name, lift, volume)
        motion.append({"chamber": letter, "lift_mm": lift, "clear": True})
    for lift in (0, 0.5, 1, 2, 4, 20):
        top = position(shapes[f"guide_{letter}"], i, p["guide_seat"] + lift)
        assert overlap(top, assembly[f"vessel_{letter}"]) < 1e-4, (letter, lift)
        assert overlap(top, assembly[f"vessel_{'ba'[i]}"]) < 1e-4
print("Removal paths clear", flush=True)
# Measure nominal socket side clearance separately from the seating contact.
sides = shapes["base"].common(
    Part.makeBox(
        p["base_width"] + 2,
        p["base_depth"] + 2,
        p["socket_height"],
        App.Vector(-1, -1, p["cradle_floor"] + 0.01),
    )
)
clearances = [sides.distToShape(assembly[f"vessel_{letter}"])[0] for letter in "ab"]
assert all(abs(v - p["cradle_clearance"]) < 1e-5 for v in clearances), clearances
wet = []
paper_tests = []
for i, letter in enumerate("ab"):
    cavity = Part.read(str(out / f"liquid-cavity-{letter}.step"))
    for loaded in (False, True):
        level = p["loaded_level"] if loaded else p["empty_level"]
        water = cavity.common(Part.makeBox(500, 500, level, App.Vector(-100, -100, 0)))
        sheet = Part.makeBox(
            p["roll_width"],
            p["paper_thickness"],
            p["paper_cut_length"],
            App.Vector(
                p["wall"] + p["side_clearance"],
                p["body_depth"] / 2 - p["paper_thickness"] / 2,
                p["paper_bottom"],
            ),
        )
        if loaded:
            water = water.cut(sheet)
        assert water.isValid() and overlap(water, shapes[f"vessel_{letter}"]) < 1e-4
        ml = water.Volume / 1000
        assert abs(ml - p["working_ml"]) < 0.01, (letter, loaded, ml)
        wet.append(
            {
                "chamber": letter,
                "loaded": loaded,
                "level_mm": level,
                "volume_ml": ml,
                "error_ml": ml - p["working_ml"],
            }
        )
    guide = moved(shapes[f"guide_{letter}"], z=p["guide_seat"])
    for gap in (p["guide_gap"],):
        g = guide
        for lift in (0, p["vertical_stroke"] / 2, p["vertical_stroke"]):
            for side in (-p["lateral_stroke"], 0, p["lateral_stroke"]):
                paper = moved(sheet, side, 0, lift)
                assert overlap(paper, shapes[f"vessel_{letter}"]) < 1e-4, (
                    "paper bath",
                    letter,
                    lift,
                    side,
                )
                assert overlap(paper, g) < 1e-4, (
                    "paper guide",
                    letter,
                    gap,
                    lift,
                    side,
                )
                margin = g.distToShape(paper)[0]
                assert margin > 0.1 - 1e-6, (gap, margin)
                paper_tests.append(
                    {
                        "chamber": letter,
                        "gap_mm": gap,
                        "lift_mm": lift,
                        "side_mm": side,
                        "guide_clearance_mm": margin,
                    }
                )
    # A single conservative box contains every intermediate agitation position.
    envelope = Part.makeBox(
        p["roll_width"] + 2 * p["lateral_stroke"],
        p["paper_thickness"],
        p["paper_cut_length"] + p["vertical_stroke"],
        App.Vector(
            p["wall"] + p["side_clearance"] - p["lateral_stroke"],
            p["body_depth"] / 2 - p["paper_thickness"] / 2,
            p["paper_bottom"],
        ),
    )
    assert overlap(envelope, shapes[f"vessel_{letter}"]) < 1e-4
    assert overlap(envelope, guide) < 1e-4
print("Wet volume and paper travel passed", flush=True)
# Verify the manufactured interfaces directly, independently of the build123d authoring.
assert len(shapes) == len(assembly) == len(model["plates"]) == 5
assert set(shapes) == {"base", "vessel_a", "vessel_b", "guide_a", "guide_b"}
magnet_checks, rim_clearances, ridge_checks = [], [], []
for letter in "ab":
    bath = shapes[f"vessel_{letter}"]
    top = moved(shapes[f"guide_{letter}"], z=p["guide_seat"])
    cavity = Part.read(str(out / f"liquid-cavity-{letter}.step"))
    ring = bath.common(
        Part.makeBox(
            500,
            500,
            p["rim_height"] - 0.02,
            App.Vector(-100, -100, p["guide_seat"] + 0.01),
        )
    )
    clearance = ring.distToShape(top)[0]
    assert abs(clearance - p["guide_fit"]) < 1e-5, clearance
    rim_clearances.append(clearance)
    assert abs(bath.BoundBox.YMax - p["body_depth"]) < 1e-5, (
        "Rear heater interface changed"
    )
    for x in p["magnet_x"]:
        bottom_z = p["guide_seat"] - p["pocket_depth"]
        top_z = p["guide_seat"] + p["magnet_depth_allowance"]
        bottom_magnet = Part.makeCylinder(
            p["magnet_diameter"] / 2,
            p["magnet_thickness"],
            App.Vector(x, p["body_depth"] / 2, bottom_z),
        )
        top_magnet = Part.makeCylinder(
            p["magnet_diameter"] / 2,
            p["magnet_thickness"],
            App.Vector(x, p["body_depth"] / 2, top_z),
        )
        for magnet, host, floor_z in [
            (bottom_magnet, bath, bottom_z - 0.1),
            (top_magnet, top, p["guide_seat"] + p["pocket_depth"] + 0.01),
        ]:
            assert overlap(magnet, host) < 1e-4
            pocket_probe = Part.makeCylinder(
                p["pocket_diameter"] / 2 - 0.01,
                p["pocket_depth"] - 0.02,
                App.Vector(
                    x,
                    p["body_depth"] / 2,
                    bottom_z + 0.01 if host is bath else p["guide_seat"] + 0.01,
                ),
            )
            assert overlap(pocket_probe, host) < 1e-4
            floor_probe = Part.makeCylinder(
                p["magnet_diameter"] / 2,
                0.08,
                App.Vector(x, p["body_depth"] / 2, floor_z),
            )
            assert abs(overlap(floor_probe, host) - floor_probe.Volume) < 1e-4
            assert overlap(magnet, cavity) < 1e-4
        separation = bottom_magnet.distToShape(top_magnet)[0]
        assert abs(separation - 2 * p["magnet_depth_allowance"]) < 1e-5
        magnet_checks.append(
            {
                "chamber": letter,
                "center_x_mm": x,
                "diameter_mm": p["pocket_diameter"],
                "depth_mm": p["pocket_depth"],
                "recessed_magnet_gap_mm": separation,
                "dry_pockets": True,
            }
        )
    # Four points check inward projection; the cavity boundary is one closed wire.
    z = p["empty_level"] - p["ridge_height"] / 2
    t = p["ridge_projection"] / 2
    for x, y in [
        (p["wall"] + t, p["body_depth"] / 2),
        (p["body_width"] - p["wall"] - t, p["body_depth"] / 2),
        (p["body_width"] / 2, p["wall"] + t),
        (p["body_width"] / 2, p["body_depth"] - p["wall"] - t),
    ]:
        assert bath.isInside(App.Vector(x, y, z), 1e-6, False)
        assert not bath.isInside(App.Vector(x, y, p["empty_level"] + 0.1), 1e-6, False)
    section = cavity.section(Part.makePlane(500, 500, App.Vector(-100, -100, z)))
    wires = Part.__sortEdges__(section.Edges)
    assert len(wires) == len(section.Edges) and Part.Wire(wires).isClosed()
    ridge_checks.append(
        {
            "chamber": letter,
            "top_edge_mm": p["empty_level"],
            "projection_mm": p["ridge_projection"],
            "height_mm": p["ridge_height"],
            "continuous_boundary": True,
        }
    )
print(
    "Five parts, dry magnet seats, rim fit and continuous fill ridge passed", flush=True
)
doc = App.newDocument("NativeProcessor")
for name, shape in assembly.items():
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = name.replace("_", " ").title()
    obj.Shape = shape
doc.recompute()
doc.saveAs(str(out / "processor.FCStd"))
report_path.write_text(
    json.dumps(
        {
            "passed": True,
            "freecad_version": App.Version(),
            "roundtrip": roundtrip,
            "magnet_seats": magnet_checks,
            "top_rim_clearance_mm": rim_clearances,
            "fill_ridge": ridge_checks,
            "plates": plates,
            "assembly_pairs": collisions,
            "bath_removal_samples": motion,
            "socket_clearance_mm": clearances,
            "wet_volume": wet,
            "paper_agitation": paper_tests,
            "limitations": [
                "Rigid geometry only; no friction, deformation, leakage or chemical compatibility tested.",
                "Paper modeled as a flat rigid sheet.",
                "Motion checks are sampled except the conservative paper agitation envelope.",
                "Magnetic force, adhesive bond and printed pocket tolerances are untested.",
                "FreeCAD and build123d share the Open Cascade geometry kernel.",
            ],
        },
        indent=2,
    )
    + "\n"
)
print("PASS: complete native processor", flush=True)
