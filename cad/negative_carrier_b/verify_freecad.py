"""Independent FreeCAD B-rep checks. Run only in FreeCAD's Python interpreter."""

import hashlib
import json
import os
from itertools import combinations
from pathlib import Path

import FreeCAD as App
import Part

out = Path(os.environ["NEGATIVE_B_OUTPUT"])
manifest_path = out / "manifest.json"
manifest = json.loads(manifest_path.read_text())
report = {
    "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    "freecad_version": App.Version(),
    "physical_fit_verified": False,
    "spring_forces_or_film_friction_solved": False,
    "evidence_level": "Sampled B-rep interference and normal-ray masks; imposed flexure shapes",
    "models": [],
}
assets = {}
for key, record in manifest["assets"].items():
    path = out / record["file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], key
    shape = Part.read(str(path))
    assert shape.isValid() and len(shape.Solids) == 1, key
    assert abs(shape.Volume - record["volume_mm3"]) < 1e-4, key
    assets[key] = shape
    if "relaxed_native" in record:
        native = record["relaxed_native"]
        path = out / native["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == native["sha256"]
        relaxed = Part.read(str(path))
        assert (
            relaxed.isValid()
            and len(relaxed.Solids) == 1
            and abs(relaxed.Volume - native["volume_mm3"]) < 1e-4
        )
print("Read", len(assets), "valid STEP solids", flush=True)


def posed(record):
    shape = assets[record["asset"]].copy()
    rotation = App.Rotation(App.Vector(0, 0, 1), record["angle"])
    pivot = App.Vector(*record["pivot"], 0)
    delta = App.Vector(*record["translation"]) + pivot - rotation.multVec(pivot)
    shape.Placement = App.Placement(delta, rotation)
    return shape


def overlap(a, b):
    aa, bb = a.BoundBox, b.BoundBox
    if any(
        min(getattr(aa, axis + "Max"), getattr(bb, axis + "Max"))
        - max(getattr(aa, axis + "Min"), getattr(bb, axis + "Min"))
        < 1e-7
        for axis in "XYZ"
    ):
        return 0.0
    return abs(a.common(b).Volume)


cache = {}
for model in manifest["models"]:
    result = {
        "format": model["format"],
        "samples": [],
        "failures": [],
        "negative_controls": {},
        "optical_samples": [],
    }
    unique_failures = set()
    for i, sample in enumerate(model["samples"]):
        shapes = {r["name"]: posed(r) for r in sample["parts"]}
        records = {r["name"]: r for r in sample["parts"]}
        maximum = 0
        for (an, a), (bn, b) in combinations(shapes.items(), 2):
            relative = a.Placement.inverse().multiply(b.Placement).toMatrix()
            key = (
                records[an]["asset"],
                records[bn]["asset"],
                *(round(v, 7) for v in relative.A),
            )
            if key not in cache:
                cache[key] = overlap(a, b)
            value = cache[key]
            maximum = max(maximum, value)
            if value > 1e-5:
                failure = (sample["group"], sample["phase"], an, bn)
                if failure not in unique_failures:
                    unique_failures.add(failure)
                    result["failures"].append(
                        {
                            "phase": sample["label"],
                            "sample": i,
                            "a": an,
                            "b": bn,
                            "overlap_mm3": value,
                        }
                    )
        result["samples"].append(
            {
                "group": sample["group"],
                "phase": sample["phase"],
                "t": sample["t"],
                "max_overlap_mm3": maximum,
            }
        )
        if i % 50 == 0:
            print(
                model["format"],
                i,
                "/",
                len(model["samples"]),
                "failures",
                len(result["failures"]),
                flush=True,
            )
    closed_sample = next(s for s in model["samples"] if s["group"] == "advance")
    closed = {r["name"]: posed(r) for r in closed_sample["parts"]}
    # Exact translational sweeps for the planar holder parts. A solid swept by
    # a vector is covered by its initial solid and the extrusions of its faces.
    # Test these separately to avoid a large, unnecessary Boolean union.
    released_sample = next(
        s
        for s in model["samples"]
        if s["group"] == "advance" and s["state"]["index_release"] == 4
    )
    released = {r["name"]: posed(r) for r in released_sample["parts"]}
    moving_names = [
        n for n in released if n in ("base", "lid", "film") or n.startswith("closure-")
    ]
    direction = App.Vector(-model["format_data"]["travel"], 0, 0)
    sweep_maximum = 0.0
    sweep_prisms = 0
    for name in moving_names:
        start = released[name]
        for face in start.Faces:
            assert type(face.Surface).__name__ == "Plane", (
                name,
                type(face.Surface).__name__,
            )
            if abs(face.normalAt(0, 0).dot(direction)) < 1e-7:
                continue
            prism = face.extrude(direction)
            if prism.Volume < 0:
                prism.reverse()
            assert prism.isValid() and len(prism.Solids) > 0
            sweep_prisms += 1
            for other, fixed in released.items():
                if other not in moving_names:
                    sweep_maximum = max(sweep_maximum, overlap(prism, fixed))
    result["continuous_frame_travel"] = {
        "distance_mm": model["format_data"]["travel"],
        "face_prisms": sweep_prisms,
        "max_overlap_mm3": sweep_maximum,
    }
    # Controls deliberately violate the mechanical constraints. They must collide.
    shifted = closed["base"].copy()
    shifted.translate(App.Vector(0.5, 0, 0))
    result["negative_controls"]["index_tooth_blocks_unreleased_slide_mm3"] = overlap(
        shifted, closed["index-latch"]
    )
    shifted = closed["base"].copy()
    shifted.translate(App.Vector(0, 0.5, 0))
    result["negative_controls"]["guide_blocks_sideways_shift_mm3"] = overlap(
        shifted, closed["collar-base"]
    )
    shifted = closed["collar-cap"].copy()
    shifted.translate(App.Vector(0, 0, 0.5))
    result["negative_controls"]["turned_keys_block_cap_lift_mm3"] = sum(
        overlap(shifted, s) for n, s in closed.items() if n.startswith("cap-lock-")
    )
    for axis, vector in [("forward", (0, 0.3, 0)), ("sideways", (0.3, 0, 0))]:
        shifted = closed["collar-base"].copy()
        shifted.translate(App.Vector(*vector))
        result["negative_controls"]["dock_cams_block_" + axis + "_shift_mm3"] = sum(
            overlap(shifted, s) for n, s in closed.items() if n.startswith("dock-lock-")
        )
    clipname = next(
        n
        for n in closed
        if n.startswith("closure-") and n.endswith("-1") and not n.endswith("--1")
    )
    shifted = closed[clipname].copy()
    shifted.translate(App.Vector(0, 0.5, 0))
    result["negative_controls"]["clip_catch_blocks_unreleased_pull_mm3"] = overlap(
        shifted, closed["base"]
    )
    shifted = closed["collar-cap"].copy()
    shifted.translate(App.Vector(0, 0, -1))
    result["negative_controls"]["overthick_mask_hits_holder_mm3"] = overlap(
        shifted, closed["lid"]
    )
    thick = Part.makeBox(100, 48, 4, App.Vector(-50, -24, -1.1))
    result["negative_controls"]["solid_slab_hits_enlarger_mm3"] = overlap(
        thick, closed["fixture-head"]
    )
    fmt = model["format_data"]
    aw, ah = fmt["aperture"]
    if model["format"] == "110" and "135/collar-cap" in assets:
        beam = Part.makeBox(40, 28, 0.1, App.Vector(-20, -14, 2))
        wrong = beam.cut(assets["135/collar-cap"])
        neighbours = 0
        for dx in (-fmt["demo_pitch"], fmt["demo_pitch"]):
            ray = Part.makeBox(
                fmt["image_width"],
                fmt["image_height"],
                0.1,
                App.Vector(dx - fmt["image_width"] / 2, -fmt["image_height"] / 2, 2),
            )
            neighbours += wrong.common(ray).Volume / 0.1
        result["negative_controls"]["wrong_35mm_mask_leaks_110_neighbours_mm2"] = (
            neighbours
        )
    for gate, z in [("collar-base", -2.1), ("collar-cap", 2.0)]:
        beam = Part.makeBox(40, 28, 0.1, App.Vector(-20, -14, z))
        transmitted = beam.cut(closed[gate])
        for selected, origin in enumerate(fmt["centers"]):
            areas = []
            for center in fmt["centers"]:
                ray = Part.makeBox(
                    fmt["image_width"],
                    fmt["image_height"],
                    0.1,
                    App.Vector(
                        center - origin - fmt["image_width"] / 2,
                        -fmt["image_height"] / 2,
                        z,
                    ),
                )
                areas.append(transmitted.common(ray).Volume / 0.1)
            result["optical_samples"].append(
                {
                    "mask": gate,
                    "frame": selected + 1,
                    "selected_area_mm2": areas[selected],
                    "neighbour_area_mm2": sum(
                        a for j, a in enumerate(areas) if j != selected
                    ),
                }
            )
    doc = App.newDocument("NegativeCarrierB")
    for name, shape in closed.items():
        obj = doc.addObject("PartDesign::Feature", name.replace("-", "_"))
        obj.Label = name
        obj.Shape = shape
        obj.addProperty("App::PropertyString", "Evidence", "Prototype")
        obj.Evidence = "Unmeasured C35 envelope; imposed motion and flexure shapes, no force solution"
    doc.recompute()
    path = out / model["format"] / "assembly.FCStd"
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str(path))
    result["freecad_document_reopened"] = len(reopened.Objects) == len(closed) and all(
        o.Shape.isValid() for o in reopened.Objects
    )
    App.closeDocument(reopened.Name)
    result["passed"] = (
        not result["failures"]
        and result["continuous_frame_travel"]["max_overlap_mm3"] < 1e-5
        and all(v > 1e-5 for v in result["negative_controls"].values())
        and all(
            abs(s["selected_area_mm2"] - aw * ah) < 1e-4
            and s["neighbour_area_mm2"] < 1e-5
            for s in result["optical_samples"]
        )
        and result["freecad_document_reopened"]
    )
    report["models"].append(result)
    print(
        "Finished",
        model["format"],
        result["passed"],
        result["negative_controls"],
        flush=True,
    )
report["passed"] = all(m["passed"] for m in report["models"])
report["unique_pair_queries"] = len(cache)
(out / "freecad-validation.json").write_text(json.dumps(report, indent=2) + "\n")
