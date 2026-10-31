"""Hashed native geometry, printable meshes, motion and assumption manifest."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import build123d as bd
import trimesh

from .fixture import PARAMETERS, fixtures
from .model import (
    Config,
    closure_clip,
    closure_stations,
    collar,
    index_latch,
    parts,
    role,
)
from .motion import State, placement, samples, sequences


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(out, formats, overrides=None):
    report = {
        "version": "B1",
        "build123d_version": bd.__version__,
        "physical_fit_verified": False,
        "evidence_level": "Sampled geometric motion; prescribed spring deflections, no FEA",
        "fixture_parameters": PARAMETERS,
        "assets": {},
        "models": [],
        "source_hashes": {},
    }
    root = Path(__file__).resolve().parents[2]
    for file in sorted((root / "cad/negative_carrier_b").glob("*.py")):
        report["source_hashes"][str(file.relative_to(root))] = sha(file)

    def save(key, shape, printable=False, print_shape=None):
        if key in report["assets"]:
            return key
        assert shape.is_valid and len(shape.solids()) == 1, (key, len(shape.solids()))
        path = out / (key + ".step")
        path.parent.mkdir(parents=True, exist_ok=True)
        bd.export_step(shape, path)
        record = {
            "file": str(path.relative_to(out)),
            "sha256": sha(path),
            "volume_mm3": shape.volume,
        }
        if printable:
            mesh_path = out / "stl" / (key + ".stl")
            mesh_path.parent.mkdir(parents=True, exist_ok=True)
            printable_shape = shape if print_shape is None else print_shape
            assert printable_shape.is_valid and len(printable_shape.solids()) == 1, key
            if print_shape is not None:
                native_path = out / "print-native" / (key + ".step")
                native_path.parent.mkdir(parents=True, exist_ok=True)
                bd.export_step(printable_shape, native_path)
                record["relaxed_native"] = {
                    "file": str(native_path.relative_to(out)),
                    "sha256": sha(native_path),
                    "volume_mm3": printable_shape.volume,
                }
            printable_shape = (
                bd.Pos(0, 0, -printable_shape.bounding_box().min.Z) * printable_shape
            )
            bd.export_stl(
                printable_shape, mesh_path, tolerance=0.04, angular_tolerance=0.12
            )
            mesh = trimesh.load(mesh_path, force="mesh")
            assert mesh.is_watertight and mesh.is_volume, key
            assert (
                abs(mesh.volume - printable_shape.volume) / printable_shape.volume
                < 0.01
            ), key
            record["print"] = {
                "file": str(mesh_path.relative_to(out)),
                "sha256": sha(mesh_path),
                "watertight": bool(mesh.is_watertight),
                "extents_mm": list(mesh.extents),
                "volume_mm3": float(mesh.volume),
            }
        report["assets"][key] = record
        return key

    fixture_map = {n: save("fixture/" + n, s) for n, s in fixtures().items()}
    for fmt in formats:
        p = Config(fmt, **(overrides or {}).get(fmt, {}))
        model = {
            "format": fmt,
            "config": asdict(p),
            "format_data": p.fmt.data(),
            "holder_length_mm": p.length,
            "film_path": {
                "open_ends": "both",
                "width_mm": p.fmt.film_width + 0.8,
                "film_length_mm": p.film_length,
                "image_centers_mm": p.film_centers,
                "unclamped_reposition_mm": p.fmt.demo_pitch
                if p.film_tail_frames
                else 0,
                "continuous_roll_transport": False,
            },
            "parts": {},
            "variants": {},
            "phases": sequences(p),
            "samples": [],
        }
        shape_map = parts(p)
        for name, shape in shape_map.items():
            common = name not in (
                "base",
                "lid",
                "film",
                "collar-base",
                "collar-cap",
            ) and not name.startswith("closure-")
            key = ("common/" if common else fmt + "/") + name
            print_shape = (
                collar(p, guide_free=1)["collar-base"]
                if name == "collar-base"
                else None
            )
            if name == "index-latch":
                print_shape = index_latch(free_pad=1)
            if name == "collar-cap":
                print_shape = collar(p, roof_free=1)["collar-cap"]
            if name.startswith("closure-"):
                x, side = next(
                    (x, side)
                    for x in closure_stations(p)
                    for side in (-1, 1)
                    if name == f"closure-{x:g}-{side}"
                )
                print_shape = closure_clip(x, side, jaw_free=1)
            model["parts"][name] = {
                "asset": save(key, shape, name != "film", print_shape),
                "role": role(name),
            }
        for index, release in enumerate([0, 1, 2, 3, 4]):
            key = save(
                f"common/index-r{index}",
                index_latch(release, free_pad=max(0, (release - 3.2) / 0.8)),
            )
            model["variants"][f"index-{index}"] = key
        for index, release in enumerate([0, 0.075, 0.15, 0.225, 0.3]):
            for x in closure_stations(p):
                for side in (-1, 1):
                    name = f"closure-{x:g}-{side}"
                    key = save(
                        f"{fmt}/variants/{name}-r{index}",
                        closure_clip(x, side, release),
                    )
                    model["variants"][f"{name}-{index}"] = key
        for sample in samples(p):
            state = State(**sample["state"])
            records = []
            for name, record in model["parts"].items():
                if name == "receiver" and not state.machine:
                    continue
                if name != "receiver" and not state.cartridge:
                    continue
                key = record["asset"]
                if name == "index-latch":
                    key = model["variants"][f"index-{round(state.index_release)}"]
                elif name.startswith("closure-"):
                    key = model["variants"][
                        f"{name}-{round(state.clips_release / 0.075)}"
                    ]
                d, c, a = placement(name, p, state)
                records.append(
                    {
                        "name": name,
                        "asset": key,
                        "translation": d,
                        "pivot": c,
                        "angle": a,
                    }
                )
            if state.machine:
                for n, key in fixture_map.items():
                    d, c, a = placement(n, p, state)
                    records.append(
                        {
                            "name": n,
                            "asset": key,
                            "translation": d,
                            "pivot": c,
                            "angle": a,
                        }
                    )
            model["samples"].append(sample | {"parts": records})
        report["models"].append(model)
        print(
            "Exported",
            fmt,
            p.length,
            "mm holder,",
            len(model["samples"]),
            "poses",
            flush=True,
        )
    (out / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
