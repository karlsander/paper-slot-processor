"""Optical/coverage regressions; do not claim real film or mechanical performance."""

import unittest

from cad.negative_carrier_concepts.spec import (
    FORMATS,
    minimum_square_bed,
    optical_check,
)


class CarrierConceptTests(unittest.TestCase):
    def test_all_frames_isolated_with_correct_stationary_mask(self):
        for fmt in FORMATS.values():
            samples = optical_check(fmt)
            self.assertEqual(len(samples), fmt.frames)
            for sample in samples:
                self.assertAlmostEqual(
                    sample["selected_area_mm2"], fmt.aperture[0] * fmt.aperture[1]
                )
                self.assertEqual(sample["neighbour_area_mm2"], 0)

    def test_wrong_35mm_mask_reveals_neighbouring_110_images(self):
        samples = optical_check(FORMATS["110"], aperture=(36, 24))
        self.assertTrue(all(s["neighbour_area_mm2"] > 0 for s in samples))

    def test_individual_index_positions_allow_irregular_spacing(self):
        samples = optical_check(
            FORMATS["110"], centers=(0, 20.2, 41.1, 61.3, 82.5, 103.2)
        )
        self.assertEqual(
            [s["translation"] for s in samples], [0, -20.2, -41.1, -61.3, -82.5, -103.2]
        )
        self.assertTrue(all(s["neighbour_area_mm2"] == 0 for s in samples))

    def test_bad_center_sequences_rejected(self):
        for centers in ((0,), (0, 0), (0, float("nan")), (0, 10), (20, 0)):
            with self.assertRaises(ValueError):
                optical_check(FORMATS["110"], centers=centers)

    def test_six_frame_35mm_needs_split_on_180mm_bed(self):
        fmt = FORMATS["135"]
        self.assertEqual(fmt.length, 244)
        self.assertGreater(minimum_square_bed(fmt.length, 56), 180)
        self.assertLess(minimum_square_bed(fmt.length / 2 + 12, 56), 174)


if __name__ == "__main__":
    unittest.main()
