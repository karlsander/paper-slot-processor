"""Requirements for full-length cartridges and safe operation ordering."""

import json
import unittest
from math import sqrt
from pathlib import Path

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

    def test_film_can_only_be_repositioned_with_clamp_and_collar_open(self):
        for fmt in ("135", "half", "aps", "110"):
            moves = []
            for phase in sequences(Config(fmt)):
                a, b = phase["start"], phase["end"]
                if a["film_x"] != b["film_x"]:
                    moves.append(phase)
                    for s in (a, b):
                        self.assertFalse(s["machine"])
                        self.assertGreaterEqual(s["film_z"], 2)
                        self.assertGreater(s["lid_z"], s["film_z"])
                        self.assertGreater(s["clips_out"], 6)
                        self.assertGreater(s["cap_z"], 40)
                        self.assertLess(s["lower_z"], -20)
            self.assertEqual(len(moves), 1)

    def test_roll_length_does_not_change_printed_dimensions_or_indexing(self):
        for fmt in ("135", "half", "aps", "110"):
            short, long = (
                Config(fmt, film_tail_frames=0),
                Config(fmt, film_tail_frames=20),
            )
            self.assertEqual(short.length, long.length)
            self.assertEqual(short.fmt.centers, long.fmt.centers)
            self.assertGreater(long.film_length, long.length)
            self.assertFalse(any(p["group"] == "reposition" for p in sequences(short)))

    def test_a1_mini_holders_fit_flat_with_five_mm_brim(self):
        path = (
            Path(__file__).resolve().parents[1] / "cad/negative_carrier_b/a1-mini.json"
        )
        for fmt, overrides in json.loads(path.read_text()).items():
            p = Config(fmt, **overrides)
            footprint = min(p.length, (p.length + 62) / sqrt(2))
            self.assertLess(footprint + 10, 180)

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
            {"film_tail_frames": -1},
            {"film_tail_frames": 1.5},
            {"film_tail_frames": True},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Config(**kwargs)


if __name__ == "__main__":
    unittest.main()
