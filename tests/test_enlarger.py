"""Negative controls for native holder fit and source parameter validation."""

import unittest

try:
    import build123d as bd
except ModuleNotFoundError as error:
    if error.name == "build123d":
        raise unittest.SkipTest(
            "Native enlarger tests run with cad/requirements.txt"
        ) from error
    raise

from cad.enlarger.checks import overlap
from cad.enlarger.model import base_halves, box, cover, cylinder, mask
from cad.enlarger.parameters import image_length, parameters


class EnlargerControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = parameters()
        cls.bases = base_halves(cls.p)

    def test_joint_misregistration_interferes(self):
        self.assertLess(
            overlap(self.bases["base_left"], self.bases["base_right"]), 1e-6
        )
        self.assertGreater(
            overlap(
                self.bases["base_left"], bd.Pos(-1, 0, 0) * self.bases["base_right"]
            ),
            1,
        )

    def test_oversized_magnet_is_detected(self):
        p = self.p
        good = cylinder(p["magnet_x"], p["attachment_y"], 1, 6, 2.9)
        bad = cylinder(p["magnet_x"], p["attachment_y"], 1, 6.6, 2.9)
        self.assertLess(overlap(self.bases["base_right"], good), 1e-6)
        self.assertGreater(overlap(self.bases["base_right"], bad), 1)

    def test_mask_inward_error_blocks_image(self):
        p = self.p
        length = image_length(p, "16:9")
        image = box(
            -length / 2,
            -p["paper_width"] / 2,
            p["paper_z"] + 0.01,
            length,
            p["paper_width"],
            0.2,
        )
        m = mask(p, "16:9", 1)
        self.assertLess(overlap(m, image), 1e-6)
        self.assertGreater(overlap(bd.Pos(-1, 0, 0) * m, image), 10)

    def test_cover_overlap_misplacement_is_detected(self):
        p = self.p
        a, b = cover(p, 0), cover(p, 1)
        self.assertLess(overlap(a, b), 1e-6)
        self.assertGreater(overlap(a, bd.Pos(-1, 0, 0) * b), 10)

    def test_invalid_parameters_rejected(self):
        for overrides in (
            {"paper_width": float("nan")},
            {"paper_width": True},
            {"band_width": 34},
            {"unknown": 1},
            {"joint_clearance": 0},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                parameters(**overrides)


if __name__ == "__main__":
    unittest.main()
