"""FreeCAD: continuous machine-clearance sweeps against the measured reference.

Planar faces generate exact translation prisms. Curved faces use conservative
swept bounding boxes; clearance therefore does not depend on path sampling.
"""

import hashlib
import json
import os
from pathlib import Path

import FreeCAD as App
import Part

out = Path(os.environ["CARRIER_INTERFACE_OUTPUT"])
manifest = out / "interface-manifest.json"
data = json.loads(manifest.read_text())
TOL = 1e-5


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(record):
    path = out / record["file"]
    assert sha(path) == record["sha256"]
    s = Part.read(str(path))
    assert s.isValid() and len(s.Solids) == 1, path
    assert abs(s.Volume / record["volume_mm3"] - 1) < 1e-4, path
    return s


def moved(shape, vector):
    s = shape.copy()
    s.translate(vector)
    return s


def overlap(a, b):
    if not a.BoundBox.intersect(b.BoundBox):
        return 0.0
    return abs(a.common(b).Volume)


def sweep(shape, vector, obstacles):
    """Return worst intersection for a closed solid's full linear translation."""
    endpoint = moved(shape, vector)
    maximum = max(
        (overlap(s, o) for s in (shape, endpoint) for o in obstacles), default=0
    )
    exact = conservative = 0
    for face in shape.Faces:
        plane = face.findPlane(1e-7)
        if plane is not None:
            if abs(plane.Axis.dot(vector)) < 1e-7:
                continue
            prism = face.extrude(vector)
            if prism.Volume < 0:
                prism.reverse()
            assert prism.isValid() and prism.Solids
            exact += 1
        else:
            b = face.BoundBox
            lo = App.Vector(
                min(b.XMin, b.XMin + vector.x),
                min(b.YMin, b.YMin + vector.y),
                min(b.ZMin, b.ZMin + vector.z),
            )
            sizes = (
                b.XLength + abs(vector.x),
                b.YLength + abs(vector.y),
                b.ZLength + abs(vector.z),
            )
            if min(sizes) < 1e-7:
                continue
            prism = Part.makeBox(*sizes, lo)
            conservative += 1
        maximum = max(maximum, max((overlap(prism, o) for o in obstacles), default=0))
    return maximum, exact, conservative


