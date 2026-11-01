"""Regression checks for manual-carrier film safety and positive location."""

import tempfile
import unittest
from pathlib import Path

import build123d as bd
import numpy as np

from cad.negative_carrier_b2.export import print_shape, volume
from cad.negative_carrier_b2.forces import canonical_deck
from cad.negative_carrier_b2.model import DEFAULT, Config, box, holder, parts, sleeve
from cad.negative_carrier_b2.workflow import phases, place
from cad.negative_carrier_fem.solver import quadratic_volume, read_dat


class ManualCarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = DEFAULT
        cls.parts = parts(cls.p)
        cls.steps = phases(cls.p)

    def test_all_printed_components_are_single_valid_solids(self):
        for n, s in self.parts.items():
            with self.subTest(part=n):
                self.assertTrue(s.is_valid)
                self.assertEqual(len(s.solids()), 1)

    def test_both_edge_wedges_print_on_solid_spine(self):
        for name in ("wedge-0-1", "wedge-0--1"):
            shape = print_shape(name, self.parts[name])
            bed_slice = shape & box(0, 0, 0, 400, 400, 0.2)
            self.assertAlmostEqual(bed_slice.volume, 20 * 2.5 * 0.2, places=5)

    def test_uncut_strip_passes_through_both_open_ends(self):
        probe = box(
            0, 0, 0, self.p.length + 100, self.p.fmt.film_width, self.p.film_thickness
        )
        for n in ("base", "lid"):
            self.assertLess(volume(probe, self.parts[n]), 1e-6)

    def test_image_surfaces_are_not_clamped(self):
        for x in self.p.film_centers:
            probe = box(
                x, 0, -0.01, self.p.fmt.image_width, self.p.fmt.image_height, 0.17
            )
            for n in ("base", "lid"):
                self.assertLess(volume(probe, self.parts[n]), 1e-6)

    def test_engaged_shoe_blocks_movement(self):
        pose = self.steps[7]["end"]
        base = place(self.parts["base"], "base", pose)
        self.assertGreater(volume(bd.Pos(0.5, 0, 0) * base, self.parts["shoe"]), 0.01)

    def test_receiver_side_datums_and_docking_stop_are_positive(self):
        self.assertGreater(
            volume(bd.Pos(0.2, 0, 0) * self.parts["sleeve"], self.parts["receiver"]),
            0.01,
        )
        self.assertGreater(
            volume(
                bd.Pos(2.1, 0, 0) * self.parts["dock-wedge"], self.parts["receiver"]
            ),
            0.01,
        )

    def test_screw_pickup_leaves_positive_release_margin(self):
        pose = self.steps[9]["end"]
        shoe = place(self.parts["shoe"], "shoe", pose)
        self.assertGreater(
            shoe.bounding_box().min.Z - self.parts["base"].bounding_box().max.Z, 0.8
        )

    def test_small_format_mask_rejects_adjacent_frame(self):
        p = Config("110", frame_count=7)
        ray = box(p.fmt.demo_pitch, 0, -2.4, p.fmt.image_width, p.fmt.image_height, 0.8)
        # Only rays inside the independently assumed 40 x 28 mm source port.
        ray = ray & box(0, 0, -3, 40, 28, 3)
        correct = sleeve(p)
        wrong = sleeve(DEFAULT)
        self.assertAlmostEqual(volume(ray, correct), ray.volume, places=5)
        self.assertLess(volume(ray, wrong), ray.volume - 1)

    def test_six_frame_single_piece_remains_supported(self):
        p = Config("135")
        h = holder(p)
        self.assertEqual(p.fmt.frames, 6)
        self.assertGreater(h["base"].bounding_box().size.X, 180)
        self.assertEqual(len(h["base"].solids()), 1)

    def test_print_orientation_stress_is_transformed_to_global_axes(self):
        sample = """total force (fx,fy,fz) for set FIX and time 1.0

0 0 5

stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set BODY and time 1.0

1 1 1 2 3 4 5 6 LAYER_X

"""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "job.dat"
            path.write_text(sample)
            rotation = [[0, 0, 1], [1, 0, 0], [0, 1, 0]]
            result = read_dat(path, {"LAYER_X": rotation})
            np.testing.assert_allclose(result[0]["stress"][0], [3, 1, 2, 5, 6, 4])
            with self.assertRaises(AssertionError):
                read_dat(path)

    def test_solver_cache_ignores_numeric_format_but_not_values(self):
        a = "*CONTROLS,PARAMETERS=FIELD\n0.005,0.01,0.00001,0.00001\n"
        b = "*CONTROLS,PARAMETERS=FIELD\n5e-3,0.01,1e-5,1e-5\n"
        self.assertEqual(canonical_deck(a), canonical_deck(b))
        self.assertNotEqual(
            canonical_deck(a), canonical_deck(b.replace("1e-5", "1e-4"))
        )

    def test_quadratic_mesh_checks_midside_inversions(self):
        corners = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        edges = [(0, 1), (1, 2), (0, 2), (0, 3), (1, 3), (2, 3)]
        xyz = np.vstack([corners, [(corners[i] + corners[j]) / 2 for i, j in edges]])
        conn = np.arange(1, 11).reshape(1, 10)
        self.assertAlmostEqual(quadratic_volume(xyz, conn), 1 / 6)
        # Corner orientation is unchanged, but the curved solid has inverted.
        xyz[4] = [-2, -2, -2]
        with self.assertRaises(AssertionError):
            quadratic_volume(xyz, conn)


if __name__ == "__main__":
    unittest.main()
