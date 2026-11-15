"""FreeCAD console errors must never reuse a successful report from an older run."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "study", Path(__file__).resolve().parents[1] / "scripts/run_freecad_study.py"
)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class FreshReportTests(unittest.TestCase):
    def test_zero_exit_without_new_report_rejects_stale_success(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            (output / "fit-report.json").write_text('{"passed":true}')
            with (
                patch.object(
                    study.subprocess,
                    "run",
                    return_value=subprocess.CompletedProcess([], 0, "", "Python error"),
                ),
                self.assertRaises(RuntimeError),
            ):
                study.run_stage("fit", output, "FreeCADCmd")
            self.assertFalse((output / "fit-report.json").exists())

    def test_failed_report_rejects_zero_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)

            def process(*args, **kwargs):
                (output / "fit-report.json").write_text('{"passed":false}')
                return subprocess.CompletedProcess([], 0, "", "")

            with (
                patch.object(study.subprocess, "run", side_effect=process),
                self.assertRaises(RuntimeError),
            ):
                study.run_stage("fit", output, "FreeCADCmd")

    def test_new_success_report_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)

            def process(*args, **kwargs):
                self.assertEqual(kwargs["env"]["PROCESSOR_STUDY_OUTPUT"], str(output))
                (output / "fit-report.json").write_text(
                    '{"passed":true,"measured":0.6}'
                )
                return subprocess.CompletedProcess([], 0, "", "")

            with patch.object(study.subprocess, "run", side_effect=process):
                self.assertEqual(
                    study.run_stage("fit", output, "FreeCADCmd")["measured"], 0.6
                )


if __name__ == "__main__":
    unittest.main()
