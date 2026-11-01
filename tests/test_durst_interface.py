"""Guard measured-vs-assumed datums and nontrivial interference scenarios."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

try:
    import build123d as bd
except ModuleNotFoundError as error:
    if error.name != "build123d":
        raise
    bd = None

if bd is not None:
    from cad.durst_c35_interface.export import export, overlap
    from cad.durst_c35_interface.model import (
        box,
        clearance_scenario,
        load_measurements,
        parts,
    )


@unittest.skipIf(
    bd is None, "Native fixture tests run in the dedicated CAD environment"
)
class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_measurements()
        cls.shapes = parts(cls.data)

    def test_actual_width_is_neck_not_larger_body(self):
        section = self.shapes["head-shell"].intersect(box(0, -43, 2, 200, 200, 1))
        self.assertAlmostEqual(
            bd.Compound(children=section).bounding_box().size.X, 88.55, places=6
        )
        self.assertGreater(self.shapes["head-shell"].bounding_box().size.X, 88.55)

    def test_rest_gap_and_independent_lower_motion(self):
        moved = parts(self.data, lower_drop_mm=0.15)
        self.assertAlmostEqual(moved["lower-support"].bounding_box().max.Z, -6.15)
        for name in self.shapes:
            if name != "lower-support":
                self.assertAlmostEqual(
                    moved[name].bounding_box().min.Z,
                    self.shapes[name].bounding_box().min.Z,
                )
        with self.assertRaises(ValueError):
            parts(self.data, lower_drop_mm=-0.1)

    def test_screw_projection_is_local_not_global_gap(self):
        r = clearance_scenario(self.data)
        self.assertEqual(r["flat_gap_mm"], 6)
        self.assertEqual(r["local_gap_at_screw_envelope_mm"], 5.5)
        self.assertIsNone(r["force_N"])
        self.assertFalse(r["physical_fit_accepted"])
        screw = self.shapes["screw-head-1"]
        c = screw.center()
        probe = box(c.X, c.Y, -6, 2, 2, 6)
        self.assertGreater(overlap(screw, probe), 0.1)

    def test_wrong_height_is_detected_without_scaling_fixture(self):
        plate = self.shapes["underside-plate"]
        self.assertLess(overlap(plate, box(0, -4, -6, 8, 2, 5.9)), 1e-6)
        self.assertGreater(overlap(plate, box(0, -4, -6, 8, 2, 6.1)), 0.1)

    def test_user_values_do_not_promote_unmeasured_interiors(self):
        entries = self.data["parameters"]
        self.assertEqual(entries["neck_width"]["status"], "user_measured")
        self.assertEqual(entries["slot_gap"]["status"], "user_approximate")
        self.assertEqual(entries["neck_depth"]["status"], "user_measured")
        self.assertEqual(entries["lower_front_offset"]["status"], "derived_from_user")
        self.assertEqual(entries["lower_opening_depth"]["status"], "provisional")
        self.assertEqual(entries["flange_depth"]["status"], "provisional")
        self.assertIsNone(
            self.data["observations"]["lower_support_stiffness_N_per_mm"]["value"]
        )

    def test_zero_protrusion_omits_degenerate_screw_solids(self):
        data = copy.deepcopy(self.data)
        data["parameters"]["screw_protrusion"]["value"] = 0
        self.assertEqual(len(parts(data)), 3)

    def test_measured_sections_share_front_and_rear_planes(self):
        # Section the neck and raised support, excluding the wider body/flange.
        for name, z in [("head-shell", 2), ("lower-support", -8)]:
            section = self.shapes[name].intersect(box(0, -49, z, 200, 200, 1))
            bounds = bd.Compound(children=section).bounding_box()
            self.assertAlmostEqual(bounds.min.Y, -98.3)
            self.assertAlmostEqual(bounds.max.Y, 0)
        flange = self.shapes["lower-support"].bounding_box()
        self.assertAlmostEqual(flange.max.Y, 4.5)
        self.assertAlmostEqual(flange.min.Z, -6 - 10.5 - 2.5)

    def test_new_caliper_readings_rebuild_without_old_gap_constants(self):
        with tempfile.TemporaryDirectory() as folder:
            data = copy.deepcopy(self.data)
            for key, value in [
                ("neck_width", 89.0),
                ("slot_gap", 6.2),
                ("neck_height", 14.0),
            ]:
                data["parameters"][key].update(
                    value=value,
                    status="user_measured",
                    source="Test measurement override",
                )
            path = Path(folder) / "readings.json"
            path.write_text(json.dumps(data))
            report = export(Path(folder) / "export", path)
            self.assertTrue(report["geometry_passed"])
            self.assertFalse(report["physical_fit_accepted"])
            self.assertEqual(report["states"]["rest"]["flat_gap_mm"], 6.2)
            self.assertAlmostEqual(
                report["negative_controls"]["flat_plate_probe_overlap_mm3"]["above"][
                    "thickness_mm"
                ],
                6.3,
            )

    def test_bad_measurement_fails_before_export(self):
        for key, value in [
            ("slot_gap", -1),
            ("lower_opening_width", 100),
            ("neck_width", float("nan")),
            ("screw_head_diameter", 50),
            ("lower_front_offset", 1),
        ]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                data = copy.deepcopy(self.data)
                data["parameters"][key]["value"] = value
                path = Path(folder) / "measurements.json"
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    load_measurements(path)


if __name__ == "__main__":
    unittest.main()
