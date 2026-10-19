import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("build", Path(__file__).resolve().parents[1] / "scripts/build_openscad.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class GcodeStatsTests(unittest.TestCase):
    def stats(self, extra):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "part.gcode"
            p.write_text('; HEADER_BLOCK_START\n; total filament volume [cm^3] : 10000\n' + extra + '\n; HEADER_BLOCK_END\n')
            return build.parse_gcode(p)["stats"]

    def test_petg_uses_its_density(self):
        self.assertEqual(self.stats('; filament_density: 1.27')["estimated_filament_g"], 12.7)

    def test_reported_mass_is_authoritative(self):
        self.assertEqual(self.stats('; filament_density: 1.27\n; total filament weight [g] : 12.65')["estimated_filament_g"], 12.65)

    def test_missing_density_does_not_assume_pla(self):
        self.assertIsNone(self.stats('')["estimated_filament_g"])

if __name__ == '__main__':
    unittest.main()
