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
from viewer_v2 import (MODELS, FIELDS, SCHEMA, META, ARTIFACTS, VIEWS,
                       PARTS, STANDARD_PARTS, QUANTITIES, preset_overrides)
import zipfile



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
    paths = [*ROOT.glob("v2/*.scad")]
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
    path.write_text("include <v2/parameters.scad>\nvalid() {\n" +
                    "echo(viewer_values=[" + ",".join(f["id"] for f in SCHEMA) + "]);\n" +
                    "echo(viewer_meta=[" + ",".join(META.values()) + "]); cube(0.1); }\n")
    defines = [arg for name, value in parameters.items() for arg in ("-D", f"{name}={json.dumps(value)}")]
    result = runner([build.OPENSCAD, "--hardwarnings", *defines, "-o", str(folder / "metadata.csg"), str(path)], cwd=folder)
    def read(name):
        match = re.search(rf"{name} = (\[[^\n]+\])", result.stdout)
        if not match:
            raise RuntimeError("OpenSCAD did not return the model parameters.")
        return json.loads(match[1])
    return dict(zip((f["id"] for f in SCHEMA), read("viewer_values"))), dict(zip(META, read("viewer_meta")))


def aggregate_stats(reports):
    seconds = 0
    for report in reports:
        text = report["stats"]["total_estimated_time"]
        seconds += report["quantity"] * sum(float(n)*{'d':86400,'h':3600,'m':60,'s':1}[unit]
                                           for n,unit in re.findall(r"([\d.]+)\s*([dhms])", text))
    hours, minutes = divmod(round(seconds / 60),60)
    return {"total_estimated_time":f"{hours}h {minutes}m",
            **{key:sum(r["quantity"]*r["stats"][key] for r in reports)
               for key in ["estimated_filament_g","estimated_filament_cm3"]}}


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
        model = payload.get("model", "assembly")
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

    def render(self, source, parameters, target, runner):
        defines = [arg for k,v in parameters.items() for arg in ("-D", f"{k}={json.dumps(v)}")]
        runner([build.OPENSCAD, "--backend", "Manifold", "--hardwarnings", "--export-format", "asciistl",
                *defines, "-o", str(target), str(source)])
        mesh = build.validate_mesh(target)
        if not mesh["is_watertight"] or not mesh["is_winding_consistent"] or mesh["degenerate_faces"] or mesh["duplicate_faces"]:
            raise RuntimeError("The generated mesh did not pass validation. Adjust the parameters.")
        return mesh

    def slice_plate(self, job, name, source, runner):
        # Shared immutable plate results avoid reslicing all parts when switching views.
        overrides = preset_overrides(name)
        key = source_key(job["sources"], job["parameters"], name, self.presets | {"overrides": overrides})[:24]
        folder = self.output / "plates" / key
        report_path = folder / "report.json"
        if report_path.is_file():
            report = json.loads(report_path.read_text())
            if all((folder / f"plate.{ext}").is_file() for ext in ("stl", "3mf")):
                return folder, report
        folder.mkdir(parents=True, exist_ok=True)
        label, part, values, count = PARTS[name]
        stl = folder / "plate.stl"
        mesh = self.render(source, job["parameters"] | values | {"part": part}, stl, runner)
        if mesh["body_count"] != count or any(a>b+0.001 for a,b in zip(mesh["extents_mm"], [174,174,178])):
            raise RuntimeError(f"{label} does not fit its reserved print volume.")
        presets = {}
        for kind, data in self.presets.items():
            presets[kind] = folder / f"{kind}.json"
            presets[kind].write_text(json.dumps(data | overrides if kind == "process" else data))
        arrange = not name.startswith("vessel_")
        sliced = build.bambu_slice(stl, folder, "plate", presets, run_command=runner, arrange=arrange)
        result = build.read_json(sliced["bambu_result"])
        warnings = [p["warning_message"] for p in result.get("sliced_plates", []) if p.get("warning_message")]
        if result.get("return_code") != 0 or warnings:
            raise RuntimeError(result.get("error_string") or "\n".join(warnings) or "Slicing failed.")
        build.bambu_project(stl, folder, folder, "plate", presets, run_command=runner, arrange=arrange)
        report = dict(name=name, label=label, quantity=QUANTITIES.get(name,1), mesh=mesh,
                      stats=build.parse_gcode(sliced["gcode"])["stats"])
        report_path.write_text(json.dumps(report, indent=2))
        # A single worker owns this cache. Completed jobs keep their own downloads.
        entries = sorted(folder.parent.iterdir(), key=lambda p: p.stat().st_mtime)
        for old in entries[:-96]:
            if old != folder: shutil.rmtree(old, ignore_errors=True)
        return folder, report

    def build(self, job):
        folder = self.output / job["id"]
        sources = folder / "sources"
        write_sources(sources, job["sources"])
        runner = lambda cmd, cwd=folder: command(cmd, cwd, job["cancel"], folder / "build.log")
        self.update(job, state="rendering")
        _, meta = metadata(sources, job["parameters"] | MODELS[job["model"]][2], runner)
        meta["adox_prints_per_fill"] = math.floor(meta["bath_ml"] / 1000 * 2 / (math.prod(meta["cut_mm"]) / 1e6))
        meta["adox_recipe"] = all(job["parameters"][f"recipe_{bath}_water"] == 4*job["parameters"][f"recipe_{bath}_concentrate"] for bath in ("a","b"))
        name = job["model"]
        source = sources / MODELS[name][1]
        params = job["parameters"] | MODELS[name][2]
        assembly = name in {"assembly", "exploded"}
        inspection = name in {"inspect_a", "inspect_b"}
        layers = []
        primary = params | ({"view_layer": "body"} if assembly or inspection else {})
        mesh = self.render(source, primary, folder / "model.stl", runner)
        solid_volume = mesh["volume_mm3"]
        boxes = [mesh["bounds_mm"]]
        if assembly or inspection:
            details = self.render(source, params | {"view_layer":"details"}, folder / "details.stl", runner)
            boxes.append(details["bounds_mm"])
            layers.append({"file":"details.stl", "color":"#cfac63"})
            solid_volume += details["volume_mm3"]
            if name == "assembly":
                hardware = self.render(source, params | {"view_layer":"hardware"}, folder / "hardware.stl", runner)
                boxes.append(hardware["bounds_mm"])
                layers.append({"file":"hardware.stl", "color":"#929b9d"})
        liquid = name == "assembly" or inspection
        if liquid:
            for part, file in [("assembly_liquid" if assembly else "liquid", "liquid"),
                               ("assembly_paper" if assembly else "paper", "paper"),
                               ("assembly_loaded_liquid" if assembly else "loaded_liquid", "loaded")]:
                self.render(source, params | {"part":part}, folder / f"{file}.stl", runner)
        manifest = dict(model=name, parameters=job["parameters"], model_info=meta,
                        source_hash=job["key"], presets=self.presets,
                        quantity=QUANTITIES.get(name,1), prototype="Physical water, paper and thermal tests pending.")
        (folder / "settings.json").write_text(json.dumps(manifest, indent=2) + "\n")
        preview_bounds = [max(b[1][i] for b in boxes)-min(b[0][i] for b in boxes) for i in range(3)]
        self.update(job, mesh=mesh, preview_bounds_mm=preview_bounds, solid_volume_mm3=solid_volume, liquid=liquid, paper=liquid,
                    layers=layers, model_info=meta, view_only=name in VIEWS,
                    quantity=QUANTITIES.get(name,1), state="slicing")
        if self.slice_error:
            self.update(job, state="preview_only", error=self.slice_error)
            return
        names = STANDARD_PARTS if assembly else (["vessel_b"] if name == "inspect_b" else ["vessel_a"] if inspection else [name])
        reports = []
        paths = []
        for i, part in enumerate(names):
            self.update(job, stage_detail=f"Slicing {PARTS[part][0]} · {i+1}/{len(names)}")
            path, report = self.slice_plate(job, part, source, runner)
            reports.append(report); paths.append(path)
        if assembly:
            stats = aggregate_stats(reports)
            with zipfile.ZipFile(folder / "print-files.zip", "w", zipfile.ZIP_DEFLATED) as archive:
                for path, report in zip(paths, reports):
                    for ext in ("stl", "3mf"):
                        archive.write(path / f"plate.{ext}", f"{report['name']}.{ext}")
                archive.writestr("plates.json", json.dumps(reports, indent=2))
                archive.write(folder / "settings.json", "settings.json")
                archive.write(ROOT / "README.md", "README.md")
                archive.write(ROOT / "docs/heating.md", "docs/heating.md")
                archive.write(ROOT / "docs/v1.md", "docs/v1.md")
        else:
            stats = reports[0]["stats"]
            shutil.copy2(paths[0] / "plate.3mf", folder / "plate.3mf")
            # Inspection STL is upright; expose only the correctly oriented project.
        manifest["plates"] = reports
        (folder / "settings.json").write_text(json.dumps(manifest, indent=2) + "\n")
        self.update(job, state="ready", stats=stats, stage_detail=None,
                    plates=reports, bundle=assembly, project=not assembly)

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
                    limits=manager.meta, models=[{"id": k, "label": v[0],
                        "fixed_parameters": {f["id"]: v[2][f["id"]] for f in SCHEMA if f["id"] in v[2]}}
                        for k, v in MODELS.items()],
                    profile=dict(machine=manager.presets.get("machine", {}).get("name", "A1 mini"),
                                 filament=filament.get("name", "PETG"), layer_height=process.get("layer_height"),
                                 walls=process.get("wall_loops"), infill=process.get("sparse_infill_density")),
                    slice_error=manager.slice_error))
            if path.startswith("/api/jobs/"):
                job = manager.get(path.rsplit("/", 1)[-1])
                return self.send(200, job) if job else self.send(404, {"error": "Build not found; update the preview again."})
            match = re.fullmatch(r"/artifacts/([a-f0-9]{24})/([a-z0-9.-]+)", path)
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
