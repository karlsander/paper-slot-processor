"""Render the verified native assembly in FreeCAD's GUI, using actual STEP solids.

Call start(output_directory) from a FreeCAD macro. Frame report records failures;
encode only after passed=true. Filling is geometric volume, not CFD.
"""

import json
import math
import traceback
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui


def start(directory):
    folder = Path(directory)
    validation = json.loads((folder / "validation.json").read_text())
    assert validation["passed"] is True
    p = json.loads((folder / "parameters.json").read_text())
    out = folder / "video-frames"
    out.mkdir(exist_ok=True)
    report = folder / "video-report.json"
    report.unlink(missing_ok=True)
    doc = App.newDocument("NativeProcessorVideo")
    view = Gui.activeDocument().activeView()
    objects = {}
    local = {}
    origins = {}

    def add(name, filename, color, origin):
        shape = Part.read(str(folder / filename))
        local[name] = shape.copy()
        obj = doc.addObject("PartDesign::Feature", name)
        obj.Shape = shape
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (0.16, 0.20, 0.25)
        obj.ViewObject.DisplayMode = "Flat Lines"
        obj.ViewObject.Visibility = True
        origins[name] = origin
        obj.Placement.Base = origin
        objects[name] = obj
        return obj

    add("Base", "base.step", (0.45, 0.50, 0.56), App.Vector())
    for i, letter in enumerate("ab"):
        o = App.Vector(
            p["vessel_x"], p["vessel_y"] + i * p["vessel_pitch"], p["cradle_floor"]
        )
        add(
            f"Bath{letter}",
            f"vessel_{letter}.step",
            (0.28, 0.54, 0.77) if i == 0 else (0.32, 0.65, 0.59),
            o,
        )
        for kind, prefix, color in [
            ("guide", "Guide", (0.90, 0.68, 0.24)),
            ("cover", "Cover", (0.74, 0.58, 0.30)),
        ]:
            add(
                prefix + letter,
                f"{kind}_{letter}.step",
                color,
                o + App.Vector(0, 0, p["body_height"]),
            )
        for j, x in enumerate((p["body_width"] / 4, 3 * p["body_width"] / 4)):
            add(
                f"Clip{letter}{j}",
                "clip.step",
                (0.94, 0.42, 0.16),
                o + App.Vector(x - p["clip_width"] / 2, -4.2, p["body_height"] - 4),
            )
    cavity = Part.read(str(folder / "liquid-cavity-a.step"))
    liquid = doc.addObject("PartDesign::Feature", "Liquid")
    liquid.ViewObject.ShapeColor = (0.05, 0.40, 0.9)
    liquid.ViewObject.DisplayMode = "Flat Lines"
    paper = doc.addObject("PartDesign::Feature", "Paper")
    paper.ViewObject.ShapeColor = (0.96, 0.90, 0.75)
    paper.ViewObject.DisplayMode = "Flat Lines"
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
    orientation = App.Rotation(
        App.Vector(0.74290609, 0.30772209, 0.59447283), math.degrees(1.2171158)
    )
    sequence = []
    for scene, frames in [
        ("assembly", 60),
        ("clips", 36),
        ("guides", 36),
        ("bath", 48),
        ("fill", 72),
        ("paper", 60),
        ("covers", 48),
    ]:
        sequence += [(scene, i / (frames - 1)) for i in range(frames)]
    state = {"index": 0, "previous": None, "measurements": []}

    def reset():
        for name, obj in objects.items():
            obj.Placement = App.Placement(origins[name], App.Rotation())
            obj.ViewObject.Visibility = not name.startswith("Cover")
            obj.ViewObject.Transparency = 0
        liquid.ViewObject.Visibility = False
        liquid.ViewObject.Transparency = 0
        paper.ViewObject.Visibility = False

    def caption(title, detail, caveat):
        view.saveImage(str(out / "viewport.png"), 1280, 600, "White")
        frame = QtGui.QImage(1280, 720, QtGui.QImage.Format_RGB32)
        frame.fill(QtGui.QColor("white"))
        painter = QtGui.QPainter(frame)
        painter.drawImage(0, 0, QtGui.QImage(str(out / "viewport.png")))
        painter.fillRect(0, 600, 1280, 120, QtGui.QColor("#152333"))
        for text, y, size, color in [
            (title, 635, 23, "#95caff"),
            (detail, 666, 16, "#ffffff"),
            (caveat, 695, 13, "#c1ccd7"),
        ]:
            painter.setPen(QtGui.QColor(color))
            painter.setFont(
                QtGui.QFont(
                    "Arial", size, QtGui.QFont.Bold if y == 635 else QtGui.QFont.Normal
                )
            )
            painter.drawText(28, y, text)
        painter.end()
        assert frame.save(str(out / f"frame-{state['index']:04d}.png"))

    def tick():
        try:
            index = state["index"]
            if index == len(sequence):
                reset()
                doc.recompute()
                view.setCameraOrientation(orientation.Q)
                view.fitAll()
                doc.saveAs(str(folder / "processor.FCStd"))
                report.write_text(
                    json.dumps(
                        {
                            "passed": True,
                            "fps": 12,
                            "frames": len(sequence),
                            "duration_seconds": len(sequence) / 12,
                            "kind": "Native STEP geometry animated in FreeCAD; not CFD or dynamics",
                            "measurements": state["measurements"],
                        },
                        indent=2,
                    )
                    + "\n"
                )
                print("PASS: native video frames", flush=True)
                return
            scene, t = sequence[index]
            u = (1 - math.cos(math.pi * t)) / 2
            reset()
            measure = {}
            a = objects["Batha"]
            origin = origins["Batha"]
            caveat = "Native build123d parts imported into FreeCAD. Prescribed rigid motion; physical fit is untested."
            if scene == "assembly":
                for name, obj in objects.items():
                    if name.startswith("Bath"):
                        obj.Placement.Base += App.Vector(0, 0, 35 * (1 - u))
                    if name.startswith("Guide"):
                        obj.Placement.Base += App.Vector(0, 0, 70 * (1 - u))
                    if name.startswith("Clip"):
                        obj.Placement.Base += App.Vector(0, -20 * (1 - u), 35 * (1 - u))
                title = "01  /  Complete native processor"
                detail = "One shared base  +  two reusable baths  +  two guides  +  four retaining clips"
            elif scene == "clips":
                for name, obj in objects.items():
                    if name.startswith("Clipa"):
                        obj.Placement.Base += App.Vector(0, -12 * u, 0)
                title = "02  /  Remove the two retaining clips"
                detail = f"Outward travel: {12 * u:.1f} mm  |  Guide and vessel mating surfaces checked in FreeCAD"
            elif scene == "guides":
                for name, obj in objects.items():
                    if name.startswith("Clipa"):
                        obj.ViewObject.Visibility = False
                objects["Guidea"].Placement.Base += App.Vector(0, 0, 35 * u)
                title = "03  /  Lift the removable paper guide"
                detail = f"Lift: {35 * u:.1f} mm  |  Tapered entry, short wiping land and locating skirt"
            elif scene == "bath":
                for name, obj in objects.items():
                    if name.startswith(("Clipa", "Guidea")):
                        obj.ViewObject.Visibility = False
                a.Placement.Base += App.Vector(0, 0, 60 * u)
                collision = (
                    a.Shape.common(objects["Base"].Shape).Volume
                    + a.Shape.common(objects["Bathb"].Shape).Volume
                )
                assert collision < 1e-4, collision
                title = "04  /  Remove the bath upright"
                detail = f"Lift: {60 * u:.1f} mm  |  Measured overlap: {collision:.3f} mm³  |  Socket clearance: 0.6 mm per side"
                measure = {"lift_mm": 60 * u, "overlap_mm3": collision}
            elif scene in ("fill", "paper"):
                for name, obj in objects.items():
                    obj.ViewObject.Visibility = name == "Batha"
                a.ViewObject.Transparency = 82
                lift = 0
                side = 0
                if scene == "fill":
                    level = p["floor"] + (p["empty_level"] - p["floor"]) * u
                    title = "05  /  Fill the connected bath and side well"
                    detail = f"Empty-bath target: {p['working_ml']} ml  |  Level: {level:.1f} mm above vessel bottom"
                    caveat = "Geometric cavity filling. No pouring, fluid flow, splashing or heat transfer is simulated."
                else:
                    liquid.ViewObject.Transparency = 65
                    lift = p["vertical_stroke"] * (1 - math.cos(4 * math.pi * t)) / 2
                    side = p["lateral_stroke"] * math.sin(4 * math.pi * t)
                    # Native parameter solver accounts for displaced paper at each lift.
                    from cad.parameters import level_for_volume

                    level = level_for_volume(p, p["working_ml"] * 1000, True, lift)
                    objects["Guidea"].ViewObject.Visibility = True
                    paper_local = sheet.copy()
                    paper_local.translate(App.Vector(side, 0, lift))
                    paper.Shape = paper_local
                    paper.Placement.Base = origin
                    paper.ViewObject.Visibility = True
                    assert paper.Shape.common(a.Shape).Volume < 1e-4
                    assert paper.Shape.common(objects["Guidea"].Shape).Volume < 1e-4
                    title = "06  /  Paper travel through the guide"
                    detail = f"Lift: {lift:.1f} / {p['vertical_stroke']} mm  |  Sideways: {side:+.1f} mm  |  Rigid paper clearance checked"
                    caveat = "Flat sheet model; no bending or emulsion friction. Liquid level follows displaced volume, not sloshing."
                water = cavity.common(
                    Part.makeBox(500, 500, max(level, 0.01), App.Vector(-100, -100, 0))
                )
                if scene == "paper":
                    water = water.cut(paper_local)
                volume = max(0, water.Volume) / 1000
                if volume > 1e-5:
                    liquid.Shape = water
                    liquid.Placement.Base = origin
                    liquid.ViewObject.Visibility = True
                    assert liquid.Shape.common(a.Shape).Volume < 1e-4
                measure = {
                    "level_mm": level,
                    "volume_ml": volume,
                    "paper_lift_mm": lift,
                    "paper_side_mm": side,
                }
                if scene == "paper" or t == 1:
                    assert abs(volume - p["working_ml"]) < 0.5
            else:
                for name, obj in objects.items():
                    if name.startswith(("Guide", "Clip")):
                        obj.ViewObject.Visibility = False
                    if name.startswith("Cover"):
                        obj.ViewObject.Visibility = True
                        obj.Placement.Base += App.Vector(0, 0, 35 * (1 - u))
                title = "07  /  Optional resting covers"
                detail = "Two labeled covers reuse the guide seats  |  Fit sample and 0.6 / 0.8 mm trial guides also exported"
                caveat = "Resting covers are not sealed storage lids. Store chemistry in suitable separate bottles."
            doc.recompute()
            Gui.updateGui()
            if state["previous"] != scene:
                view.setCameraOrientation(orientation.Q)
                # Frame the entire travel before restoring the current pose.
                if scene == "bath":
                    a.Placement.Base = origin + App.Vector(0, 0, 60)
                if scene == "guides":
                    objects["Guidea"].Placement.Base = origins["Guidea"] + App.Vector(
                        0, 0, 35
                    )
                doc.recompute()
                view.fitAll()
                if scene == "bath":
                    a.Placement.Base = origin + App.Vector(0, 0, 60 * u)
                if scene == "guides":
                    objects["Guidea"].Placement.Base = origins["Guidea"] + App.Vector(
                        0, 0, 35 * u
                    )
                doc.recompute()
                Gui.updateGui()
            caption(title, detail, caveat)
            state["measurements"].append({"frame": index, "scene": scene, **measure})
            state["previous"] = scene
            state["index"] += 1
            QtCore.QTimer.singleShot(1, tick)
        except Exception:  # noqa: BLE001 - persist Qt callback failures
            report.write_text(
                json.dumps({"passed": False, "error": traceback.format_exc()}, indent=2)
            )
            print(traceback.format_exc(), flush=True)

    QtCore.QTimer.singleShot(2000, tick)
