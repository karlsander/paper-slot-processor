"""Render actual FreeCAD fit geometry and a geometric filling sequence.

Run in FreeCAD's GUI Python console, then call start('/absolute/study/directory').
Frames go into video-frames/. Encode with ffmpeg at 15 fps; see the study guide.
The filling sequence is a series of horizontal cavity intersections, not CFD.
"""

import json
import math
import traceback
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtGui


def start(study_dir):
    folder = Path(study_dir)
    output = folder / "video-frames"
    output.mkdir(exist_ok=True)
    completion = folder / "video-report.json"
    completion.unlink(missing_ok=True)
    p = json.loads((folder / "parameters.json").read_text())
    doc = App.newDocument("ProcessorVideo")
    view = Gui.activeDocument().activeView()
    objects = {}
    for name, filename, color in [
        ("Base", "base.step", (0.46, 0.51, 0.57)),
        ("BathA", "vessel_a.step", (0.30, 0.55, 0.78)),
        ("BathB", "vessel_b.step", (0.35, 0.66, 0.63)),
    ]:
        obj = doc.addObject("PartDesign::Feature", name)
        obj.Shape = Part.read(str(folder / filename))
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (0.14, 0.20, 0.27)
        obj.ViewObject.DisplayMode = "Flat Lines"
        objects[name] = obj
    a, b, base = objects["BathA"], objects["BathB"], objects["Base"]
    origin = App.Vector(p["vessel_x"], p["vessel_y"], p["cradle_floor"])
    a.Placement.Base = origin
    b.Placement.Base = origin + App.Vector(0, p["vessel_pitch"], 0)
    vessel_local = a.Shape.copy()
    vessel_local.Placement = App.Placement()
    cavity = Part.read(str(folder / "liquid-cavity.step"))
    liquid = doc.addObject("PartDesign::Feature", "Liquid")
    liquid.ViewObject.ShapeColor = (0.05, 0.40, 0.85)
    liquid.ViewObject.LineColor = (0.02, 0.22, 0.55)
    liquid.ViewObject.DisplayMode = "Flat Lines"
    liquid.Placement.Base = origin
    liquid.ViewObject.Visibility = False
    # Frame the whole removal path once, so the camera does not follow the bath.
    a.Placement.Base = origin + App.Vector(0, 0, 60)
    doc.recompute()
    view.viewIsometric()
    view.fitAll()
    a.Placement.Base = origin
    doc.recompute()
    sequence = []
    sequence += [("lift", 0)] * 15
    sequence += [("lift", 60 * (1 - math.cos(math.pi * i / 59)) / 2) for i in range(60)]
    sequence += [("lift", 60)] * 15
    sequence += [("lift", 60 * (1 + math.cos(math.pi * i / 44)) / 2) for i in range(45)]
    sequence += [("tilt", 2 * i / 59) for i in range(60)]
    sequence += [("tilt", 2)] * 20
    sequence += [("fill", i / 119) for i in range(120)]
    sequence += [("fill", 1)] * 30
    state = {"index": 0, "previous_scene": None, "measurements": []}
    # Set a fixed camera directly: startup view animations can overwrite viewIsometric().
    orientation = App.Rotation(
        App.Vector(0.74290609, 0.30772209, 0.59447283), math.degrees(1.2171158)
    )

    def capture(title, detail, caveat, status_color):
        raw = output / "viewport.png"
        view.saveImage(str(raw), 1280, 600, "White")
        frame = QtGui.QImage(1280, 720, QtGui.QImage.Format_RGB32)
        frame.fill(QtGui.QColor("white"))
        painter = QtGui.QPainter(frame)
        painter.drawImage(0, 0, QtGui.QImage(str(raw)))
        painter.fillRect(0, 600, 1280, 120, QtGui.QColor("#152333"))
        painter.setPen(QtGui.QColor(status_color))
        painter.setFont(QtGui.QFont("Arial", 23, QtGui.QFont.Bold))
        painter.drawText(32, 635, title)
        painter.setPen(QtGui.QColor("#ffffff"))
        painter.setFont(QtGui.QFont("Arial", 16))
        painter.drawText(32, 666, detail)
        painter.setPen(QtGui.QColor("#c1ccd7"))
        painter.setFont(QtGui.QFont("Arial", 13))
        painter.drawText(32, 695, caveat)
        painter.end()
        assert frame.save(str(output / f"frame-{state['index']:04d}.png"))

    def tick():
        try:
            index = state["index"]
            if index == len(sequence):
                completion.write_text(
                    json.dumps(
                        {
                            "passed": True,
                            "fps": 15,
                            "frames": len(sequence),
                            "duration_seconds": len(sequence) / 15,
                            "kind": "FreeCAD geometry animation; not fluid dynamics",
                            "measurements": state["measurements"],
                        },
                        indent=2,
                    )
                    + "\n"
                )
                print(f"Video frames complete: {output}")
                return
            if index == 0:
                view.setCameraOrientation(orientation.Q)
                a.Placement.Base = origin + App.Vector(0, 0, 60)
                doc.recompute()
                view.fitAll()
            scene, value = sequence[index]
            a.Placement = App.Placement(origin, App.Rotation())
            if scene == "lift":
                a.Placement.Base = origin + App.Vector(0, 0, value)
                overlap = (
                    a.Shape.common(base.Shape).Volume + a.Shape.common(b.Shape).Volume
                )
                assert overlap < 1e-5, overlap
                title = "01  /  Upright removal"
                detail = f"Lift: {value:.1f} mm    |    Base + adjacent bath overlap: {overlap:.3f} mm³"
                caveat = "Prescribed motion; rigid CAD geometry. Printed friction and deformation are not modeled."
                color = "#89e4b3"
                measure = {"lift_mm": value, "overlap_mm3": overlap}
            elif scene == "tilt":
                pivot = origin + App.Vector(p["body_width"] / 2, 0, 0)
                rotation = App.Rotation(App.Vector(1, 0, 0), value)
                a.Placement = App.Placement(
                    pivot - rotation.multVec(pivot), rotation
                ).multiply(App.Placement(origin, App.Rotation()))
                overlap = a.Shape.common(base.Shape).Volume
                hit = overlap > 1e-5
                a.ViewObject.ShapeColor = (
                    (0.85, 0.23, 0.20) if hit else (0.30, 0.55, 0.78)
                )
                title = "02  /  Rocking in the socket"
                detail = f"Tilt: {value:.2f}°    |    {'INTERFERENCE' if hit else 'CLEAR'}    |    Overlap: {overlap:.1f} mm³"
                caveat = "Rotation about the front bottom edge. Red marks geometric intersection, not simulated stress."
                color = "#ff9d94" if hit else "#89e4b3"
                measure = {"angle_degrees": value, "overlap_mm3": overlap}
            else:
                if state["previous_scene"] != "fill":
                    base.ViewObject.Visibility = False
                    b.ViewObject.Visibility = False
                    a.ViewObject.ShapeColor = (0.68, 0.75, 0.82)
                    a.ViewObject.Transparency = 82
                    view.setCameraOrientation(orientation.Q)
                    view.fitAll()
                level = p["floor"] + (p["empty_level"] - p["floor"]) * value
                water = cavity.common(
                    Part.makeBox(500, 500, max(level, 0.01), App.Vector(-100, -100, 0))
                )
                volume = max(0, water.Volume) / 1000
                if value > 0:
                    assert water.isValid() and volume > 0
                    assert water.common(vessel_local).Volume < 1e-4
                    liquid.Shape = water
                    # Assigning Shape also replaces the feature placement in FreeCAD.
                    liquid.Placement.Base = origin
                    assert liquid.Shape.common(a.Shape).Volume < 1e-4
                    liquid.ViewObject.Visibility = True
                else:
                    liquid.ViewObject.Visibility = False
                title = "03  /  Filling the empty bath"
                detail = f"Liquid: {volume:.1f} ml    |    Level above vessel bottom: {level:.1f} mm    |    Recipe: {p['working_ml']} ml"
                caveat = "Geometric fill, no paper. Level animation is illustrative; no pouring, flow, splashing or cooling solved."
                color = "#95caff"
                measure = {"level_mm": level, "volume_ml": volume}
                if value == 1:
                    assert abs(volume - p["working_ml"]) < 1, (volume, p["working_ml"])
            doc.recompute()
            Gui.updateGui()
            capture(title, detail, caveat, color)
            state["measurements"].append({"frame": index, "scene": scene, **measure})
            state["previous_scene"] = scene
            state["index"] += 1
            QtCore.QTimer.singleShot(1, tick)
        except Exception:  # noqa: BLE001 - persist errors raised inside the Qt callback
            completion.write_text(
                json.dumps({"passed": False, "error": traceback.format_exc()}, indent=2)
            )
            print(traceback.format_exc())

    QtCore.QTimer.singleShot(100, tick)
