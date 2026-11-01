"""Numerical workflow guards against false force results and overconstrained tips."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

try:
    from cad.negative_carrier_fem.cases import conditions, coupon_cells
    from cad.negative_carrier_fem.solver import (
        cached_mesh,
        exterior_faces,
        frd_fields,
        read_dat,
        solve,
    )
except ModuleNotFoundError as error:
    if error.name == "build123d":
        raise unittest.SkipTest("FEM tests need cad/requirements.txt") from error
    raise


class BoundaryTests(unittest.TestCase):
    def test_tip_faces_do_not_clamp_a_finite_length_of_spring(self):
        cases = {
            "guide": [[11, -19, -0.9], [10.999, -19, -0.9]],
            "index-tip": [[2.2, 25, 0.5], [2.2, 25.001, 0.5]],
            "clip-catch": [
                [3.8, 22.8, -0.65],
                [3.801, 22.8, -0.65],
                [4.7, 22.8, -0.65],
            ],
            "roof": [[-0.4, 20, 1.1], [-0.399, 20, 1.1], [-0.4, 20, 1.101]],
        }
        for name, points in cases.items():
            with self.subTest(name=name):
                fixed, loaded, _, _ = conditions(name, np.array(points))
                self.assertEqual(loaded.tolist(), [True] + [False] * (len(points) - 1))
                self.assertFalse(np.any(fixed & loaded))

    def test_front_and_rear_footprints_follow_actual_frame_reliefs(self):
        front, rear = coupon_cells(1), coupon_cells(-1)
        self.assertAlmostEqual(max(c[3] for c in front["TOP"]), 23.6)
        self.assertAlmostEqual(max(c[3] for c in front["BOTTOM"]), 23.7)
        for name in ["TOP", "BOTTOM"]:
            self.assertAlmostEqual(max(c[3] for c in rear[name]), 24)
        # No fictitious support across the positive catch's clearance pocket.
        for cells in [front["BOTTOM"], rear["BOTTOM"]]:
            self.assertFalse(
                any(x0 < 2.4 < x1 and y0 < 22.8 < y1 for x0, x1, y0, y1 in cells)
            )


class ResultsTests(unittest.TestCase):
    def test_contact_and_stress_rows_stay_in_their_own_time_step(self):
        fixture = """total force (fx,fy,fz) for set FIX and time 1.0

0 0 -2

stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set BODY and time 1.0

1 1 1 2 3 4 5 6

relative contact displacement (slave element+face,normal,tang1,tang2) for all contact elements and time 1.0

1 2 -.0001 .02 0

contact stress (slave element+face,press,tang1,tang2) for all contact elements and time 1.0

1 2 10 3 0

total force (fx,fy,fz) for set LOAD and time 1.0

0 0 2

total force (fx,fy,fz) for set FIX and time 2.0

0 0 -4
"""
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "job.dat"
            path.write_text(fixture)
            rows = read_dat(path)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["load_force"], [0, 0, 2])
        self.assertEqual(rows[0]["stress"].shape, (1, 6))
        self.assertEqual(rows[0]["contact_stress"].tolist(), [[10, 3, 0]])
        self.assertAlmostEqual(rows[0]["contact_displacement"][0, 0], -0.0001)
        self.assertNotIn("contact_stress", rows[1])

    def test_mortar_contact_components_are_not_confused_with_stress_tensor(self):
        values = [-0.0002, 0.05, 0, 20, 6, 0]
        fixture = (
            "  100C  1  1.0\n -4 CONTACT 6 1\n"
            + f" -1{42:10d}"
            + "".join(f"{v:12.5E}" for v in values)
            + "\n -3\n"
        )
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "job.frd"
            path.write_text(fixture)
            field = frd_fields(path)[0]["CONTACT"][42]
        self.assertEqual(field, values)
        self.assertEqual(field[3], 20)  # pressure, not opening or shear

    def test_same_volume_and_bounds_do_not_allow_reusing_changed_geometry(self):
        import build123d as bd

        a = bd.Box(4, 4, 1) - bd.Pos(-1, 0, 0) * bd.Cylinder(0.3, 2)
        b = bd.Box(4, 4, 1) - bd.Pos(1, 0, 0) * bd.Cylinder(0.3, 2)
        self.assertAlmostEqual(a.volume, b.volume)
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            bd.export_step(a, folder / "part.step")
            (folder / "mesh.npz").touch()
            with patch(
                "cad.negative_carrier_fem.solver.mesh", return_value="remeshed"
            ) as build:
                self.assertEqual(cached_mesh(b, folder, 0.3), "remeshed")
                build.assert_called_once()

    def test_old_success_is_removed_if_solver_returns_without_completion(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "result.json").write_text(json.dumps({"passed": True}))
            with patch("cad.negative_carrier_fem.solver.subprocess.run") as run:
                run.return_value.returncode = 0
                with self.assertRaises(AssertionError):
                    solve(folder, "new input", "fake-ccx")
            self.assertFalse((folder / "result.json").exists())

    def test_internal_tetra_faces_are_not_contact_surfaces(self):
        a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        b = [1, 3, 2, 11, 7, 6, 5, 12, 13, 14]
        faces = exterior_faces(np.array([a, b]))
        self.assertEqual(len(faces), 6)
        self.assertFalse(any(set(nodes[:3]) == {1, 2, 3} for _, _, nodes in faces))


if __name__ == "__main__":
    unittest.main()
