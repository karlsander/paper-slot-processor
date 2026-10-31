"""Regression coverage for the reported slab and stale FreeCAD evidence failures."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cad.durst_c35.parameters import parameters
from scripts.check_durst_geometry import verify


class ParameterTests(unittest.TestCase):
    def test_sheet_and_rim_are_independent(self):
        p = parameters(sheet_thickness=1.0)
        self.assertEqual(p["window_rim_height"], 2.5)
        self.assertAlmostEqual(p["b_pin_boss_height"] - p["b_pin_recess_depth"], 0.6)
        self.assertEqual(p["window_x"], 36)
        self.assertEqual(p["film_pin_spacing"], 58)

    def test_bad_interfaces_rejected(self):
        for changes in [
            {"sheet_thickness": 2.5},
            {"sheet_thickness": 0},
            {"sheet_thickness": float("nan")},
            {"side_wall": True},
            {"plate_thickness": 2.5},
            {"hinge_hole_diameter": 2},
            {"film_pin_height": 2},
            {"b_pin_recess_bottom": 1},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parameters(**changes)


class FreshReportTests(unittest.TestCase):
    def test_zero_exit_must_write_new_success(self):
        for report in [None, {"passed": False}, {"passed": True}]:
            with self.subTest(report=report), tempfile.TemporaryDirectory() as folder:
                out = Path(folder)
                (out / "model-report.json").write_text(
                    json.dumps({"passed": True, "files_sha256": {}})
                )
                (out / "validation.json").write_text('{"passed":true}')

                def run(*args, out=out, report=report, **kwargs):
                    self.assertFalse((out / "validation.json").exists())
                    if report is not None:
                        (out / "validation.json").write_text(json.dumps(report))
                    return subprocess.CompletedProcess([], 0, "", "")

                with patch(
                    "scripts.check_durst_geometry.subprocess.run", side_effect=run
                ):
                    if report and report["passed"]:
                        self.assertTrue(verify(out, "fake")["passed"])
                    else:
                        with self.assertRaises(RuntimeError):
                            verify(out, "fake")

    def test_changed_export_cannot_reuse_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / "a.step").write_text("changed")
            (out / "validation.json").write_text('{"passed":true}')
            (out / "model-report.json").write_text(
                json.dumps({"passed": True, "files_sha256": {"a.step": "old"}})
            )
            with self.assertRaisesRegex(RuntimeError, "Export changed"):
                verify(out, "fake")
            self.assertFalse((out / "validation.json").exists())


@unittest.skipUnless(
    importlib.util.find_spec("build123d"), "native CAD environment required"
)
class GeometryRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from cad.durst_c35 import parts

        cls.p = parameters()
        cls.shapes = {"a": parts.lower(cls.p), "b": parts.upper(cls.p)}

    def test_thin_panels_pass_but_solid_slab_fails(self):
        import build123d as bd

        from cad.durst_c35 import parts
        from cad.durst_c35.export import check_shell

        for half, shape in self.shapes.items():
            with self.subTest(half=half):
                self.assertEqual(len(check_shell(shape, self.p, half)), 8)
                # Recreate the failure while keeping one valid solid: fill a
                # broad panel region to the rim height, then to the side height.
                for height in [2.5, 13.5]:
                    slab = parts.box(-40, 75, 0, 80, 15, height)
                    if half == "a":
                        slab = bd.mirror(slab, about=bd.Plane.XY)
                    broken = shape + slab
                    self.assertTrue(broken.is_valid)
                    self.assertEqual(len(broken.solids()), 1)
                    with self.assertRaisesRegex(ValueError, "expected thin sheet"):
                        check_shell(broken, self.p, half)


if __name__ == "__main__":
    unittest.main()
