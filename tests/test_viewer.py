"""Viewer boundaries and job isolation, without requiring Bambu Studio in CI."""
from collections import OrderedDict
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import viewer_server as viewer


def defaults():
    return {f['id']: True if f['type'] == 'boolean' else f['min'] for f in viewer.SCHEMA}


def manager(folder):
    m = viewer.Manager.__new__(viewer.Manager)
    m.output = Path(folder)
    m.defaults, m.meta, m.presets = defaults(), {}, {}
    m.slice_error, m.token = None, 'test-token'
    m.lock, m.jobs = threading.Condition(), OrderedDict()
    m.pending, m.closed = None, False
    return m


class ParameterTests(unittest.TestCase):
    def test_rejects_code_unknown_nonfinite_and_wrong_types(self):
        for values in [[], {'path': '/etc/passwd'}, {'paper_width': 'cube(3)'},
                       {'paper_width': float('nan')}, {'paper_width': float('inf')},
                       {'paper_width': True}, {'paper_width': 999},
                       {'chamber_count': 1.5}, {'base_enabled': 1}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                viewer.validate_parameters(values, defaults())

    def test_partial_override_preserves_other_defaults(self):
        result = viewer.validate_parameters({'paper_width': 120}, defaults())
        self.assertEqual(result['paper_width'], 120)
        self.assertEqual(result['paper_height'], defaults()['paper_height'])

    def test_cache_key_tracks_source_parameter_plate_and_profile(self):
        args = [{'lib/a.scad': b'cube(1);'}, {'paper_width': 120}, 'tank', {'infill': '15%'}]
        key = viewer.source_key(*args)
        variants = [{ 'lib/a.scad': b'cube(2);'}, {'paper_width': 125}, 'fit', {'infill': '20%'}]
        for index, value in enumerate(variants):
            changed = args.copy()
            changed[index] = value
            self.assertNotEqual(key, viewer.source_key(*changed))


class JobTests(unittest.TestCase):
    def test_new_edit_cancels_old_job_and_blocks_stale_result(self):
        with tempfile.TemporaryDirectory() as folder:
            m = manager(folder)
            first = m.submit({'parameters': {'paper_width': 120}})
            second = m.submit({'parameters': {'paper_width': 125}})
            old = m.jobs[first['id']]
            self.assertTrue(old['cancel'].is_set())
            self.assertEqual(m.get(first['id'])['state'], 'superseded')
            self.assertIs(m.pending, m.jobs[second['id']])
            with self.assertRaises(viewer.Cancelled):
                m.update(old, state='ready', stats={'estimated_filament_g': 999})
            self.assertIsNone(m.get(first['id'])['stats'])
            self.assertNotIn('sources', second)
            self.assertNotIn('cancel', second)

    def test_cached_result_cancels_pending_build_and_changed_source_misses_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            m = manager(folder)
            with patch.object(viewer, 'source_snapshot', return_value={'part.scad': b'cube(1);'}):
                first = m.submit({})
                m.update(m.jobs[first['id']], state='ready')
                second = m.submit({'model': 'fit'})
                self.assertEqual(m.submit({})['id'], first['id'])
                self.assertIsNone(m.pending)
                self.assertTrue(m.jobs[second['id']]['cancel'].is_set())
            with patch.object(viewer, 'source_snapshot', return_value={'part.scad': b'cube(2);'}):
                self.assertNotEqual(m.submit({})['id'], first['id'])

    def test_command_cancellation_reaps_process_and_detects_zero_exit_scad_error(self):
        with tempfile.TemporaryDirectory() as folder:
            log = Path(folder) / 'build.log'
            event = threading.Event()
            event.set()
            start = time.monotonic()
            with self.assertRaises(viewer.Cancelled):
                viewer.command([sys.executable, '-c', 'import time; time.sleep(30)'], folder, event, log)
            self.assertLess(time.monotonic() - start, 5)
            with self.assertRaisesRegex(RuntimeError, 'Assertion'):
                viewer.command([sys.executable, '-c', 'print("ERROR: Assertion failed")'], folder, threading.Event(), log)
            with self.assertRaisesRegex(RuntimeError, '^Tank exceeds the printer volume.$'):
                viewer.command([sys.executable, '-c', 'print(\'ERROR: Assertion (size < limit) failed: "Tank exceeds the printer volume." in file parameters.scad, line 193\')'], folder, threading.Event(), log)


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.manager = manager(cls.temp.name)
        cls.server = viewer.ThreadingHTTPServer(('127.0.0.1', 0), viewer.handler_for(cls.manager))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        conn.request(method, path, body, headers or {})
        response = conn.getresponse()
        status, data = response.status, response.read()
        conn.close()
        return status, data

    def test_origin_host_and_token_boundaries(self):
        self.assertEqual(self.request('GET', '/api/config')[0], 200)
        for headers in [{'Origin': 'https://other.example'}, {'Host': 'other.example'}]:
            self.assertEqual(self.request('GET', '/api/config', headers=headers)[0], 403)
        self.assertEqual(self.request('POST', '/api/jobs', '{}')[0], 403)
        headers = {'Content-Type': 'application/json', 'X-Viewer-Token': self.manager.token}
        code, data = self.request('POST', '/api/jobs', '{"model":"fit"}', headers)
        self.assertEqual(code, 202)
        self.assertEqual(json.loads(data)['model'], 'fit')
        self.assertEqual(self.request('POST', '/api/jobs', '{bad', headers)[0], 400)
        self.assertEqual(self.request('POST', '/api/jobs', '{"parameters":{"paper_width":"evil"}}', headers)[0], 400)

    def test_artifacts_cannot_escape_job_or_serve_private_files(self):
        job = self.manager.submit({})
        folder = self.manager.output / job['id']
        folder.mkdir()
        (folder/'settings.json').write_text('{}')
        for path in ['/../lib/parameters.scad', '/artifacts/' + job['id'] + '/build.log',
                     '/artifacts/' + job['id'] + '/../../README.md', '/artifacts/' + '0'*24 + '/settings.json']:
            self.assertEqual(self.request('GET', path)[0], 404)
        self.assertEqual(self.request('GET', '/artifacts/' + job['id'] + '/settings.json'), (200, b'{}'))


@unittest.skipUnless(Path(viewer.build.OPENSCAD).is_file(), 'OpenSCAD not installed')
class PreviewIntegrationTests(unittest.TestCase):
    def test_source_defaults_build_watertight_preview_without_slicer(self):
        # Keep output inside the repository so CI's OpenSCAD container can see it.
        output = viewer.ROOT / 'build'
        output.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output) as folder, patch.object(viewer.build, 'BAMBU', '/missing/bambu'):
            m = viewer.Manager(Path(folder))
            try:
                ident = m.submit({})['id']
                deadline = time.monotonic() + 60
                while m.get(ident)['state'] in {'queued', 'rendering', 'slicing'} and time.monotonic() < deadline:
                    time.sleep(0.1)
                job = m.get(ident)
                self.assertEqual(job['state'], 'preview_only', job.get('error'))
                self.assertTrue(job['mesh']['is_watertight'])
                self.assertEqual(job['mesh']['body_count'], 1)
                self.assertIsNone(job['stats'])
                self.assertEqual(job['model_info']['mix_first_ml'] + job['model_info']['mix_second_ml'], job['model_info']['bath_ml'])
                manifest = json.loads((Path(folder)/ident/'settings.json').read_text())
                self.assertEqual(manifest['parameters'], m.defaults)
            finally:
                m.close()


if __name__ == '__main__':
    unittest.main()
