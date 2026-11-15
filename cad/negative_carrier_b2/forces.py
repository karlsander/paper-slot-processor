"""Actual B2 solid contact models, solved by CalculiX, not animation forces.

Reuses the independently benchmarked quadratic mesh/material/result helpers.
Material is elastic orthotropic PETG; 35 C and creep remain uncalibrated.
"""

import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

import build123d as bd
import numpy as np

from cad.negative_carrier_fem.solver import (
    cached_mesh,
    exterior_faces,
    frd_fields,
    material,
    nset,
    read_dat,
    sha,
    solve,
    stress_metrics,
)

from .model import (
    Config,
    bearing_head,
    box,
    closure_wedge,
    dock_wedge,
    edge_offset,
    holder,
    receiver,
    screw,
    shoe,
    sleeve,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/negative-carrier-b2/forces"


def canonical_deck(text):
    """Compare numeric fields exactly despite decimal/scientific formatting."""

    def field(s):
        s = s.strip()
        try:
            return Decimal(s)
        except InvalidOperation:
            return s

    return tuple(tuple(field(s) for s in line.split(",")) for line in text.splitlines())


def geometry(case):
    p = Config("110" if case == "wedge-110" else "135", frame_count=3)
    h = holder(p)
    if case == "index":
        return {
            "RAIL": h["base"] & box(0, 53.5, -2, 24, 21, 12),
            "SHOE": shoe(),
            "CAP": bearing_head(),
        }
    if case in ("wedge", "wedge-110"):
        y0 = p.fmt.film_width / 2 - 0.5
        y1 = 27.3 + edge_offset(p)
        cut = box(0, (y0 + y1) / 2, -2, 24, y1 - y0, 4)
        return {
            "BASE": h["base"] & cut,
            "LID": h["lid"] & cut,
            "WEDGE": bd.Pos(0, edge_offset(p), 0) * closure_wedge(),
        }
    if case == "thread":
        return {"NUT": sleeve(p) & box(0, 57, 17, 30, 14, 12), "SCREW": screw()}
    if case == "screw-load":
        return {"SCREW": screw()}
    if case == "nut-load":
        return {"NUT": sleeve(p) & box(0, 57, 17, 30, 14, 12)}
    if case in ("dock", "dock-stop"):
        return {
            "BASE": receiver() & box(0, 74, -7, 26, 6, 5),
            "LID": sleeve(p) & box(0, 72, -2.4, 26, 6, 7),
            "WEDGE": dock_wedge(),
        }
    raise ValueError(case)


class Deck:
    def __init__(self, meshes, scale, mu, penalty):
        self.meshes, self.offsets, self.faces = meshes, {}, {}
        self.lines = [
            "*HEADING",
            "B2 actual PETG contact; mm N MPa",
            material(scale),
            "*ORIENTATION,NAME=LAYER_Y\n1,0,0,0,0,-1",
            "*ORIENTATION,NAME=LAYER_X\n0,1,0,0,0,1",
        ]
        no, eo = 0, 0
        self.xyz, self.conn = [], []
        for name, (xyz, conn, _info) in meshes.items():
            self.offsets[name] = (no, eo)
            self.xyz.extend(xyz)
            self.conn.extend(conn + no)
            self.lines += [
                "*NODE",
                *[
                    f"{i + no}," + ",".join(f"{v:.10g}" for v in p)
                    for i, p in enumerate(xyz, 1)
                ],
                f"*ELEMENT,TYPE=C3D10,ELSET={name}",
                *[
                    f"{i + eo}," + ",".join(map(str, c + no))
                    for i, c in enumerate(conn, 1)
                ],
                f"*SOLID SECTION,ELSET={name},MATERIAL=PETG"
                + (
                    ",ORIENTATION=LAYER_Y"
                    if name == "WEDGE"
                    else ",ORIENTATION=LAYER_X"
                    if name == "NUT"
                    else ""
                ),
            ]
            self.faces[name] = exterior_faces(conn)
            no += len(xyz)
            eo += len(conn)
        self.lines += [
            f"*ELSET,ELSET=BODY,GENERATE\n1,{eo},1",
            f"*NSET,NSET=ALL,GENERATE\n1,{no},1",
        ]
        self.xyz, self.conn = np.array(self.xyz), np.array(self.conn)
        self.fixed = set()
        self.bc = []
        self.loads = {}
        self.lines += [
            "*SURFACE INTERACTION,NAME=CONTACT",
            "*SURFACE BEHAVIOR,PRESSURE-OVERCLOSURE=LINEAR",
            str(penalty),
        ]
        if mu:
            self.lines += ["*FRICTION", f"{mu},{penalty / 100}"]

    def nodes(self, body, predicate):
        pts = self.meshes[body][0]
        ids = np.flatnonzero(predicate(*pts.T)) + self.offsets[body][0] + 1
        assert len(ids), (body, predicate)
        return ids

    def support(self, body, predicate, axes):
        ids = self.nodes(body, predicate)
        self.fixed.update(ids)
        for axis in axes:
            self.bc.extend(f"{n},{axis},{axis},0" for n in ids)

    def surface(self, body, label, predicate):
        pts = self.meshes[body][0]
        selected = [
            (e, s, nodes)
            for e, s, nodes in self.faces[body]
            if predicate(pts[nodes - 1])
        ]
        assert selected, (body, label)
        self.lines += [
            f"*SURFACE,NAME={label},TYPE=ELEMENT",
            *[f"{e + self.offsets[body][1]},S{s}" for e, s, _ in selected],
        ]
        return selected

    def pair(self, a, b):
        self.lines += ["*CONTACT PAIR,INTERACTION=CONTACT,TYPE=MORTAR", f"{a},{b}"]

    def force(self, body, predicate, axis, total):
        # Equal nodal weighting on the stated loading patch, total exactly N.
        ids = self.nodes(body, predicate)
        return {(int(n), axis): total / len(ids) for n in ids}

    def finish(self, steps, force_reference=0.00001):
        self.lines += [nset("FIX", sorted(self.fixed)), "*BOUNDARY", *self.bc]
        for forces, displacements in steps:
            self.lines += ["*STEP,NLGEOM,INC=500", "*STATIC", "0.25,1,1e-7,1"]
            # Fixed 0.00001 N reference avoids a vanishing force criterion in
            # almost-unloaded seating steps: 5e-8 N residual per nodal DOF.
            # Independent resultant equilibrium below remains mandatory.
            self.lines += [
                "*CONTROLS,PARAMETERS=FIELD",
                f"0.005,0.01,{force_reference:g},{force_reference:g}",
            ]
            self.lines += [
                "*CLOAD,OP=NEW",
                *[f"{n},{a},{v:.12g}" for (n, a), v in forces.items()],
            ]
            if displacements:
                self.lines += [
                    "*BOUNDARY",
                    *[f"{n},{a},{a},{v:.12g}" for (n, a), v in displacements.items()],
                ]
            self.lines += [
                "*NODE PRINT,NSET=FIX,TOTALS=ONLY",
                "RF",
                "*EL PRINT,ELSET=BODY",
                "S,E",
                "*NODE FILE,FREQUENCY=999999",
                "U,RF",
                "*EL FILE",
                "S,E",
                "*CONTACT FILE",
                "CDIS,CSTR",
                "*END STEP",
            ]
        return "\n".join(self.lines) + "\n"


def make_deck(case, meshes, scale=1, mu=0.3, penalty=100000):
    d = Deck(meshes, scale, mu, penalty)
    steps, labels = [], []
    if case == "index":
        d.support("RAIL", lambda x, y, z: abs(y - 43) < 1e-6, [2, 3])
        d.support("CAP", lambda x, y, z: abs(z - 13.2) < 1e-6, [1, 2])
        # The screw's remote cut remains normal to its guided axis while it
        # translates axially. Leaving independent Z DOFs here admits a rigid
        # tilt of the whole shortened head, absent from this local fixture.
        top = d.nodes("CAP", lambda x, y, z: abs(z - 13.2) < 1e-6)
        for node in top[1:]:
            d.lines += ["*EQUATION", "2", f"{node},3,1,{top[0]},3,-1"]
        for label, test in [
            ("RIGHT", lambda p: np.max(abs(p[:, 0] + p[:, 2] - 3)) < 1e-6),
            ("LEFT", lambda p: np.max(abs(p[:, 0] - p[:, 2] + 3)) < 1e-6),
            ("REAR", lambda p: np.max(abs(p[:, 1] + p[:, 2] - 59)) < 1e-6),
        ]:
            for body in ("RAIL", "SHOE"):
                d.surface(body, body + label, test)
            d.pair("SHOE" + label, "RAIL" + label)
        for body in ("CAP", "SHOE"):
            d.surface(
                body,
                body + "CONE",
                lambda p: (
                    p[:, 2].min() > 8.99999
                    and p[:, 2].max() < 10.30001
                    and np.max(
                        abs(np.linalg.norm(p[:, :2] - [0, 57], axis=1) - p[:, 2] + 7.3)
                    )
                    < 1e-6
                ),
            )
        d.pair("SHOECONE", "CAPCONE")
        for f, bump in ((2, 0), (5, 0), (5, 2), (5, -2), (5, 0), (10, 0)):
            loads = d.force(
                "CAP",
                lambda x, y, z: abs(z - 13.2) < 1e-6,
                3,
                -f,
            )
            if bump:
                loads.update(
                    d.force(
                        "RAIL",
                        lambda x, y, z: (abs(y - 43) < 1e-6) & (z > 6),
                        1,
                        bump,
                    )
                )
            steps.append((loads, {}))
            labels.append(f"{f} N seating; {bump:+g} N X disturbance")
        notes = "Actual 24 mm rail section with Y/Z held at its Y=43 cut; X remains free. The actual screw bearing head has an X/Y-guided, axially translating flat remote cut at Z=13.2, and receives 2/5/10 N axial force. The shoe is completely free, located by the tapered bearing and three notch faces. +/-2 N X disturbance is applied to the rail's front cut above Z=6. This tests local contact load transfer and centering; sleeve, threads, full frame and enlarger compliance remain outside this fixture."
    elif case in ("wedge", "wedge-110"):
        config = Config("110" if case == "wedge-110" else "135")
        y0 = config.fmt.film_width / 2 - 0.5
        delta = edge_offset(config)
        for body in ("BASE", "LID"):
            d.support(body, lambda x, y, z: abs(y - y0) < 1e-6, [1, 2, 3])
        d.support("WEDGE", lambda x, y, z: y >= 26.6 + delta, [1])
        load_ids = d.nodes("WEDGE", lambda x, y, z: y >= 26.6 + delta)
        d.fixed.update(load_ids)
        d.surface(
            "WEDGE",
            "WTOP",
            lambda p: np.max(abs(p[:, 2] - 1.75 + 0.05 * (p[:, 1] - delta))) < 1e-6,
        )
        d.surface(
            "LID",
            "LTOP",
            lambda p: np.max(abs(p[:, 2] - 1.75 + 0.05 * (p[:, 1] - delta))) < 1e-6,
        )
        d.surface("WEDGE", "WBOT", lambda p: np.max(abs(p[:, 2] + 0.45)) < 1e-6)
        d.surface("BASE", "BBOT", lambda p: np.max(abs(p[:, 2] + 0.45)) < 1e-6)
        d.pair("WTOP", "LTOP")
        d.pair("WBOT", "BBOT")
        if case != "wedge-110":
            d.surface("LID", "LBASE", lambda p: np.max(abs(p[:, 2] - 0.2)) < 1e-6)
            d.surface("BASE", "BTOP", lambda p: np.max(abs(p[:, 2])) < 1e-6)
            d.pair("LBASE", "BTOP")
        for travel in (0.25, 0.5, 1, 0.5, 0):
            steps.append(({}, {(int(n), 2): -travel for n in load_ids}))
            labels.append(f"{travel:g} mm wedge travel")
        notes = f"Actual 24 mm frame/key slice with film-side cut at Y={y0:g} clamped. Broad wedge advances on 1:20 edge ramp; both jaws and base/lid contact solved simultaneously. Remote cut represents rest of frame; film itself and whole-holder pressure distribution are not calibrated."
        if case == "wedge-110":
            notes = notes.replace(
                "both jaws and base/lid contact solved simultaneously",
                "both jaw contacts solved; the separated base/lid faces are omitted and their remaining gap is checked after deformation",
            )
    elif case in ("dock", "dock-stop"):
        d.support("BASE", lambda x, y, z: abs(abs(x) - 13) < 1e-6, [1, 2, 3])
        d.support("LID", lambda x, y, z: abs(y - 69) < 1e-6, [1, 2, 3])
        d.support("WEDGE", lambda x, y, z: y >= 84, [2])
        load_ids = d.nodes("WEDGE", lambda x, y, z: y >= 84)
        d.fixed.update(load_ids)
        d.surface(
            "WEDGE",
            "WTOP",
            lambda p: np.max(abs(p[:, 2] - 1.2 - 0.05 * p[:, 0])) < 1e-6,
        )
        d.surface(
            "LID", "LTOP", lambda p: np.max(abs(p[:, 2] - 1.2 - 0.05 * p[:, 0])) < 1e-6
        )
        d.surface("WEDGE", "WBOT", lambda p: np.max(abs(p[:, 2] + 6.4)) < 1e-6)
        d.surface("BASE", "BBOT", lambda p: np.max(abs(p[:, 2] + 6.4)) < 1e-6)
        d.pair("WTOP", "LTOP")
        d.pair("WBOT", "BBOT")
        d.surface("LID", "FLANGE_BOTTOM", lambda p: np.max(abs(p[:, 2] + 2.4)) < 1e-6)
        d.surface("BASE", "RECEIVER_TOP", lambda p: np.max(abs(p[:, 2] + 2.4)) < 1e-6)
        d.pair("FLANGE_BOTTOM", "RECEIVER_TOP")
        for travel in (2,) if case == "dock-stop" else (0.25, 0.5, 1, 0.5, 0):
            steps.append(({}, {(int(n), 1): travel for n in load_ids}))
            labels.append(f"{travel:g} mm docking wedge travel")
        notes = "Actual local dock flange, receiver crossbar and broad C wedge. Remote flange Y=69 and crossbar X=+/-13 cuts held. Both jaw contacts deform with friction; imposed X seating/release. Full receiver arms and enlarger support stiffness are outside this local model."
    elif case in ("screw-load", "nut-load"):
        body = "SCREW" if case == "screw-load" else "NUT"
        xyz = meshes[body][0]

        def bearing(p):
            normal = -np.cross(p[1] - p[0], p[2] - p[0])
            normal /= np.linalg.norm(normal)
            return normal

        selected = [
            (e, s, n)
            for e, s, n in d.faces[body]
            if (17.05 < xyz[n - 1, 2].mean() < 20.05)
            and (np.linalg.norm(xyz[n - 1, :2] - [0, 57], axis=1).max() < 6.6)
            and (bearing(xyz[n - 1])[2] * (1 if body == "SCREW" else -1) > 0.2)
        ]
        assert selected
        if body == "SCREW":
            ids = {int(i) for _, _, ns in selected for i in ns}
            d.fixed.update(ids)
            d.bc.extend(f"{n},{a},{a},0" for n in ids for a in (1, 2, 3))
        else:
            d.support(body, lambda x, y, z: abs(y - 64) < 1e-6, [1, 2, 3])
        for force in (5, 15, 30):
            if body == "SCREW":
                loads = d.force(body, lambda x, y, z: abs(z - 9) < 1e-6, 3, force)
            else:
                loads = {}
                for _, _, ns in selected:
                    pts = xyz[ns - 1]
                    area = (
                        np.linalg.norm(np.cross(pts[1] - pts[0], pts[2] - pts[0])) / 2
                    )
                    # Normal bearing traction, first engaged turn carries all load.
                    normal = -bearing(pts)
                    for n in ns[3:]:
                        for a in (1, 2, 3):
                            loads[int(n), a] = (
                                loads.get((int(n), a), 0) + normal[a - 1] * area / 3
                            )
                axial = sum(v for (_, a), v in loads.items() if a == 3)
                loads = {key: value * (-force / axial) for key, value in loads.items()}
            steps.append((loads, {}))
            labels.append(f"{force} N on first engaged thread")
        notes = "Actual helical solid; conservative prescribed-bearing-load structural screen. One engaged turn takes all axial load. Screw flank nodes fixed with flange loaded; nut receives normal tractions on its first load-bearing flank and is held at remote Y=64. This is NOT a solved screw/nut contact distribution, torque, backdrive, stripping or fatigue prediction."
    else:
        d.support("NUT", lambda x, y, z: abs(y - 64) < 1e-6, [1, 2, 3])
        d.support("SCREW", lambda x, y, z: z > 29, [1, 2])

        def nz(p):
            normal = -np.cross(p[1] - p[0], p[2] - p[0])
            return normal[2] / np.linalg.norm(normal)

        # Only the opposing load-bearing helical flanks. Selecting both sides
        # of every thread produces ambiguous mortar projections across crests.
        d.surface(
            "NUT",
            "NTHREAD",
            lambda p: (
                nz(p) < -0.2
                and p[:, 2].min() > 17.001
                and p[:, 2].max() < 29.01
                and np.max(np.sqrt(p[:, 0] ** 2 + (p[:, 1] - 57) ** 2)) < 6.6
            ),
        )
        d.surface(
            "SCREW",
            "STHREAD",
            lambda p: (
                nz(p) > 0.2
                and p[:, 2].min() > 16.5
                and p[:, 2].max() < 29.01
                and np.min(np.sqrt(p[:, 0] ** 2 + (p[:, 1] - 57) ** 2)) > 4.4
            ),
        )
        d.pair("STHREAD", "NTHREAD")
        load_ids = d.nodes("SCREW", lambda x, y, z: z > 29.2)
        d.fixed.update(load_ids)
        for travel in (0.12, 0.15, 0.17, 0.18):
            steps.append(({}, {(int(n), 3): travel for n in load_ids}))
            labels.append(f"{travel:g} mm axial travel including flank clearance")
        notes = "Actual helical D12x3 screw and cropped nut boss, with printed clearances. Nut remote Y=64 face held; knob guided without rotation and displaced axially upward to close flank clearance and load the threads. Static axial stiffness/contact; tightening torque, stripping, wear and creep are not predicted."
    return (
        d,
        d.finish(steps, 0.01 if case == "index" else 0.00001),
        steps,
        labels,
        notes,
    )


def run(case, size=1, scale=1, mu=0.3, penalty=100000):
    source_sha = sha(Path(__file__).with_name("model.py"))
    tag = f"{case}-h{size:g}-E{scale:g}-mu{mu:g}-K{penalty:g}"
    folder = OUT / tag
    meshes = {
        n: cached_mesh(s, folder / n.lower(), size) for n, s in geometry(case).items()
    }
    d, deck, steps, labels, notes = make_deck(case, meshes, scale, mu, penalty)
    # A combined native reference and hashed mesh accompany the exact input deck.
    bd.export_step(
        bd.Compound(children=list(geometry(case).values())), folder / "part.step"
    )
    np.savez_compressed(folder / "mesh.npz", xyz=d.xyz, conn=d.conn)
    old = folder / "job.inp"
    cached = (
        old.exists()
        and canonical_deck(old.read_text()) == canonical_deck(deck)
        and (folder / "solver.log").exists()
    )
    cached = (
        cached
        and "Job finished" in (folder / "solver.log").read_text()
        and "*ERROR" not in (folder / "solver.log").read_text()
    )
    print(f"{'Reuse' if cached else 'Solve'} {tag}: {len(d.xyz)} nodes", flush=True)
    if not cached:
        solve(folder, deck, timeout=7200)
    data = read_dat(
        folder / "job.dat",
        orientations={
            "LAYER_X": [[0, 0, 1], [1, 0, 0], [0, 1, 0]],
            "LAYER_Y": [[1, 0, 0], [0, 0, 1], [0, -1, 0]],
        },
    )
    all_fields = frd_fields(folder / "job.frd")
    fields = [r["DISP"] for r in all_fields if "DISP" in r]
    force_fields = [r["FORC"] for r in all_fields if "FORC" in r]
    assert len(data) == len(steps) == len(fields) == len(force_fields)
    history = []
    for i, r in enumerate(data):
        forces, _disp = steps[i]
        external = np.zeros(3)
        for (_, a), f in forces.items():
            external[a - 1] += f
        # CalculiX mortar_prefrd adds contact forces before writing FRD and
        # mortar_postfrd removes them again. DAT RF can therefore omit contact
        # contributions at a supported contact node. Use final FRD FORC at
        # actual constrained DOFs, not the uncorrected DAT node-set total.
        constrained = set()
        for line in d.bc:
            n, low, high, _ = line.split(",")
            constrained.update((int(n), a) for a in range(int(low), int(high) + 1))
        constrained.update(_disp)
        reaction = np.zeros(3)
        for n, a in constrained:
            reaction[a - 1] += force_fields[i][n][a - 1] - forces.get((n, a), 0)
        # For imposed travel this includes the drive reactions as well.
        error = float(np.linalg.norm(external + reaction))
        assert error < max(1e-4, float(np.linalg.norm(external)) * 0.005), (
            tag,
            error,
            reaction,
            external,
        )
        u = np.array([fields[i][j] for j in range(1, len(d.xyz) + 1)])
        row = {
            "step": i + 1,
            "label": labels[i],
            "support_force_n": reaction.tolist(),
            "dat_uncorrected_node_set_force_n": r["fix_force"],
            "applied_force_n": external.tolist(),
            "equilibrium_error_n": error,
            "max_displacement_mm": float(np.linalg.norm(u, axis=1).max()),
            **stress_metrics(r["stress"]),
        }
        per = {}
        for n, (xyz, conn, _) in meshes.items():
            no, eo = d.offsets[n]
            select = (r["integration_elements"] > eo) & (
                r["integration_elements"] <= eo + len(conn)
            )
            per[n] = stress_metrics(r["stress"][select])
            layer_axis = 0 if n == "NUT" else 1 if n == "WEDGE" else 2
            per[n]["layer_normal_tension_max_mpa"] = float(
                np.maximum(r["stress"][select, layer_axis], 0).max()
            )
            per[n]["mean_displacement_mm"] = u[no : no + len(xyz)].mean(axis=0).tolist()
            # Compare displacement at the actual loading patch, rather than
            # averaging all nodes (whose spatial density changes with mesh size).
            load_patch = []
            for axis in (1, 2, 3):
                loaded = [
                    (j, abs(f))
                    for (j, a), f in forces.items()
                    if a == axis and no < j <= no + len(xyz) and f
                ]
                load_patch.append(
                    float(
                        sum(weight * u[j - 1, axis - 1] for j, weight in loaded)
                        / sum(weight for _, weight in loaded)
                    )
                    if loaded
                    else None
                )
            per[n]["load_patch_displacement_mm"] = load_patch
            part_reaction = np.zeros(3)
            for j, a in constrained:
                if no < j <= no + len(xyz):
                    part_reaction[a - 1] += force_fields[i][j][a - 1] - forces.get(
                        (j, a), 0
                    )
            per[n]["fixture_reaction_n"] = part_reaction.tolist()
        row["parts"] = per
        if case == "wedge-110":
            no, _ = d.offsets["BASE"]
            xyz = meshes["BASE"][0]
            base_top = np.max(xyz[:, 2] + u[no : no + len(xyz), 2])
            no, _ = d.offsets["LID"]
            xyz = meshes["LID"][0]
            lid_bottom = np.min(xyz[:, 2] + u[no : no + len(xyz), 2])
            row["omitted_base_lid_gap_lower_bound_mm"] = float(lid_bottom - base_top)
            assert lid_bottom - base_top > 0.05
        history.append(row)
    result = {
        "id": tag,
        "notes": notes,
        "case": case,
        "mesh": {k: v[2] for k, v in meshes.items()},
        "boundary": {
            "modeled_bodies": "elastic solids",
            "remote_supports": "prescribed constraints described in notes",
            "whole_assembly_compliance": False,
        },
        "history": history,
        "mu": mu,
        "material_scale": scale,
        "requested_temperature_c": 35,
        "temperature_calibrated": False,
        "creep_calibrated": False,
        "input_sha256": sha(old),
        "frd_sha256": sha(folder / "job.frd"),
        "cad_source_sha256": source_sha,
        "print_layer_normals": {
            "WEDGE": "global Y",
            "NUT": "global X",
            "others": "global Z",
        },
    }
    assert sha(Path(__file__).with_name("model.py")) == source_sha, (
        "CAD changed during solve; rerun"
    )
    (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"id": tag, "history": history}), flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "case",
        choices=[
            "index",
            "wedge",
            "wedge-110",
            "thread",
            "dock",
            "dock-stop",
            "screw-load",
            "nut-load",
        ],
    )
    p.add_argument("--size", type=float, default=1)
    p.add_argument("--scale", type=float, default=1)
    p.add_argument("--mu", type=float, default=0.3)
    p.add_argument("--penalty", type=float, default=100000)
    a = p.parse_args()
    run(a.case, a.size, a.scale, a.mu, a.penalty)
