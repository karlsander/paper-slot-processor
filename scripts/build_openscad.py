#!/usr/bin/env python3
"""Build and validate OpenSCAD models in a project.

Renders each root-level .scad file with OpenSCAD (Manifold backend), validates
the mesh with trimesh, slices it with the Bambu Studio CLI, and writes a
validation summary. See README.md for commands, outputs and validation limits.

Paths and the project root are configurable via flags and environment
variables (see resolve_root() and the env vars below).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


# Keep invocation independent of the current directory.
# Precedence: --root flag > OPENSCAD_BUILD_ROOT env var > this repository.
ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"
SCAD_DEFINES: list[str] = []

# Tool paths default to a typical macOS install but can be overridden by env
# vars so the pipeline works across machines without editing this file.
OPENSCAD = os.environ.get("OPENSCAD_BIN") or shutil.which("openscad") or "/opt/homebrew/bin/openscad"
BAMBU = os.environ.get("BAMBU_STUDIO_BIN") or "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"

_BBL = os.environ.get("BAMBU_SYSTEM_DIR") or str(
    Path.home() / "Library/Application Support/BambuStudio/system/BBL"
)
BAMBU_SYSTEM_DIR = _BBL
BAMBU_MACHINE = os.environ.get("BAMBU_MACHINE") or f"{_BBL}/machine/Bambu Lab A1 mini 0.4 nozzle.json"
BAMBU_PROCESS = os.environ.get("BAMBU_PROCESS") or str(ROOT / "profiles/Processor 0.20mm @BBL A1M.json")
BAMBU_FILAMENT = os.environ.get("BAMBU_FILAMENT") or f"{_BBL}/filament/Generic PETG @BBL A1M.json"


def resolve_root(arg_root: str | None) -> Path:
    """Resolve the project root holding the .scad sources and build/ output."""
    if arg_root:
        return Path(arg_root).expanduser().resolve()
    env_root = os.environ.get("OPENSCAD_BUILD_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return ROOT

RENDER_VIEWS = {
    "iso": ("0,0,0,55,0,25,400", "p"),
    "iso_back": ("0,0,0,55,0,205,400", "p"),
    "front": ("0,0,0,90,0,0,400", "o"),
    "back": ("0,0,0,90,0,180,400", "o"),
    "left": ("0,0,0,90,0,-90,400", "o"),
    "right": ("0,0,0,90,0,90,400", "o"),
    "top": ("0,0,0,0,0,0,400", "o"),
    "bottom": ("0,0,0,180,0,0,400", "o"),
}

BAMBU_PLATE_VIEWS = {
    0: "iso",
    1: "top_front",
    2: "left",
    3: "right",
    10: "iso_1",
    11: "iso_2",
    12: "iso_3",
}

HEADER_PAIR_RE = re.compile(r"^;\s*([^:=]+?)\s*(?::|=)\s*(.*?)\s*$")


def run(cmd: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    if cmd[0] == OPENSCAD:
        cmd = [cmd[0], *[arg for value in SCAD_DEFINES for arg in ("-D", value)], *cmd[1:]]
    print("$ " + " ".join(shell_quote(part) for part in cmd))
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        raise subprocess.CalledProcessError(proc.returncode, cmd, proc.stdout, proc.stderr)
    return proc


def shell_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:=,@%+-]+", value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def require_trimesh():
    try:
        import trimesh  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing Python dependency: trimesh. Install with "
            "`python3 -m pip install -r requirements.txt`."
        ) from exc
    return trimesh


def discover_scad_files(selected: list[str]) -> list[Path]:
    if selected:
        files = [Path(item) for item in selected]
    else:
        files = sorted(ROOT.glob("*.scad"))
    normalized = []
    for path in files:
        source = path if path.is_absolute() else ROOT / path
        if not source.exists():
            raise SystemExit(f"OpenSCAD source not found: {path}")
        if source.suffix != ".scad":
            raise SystemExit(f"Expected a .scad file, got: {path}")
        normalized.append(source)
    return normalized


def prepare_model_dirs(name: str) -> tuple[Path, Path, Path]:
    out_dir = BUILD_DIR / name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    images_dir = out_dir / "images"
    generated_dir = out_dir / "generated"
    images_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True)
    return out_dir, images_dir, generated_dir


def openscad_outputs(
    source: Path, generated_dir: Path, images_dir: Path, name: str
) -> dict[str, Path]:
    stl_path = generated_dir / f"{name}.stl"
    source_3mf_path = generated_dir / f"{name}.openscad.3mf"
    summary_path = generated_dir / f"{name}.openscad-summary.json"

    run(
        [
            OPENSCAD,
            "--backend",
            "Manifold",
            "--hardwarnings",
            "-o",
            str(stl_path),
            "-o",
            str(source_3mf_path),
            "--summary",
            "all",
            "--summary-file",
            str(summary_path),
            str(source),
        ]
    )

    render_paths = []
    for view_name, (camera, projection) in RENDER_VIEWS.items():
        render_path = images_dir / f"{name}_{view_name}.png"
        run(
            [
                OPENSCAD,
                "--backend",
                "Manifold",
                "-o",
                str(render_path),
                "--imgsize",
                "1800,1400",
                "--autocenter",
                "--viewall",
                "--render",
                "--camera",
                camera,
                "--projection",
                projection,
                "--colorscheme",
                "Cornfield",
                str(source),
            ]
        )
        render_paths.append(render_path)

    return {
        "stl": stl_path,
        "openscad_3mf": source_3mf_path,
        "summary": summary_path,
        "renders": render_paths,
    }


def validate_mesh(stl_path: Path) -> dict:
    trimesh = require_trimesh()
    raw_loaded = trimesh.load_mesh(stl_path, force="mesh", process=False)
    raw_mesh = raw_loaded.dump(concatenate=True) if hasattr(raw_loaded, "dump") else raw_loaded
    loaded = trimesh.load_mesh(stl_path, force="mesh", process=True)
    mesh = loaded.dump(concatenate=True) if hasattr(loaded, "dump") else loaded

    bounds = mesh.bounds.tolist() if getattr(mesh, "bounds", None) is not None else None
    extents = mesh.extents.tolist() if getattr(mesh, "extents", None) is not None else None
    duplicate_faces = count_duplicate_faces(mesh)
    degenerate_faces = count_degenerate_faces(mesh)

    return {
        "raw_vertices": int(len(raw_mesh.vertices)),
        "raw_faces": int(len(raw_mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "is_empty": bool(mesh.is_empty),
        "is_watertight": bool(mesh.is_watertight),
        "is_winding_consistent": bool(mesh.is_winding_consistent),
        "euler_number": int(mesh.euler_number),
        "body_count": connected_face_component_count(mesh),
        "bounds_mm": bounds,
        "extents_mm": extents,
        "volume_mm3": finite_float(mesh.volume),
        "surface_area_mm2": finite_float(mesh.area),
        "duplicate_faces": duplicate_faces,
        "degenerate_faces": degenerate_faces,
    }


def count_duplicate_faces(mesh) -> int:
    if len(mesh.faces) == 0:
        return 0
    faces = [tuple(sorted(face)) for face in mesh.faces.tolist()]
    return len(faces) - len(set(faces))


def count_degenerate_faces(mesh) -> int:
    if len(mesh.faces) == 0:
        return 0
    try:
        mask = mesh.nondegenerate_faces()
    except AttributeError:
        mask = mesh.remove_degenerate_faces()
    if isinstance(mask, bool):
        return 0
    return int(len(mask) - int(sum(mask)))


def connected_face_component_count(mesh) -> int:
    face_count = len(mesh.faces)
    if face_count == 0:
        return 0

    parent = list(range(face_count))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left, right in mesh.face_adjacency:
        union(int(left), int(right))

    return len({find(index) for index in range(face_count)})


def finite_float(value) -> float | None:
    value = float(value)
    return value if math.isfinite(value) else None


def bambu_settings_args(presets: dict[str, Path], *, arrange: bool = True) -> list[str]:
    return [
        "--load-settings",
        f"{presets['machine']};{presets['process']}",
        "--load-filaments",
        str(presets["filament"]),
        "--arrange",
        "1" if arrange else "0",
        "--orient",
        "0",
        "--ensure-on-bed",
    ]


def resolved_bambu_presets(generated_dir: Path) -> dict[str, Path]:
    presets_dir = generated_dir / "presets"
    presets_dir.mkdir(exist_ok=True)
    inputs = {
        "machine": Path(BAMBU_MACHINE),
        "process": Path(BAMBU_PROCESS),
        "filament": Path(BAMBU_FILAMENT),
    }
    outputs = {}
    for preset_type, source in inputs.items():
        resolved = resolve_preset(source)
        resolved.pop("inherits", None)
        dest = presets_dir / f"{source.stem}.resolved.json"
        dest.write_text(json.dumps(resolved, indent=4, sort_keys=True) + "\n")
        outputs[preset_type] = dest
    return outputs


def resolve_preset(path: Path, seen: set[Path] | None = None) -> dict:
    if seen is None:
        seen = set()
    path = path.resolve()
    if path in seen:
        raise ValueError(f"Cyclic Bambu preset inheritance involving {path}")
    seen.add(path)

    data = read_json(path)
    inherited_name = data.get("inherits")
    if not inherited_name:
        return data

    parent_path = find_bambu_preset(inherited_name, data.get("type"), path.parent)
    parent = resolve_preset(parent_path, seen)
    merged = dict(parent)
    merged.update(data)
    return merged


def find_bambu_preset(name: str, preset_type: str | None, current_dir: Path) -> Path:
    candidates = [
        current_dir / f"{name}.json",
        Path(BAMBU_SYSTEM_DIR) / str(preset_type or "") / f"{name}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    matches = [
        path
        for path in Path(BAMBU_SYSTEM_DIR).rglob(f"{name}.json")
        if preset_type is None or path.parent.name == preset_type
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise FileNotFoundError(f"Ambiguous Bambu preset inheritance {name!r}: {matches}")
    raise FileNotFoundError(f"Could not resolve Bambu preset inheritance {name!r}")


def bambu_info(mesh_path: Path, out_dir: Path, name: str) -> dict:
    proc = run([BAMBU, "--info", str(mesh_path)], cwd=out_dir)
    sidecar = out_dir / "result.json"
    sidecar_dest = None
    if sidecar.exists():
        sidecar_dest = out_dir / f"{name}.bambu-info-result.json"
        replace_output(sidecar, sidecar_dest)
    return {"stdout": proc.stdout, "result_json": sidecar_dest}


def bambu_slice(
    mesh_path: Path, out_dir: Path, name: str, presets: dict[str, Path], *, run_command=run, arrange: bool = True
) -> dict[str, Path]:
    run_command(
        [
            BAMBU,
            *bambu_settings_args(presets, arrange=arrange),
            "--slice",
            "0",
            "--outputdir",
            str(out_dir.resolve()),
            str(mesh_path),
        ],
        cwd=out_dir,
    )

    plate_gcode = out_dir / "plate_1.gcode"
    result_json = out_dir / "result.json"
    gcode_path = out_dir / f"{name}.gcode"
    bambu_result_path = out_dir / f"{name}.bambu-result.json"

    replace_output(plate_gcode, gcode_path)
    replace_output(result_json, bambu_result_path)

    return {"gcode": gcode_path, "bambu_result": bambu_result_path}


def replace_output(source: Path, dest: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Expected Bambu output was not created: {source}")
    if dest.exists():
        dest.unlink()
    source.rename(dest)


def capture_sidecar_json(cwd: Path, dest: Path) -> Path | None:
    sidecar = cwd / "result.json"
    if not sidecar.exists():
        return None
    replace_output(sidecar, dest)
    return dest


def bambu_project(
    mesh_path: Path,
    out_dir: Path,
    generated_dir: Path,
    name: str,
    presets: dict[str, Path],
    *, run_command=run,
    arrange: bool = True,
) -> Path:
    project_path = out_dir / f"{name}.3mf"
    run_command(
        [
            BAMBU,
            *bambu_settings_args(presets, arrange=arrange),
            "--export-3mf",
            str(project_path.resolve()),
            str(mesh_path),
        ],
        cwd=generated_dir,
    )
    capture_sidecar_json(generated_dir, generated_dir / f"{name}.bambu-project-result.json")
    return project_path


def bambu_plate_renders(
    project_path: Path, images_dir: Path, generated_dir: Path, name: str
) -> list[Path]:
    render_paths = []
    for angle, label in BAMBU_PLATE_VIEWS.items():
        temporary = images_dir / f"plate_1_{angle}.png"
        if temporary.exists():
            temporary.unlink()
        run(
            [
                BAMBU,
                "--camera-view",
                str(angle),
                "--export-png",
                "0",
                "--outputdir",
                str(images_dir.resolve()),
                str(project_path.resolve()),
            ],
            cwd=generated_dir,
        )
        if not temporary.exists():
            raise FileNotFoundError(f"Expected Bambu plate render was not created: {temporary}")
        capture_sidecar_json(images_dir, generated_dir / f"{name}.bambu-plate-render-result.json")
        dest = images_dir / f"{name}_bambu_plate_{label}.png"
        replace_output(temporary, dest)
        render_paths.append(dest)
    return render_paths


def parse_gcode(gcode_path: Path) -> dict:
    header: dict[str, str] = {}
    config: dict[str, str] = {}
    section = None

    with gcode_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped == "; HEADER_BLOCK_START":
                section = "header"
                continue
            if stripped == "; CONFIG_BLOCK_START":
                section = "config"
                continue
            if stripped in {"; HEADER_BLOCK_END", "; CONFIG_BLOCK_END"}:
                section = None
                if stripped == "; CONFIG_BLOCK_END":
                    break
                continue
            if section not in {"header", "config"}:
                continue
            if section == "header":
                for key, value in parse_header_pairs(line):
                    header[key] = value
            else:
                match = HEADER_PAIR_RE.match(line)
                if not match:
                    continue
                key = normalize_key(match.group(1))
                value = match.group(2).strip().strip('"')
                config[key] = value

    raw_volume = parse_number(header.get("total_filament_volume_cm3"))
    estimated_cm3 = raw_volume / 1000.0 if raw_volume is not None else None
    density = parse_number(config.get("filament_density") or header.get("filament_density"))
    # Prefer the slicer's mass, which already uses the selected material's density.
    mass_g = parse_number(header.get("total_filament_weight_g"))
    if mass_g is None and estimated_cm3 is not None and density is not None:
        mass_g = estimated_cm3 * density

    return {
        "header": header,
        "config": interesting_config(config),
        "stats": {
            "model_printing_time": header.get("model_printing_time"),
            "total_estimated_time": header.get("total_estimated_time"),
            "total_layer_number": parse_number(header.get("total_layer_number")),
            "total_filament_length_mm": parse_number(header.get("total_filament_length_mm")),
            "bambu_total_filament_volume_raw": raw_volume,
            "estimated_filament_cm3": estimated_cm3,
            "estimated_filament_g": mass_g,
            "filament_density_g_cm3": density,
            "max_z_height_mm": parse_number(header.get("max_z_height")),
        },
    }


def parse_header_pairs(line: str) -> list[tuple[str, str]]:
    payload = line.lstrip()
    if payload.startswith(";"):
        payload = payload[1:]
    pairs = []
    for segment in payload.split(";"):
        match = HEADER_PAIR_RE.match("; " + segment.strip())
        if match:
            pairs.append((normalize_key(match.group(1)), match.group(2).strip().strip('"')))
    return pairs


def normalize_key(key: str) -> str:
    key = key.strip().lower()
    key = key.replace("[", "").replace("]", "")
    key = key.replace("^", "")
    key = re.sub(r"[^a-z0-9]+", "_", key)
    return key.strip("_")


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


def interesting_config(config: dict[str, str]) -> dict[str, str]:
    keys = [
        "default_filament_profile",
        "default_print_profile",
        "filament_type",
        "enable_support",
        "detect_overhang_wall",
        "detect_floating_vertical_shell",
        "sparse_infill_density",
        "wall_loops",
        "layer_height",
        "bottom_shell_layers",
        "top_shell_layers",
        "nozzle_diameter",
    ]
    return {key: config[key] for key in keys if key in config}


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def zip_ok(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None
    except zipfile.BadZipFile:
        return False


def png_ok(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(8) == b"\x89PNG\r\n\x1a\n"
    except FileNotFoundError:
        return False


def build_one(source: Path, *, skip_bambu_project: bool) -> dict:
    name = source.stem
    out_dir, images_dir, generated_dir = prepare_model_dirs(name)
    presets = resolved_bambu_presets(generated_dir)

    outputs = openscad_outputs(source, generated_dir, images_dir, name)
    mesh_report = validate_mesh(outputs["stl"])
    info = bambu_info(outputs["openscad_3mf"], generated_dir, name)

    try:
        slice_outputs = bambu_slice(outputs["openscad_3mf"], generated_dir, name, presets)
        bambu_input = outputs["openscad_3mf"]
        fallback_reason = None
    except subprocess.CalledProcessError as exc:
        fallback_reason = f"Bambu did not slice OpenSCAD 3MF; retried STL. Exit {exc.returncode}."
        print(fallback_reason)
        slice_outputs = bambu_slice(outputs["stl"], generated_dir, name, presets)
        bambu_input = outputs["stl"]

    project_path = None
    plate_render_paths: list[Path] = []
    if not skip_bambu_project:
        project_path = bambu_project(bambu_input, out_dir, generated_dir, name, presets)
        plate_render_paths = bambu_plate_renders(project_path, images_dir, generated_dir, name)

    validation = summarize_validation(
        source=source,
        out_dir=out_dir,
        generated_dir=generated_dir,
        outputs=outputs,
        presets=presets,
        mesh_report=mesh_report,
        bambu_info=info,
        slice_outputs=slice_outputs,
        project_path=project_path,
        plate_render_paths=plate_render_paths,
        bambu_input=bambu_input,
        fallback_reason=fallback_reason,
    )
    validation_path = generated_dir / f"{name}.validation.json"
    validation_path.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n")
    return validation


def summarize_validation(
    *,
    source: Path,
    out_dir: Path,
    generated_dir: Path,
    outputs: dict[str, Path],
    presets: dict[str, Path],
    mesh_report: dict,
    bambu_info: dict,
    slice_outputs: dict[str, Path],
    project_path: Path | None,
    plate_render_paths: list[Path],
    bambu_input: Path,
    fallback_reason: str | None,
) -> dict:
    name = source.stem
    openscad_summary = read_json(outputs["summary"])
    bambu_result = read_json(slice_outputs["bambu_result"])
    gcode = parse_gcode(slice_outputs["gcode"])
    render_paths = outputs["renders"]
    warnings = collect_warnings(mesh_report, openscad_summary, bambu_result, fallback_reason)

    artifacts = {
        "source_scad": rel(source),
        "stl": rel(outputs["stl"]),
        "openscad_3mf": rel(outputs["openscad_3mf"]),
        "bambu_project_3mf": rel(project_path) if project_path else None,
        "gcode": rel(slice_outputs["gcode"]),
        "openscad_summary": rel(outputs["summary"]),
        "bambu_result": rel(slice_outputs["bambu_result"]),
        "bambu_info_result": rel(bambu_info["result_json"]),
        "validation": rel(generated_dir / f"{name}.validation.json"),
        "validation_summary": rel(out_dir / "validation-summary.json"),
        "resolved_presets": {key: rel(path) for key, path in presets.items()},
        "renders": [rel(path) for path in render_paths],
        "bambu_plate_renders": [rel(path) for path in plate_render_paths],
    }

    return {
        "model": name,
        "parameters": SCAD_DEFINES.copy(),
        "status": "warning" if warnings else "ok",
        "warnings": warnings,
        "artifacts": artifacts,
        "bambu_input": rel(bambu_input),
        "openscad": {
            "simple": openscad_summary.get("geometry", {}).get("simple"),
            "bounding_box": openscad_summary.get("geometry", {}).get("bounding_box"),
            "facets": openscad_summary.get("geometry", {}).get("facets"),
            "vertices": openscad_summary.get("geometry", {}).get("vertices"),
        },
        "trimesh": mesh_report,
        "bambu": {
            "return_code": bambu_result.get("return_code"),
            "error_string": bambu_result.get("error_string"),
            "plate_warnings": [
                plate.get("warning_message", "")
                for plate in bambu_result.get("sliced_plates", [])
                if plate.get("warning_message", "")
            ],
            "objects": [
                item
                for plate in bambu_result.get("sliced_plates", [])
                for item in plate.get("objects", [])
            ],
            "gcode": gcode,
            "info_text": bambu_info["stdout"],
        },
        "artifact_checks": {
            "openscad_3mf_zip_ok": zip_ok(outputs["openscad_3mf"]),
            "bambu_project_3mf_zip_ok": zip_ok(project_path) if project_path else None,
            "renders_png_ok": {rel(path): png_ok(path) for path in render_paths},
            "bambu_plate_renders_png_ok": {
                rel(path): png_ok(path) for path in plate_render_paths
            },
        },
    }


def collect_warnings(
    mesh_report: dict,
    openscad_summary: dict,
    bambu_result: dict,
    fallback_reason: str | None,
) -> list[str]:
    warnings = []
    geometry = openscad_summary.get("geometry", {})
    if geometry.get("simple") is not True:
        warnings.append("OpenSCAD did not report simple geometry.")
    if not mesh_report["is_watertight"]:
        warnings.append("trimesh reports the STL is not watertight.")
    if not mesh_report["is_winding_consistent"]:
        warnings.append("trimesh reports inconsistent winding.")
    if mesh_report["duplicate_faces"]:
        warnings.append(f"trimesh found {mesh_report['duplicate_faces']} duplicate faces.")
    if mesh_report["degenerate_faces"]:
        warnings.append(f"trimesh found {mesh_report['degenerate_faces']} degenerate faces.")
    if fallback_reason:
        warnings.append(fallback_reason)
    for plate in bambu_result.get("sliced_plates", []):
        message = plate.get("warning_message", "")
        if message:
            warnings.append(f"Bambu warning: {message}")
    if bambu_result.get("return_code") not in {0, None}:
        warnings.append(f"Bambu returned code {bambu_result.get('return_code')}.")
    return warnings


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path.resolve().relative_to(ROOT))


def compact_validation_summary(item: dict) -> dict:
    gcode_stats = item["bambu"]["gcode"]["stats"]
    return {
        "model": item["model"],
        "parameters": item["parameters"],
        "status": item["status"],
        "warnings": item["warnings"],
        "artifacts": item["artifacts"],
        "dimensions_mm": item["trimesh"]["extents_mm"],
        "mesh": {
            "watertight": item["trimesh"]["is_watertight"],
            "winding_consistent": item["trimesh"]["is_winding_consistent"],
            "body_count": item["trimesh"]["body_count"],
            "volume_mm3": item["trimesh"]["volume_mm3"],
            "surface_area_mm2": item["trimesh"]["surface_area_mm2"],
            "faces": item["trimesh"]["faces"],
            "vertices": item["trimesh"]["vertices"],
        },
        "print": {
            "model_printing_time": gcode_stats["model_printing_time"],
            "total_estimated_time": gcode_stats["total_estimated_time"],
            "total_layer_number": gcode_stats["total_layer_number"],
            "total_filament_length_mm": gcode_stats["total_filament_length_mm"],
            "estimated_filament_cm3": gcode_stats["estimated_filament_cm3"],
            "estimated_filament_g": gcode_stats["estimated_filament_g"],
            "max_z_height_mm": gcode_stats["max_z_height_mm"],
        },
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scad", nargs="*", help="Optional .scad files. Defaults to every root *.scad.")
    parser.add_argument("-D", "--define", action="append", default=[], help="OpenSCAD parameter override; repeat as needed.")
    parser.add_argument("--variant", help="Save under build/NAME, keeping default exports intact.")
    parser.add_argument(
        "--root",
        default=None,
        help="Project root holding the .scad sources and build/ output. "
        "Defaults to OPENSCAD_BUILD_ROOT env var, then this repository.",
    )
    parser.add_argument(
        "--skip-bambu-project",
        action="store_true",
        help="Skip Bambu Studio project 3MF export.",
    )
    args = parser.parse_args(argv)

    if args.define and not args.variant:
        parser.error("Parameter overrides require --variant NAME to protect the default exports.")
    if args.variant and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.variant):
        parser.error("Variant names may contain letters, numbers, hyphens and underscores.")
    global ROOT, BUILD_DIR, SCAD_DEFINES
    ROOT = resolve_root(args.root)
    BUILD_DIR = ROOT / "build"
    if args.variant:
        BUILD_DIR = BUILD_DIR / args.variant
    SCAD_DEFINES = args.define

    require_trimesh()
    files = discover_scad_files(args.scad)
    if not files:
        raise SystemExit("No .scad files found.")

    validations = [build_one(source, skip_bambu_project=args.skip_bambu_project) for source in files]
    summaries = [compact_validation_summary(item) for item in validations]

    for summary in summaries:
        folder_summary_path = BUILD_DIR / summary["model"] / "validation-summary.json"
        folder_summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    report_path = BUILD_DIR / "validation-summary.json"
    report_path.write_text(json.dumps(summaries, indent=2, sort_keys=True) + "\n")

    print("\nBuild summary")
    failed = False
    for item in validations:
        warnings = item["warnings"]
        print(f"- {item['model']}: {item['status']}")
        for warning in warnings:
            print(f"  - {warning}")
        failed = failed or bool(warnings)
    print(f"\nWrote {rel(report_path)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
