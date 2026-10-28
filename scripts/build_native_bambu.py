"""Export and re-slice a five-plate A1 mini project in Bambu Studio.

Uses Bambu's assemble-list importer, not hand-authored 3MF internals. Saving and
reopening before slicing verifies that object overrides survive the round trip.
"""

import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import build_openscad as build
import numpy as np
import trimesh
from scipy.spatial import cKDTree

PARTS = ["base", "vessel_a", "vessel_b", "guide_a", "guide_b"]


def metadata(element):
    return {
        m.attrib["key"]: m.attrib.get("value", "")
        for m in element.findall("metadata")
        if "key" in m.attrib
    }


def settings(output, nozzle):
    system = Path(build.BAMBU_SYSTEM_DIR)
    sources = {
        "machine": system / "machine" / f"Bambu Lab A1 mini {nozzle:g} nozzle.json",
        "process": system
        / "process"
        / (
            "0.10mm Standard @BBL A1M 0.2 nozzle.json"
            if nozzle == 0.2
            else "0.20mm Standard @BBL A1M.json"
        ),
        "filament": system
        / "filament"
        / (
            "Generic PETG @BBL A1M 0.2 nozzle.json"
            if nozzle == 0.2
            else "Generic PETG @BBL A1M.json"
        ),
    }
    result = {}
    for kind, source in sources.items():
        data = build.resolve_preset(source)
        data.pop("inherits", None)
        if kind == "process":
            data.update(
                wall_loops="4",
                top_shell_layers="12" if nozzle == 0.2 else "6",
                bottom_shell_layers="12" if nozzle == 0.2 else "6",
                sparse_infill_density="15%",
                curr_bed_type="Textured PEI Plate",
                enable_support="0",
                brim_type="no_brim",
            )
        result[kind] = output / f"{kind}.json"
        result[kind].write_text(json.dumps(data, indent=2))
    return result


def run(output, label, *args):
    with (output / f"{label}.log").open("w") as log:
        result = subprocess.run(
            [build.BAMBU, *map(str, args)],
            cwd=output,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=1800,
            check=False,
        )
    if result.returncode:
        raise RuntimeError(
            f"{label}: Bambu exit {result.returncode}; see {output}/{label}.log"
        )


def verify(project, nozzle, sliced=False, source=None):
    with zipfile.ZipFile(project) as archive:
        assert archive.testzip() is None
        config = json.loads(archive.read("Metadata/project_settings.config"))
        assert list(map(float, config["nozzle_diameter"])) == [nozzle]
        assert config["printer_model"] == "Bambu Lab A1 mini"
        assert config["filament_type"] == ["PETG"]
        assert float(config["layer_height"]) == (0.1 if nozzle == 0.2 else 0.2)
        assert config["wall_loops"] == "4"
        shells = "12" if nozzle == 0.2 else "6"
        assert config["top_shell_layers"] == config["bottom_shell_layers"] == shells
        assert config["sparse_infill_density"] == "15%"
        assert config["curr_bed_type"] == "Textured PEI Plate"
        model = ET.fromstring(archive.read("Metadata/model_settings.config"))
        ns = {
            "c": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02",
            "p": "http://schemas.microsoft.com/3dmanufacturing/production/2015/06",
        }
        scene = ET.fromstring(archive.read("3D/3dmodel.model"))
        objects = {obj.attrib["id"]: metadata(obj) for obj in model.findall("object")}
        plates = model.findall("plate")
        assert len(plates) == len(objects) == 5
        for expected, plate in zip(PARTS, plates):
            plate_data = metadata(plate)
            assert plate_data["plater_name"] == expected
            instances = plate.findall("model_instance")
            assert len(instances) == 1
            object_id = metadata(instances[0])["object_id"]
            obj = objects[object_id]
            if source:
                component = scene.find(
                    f"c:resources/c:object[@id='{object_id}']/c:components/c:component",
                    ns,
                )
                matrix = np.array(
                    list(map(float, component.attrib["transform"].split()))
                )
                np.testing.assert_allclose(
                    matrix[:9].reshape(3, 3), np.eye(3), atol=1e-9
                )
                mesh_path = component.attrib[f"{{{ns['p']}}}path"].lstrip("/")
                mesh = ET.fromstring(archive.read(mesh_path))
                vertices = np.array(
                    [
                        [float(v.attrib[a]) for a in "xyz"]
                        for v in mesh.findall(".//c:vertices/c:vertex", ns)
                    ]
                )
                vertices += matrix[9:]
                original = trimesh.load_mesh(
                    source / "plates" / f"{expected}.stl"
                ).vertices
                # Bambu welds/reorders vertices. Compare both sets after its
                # local recentering, before the multi-plate display translation.
                assert cKDTree(original).query(vertices)[0].max() < 1e-4
                assert cKDTree(vertices).query(original)[0].max() < 1e-4
            assert obj["name"].startswith(expected)
            vessel = expected.startswith("vessel")
            assert obj["enable_support"] == ("1" if vessel else "0")
            assert obj["brim_type"] == ("outer_only" if vessel else "no_brim")
            if vessel:
                assert obj["support_type"] == "tree(auto)"
                assert obj["support_on_build_plate_only"] == "1"
                assert obj["support_threshold_angle"] == "30"
                assert obj["brim_width"] == "3"
            if sliced:
                assert plate_data["gcode_file"] in archive.namelist()
        return {
            "nozzle_mm": nozzle,
            "layer_height_mm": float(config["layer_height"]),
            "printer": config["printer_model"],
            "filament": config["filament_type"],
            "plates": PARTS,
            "saved_settings_verified": True,
            "embedded_gcode": sliced,
            "source_vertices_preserved": bool(source),
        }


