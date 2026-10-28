"""Design-contract tests for the native parameter and capacity authority."""

import unittest

from cad.parameters import capacity, displacement, level_for_volume, parameters


class NativeParameterTests(unittest.TestCase):
    def test_presets_preserve_recipe_and_shared_base(self):
        for aspect, fill, cut in [(16 / 9, 323, 208), (2, 360, 230)]:
            with self.subTest(aspect=aspect):
                p = parameters(image_aspect=aspect)
                self.assertEqual(p["working_ml"], fill)
                self.assertEqual(p["paper_cut_length"], cut)
                self.assertEqual((p["base_width"], p["base_depth"]), (170.8, 138))
                self.assertGreaterEqual(p["body_height"] - p["loaded_level"], 6)
                self.assertGreaterEqual(
                    p["loaded_level"] - p["image_top"] - p["vertical_stroke"], 1
                )
                self.assertEqual(sum(p["amounts_a"]), fill)

    def test_volume_inverse_with_paper_at_each_agitation_extreme(self):
        for aspect in (16 / 9, 2):
            p = parameters(image_aspect=aspect)
            for loaded in (False, True):
                for lift in (0, 6):
                    level = level_for_volume(p, p["working_ml"] * 1000, loaded, lift)
                    volume = capacity(p, level) - (
                        displacement(p, level, lift) if loaded else 0
                    )
                    self.assertAlmostEqual(volume / 1000, p["working_ml"], places=4)

    def test_recipe_b_does_not_reposition_the_shared_fill_mark(self):
        a = parameters()
        b = parameters(recipe_b_concentrate=1, recipe_b_water=9)
        self.assertEqual(a["empty_level"], b["empty_level"])
        self.assertEqual(b["amounts_b"], [32, 291])

    def test_fill_ridge_is_calibrated_and_displaces_liquid(self):
        for aspect in (16 / 9, 2):
            p = parameters(image_aspect=aspect)
            self.assertAlmostEqual(
                capacity(p, p["empty_level"]) / 1000, p["working_ml"], places=4
            )
            bare = p | {"ridge_projection": 0}
            from cad.parameters import ridge_area

            self.assertAlmostEqual(
                capacity(bare, p["empty_level"]) - capacity(p, p["empty_level"]),
                ridge_area(p) * p["ridge_height"],
                places=5,
            )
            self.assertLess(p["empty_level"], p["loaded_level"])

    def test_magnet_pockets_have_closed_floors_and_dry_wall_clearance(self):
        p = parameters()
        self.assertEqual((p["pocket_diameter"], p["pocket_depth"]), (6.3, 3.2))
        self.assertGreaterEqual(p["guide_thickness"] - p["pocket_depth"], 1.2)
        self.assertGreater(
            p["wall"] - (p["magnet_x"][0] + p["pocket_diameter"] / 2), p["wall"]
        )
        self.assertEqual(p["guide_top"], p["body_height"] + 3)

    def test_unsafe_or_unprintable_settings_are_rejected(self):
        for overrides in (
            {"guide_gap": 0.4},
            {"module_gap": 50},
            {"image_aspect": 3},
            {"wall": 2},
            {"guide_fit": 1},
            {"paper_thickness": float("nan")},
            {"recipe_a_water": 0},
            {"recipe_b_water": 1.5},
            {"typo": 1},
            {"magnet_thickness": 4},
            {"magnet_diameter": 8},
            {"magnet_depth_allowance": 0},
            {"ridge_projection": 3},
        ):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                parameters(**overrides)


if __name__ == "__main__":
    unittest.main()
