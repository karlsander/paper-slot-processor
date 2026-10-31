#!/usr/bin/env python3
"""Create two individual A1 mini PETG projects; reopen, slice and verify each."""

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import build_openscad as build
import numpy as np
import trimesh
from build_native_bambu import metadata, run
from scipy.spatial import cKDTree


def verify(project, source, half, sliced=False):
    ns = {
        "c": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
        "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06",
    }
    with zipfile.ZipFile(project) as archive:
        assert archive.testzip() is None
        config = json.loads(archive.read("Metadata/project_settings.config"))
        assert config["printer_model"] == "Bambu Lab A1 mini"
        assert list(map(float, config["nozzle_diameter"])) == [0.4]
        assert (
            config["filament_type"] == ["PETG"] and float(config["layer_height"]) == 0.2
        )
        assert (
            config["enable_support"] == "1" and config["support_type"] == "normal(auto)"
        )
        model = ET.fromstring(archive.read("Metadata/model_settings.config"))
        scene = ET.fromstring(archive.read("3D/3dmodel.model"))
        objects = model.findall("object")
        plates = model.findall("plate")
        assert len(objects) == len(plates) == 1
        plate = metadata(plates[0])
        assert len(plates[0].findall("model_instance")) == 1
        if sliced:
            assert plate["gcode_file"] in archive.namelist()
        object_id = objects[0].attrib["id"]
        component = scene.find(
            f"c:resources/c:object[@id='{object_id}']/c:components/c:component", ns
        )
        transform = np.array(list(map(float, component.attrib["transform"].split())))
        np.testing.assert_allclose(transform[:9].reshape(3, 3), np.eye(3), atol=1e-9)
        mesh = ET.fromstring(
            archive.read(component.attrib[f"{{{ns['p']}}}path"].lstrip("/"))
        )
        vertices = (
            np.array(
                [
                    [float(v.attrib[a]) for a in "xyz"]
                    for v in mesh.findall(".//c:vertices/c:vertex", ns)
                ]
            )
            + transform[9:]
        )
        item = scene.find(f"c:build/c:item[@objectid='{object_id}']", ns)
        placement = np.array(list(map(float, item.attrib["transform"].split())))
        np.testing.assert_allclose(placement[:9].reshape(3, 3), np.eye(3), atol=1e-9)
        placed = vertices + placement[9:]
        assert abs(placed[:, 2].min()) < 1e-4
        assert np.all(placed.min(axis=0) >= -1e-4) and np.all(
            placed.max(axis=0) <= [180.0001] * 3
        )
        original = trimesh.load_mesh(source / "plates" / f"{half}.stl").vertices
        vertices -= (vertices.min(axis=0) + vertices.max(axis=0)) / 2
        original -= (original.min(axis=0) + original.max(axis=0)) / 2
        assert cKDTree(original).query(vertices)[0].max() < 1e-4
        assert cKDTree(vertices).query(original)[0].max() < 1e-4


def export(source, output):
    # No slicing of unverified or stale model exports.
    validation = json.loads((source / "validation.json").read_text())
    assert validation.get("passed") is True
    assert (
        validation["model_report_sha256"]
        == hashlib.sha256((source / "model-report.json").read_bytes()).hexdigest()
    )
    model = json.loads((source / "model-report.json").read_text())
    for relative, digest in model["files_sha256"].items():
        assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == digest, (
            relative
        )
    output.mkdir(parents=True, exist_ok=True)
    build.BAMBU_PROCESS = str(build.ROOT / "profiles/Durst 0.20mm @BBL A1M.json")
    for half in "ab":
        folder = output / half
        folder.mkdir(parents=True, exist_ok=True)
        presets = build.resolved_bambu_presets(folder)
        assembly = folder / "assemble.json"
        assembly.write_text(
            json.dumps(
                {
                    "plates": [
                        {
                            "plate_name": f"Carrier {half.upper()}",
                            "need_arrange": False,
                            "objects": [
                                {
                                    "path": str(source / "plates" / f"{half}.stl"),
                                    "count": 1,
                                    "filaments": [1],
                                }
                            ],
                        }
                    ]
                },
                indent=2,
            )
        )
        name = f"Durst-C35-v0.2-{half.upper()}-A1mini-PETG-0.4mm.3mf"
        project = folder / name
        run(
            folder,
            "export",
            *build.bambu_settings_args(presets, arrange=False),
            "--load-assemble-list",
            assembly,
            "--export-3mf",
            name,
            "--outputdir",
            folder,
        )
        verify(project, source, half)
        run(
            folder,
            "reload-slice",
            "--arrange",
            "0",
            "--orient",
            "0",
            "--slice",
            "0",
            "--export-3mf",
            "sliced.3mf",
            "--outputdir",
            folder,
            project,
        )
        result = json.loads((folder / "result.json").read_text())
        assert result["return_code"] == 0 and len(result["sliced_plates"]) == 1
        assert not result["sliced_plates"][0].get("warning_message"), result
        verify(folder / "sliced.3mf", source, half, sliced=True)
        gcode = folder / "plate_1.gcode"
        assert "; FEATURE: Support" in gcode.read_text()
        (folder / "sliced.3mf").replace(project)
        report = {
            "passed": True,
            "source_vertices_preserved": True,
            "saved_profile_verified": True,
            "warnings": [],
            "stats": build.parse_gcode(gcode)["stats"],
            "model_report_sha256": hashlib.sha256(
                (source / "model-report.json").read_bytes()
            ).hexdigest(),
            "project_sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
        }
        (folder / "project-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(project, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export(args.source.resolve(), args.output.resolve())