def export(source, output, nozzle, name):
    output.mkdir(parents=True, exist_ok=True)
    presets = settings(output, nozzle)
    plates = []
    for part in PARTS:
        path = source / "plates" / f"{part}.stl"
        assert path.is_file(), path
        vessel = part.startswith("vessel")
        params = {
            "enable_support": "1" if vessel else "0",
            "brim_type": "outer_only" if vessel else "no_brim",
        }
        if vessel:
            params.update(
                support_type="tree(auto)",
                support_on_build_plate_only="1",
                support_threshold_angle="30",
                brim_width="3",
            )
        plates.append(
            {
                "plate_name": part,
                "need_arrange": False,
                "objects": [
                    {
                        "path": str(path),
                        "count": 1,
                        "filaments": [1],
                        "print_params": params,
                    }
                ],
            }
        )
    assembly = output / "assemble.json"
    assembly.write_text(json.dumps({"plates": plates}, indent=2))
    project = output / f"{name}.3mf"
    run(
        output,
        "export",
        *build.bambu_settings_args(presets, arrange=False),
        "--load-assemble-list",
        assembly,
        "--export-3mf",
        project.name,
        "--outputdir",
        output,
    )
    report = verify(project, nozzle, source=source)
    # No preset overrides on reload: the saved project must carry its own setup.
    sliced_name = f"{name}.sliced.3mf"
    run(
        output,
        "reload-slice",
        "--arrange",
        "0",
        "--orient",
        "0",
        "--slice",
        "0",
        "--export-3mf",
        sliced_name,
        "--outputdir",
        output,
        project,
    )
    result = json.loads((output / "result.json").read_text())
    assert result["return_code"] == 0
    sliced = result["sliced_plates"]
    assert len(sliced) == 5
    assert not any(p.get("warning_message") for p in sliced), sliced
    report.update(verify(output / sliced_name, nozzle, sliced=True, source=source))
    report["toolpaths"] = []
    for i, part in enumerate(PARTS, 1):
        gcode = output / f"plate_{i}.gcode"
        if part.startswith("vessel"):
            assert "; FEATURE: Support" in gcode.read_text()
        report["toolpaths"].append(
            {"part": part, "stats": build.parse_gcode(gcode)["stats"]}
        )
    (output / sliced_name).replace(project)
    (output / "project-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(project, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--nozzle", type=float, choices=[0.2, 0.4], default=0.4)
    parser.add_argument("--name", default="processor-v1.8")
    args = parser.parse_args()
    export(args.source.resolve(), args.output.resolve(), args.nozzle, args.name)
