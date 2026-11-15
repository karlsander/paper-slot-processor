"""Bambu presets and G-code statistics for native CAD builds."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

BAMBU = (
    os.environ.get("BAMBU_STUDIO_BIN")
    or "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
)
BAMBU_SYSTEM_DIR = os.environ.get("BAMBU_SYSTEM_DIR") or str(
    Path.home() / "Library/Application Support/BambuStudio/system/BBL"
)
HEADER_PAIR_RE = re.compile(r"^;\s*([^:=]+?)\s*(?::|=)\s*(.*?)\s*$")


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
        raise FileNotFoundError(
            f"Ambiguous Bambu preset inheritance {name!r}: {matches}"
        )
    raise FileNotFoundError(f"Could not resolve Bambu preset inheritance {name!r}")


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
    density = parse_number(
        config.get("filament_density") or header.get("filament_density")
    )
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
            "total_filament_length_mm": parse_number(
                header.get("total_filament_length_mm")
            ),
            "bambu_total_filament_volume_raw": raw_volume,
            "estimated_filament_cm3": estimated_cm3,
            "estimated_filament_g": mass_g,
            "filament_density_g_cm3": density,
            "max_z_height_mm": parse_number(header.get("max_z_height")),
        },
    }


def parse_header_pairs(line: str) -> list[tuple[str, str]]:
    payload = line.lstrip()
    payload = payload.removeprefix(";")
    pairs = []
    for segment in payload.split(";"):
        match = HEADER_PAIR_RE.match("; " + segment.strip())
        if match:
            pairs.append(
                (normalize_key(match.group(1)), match.group(2).strip().strip('"'))
            )
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
