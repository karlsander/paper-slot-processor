#!/usr/bin/env python3
"""Local CAD viewer. Runs OpenSCAD and the existing Bambu pipeline on isolated jobs."""
from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import threading
import time
from urllib.parse import urlsplit
import webbrowser

import build_openscad as build

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "tank": ("Tank", "paper_slot_processor.scad", []),
    "inlet_caps": ("Inlet caps", "paper_slot_processor_inlet_caps.scad", []),
    "slit_caps": ("Slot covers", "paper_slot_processor_slit_caps.scad", []),
    "fit": ("Fit section", "paper_slot_processor.scad", ['view="fit"']),
}
# Defaults are evaluated from parameters.scad, rather than copied into the UI.
FIELDS = [
    ("paper_width", "Paper width", "Paper", "number", 40, 170, 0.1, "mm"),
    ("paper_height", "Paper height", "Paper", "number", 40, 180, 0.1, "mm"),
    ("paper_thickness", "Paper thickness", "Paper", "number", 0.1, 1, 0.05, "mm"),
    ("paper_face_clearance", "Slit clearance per face", "Paper", "number", 0.05, 1, 0.05, "mm"),
    ("paper_grip_height", "Grip above rim", "Paper", "number", 6, 25, 1, "mm"),
    ("chamber_count", "Chambers", "Tank", "integer", 1, 2, 1, ""),
    ("slot_gap", "Chamber depth", "Tank", "number", 6, 24, 0.5, "mm"),
    ("side_clearance", "Paper side clearance", "Tank", "number", 0, 15, 0.5, "mm"),
    ("bottom_clearance", "Space below paper", "Tank", "number", 3, 20, 0.5, "mm"),
    ("inlets_enabled", "Fill inlets", "Tank", "boolean", 0, 1, 1, ""),
    ("inlet_opening_diameter", "Inlet diameter", "Tank", "number", 24, 60, 1, "mm"),
    ("inlet_bore_diameter", "Inlet bore", "Tank", "number", 10, 20, 0.5, "mm"),
    ("inlet_sight_depth", "Target visible pool", "Tank", "number", 0.5, 2.5, 0.1, "mm"),
    ("inlet_funnel_height", "Funnel flare height", "Advanced", "number", 12, 40, 0.5, "mm"),
    ("wall_thickness", "Wall thickness", "Advanced", "number", 2, 8, 0.2, "mm"),
    ("floor_thickness", "Floor thickness", "Advanced", "number", 2, 10, 0.2, "mm"),
    ("entry_depth", "Drip taper depth", "Advanced", "number", 0.8, 3, 0.1, "mm"),
    ("fill_headroom", "Fill headroom", "Advanced", "number", 1.5, 6, 0.5, "mm"),
    ("cap_clearance", "Cap clearance", "Advanced", "number", 0.15, 0.7, 0.05, "mm"),
    ("base_extension", "Base extension", "Advanced", "number", 20, 70, 1, "mm"),
    ("base_enabled", "Base", "Advanced", "boolean", 0, 1, 1, ""),
    ("rib_enabled", "Reinforcement ribs", "Advanced", "boolean", 0, 1, 1, ""),
]
SCHEMA = [dict(zip(("id", "label", "group", "type", "min", "max", "step", "unit"), f)) for f in FIELDS]
META = ["working_volume_ml", "mix_first_ml", "mix_second_ml", "paper_slit_width",
        "paper_top_z - loaded_fill_z", "max_paper_width", "max_paper_height", "indicator_depth", "indicator_volume_ml"]
META_KEYS = ["bath_ml", "mix_first_ml", "mix_second_ml", "slit_mm", "dry_border_mm", "max_width_mm", "max_height_mm", "indicator_depth_mm", "indicator_ml"]
ARTIFACTS = {"model.stl", "liquid.stl", "plate.3mf", "settings.json"}


class Cancelled(Exception):
    pass


def validate_parameters(values, defaults):
    if not isinstance(values, dict) or set(values) - set(defaults):
        raise ValueError("Use only the parameters listed in the viewer.")
    result = defaults | values
    for field in SCHEMA:
        value = result[field["id"]]
        if field["type"] == "boolean":
            valid = type(value) is bool
        else:
            valid = type(value) in (int, float) and math.isfinite(value) and field["min"] <= value <= field["max"]
            if field["type"] == "integer":
                valid = valid and int(value) == value
        if not valid:
            raise ValueError(f"Invalid value for {field['label']}.")
    return result


