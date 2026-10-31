"""Quadratic solid meshing, nonlinear CalculiX decks and result extraction."""

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import build123d as bd
import numpy as np

from .cases import conditions, coupon_cells

CCX = (
    os.environ.get("CCX_CMD")
    or shutil.which("ccx")
    or "/Applications/FreeCAD.app/Contents/Resources/bin/ccx"
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mesh(shape, folder, size):
    import gmsh

    folder.mkdir(parents=True, exist_ok=True)
    native = folder / "part.step"
    assert shape.is_valid and len(shape.solids()) == 1
    bd.export_step(shape, native)
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.occ.importShapes(str(native))
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMin", size * 0.65)
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
        gmsh.model.mesh.generate(3)
        gmsh.model.mesh.setOrder(2)
        tags, coords, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(tags)
        tags, xyz = tags[order], np.array(coords).reshape(-1, 3)[order]
        _, conn = gmsh.model.mesh.getElementsByType(11)
        # Gmsh's last two tetra midside nodes differ from Abaqus/CalculiX.
        conn = np.asarray(conn).reshape(-1, 10)[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
        conn = np.searchsorted(tags, conn) + 1
        jac = np.linalg.det(
            np.stack(
                [xyz[conn[:, i] - 1] - xyz[conn[:, 0] - 1] for i in (1, 2, 3)], axis=2
            )
        )
        assert np.all(jac > 0)
        volume = float(jac.sum() / 6)
        assert abs(volume / shape.volume - 1) < 0.015
        gmsh.write(str(folder / "part.msh"))
        np.savez_compressed(folder / "mesh.npz", xyz=xyz, conn=conn)
        return (
            xyz,
            conn,
            {
                "nodes": len(xyz),
                "elements": len(conn),
                "size_mm": size,
                "native_volume_mm3": shape.volume,
                "mesh_volume_mm3": volume,
                "native_sha256": sha(native),
                "mesh_sha256": sha(folder / "mesh.npz"),
            },
        )
    finally:
        gmsh.finalize()


def cached_mesh(shape, folder, size):
    """Reuse only after comparing the present native solid to the saved solid."""
    if (folder / "mesh.npz").exists() and (folder / "part.step").exists():
        old_shape = bd.import_step(folder / "part.step")
        if (
            old_shape.is_valid
            and (shape.cut(old_shape).volume + old_shape.cut(shape).volume) < 1e-7
        ):
            archive = np.load(folder / "mesh.npz")
            xyz, conn = archive["xyz"], archive["conn"]
            jac = np.linalg.det(
                np.stack(
                    [xyz[conn[:, i] - 1] - xyz[conn[:, 0] - 1] for i in (1, 2, 3)],
                    axis=2,
                )
            )
            volume = float(jac.sum() / 6)
            assert np.all(jac > 0) and abs(volume / shape.volume - 1) < 0.015
            return (
                xyz,
                conn,
                {
                    "nodes": len(xyz),
                    "elements": len(conn),
                    "size_mm": size,
                    "native_volume_mm3": shape.volume,
                    "mesh_volume_mm3": volume,
                    "native_sha256": sha(folder / "part.step"),
                    "mesh_sha256": sha(folder / "mesh.npz"),
                },
            )
    return mesh(shape, folder, size)


def nset(name, ids):
    assert len(ids), name
    return (
        f"*NSET,NSET={name}\n"
        + "\n".join(",".join(map(str, ids[i : i + 16])) for i in range(0, len(ids), 16))
        + "\n"
    )


def material(scale=1, isotropic=False):
    # Current Bambu PETG Basic V3 tensile moduli. The missing Poisson/shear
    # constants are explicit estimates, not measured orthotropic calibration.
    e, ez, nu = 2780 * scale, 2550 * scale, 0.38
    if isotropic:
        return f"*MATERIAL,NAME=PETG\n*ELASTIC\n{e},{nu}\n"
    gxy, gxz = e / (2 * (1 + nu)), (e * ez) ** 0.5 / (2 * (1 + nu))
    return (
        "*MATERIAL,NAME=PETG\n*ELASTIC,TYPE=ENGINEERING CONSTANTS\n"
        f"{e},{e},{ez},{nu},{nu},{nu},{gxy},{gxz}\n{gxz}\n"
    )


def header(xyz, conn, scale=1, isotropic=False):
    lines = ["*HEADING", "B1 printed PETG force study; mm N MPa", "*NODE,NSET=ALL"]
    lines += [f"{i}," + ",".join(f"{v:.10g}" for v in p) for i, p in enumerate(xyz, 1)]
    lines += ["*ELEMENT,TYPE=C3D10,ELSET=BODY"]
    lines += [f"{i}," + ",".join(map(str, c)) for i, c in enumerate(conn, 1)]
    return (
        "\n".join(lines)
        + "\n"
        + material(scale, isotropic)
        + "*SOLID SECTION,ELSET=BODY,MATERIAL=PETG\n"
    )


def outputs(contact=False):
    text = (
        "*NODE FILE,FREQUENCY=999999\nU,RF\n*EL FILE\nS,E\n"
        "*NODE PRINT,NSET=FIX,TOTALS=ONLY\nRF\n"
        "*NODE PRINT,NSET=LOAD,TOTALS=ONLY\nRF\n"
        "*EL PRINT,ELSET=BODY\nS,E\n"
    )
    if contact:
        text += "*CONTACT PRINT\nCDIS,CSTR\n"
    return text


def elastic_deck(name, xyz, conn, scale=1, isotropic=False):
    fixed, loaded, axis, travel = conditions(name, xyz)
    assert not np.any(fixed & loaded)
    deck = header(xyz, conn, scale, isotropic)
    if name == "index-pinned":
        refs = []
        rotations = []
        for i, side in enumerate((-1, 1)):
            ref, rot = len(xyz) + 1 + 2 * i, len(xyz) + 2 + 2 * i
            refs.append(ref)
            rotations.append(rot)
            deck += f"*NODE\n{ref},{20 * side},36,0\n{rot},0,0,0\n"
            deck += nset(
                f"PAD{i}", list(np.flatnonzero(xyz[:, 0] * side >= 17.5 - 1e-6) + 1)
            )
            deck += f"*RIGID BODY,NSET=PAD{i},REF NODE={ref},ROT NODE={rot}\n"
        deck += nset("FIX", refs) + nset("ROT", rotations) + "*BOUNDARY\nROT,1,2,0\n"
    else:
        deck += nset("FIX", list(np.flatnonzero(fixed) + 1))
    deck += nset("LOAD", list(np.flatnonzero(loaded) + 1))
    deck += "*BOUNDARY\nFIX,1,3,0\n"
    if name in ("index", "index-pinned"):
        deck += "LOAD,1,1,0\nLOAD,3,3,0\n"
    steps = [0.25, 0.5, 0.75, 1] if name != "benchmark" else [1]
    for f in steps:
        deck += "*STEP,NLGEOM,INC=300\n*STATIC\n0.1,1,1e-7,0.2\n*BOUNDARY\n"
        deck += f"LOAD,{axis},{axis},{f * travel}\n" + outputs() + "*END STEP\n"
    return deck, {
        "fixed_nodes": int(fixed.sum()),
        "load_nodes": int(loaded.sum()),
        "axis": axis,
        "travel_mm": travel,
    }


def exterior_faces(conn):
    patterns = [
        (0, 1, 2, 4, 5, 6),
        (0, 3, 1, 7, 8, 4),
        (1, 3, 2, 8, 9, 5),
        (2, 3, 0, 9, 7, 6),
    ]
    found = {}
    for element, c in enumerate(conn, 1):
        for side, p in enumerate(patterns, 1):
            nodes = c[list(p)]
            key = tuple(sorted(nodes[:3]))
            if key in found:
                found[key] = None
            else:
                found[key] = (element, side, nodes)
    return [f for f in found.values() if f is not None]


def contact_deck(
    xyz,
    conn,
    scale=1,
    mu=0.3,
    penalty=100000,
    interference=0.1,
    side=1,
    mate_meshes=None,
):
    """Friction test with actual clip jaws and prescribed rigid contact coupons.

    Rigid footprints or elastic local frame slices reproduce the actual mating faces.
    This intentionally measures friction alone, not forced break-out of the catch.
    Both contact normal pressure and stick/slip traction are solved by CalculiX.
    """
    deck = header(xyz, conn, scale)
    contact_type = "MORTAR" if mate_meshes else "SURFACE TO SURFACE"
    # Minimal in-plane supports remove rigid-body motion without holding the
    # entire C spine artificially straight during jaw opening. Normal contact
    # supplies the remaining normal/tilt constraints.
    a = int(np.argmin(np.linalg.norm(xyz - (-5, 26.6, -1.1), axis=1))) + 1
    b = int(np.argmin(np.linalg.norm(xyz - (5, 26.6, -1.1), axis=1))) + 1
    assert a != b
    deck += nset("FIX", [a, b])
    node = len(xyz) + 1
    element = len(conn) + 1
    plates = {}
    surface = {}
    cells = coupon_cells(side)
    if mate_meshes:
        for name, (points, connectivity, _info) in mate_meshes.items():
            deck += (
                "*NODE\n"
                + "\n".join(
                    f"{node + i}," + ",".join(f"{v:.10g}" for v in p)
                    for i, p in enumerate(points)
                )
                + "\n"
            )
            deck += (
                f"*ELEMENT,TYPE=C3D10,ELSET={name}\n"
                + "\n".join(
                    f"{element + i}," + ",".join(map(str, c + node - 1))
                    for i, c in enumerate(connectivity)
                )
                + "\n"
            )
            z = 0.55 if name == "TOP" else -0.45
            surface[name] = [
                (element + e - 1, s)
                for e, s, nodes in exterior_faces(connectivity)
                if np.max(np.abs(points[nodes - 1, 2] - z)) < 1e-6
            ]
            plates[name] = list(
                np.flatnonzero(np.abs(points[:, 1] - points[:, 1].min()) < 1e-6) + node
            )
            node += len(points)
            element += len(connectivity)
            deck += f"*SOLID SECTION,ELSET={name},MATERIAL=PETG\n" + nset(
                name, plates[name]
            )
    else:
        for name, z0, z1, face in [("TOP", 0.05, 0.55, 2), ("BOTTOM", -0.45, 0.05, 1)]:
            plates[name] = []
            surface[name] = []
            for x0, x1, y0, y1 in cells[name]:
                points = [
                    (x0, y0, z0),
                    (x1, y0, z0),
                    (x1, y1, z0),
                    (x0, y1, z0),
                    (x0, y0, z1),
                    (x1, y0, z1),
                    (x1, y1, z1),
                    (x0, y1, z1),
                ]
                ids = list(range(node, node + 8))
                plates[name] += ids
                deck += (
                    "*NODE\n"
                    + "\n".join(
                        f"{n}," + ",".join(map(str, p)) for n, p in zip(ids, points)
                    )
                    + "\n"
                )
                deck += (
                    f"*ELEMENT,TYPE=C3D8,ELSET={name}\n{element},"
                    + ",".join(map(str, ids))
                    + "\n"
                )
                surface[name].append((element, face))
                element += 1
                node += 8
            deck += f"*SOLID SECTION,ELSET={name},MATERIAL=PETG\n"
            deck += nset(name, plates[name])
    deck += nset("LOAD", plates["TOP"] + plates["BOTTOM"])
    faces = exterior_faces(conn)
    for name, z in [("TOP", 0.55), ("BOTTOM", -0.45)]:
        selected = []
        for e, s, nodes in faces:
            pts = xyz[nodes - 1]
            if np.max(np.abs(pts[:, 2] - z)) < 1e-6 and pts[:, 1].mean() < 24.4 + 1e-6:
                selected.append((e, s))
        assert selected
        deck += (
            f"*SURFACE,NAME=CLIP_{name},TYPE=ELEMENT\n"
            + "\n".join(f"{e},S{s}" for e, s in selected)
            + "\n"
        )
        deck += (
            f"*SURFACE,NAME=PLATE_{name},TYPE=ELEMENT\n"
            + "\n".join(f"{e},S{s}" for e, s in surface[name])
            + "\n"
        )
        deck += f"*CONTACT PAIR,INTERACTION=FRIC,TYPE={contact_type}\nCLIP_{name},PLATE_{name}\n"
    deck += f"*SURFACE INTERACTION,NAME=FRIC\n*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR\n{penalty:g}\n"
    if mu > 0:
        deck += f"*FRICTION\n{mu},{penalty / 100}\n"
    deck += f"*BOUNDARY\n{a},1,2,0\n{b},2,2,0\nTOP,1,3,0\nBOTTOM,1,3,0\n"
    # Normal settlement first; outward slip then tests friction under preload.
    for slide in [None, 0.05, 0.15]:
        stepping = "0.1,1,1e-6,0.2" if mate_meshes else "0.02,1,1e-8,0.1"
        deck += f"*STEP,NLGEOM,INC=500\n*STATIC\n{stepping}\n*BOUNDARY\n"
        deck += f"TOP,3,3,{interference}\n"
        if slide is not None:
            deck += f"TOP,2,2,{-slide}\nBOTTOM,2,2,{-slide}\n"
        deck += outputs(contact=True)
        if mate_meshes:
            deck += "*CONTACT FILE\nCDIS,CSTR\n"
        for name in ("TOP", "BOTTOM"):
            deck += f"*NODE PRINT,NSET={name},TOTALS=ONLY\nRF\n"
            deck += (
                f"*CONTACT PRINT,SLAVE=CLIP_{name},MASTER=PLATE_{name}\nCF,CFN,CFS\n"
            )
        deck += "*END STEP\n"
    return deck, {
        "mu": mu,
        "penalty_n_mm3": penalty,
        "interference_mm": interference,
        "holder_side": side,
        "coupon_cells": cells,
        "fixed_nodes": 2,
        "support_node_ids": [a, b],
        "mate_fixture_nodes": sum(map(len, plates.values())),
        "elastic_mates": bool(mate_meshes),
        "contact_formulation": contact_type,
        "mate_meshes": {k: v[2] for k, v in mate_meshes.items()} if mate_meshes else {},
    }


def solve(folder, deck, executable=CCX):
    path = folder / "job.inp"
    (folder / "result.json").unlink(missing_ok=True)
    path.write_text(deck)
    env = dict(
        os.environ, OMP_NUM_THREADS="2", CCX_NPROC_RESULTS="2", CCX_NPROC_STIFFNESS="2"
    )
    with (folder / "solver.log").open("w") as log:
        proc = subprocess.run(
            [executable, "job"],
            check=False,
            cwd=folder,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=1800,
        )
    log = (folder / "solver.log").read_text()
    assert proc.returncode == 0 and "Job finished" in log and "*ERROR" not in log, log[
        -3500:
    ]
    return sha(path)


FLOAT = r"[-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?"


def read_dat(path):
    lines = Path(path).read_text().splitlines()
    results, current = [], None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("total force"):
            m = re.search(r"set\s+(\S+)\s+and time\s+(\S+)", line)
            if m:
                name, time = m[1], float(m[2])
                if current is None or current["time"] != time:
                    current = {"time": time}
                    results.append(current)
                i += 1
                while not lines[i].strip():
                    i += 1
                current[name.lower() + "_force"] = list(map(float, lines[i].split()))
        if line.startswith(
            (
                "stresses (",
                "strains (",
                "contact stress (",
                "relative contact displacement (",
            )
        ):
            kind = next(
                value
                for prefix, value in [
                    ("stresses", "stress"),
                    ("strains", "strain"),
                    ("contact stress", "contact_stress"),
                    ("relative contact", "contact_displacement"),
                ]
                if line.startswith(prefix)
            )
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            rows = []
            while i < len(lines) and lines[i].strip():
                rows.append(list(map(float, lines[i].split())))
                i += 1
            if rows and current is not None:
                a = np.array(rows)
                current[kind] = a[:, 2:8]
                if kind == "stress":
                    current["integration_elements"] = a[:, 0].astype(int)
        i += 1
    return results


def frd_fields(path):
    """Read nodal fields only; mesh and node IDs come from our hashed input."""
    result = []
    current = None
    name = None
    values = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith("  100C"):
            if current is not None:
                result.append(current)
            current = {"record": line.strip()}
        elif line.startswith(" -4"):
            name = line.split()[1]
            values = {}
        elif name and line.startswith(" -1"):
            node = int(line[3:13])
            values[node] = [
                float(s.replace("D", "E")) for s in re.findall(FLOAT, line[13:])
            ]
        elif name and line.startswith(" -3"):
            current[name] = values
            name = None
    if current is not None:
        result.append(current)
    return result


def stress_metrics(stress):
    xx, yy, zz, xy, xz, yz = stress.T
    vm = np.sqrt(
        0.5 * ((xx - yy) ** 2 + (yy - zz) ** 2 + (zz - xx) ** 2)
        + 3 * (xy**2 + xz**2 + yz**2)
    )
    # Axial layer-normal stress is retained separately; Mises is not a printed
    # polymer failure criterion. UTS comparisons are flags, not a yield model.
    return {
        "vm_max_mpa": float(vm.max()),
        "vm_p95_mpa": float(np.quantile(vm, 0.95)),
        "z_tension_max_mpa": float(max(0, zz.max())),
        "xy_tension_max_mpa": float(max(0, xx.max(), yy.max())),
    }
