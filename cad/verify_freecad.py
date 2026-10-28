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
parity = []
for file in sorted((out / "parity").glob("*.step")):
    shape = Part.read(str(file))
    mesh = Mesh.Mesh(str(file.with_suffix(".stl")))
    assert mesh.isSolid(), file.name
    # Sample all vertices plus a deterministic subset of triangle centroids.
    points = [v.Vector for v in mesh.Points]
    facets = mesh.Facets
    points += [
        sum((App.Vector(*v) for v in facets[i].Points), App.Vector()) / 3
        for i in range(0, len(facets), max(1, len(facets) // 200))
    ]
    boundary = Part.makeCompound(shape.Shells)
    dev = max(Part.Vertex(point).distToShape(boundary)[0] for point in points)
    rel = abs(shape.Volume - mesh.Volume) / mesh.Volume
    assert dev < 0.05, (file.stem, "boundary", dev)
    assert rel < 0.003, (file.stem, "volume", rel)
    parity.append(
        {
            "part": file.stem,
            "sample_points": len(points),
            "maximum_sampled_deviation_mm": dev,
            "relative_volume_error": rel,
        }
    )
    print("Parity", file.stem, dev, rel, flush=True)
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
        shapes[f"guide_{letter}"], i, p["body_height"]
    )
    for j, x in enumerate((p["body_width"] / 4, 3 * p["body_width"] / 4)):
        assembly[f"clip_{letter}{j}"] = position(
            moved(shapes["clip"], x - p["clip_width"] / 2, -4.2, p["body_height"] - 4),
            i,
        )
collisions = []
for i, (name, a) in enumerate(assembly.items()):
    for other, b in list(assembly.items())[i + 1 :]:
        volume = overlap(a, b)
        assert volume < 1e-4, (name, other, volume)
        collisions.append({"parts": [name, other], "overlap_mm3": volume})
print("Assembly pairs clear", flush=True)
# Covers substitute for guides, using the same seats and clips.
for i, letter in enumerate("ab"):
    cover = position(shapes[f"cover_{letter}"], i, p["body_height"])
    for name in (f"vessel_{letter}", f"clip_{letter}0", f"clip_{letter}1"):
        assert overlap(cover, assembly[name]) < 1e-4, ("cover", name)

motion = []
for i, letter in enumerate("ab"):
    moving_names = [
        f"vessel_{letter}",
        f"guide_{letter}",
        f"clip_{letter}0",
        f"clip_{letter}1",
    ]
    # Move a complete bath module; include the neighboring module's guide/clips.
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
    # Remove the clips first, then lift each guide/cover vertically.
    for kind in ("guide", "cover"):
        for lift in (0, 0.5, 1, 2, 4, 20):
            s = position(shapes[f"{kind}_{letter}"], i, p["body_height"] + lift)
            assert overlap(s, assembly[f"vessel_{letter}"]) < 1e-4, (kind, letter, lift)
    for offset in (0, -0.5, -1, -2, -4, -8, -12):
        for j in (0, 1):
            s = moved(assembly[f"clip_{letter}{j}"], y=offset)
            for name in (f"vessel_{letter}", f"guide_{letter}"):
                assert overlap(s, assembly[name]) < 1e-4, (
                    "clip slide",
                    letter,
                    offset,
                    name,
                )
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
        assert abs(ml - p["working_ml"]) < 0.5, (letter, loaded, ml)
        wet.append(
            {
                "chamber": letter,
                "loaded": loaded,
                "level_mm": level,
                "volume_ml": ml,
                "error_ml": ml - p["working_ml"],
            }
        )
    guide = moved(shapes[f"guide_{letter}"], z=p["body_height"])
    for gap in (0.6, 0.8, 1.2):
        g = (
            guide
            if gap == 1.2
            else moved(shapes[f"trial_{letter}_{int(gap * 10)}"], z=p["body_height"])
        )
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
doc = App.newDocument("NativeProcessor")
for name, shape in assembly.items():
    obj = doc.addObject("PartDesign::Feature", name)
    obj.Label = name.replace("_", " ").title()
    obj.Shape = shape
for i, letter in enumerate("ab"):
    obj = doc.addObject("PartDesign::Feature", f"Cover_{letter}")
    obj.Shape = position(shapes[f"cover_{letter}"], i, p["body_height"] + 45)
doc.recompute()
doc.saveAs(str(out / "processor.FCStd"))
report_path.write_text(
    json.dumps(
        {
            "passed": True,
            "freecad_version": App.Version(),
            "roundtrip": roundtrip,
            "functional_surface_parity": parity,
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
                "Lettering excluded from SCAD parity; analytic arcs differ from tessellated circles.",
                "FreeCAD and build123d share the Open Cascade geometry kernel.",
            ],
        },
        indent=2,
    )
    + "\n"
)
print("PASS: complete native processor", flush=True)
