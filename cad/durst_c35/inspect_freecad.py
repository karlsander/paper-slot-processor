"""FreeCAD GUI inspection: exec this file, then start('/absolute/export/folder').

A slider drives B about the same explicit axis as the headless motion checks.
This is rigid collision inspection, with no enlarger-slot model yet.
"""

import json
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore, QtWidgets


def start(folder):
    global _durst_dialog
    out = Path(folder)
    p = json.loads((out / "parameters.json").read_text())
    doc = App.openDocument(str(out / "carrier.FCStd"))
    a, b = doc.getObject("A"), doc.getObject("B")
    original = Part.read(str(out / "b.step"))
    a.ViewObject.ShapeColor = (0.28, 0.34, 0.39)
    b.ViewObject.ShapeColor = (0.72, 0.77, 0.80)
    dialog = QtWidgets.QDialog(Gui.getMainWindow())
    dialog.setWindowTitle("Durst C35 — rigid hinge study")
    layout = QtWidgets.QVBoxLayout(dialog)
    label = QtWidgets.QLabel()
    layout.addWidget(label)
    slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    slider.setRange(0, 180)
    layout.addWidget(slider)
    layout.addWidget(
        QtWidgets.QLabel(
            f"{p['sheet_thickness']:g} mm provisional sheet. Enlarger slot not yet modeled."
        )
    )

    def update(angle):
        s = original.copy()
        s.translate(App.Vector(0, 0, p["film_gap"]))
        s.rotate(App.Vector(0, p["hinge_y"], p["hinge_z"]), App.Vector(1, 0, 0), angle)
        b.Shape = s
        volume = max(0, a.Shape.common(s).Volume)
        b.ViewObject.ShapeColor = (
            (0.9, 0.15, 0.1) if volume > 1e-4 else (0.72, 0.77, 0.80)
        )
        label.setText(f"Opening: {angle}°    Intersection: {volume:.6f} mm³")
        doc.recompute()
        Gui.activeDocument().activeView().fitAll()

    slider.valueChanged.connect(update)
    Gui.activeDocument().activeView().viewAxonometric()
    slider.setValue(110)
    dialog.resize(430, 120)
    dialog.show()
    _durst_dialog = dialog
    return dialog
