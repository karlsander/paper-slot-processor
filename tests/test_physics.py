"""Numerical bookkeeping tests independent of the optional CFD/CAD runtime."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from simulation.physics.analyze import check_complete, liquid_flux, table
from simulation.physics.cases import grid


class PhysicsTests(unittest.TestCase):
    def test_phase_flux_recovery_with_air_and_reverse_flow(self):
        water = np.array([2e-6, -3e-6, 0.0])
        air = np.array([5e-6, 4e-6, -1e-6])
        np.testing.assert_allclose(
            liquid_flux(water + air, 1000 * water + air), water, atol=1e-18
        )

    def test_restart_tables_replace_duplicate_time_without_double_counting(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = []
            for start, text in [("0", "# header\n1 2\n2 3\n"), ("2", "2 4\n3 6\n")]:
                p = Path(temp) / start / "data.dat"
                p.parent.mkdir()
                p.write_text(text)
                paths.append(p)
            np.testing.assert_equal(table(reversed(paths)), [[1, 2], [2, 4], [3, 6]])

    def test_early_solver_exit_cannot_pass_as_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            log = p / "log.solver"
            log.write_text("Time = 30\nEnd\n")
            with self.assertRaises(ValueError):
                check_complete(p, 3600)
            log.write_text("Time = 3600\nFOAM FATAL ERROR\n")
            with self.assertRaises(ValueError):
                check_complete(p, 3600)
            log.write_text("Time = 3600\nEnd\n")
            check_complete(p, 3600)

    def test_mesh_volumes_respect_material_interface(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            volumes = grid(
                p,
                [[0, 0.01, 0.02], [0, 0.005], [0, 0.1]],
                lambda x, y, z: "water" if x < 0.01 else "petg",
                [0.005] * 3,
            )
            self.assertAlmostEqual(volumes["water"], 5e-6)
            self.assertAlmostEqual(volumes["petg"], 5e-6)
            self.assertIn("freeSurface", (p / "system/blockMeshDict").read_text())


if __name__ == "__main__":
    unittest.main()
