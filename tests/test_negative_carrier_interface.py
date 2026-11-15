"""Containment and measured-machine registration regression controls."""

import unittest

try:
    import build123d as bd
except ModuleNotFoundError as error:
    if error.name == "build123d":
        raise unittest.SkipTest(
            "Interface tests run with cad/requirements.txt"
        ) from error
    raise

from cad.durst_c35_interface.export import overlap
from cad.durst_c35_interface.model import load_measurements
from cad.durst_c35_interface.model import parts as fixture_parts
from cad.negative_carrier_b2.interface import registration
from cad.negative_carrier_b2.model import DEFAULT, box, parts
from cad.negative_carrier_b2.workflow import phases, place


class MeasuredInterfaceTests(unittest.TestCase):
    def test_contained_and_identical_bounds_are_not_skipped(self):
        outer = box(0, 0, 0, 10, 10, 10)
        inner = box(0, 0, 2, 2, 2, 2)
        self.assertAlmostEqual(overlap(outer, inner), 8)
        self.assertAlmostEqual(overlap(inner, outer), 8)
        self.assertAlmostEqual(overlap(inner, inner), 8)
        self.assertAlmostEqual(overlap(outer, bd.Pos(20, 0, 0) * inner), 0)

    def test_measured_seating_replaces_legacy_height(self):
        data = load_measurements()
        shapes = parts(DEFAULT)
        fixture = fixture_parts(data)
        offset = registration(data, shapes)
        for actual, expected in zip(offset, (0, -42, -2.6)):
            self.assertAlmostEqual(actual, expected)
        sleeve = bd.Pos(*offset) * shapes["sleeve"]
        self.assertLess(sum(overlap(sleeve, f) for f in fixture.values()), 1e-5)
        self.assertGreater(
            overlap(bd.Pos(0, 0, 1.2) * sleeve, fixture["underside-plate"]), 100
        )

    def test_small_screw_blocks_unreleased_insertion(self):
        data = load_measurements()
        shapes = parts(DEFAULT)
        offset = registration(data, shapes)
        sleeve = bd.Pos(offset[0], offset[1] + 10, offset[2]) * shapes["sleeve"]
        screw = fixture_parts(data)["screw-head-5"]
        self.assertGreater(overlap(sleeve, screw), 1)
        self.assertLess(overlap(bd.Pos(0, 0, -0.4) * sleeve, screw), 1e-5)

    def test_withdrawn_wedges_clear_front_spine(self):
        shapes = parts(DEFAULT)
        pose = phases(DEFAULT)[0]["start"]
        for name, shape in shapes.items():
            if name.startswith("wedge-"):
                with self.subTest(name=name):
                    self.assertLess(
                        overlap(place(shape, name, pose), shapes["base"]), 1e-5
                    )

    def test_receiver_cannot_drop_into_unreleased_support(self):
        data = load_measurements()
        shapes = parts(DEFAULT)
        offset = registration(data, shapes)
        receiver = bd.Pos(*offset) * shapes["receiver"]
        support = fixture_parts(data)["lower-support"]
        self.assertLess(overlap(receiver, support), 1e-5)
        self.assertGreater(overlap(bd.Pos(0, 0, -0.2) * receiver, support), 1)


if __name__ == "__main__":
    unittest.main()