fixture = {n: read(r) for n, r in data["fixture"].items()}
fixed = [s for n, s in fixture.items() if n != "lower-support"]
drop = data["release_drop_mm"]
released = fixed + [moved(fixture["lower-support"], App.Vector(0, 0, -drop))]
reports = []
for model in data["models"]:
    shapes = {n: read(r) for n, r in model["parts"].items()}
    seated = max(overlap(s, f) for s in shapes.values() for f in fixture.values())
    assert seated < TOL, (model["name"], "seated", seated)
    # A nonzero contact area establishes the modeled support relationship only.
    contact_distance = shapes["receiver"].distToShape(fixture["lower-support"])[0]
    support_probe = overlap(
        moved(shapes["receiver"], App.Vector(0, 0, -0.01)), fixture["lower-support"]
    )
    assert contact_distance < 1e-6 and support_probe > 0.05, (
        model["name"],
        "missing modeled support",
        contact_distance,
        support_probe,
    )
    maxima = {
        "frame_travel": 0.0,
        "insertion_and_withdrawal": 0.0,
        "release_and_seating": 0.0,
    }
    exact = conservative = 0
    for n, s in shapes.items():
        paths = [
            (
                "insertion_and_withdrawal",
                moved(s, App.Vector(0, 0, -drop)),
                App.Vector(0, model["withdrawal_mm"], 0),
                released,
            )
        ]
        if drop:
            paths += [
                (
                    "release_and_seating",
                    moved(s, App.Vector(0, 0, -drop)),
                    App.Vector(0, 0, drop),
                    fixed,
                )
            ]
        if n in model["moving"]:
            paths += [
                (
                    "frame_travel",
                    s,
                    App.Vector(-model["frame_travel_mm"], 0, 0),
                    list(fixture.values()),
                )
            ]
        for kind, shape, vector, obstacles in paths:
            v, a, b = sweep(shape, vector, obstacles)
            exact += a
            conservative += b
            maxima[kind] = max(maxima[kind], v)
    assert max(maxima.values()) < TOL, (model["name"], maxima)
    # Default-unreleased insertion must expose the front screw interference.
    blocked = sweep(shapes["sleeve"], App.Vector(0, model["withdrawal_mm"], 0), fixed)[
        0
    ]
    assert blocked > 0.01, (model["name"], "unreleased insertion control", blocked)
    old = overlap(
        moved(shapes["sleeve"], App.Vector(0, 0, 1.2)), fixture["underside-plate"]
    )
    assert old > 1, (model["name"], "legacy height control", old)
    too_low = overlap(
        moved(shapes["receiver"], App.Vector(0, 0, -0.2)), fixture["lower-support"]
    )
    assert too_low > 1, (model["name"], "support penetration control", too_low)
    x, y, z = model["translation_mm"]
    w, h = model["aperture_mm"]
    beam = Part.makeBox(
        w - 0.1, h - 0.1, 100, App.Vector(x - w / 2 + 0.05, y - h / 2 + 0.05, -50)
    )
    beam_overlap = sum(overlap(beam, s) for s in fixture.values())
    beam_overlap += sum(overlap(beam, s) for n, s in shapes.items() if n != "film")
    assert beam_overlap < TOL, (model["name"], "straight optical passage", beam_overlap)
    # Prove containment in a cylinder, then sweep that cylinder through the
    # entire axial lift. This bounds every screw angle, not sampled rotations.
    screw = shapes["screw"]
    radius = model["screw_rotation_radius_mm"]
    bounds = screw.BoundBox
    rotation_envelope = Part.makeCylinder(
        radius, bounds.ZLength, App.Vector(x, y + 57, bounds.ZMin)
    )
    assert abs(screw.cut(rotation_envelope).Volume) < TOL
    lifted_envelope = Part.makeCylinder(
        radius,
        bounds.ZLength + model["screw_lift_mm"],
        App.Vector(x, y + 57, bounds.ZMin),
    )
    rotation_overlap = sum(overlap(lifted_envelope, s) for s in fixture.values())
    assert rotation_overlap < TOL, (
        model["name"],
        "full screw rotation/lift",
        rotation_overlap,
    )
    # One of the old grip wings rotated 90 degrees crosses the housing front.
    old_wing = Part.makeBox(4, 9, 4.2, App.Vector(-12, 52.5, 29.2))
    old_wing.rotate(App.Vector(0, 57, 0), App.Vector(0, 0, 1), 90)
    old_wing.translate(App.Vector(x, y, z))
    wing_collision = overlap(old_wing, fixture["head-shell"])
    assert wing_collision > 1, (model["name"], "old grip control", wing_collision)
    doc = App.newDocument("B2_Measured_Interface")
    for group in (fixture, shapes):
        for n, s in group.items():
            obj = doc.addObject("Part::Feature", n.replace("-", "_"))
            obj.Label = n
            obj.Shape = s
    doc.recompute()
    path = out / model["name"] / "measured-assembly.FCStd"
    doc.saveAs(str(path))
    App.closeDocument(doc.Name)
    doc = App.openDocument(str(path))
    assert len(doc.Objects) == len(fixture) + len(shapes) and all(
        o.Shape.isValid() for o in doc.Objects
    )
    App.closeDocument(doc.Name)
    reports.append(
        {
            "name": model["name"],
            "translation_mm": model["translation_mm"],
            "passed": True,
            "seated_overlap_mm3": seated,
            "receiver_support_distance_mm": contact_distance,
            "support_penetration_0_01_mm_control_mm3": support_probe,
            "continuous_path_max_overlap_mm3": maxima,
            "exact_face_prisms": exact,
            "conservative_curved_face_boxes": conservative,
            "straight_optical_overlap_mm3": beam_overlap,
            "full_screw_rotation_and_lift_overlap_mm3": rotation_overlap,
            "negative_controls_mm3": {
                "unreleased_insertion": blocked,
                "legacy_height": old,
                "below_support": too_low,
                "old_rotated_knob_wing": wing_collision,
            },
            "native_document_sha256": sha(path),
        }
    )
    print("PASS measured-interface paths", model["name"], flush=True)
(out / "interface-validation.json").write_text(
    json.dumps(
        {
            "passed": True,
            "manifest_sha256": sha(manifest),
            "freecad_version": App.Version(),
            "physical_fit_accepted": False,
            "registration_measured": False,
            "models": reports,
        },
        indent=2,
    )
    + "\n"
)
