"""Requirements for full-length cartridges and safe operation ordering."""

import unittest

try:
    from cad.negative_carrier_b.model import Config, closure_stations
    from cad.negative_carrier_b.motion import sequences
except ModuleNotFoundError as error:
    if error.name == "build123d":
        raise unittest.SkipTest(
            "B1 tests run in the CAD workflow with cad/requirements.txt"
        ) from error
    raise


class CartridgeRequirements(unittest.TestCase):
    def test_every_end_frame_reaches_mask_before_stop(self):
        for fmt in ("135", "half", "aps", "110"):
            p = Config(fmt)
            with self.subTest(fmt=fmt):
                # 24 mm half-collar, 2 mm end stop, at least 1 mm running space.
                self.assertGreaterEqual((p.length - p.fmt.travel) / 2 - 2, 25)
        self.assertEqual(Config("135").length, 244)
        self.assertEqual(Config("half").length, 263)

    def test_frame_travel_requires_released_index_and_closed_holder(self):
        for fmt in ("135", "half", "aps", "110"):
            for phase in sequences(Config(fmt)):
                a, b = phase["start"], phase["end"]
                if a["holder_x"] != b["holder_x"]:
                    self.assertEqual(a["index_release"], 4)
                    self.assertEqual(b["index_release"], 4)
                    for k in (
                        "film_z",
                        "lid_z",
                        "clips_out",
                        "clips_release",
                        "lower_z",
                        "cap_z",
                    ):
                        self.assertEqual(a[k], 0)
                        self.assertEqual(b[k], 0)
                    self.assertEqual(a["cap_angle"], 90)
                    self.assertEqual(a["dock_angle"], 90)

    def test_docking_keeps_pins_clear_until_seated(self):
        for phase in sequences(Config()):
            a, b = phase["start"], phase["end"]
            if a["assembly_y"] != b["assembly_y"]:
                self.assertEqual(a["dock_pin_z"], 9)
                self.assertEqual(b["dock_pin_z"], 9)
                self.assertEqual(a["dock_angle"], 0)

    def test_real_strip_calibration_is_explicit(self):
        p = Config("half", frame_pitch=19.1, image_width=17, frame_count=14)
        self.assertEqual(p.fmt.frames, 14)
        self.assertEqual(p.fmt.image_width, 17)
        self.assertAlmostEqual(p.fmt.centers[1] - p.fmt.centers[0], 19.1)
        self.assertGreater(p.length, 263)

    def test_closure_recesses_preserve_every_index_pocket(self):
        choices = [Config(f) for f in ("135", "half", "aps", "110")]
        choices += [Config("135", frame_count=7), Config("half", frame_count=13)]
        for p in choices:
            for clip in closure_stations(p):
                for center in p.fmt.centers:
                    self.assertGreaterEqual(abs(clip - center), 7.4)

    def test_invalid_physical_inputs_fail(self):
        for kwargs in (
            {"format": "6x6"},
            {"film_thickness": 0},
            {"film_thickness": 0.25},
            {"frame_count": 1},
            {"frame_count": 2.5},
            {"frame_pitch": 36},
            {"frame_pitch": float("nan")},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Config(**kwargs)


if __name__ == "__main__":
    unittest.main()