def source_snapshot():
    paths = [*ROOT.glob("*.scad"), *ROOT.glob("lib/*.scad")]
    return {str(p.relative_to(ROOT)): p.read_bytes() for p in paths}


def source_key(sources, parameters, model, presets):
    digest = hashlib.sha256(json.dumps([parameters, model, presets], sort_keys=True).encode())
    for name, content in sorted(sources.items()):
        digest.update(name.encode() + b"\0" + content)
    return digest.hexdigest()


def command(cmd, cwd, cancel, log, timeout=180):
    """Drain output into a file; stop this job's process group when superseded."""
    started = time.monotonic()
    with log.open("ab") as output:
        offset = output.tell()
        process = subprocess.Popen(cmd, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while process.poll() is None:
                if cancel.wait(0.1):
                    raise Cancelled()
                if time.monotonic() - started > timeout:
                    raise RuntimeError("The build timed out. Try a smaller change or inspect the local job log.")
        finally:
            if process.poll() is None:
                import os
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
    with log.open("rb") as output:
        output.seek(offset)
        text = output.read().decode(errors="replace")
    if process.returncode or re.search(r"^ERROR:", text, re.MULTILINE):
        assertions = re.findall(r'Assertion[^\n]+failed:\s*"([^"]+)"', text)
        if assertions:
            raise RuntimeError(assertions[-1])
        errors = [line for line in text.splitlines() if "ERROR" in line or "Assertion" in line]
        raise RuntimeError("\n".join(errors[-4:] or text.splitlines()[-8:]) or "The build failed.")
    return subprocess.CompletedProcess(cmd, process.returncode, text, "")


def write_sources(folder, sources):
    for name, content in sources.items():
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def metadata(folder, parameters, runner):
    path = folder / "viewer_metadata.scad"
    path.write_text("include <lib/parameters.scad>\nvalidate_parameters() {\n" +
                    "echo(viewer_values=[" + ",".join(f["id"] for f in SCHEMA) + "]);\n" +
                    "echo(viewer_meta=[" + ",".join(META) + "]); cube(0.1); }\n")
    defines = [arg for name, value in parameters.items() for arg in ("-D", f"{name}={json.dumps(value)}")]
    result = runner([build.OPENSCAD, "--hardwarnings", *defines, "-o", str(folder / "metadata.csg"), str(path)], cwd=folder)
    def read(name):
        match = re.search(rf"{name} = (\[[^\n]+\])", result.stdout)
        if not match:
            raise RuntimeError("OpenSCAD did not return the model parameters.")
        return json.loads(match[1])
    return dict(zip((f["id"] for f in SCHEMA), read("viewer_values"))), dict(zip(META_KEYS, read("viewer_meta")))


class Manager:
    def __init__(self, output=None):
        self.output = output or ROOT / "build/viewer"
        self.output.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.Condition()
        self.jobs = OrderedDict()
        self.pending = None
        self.closed = False
        self.presets = {}
        self.slice_error = None
        try:
            if not Path(build.BAMBU).is_file():
                raise FileNotFoundError("Bambu Studio was not found. Set BAMBU_STUDIO_BIN and restart for print estimates.")
            for key, path in [("machine", build.BAMBU_MACHINE), ("process", build.BAMBU_PROCESS), ("filament", build.BAMBU_FILAMENT)]:
                self.presets[key] = build.resolve_preset(Path(path))
                self.presets[key].pop("inherits", None)
        except (OSError, ValueError) as error:
            self.slice_error = str(error)
        folder = self.output / "defaults"
        write_sources(folder, source_snapshot())
        self.defaults, self.meta = metadata(folder, {}, lambda cmd, cwd: command(cmd, cwd, threading.Event(), self.output / "defaults.log"))
        self.thread = threading.Thread(target=self.work, daemon=True)
        self.thread.start()

    def submit(self, payload):
        if not isinstance(payload, dict) or set(payload) - {"model", "parameters"}:
            raise ValueError("Expected a model and parameters.")
        model = payload.get("model", "tank")
        if not isinstance(model, str) or model not in MODELS:
            raise ValueError("Choose a supported print plate.")
        parameters = validate_parameters(payload.get("parameters", {}), self.defaults)
        sources = source_snapshot()
        key = source_key(sources, parameters, model, self.presets)
        with self.lock:
            # A ready result is reusable only for the same sources, values and presets.
            cached = next((j for j in self.jobs.values() if j["key"] == key and j["state"] in {"ready", "preview_only"}), None)
            for old in self.jobs.values():
                if old["state"] in {"queued", "rendering", "slicing"}:
                    old["cancel"].set()
                    old["state"] = "superseded"
            if cached:
                self.pending = None
                self.jobs.move_to_end(cached["id"])
                return self.public(cached)
            ident = secrets.token_hex(12)
            job = dict(id=ident, key=key, state="queued", model=model, parameters=parameters,
                       cancel=threading.Event(), sources=sources, mesh=None, stats=None, error=None, warnings=[])
            self.jobs[ident] = job
            self.pending = job
            self.lock.notify()
            return self.public(job)

    @staticmethod
    def public(job):
        return {k: v for k, v in job.items() if k not in {"cancel", "sources", "key"}}

    def get(self, ident):
        with self.lock:
            return self.public(self.jobs[ident]) if ident in self.jobs else None

    def update(self, job, **values):
        with self.lock:
            if job["cancel"].is_set():
                raise Cancelled()
            job.update(values)

    def work(self):
        while True:
            with self.lock:
                self.lock.wait_for(lambda: self.pending is not None or self.closed)
                if self.closed:
                    return
                job, self.pending = self.pending, None
            try:
                self.build(job)
            except Cancelled:
                pass
            except Exception as error:
                with self.lock:
                    if not job["cancel"].is_set():
                        job.update(state="error", error=str(error))
            finally:
                with self.lock:
                    job.pop("sources", None)
                    # Keep the local cache bounded. Current jobs are never removed.
                    while len(self.jobs) > 12:
                        ident, old = next(iter(self.jobs.items()))
                        if old["state"] in {"queued", "rendering", "slicing"}:
                            break
                        self.jobs.pop(ident)
                        shutil.rmtree(self.output / ident, ignore_errors=True)

    def build(self, job):
        folder = self.output / job["id"]
        sources = folder / "sources"
        write_sources(sources, job["sources"])
        runner = lambda cmd, cwd=folder: command(cmd, cwd, job["cancel"], folder / "build.log")
        self.update(job, state="rendering")
        _, meta = metadata(sources, job["parameters"], runner)
        defines = [f"{k}={json.dumps(v)}" for k, v in job["parameters"].items()] + MODELS[job["model"]][2]
        source = sources / MODELS[job["model"]][1]
        stl = folder / "model.stl"
        # Match the build pipeline's ASCII STL precision around fine engraved edges.
        runner([build.OPENSCAD, "--backend", "Manifold", "--hardwarnings", "--export-format", "asciistl",
                *[arg for value in defines for arg in ("-D", value)], "-o", str(stl), str(source)])
        mesh = build.validate_mesh(stl)
        if not mesh["is_watertight"] or not mesh["is_winding_consistent"] or mesh["degenerate_faces"] or mesh["duplicate_faces"]:
            raise RuntimeError("The generated mesh did not pass validation. Adjust the parameters.")
        liquid = job["model"] in {"tank", "fit"}
        if liquid:
            water_source = sources / "viewer_liquid.scad"
            cut = "inlet_exit_z - 3" if job["model"] == "fit" else "0"
            water_source.write_text("include <lib/parameters.scad>\ninclude <lib/geometry.scad>\ninclude <lib/tank.scad>\n" +
                f"cut_z = {cut};\n" +
                "translate([0,0,-cut_z]) intersection() {\n" +
                "union() for (i=[0:chamber_count-1]) { chamber_void(i); inlet_void(i); }\n" +
                "translate([0,-tank_front,cut_z]) cube([outer_width,outer_depth+tank_front+tank_back,working_fill_z-cut_z]); }\n")
            runner([build.OPENSCAD, "--backend", "Manifold", "--hardwarnings", "--export-format", "asciistl",
                *[arg for value in defines for arg in ("-D", value)], "-o", str(folder / "liquid.stl"), str(water_source)])
        manifest = dict(model=job["model"], parameters=job["parameters"], model_info=meta, source_hash=job["key"], presets=self.presets)
        (folder / "settings.json").write_text(json.dumps(manifest, indent=2) + "\n")
        self.update(job, mesh=mesh, liquid=liquid, model_info=meta, state="slicing")
        if self.slice_error:
            self.update(job, state="preview_only", error=self.slice_error)
            return
        presets = {}
        for key, data in self.presets.items():
            presets[key] = folder / f"{key}.json"
            presets[key].write_text(json.dumps(data))
        sliced = build.bambu_slice(stl, folder, "plate", presets, run_command=runner)
        stats = build.parse_gcode(sliced["gcode"])["stats"]
        result = build.read_json(sliced["bambu_result"])
        warnings = [p["warning_message"] for p in result.get("sliced_plates", []) if p.get("warning_message")]
        if result.get("return_code") not in (0, None):
            raise RuntimeError(result.get("error_string") or "Bambu Studio could not slice this plate.")
        build.bambu_project(stl, folder, folder, "plate", presets, run_command=runner)
        self.update(job, state="ready", stats=stats, warnings=warnings)

    def close(self):
        with self.lock:
            self.closed = True
            for job in self.jobs.values():
                job["cancel"].set()
            self.lock.notify()
        self.thread.join(timeout=5)


def handler_for(manager):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            if args and str(args[1] if len(args) > 1 else "") not in {"200", "304"}:
                super().log_message(fmt, *args)

        def local_request(self):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            origin = self.headers.get("Origin", f"http://{self.headers.get('Host')}")
            return self.headers.get("Host") in allowed and origin in {f"http://{h}" for h in allowed}

        def send(self, status, data, content_type="application/json"):
            if content_type == "application/json" and not isinstance(data, bytes):
                data = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if not self.local_request():
                return self.send(403, {"error": "Use the local viewer address."})
            path = urlsplit(self.path).path
            if path == "/api/config":
                process = manager.presets.get("process", {})
                filament = manager.presets.get("filament", {})
                return self.send(200, dict(token=manager.token, fields=SCHEMA, defaults=manager.defaults,
                    limits=manager.meta, models=[{"id": k, "label": v[0]} for k, v in MODELS.items()],
                    profile=dict(machine=manager.presets.get("machine", {}).get("name", "A1 mini"),
                                 filament=filament.get("name", "PETG"), layer_height=process.get("layer_height"),
                                 walls=process.get("wall_loops"), infill=process.get("sparse_infill_density")),
                    slice_error=manager.slice_error))
            if path.startswith("/api/jobs/"):
                job = manager.get(path.rsplit("/", 1)[-1])
                return self.send(200, job) if job else self.send(404, {"error": "Build not found; update the preview again."})
            match = re.fullmatch(r"/artifacts/([a-f0-9]{24})/([a-z0-9.]+)", path)
            if match and match[2] in ARTIFACTS and manager.get(match[1]):
                target = manager.output / match[1] / match[2]
            else:
                assets = {"/": "index.html", "/app.js": "dist/app.js", "/app.js.LEGAL.txt": "dist/app.js.LEGAL.txt", "/style.css": "style.css"}
                target = ROOT / "viewer" / assets[path] if path in assets else None
            if target and target.is_file():
                return self.send(200, target.read_bytes(), mimetypes.guess_type(target)[0] or "application/octet-stream")
            return self.send(404, {"error": "Not found."})

        def do_POST(self):
            if not self.local_request() or self.headers.get("X-Viewer-Token") != manager.token:
                return self.send(403, {"error": "Reload the local viewer before submitting a build."})
            if self.path != "/api/jobs":
                return self.send(404, {"error": "Not found."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384 or self.headers.get("Content-Type") != "application/json":
                    raise ValueError("Expected a small JSON parameter object.")
                payload = json.loads(self.rfile.read(length))
                self.send(202, manager.submit(payload))
            except (ValueError, TypeError) as error:
                self.send(400, {"error": str(error)})

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    # SIGTERM follows the same cleanup path as Ctrl+C, including child processes.
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    if not (ROOT / "viewer/dist/app.js").is_file():
        raise SystemExit("Build the viewer first: cd viewer && npm ci && npm run build")
    try:
        manager = Manager()
    except (OSError, RuntimeError) as error:
        raise SystemExit(f"Could not start the viewer: {error}") from error
    try:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(manager))
        except OSError as error:
            raise SystemExit(f"Could not listen on port {args.port}: {error}. Try --port with a different number.") from error
        url = f"http://127.0.0.1:{server.server_port}"
        print(f"Processor viewer: {url}\nPress Ctrl+C to stop.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
