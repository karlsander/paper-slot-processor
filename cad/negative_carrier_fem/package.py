"""Bundle only accepted, hashed results; never glob failed development runs."""

import json
import zipfile

from .solver import sha
from .study import ROOT


def main():
    output = ROOT / "build/negative-carrier-fem"
    summary = json.loads((output / "summary.json").read_text())
    native = json.loads((output / "freecad-results.json").read_text())
    native_ids = {case["id"]: case for case in native["cases"]}
    files = [
        (output / "summary.json", "summary.json"),
        (output / "freecad-results.json", "freecad-results.json"),
    ]
    for case in summary["studies"]:
        folder = output / case["id"]
        for file, key in [
            ("job.inp", "input_sha256"),
            ("job.frd", "frd_sha256"),
            ("job.dat", "dat_sha256"),
            ("solver.log", "log_sha256"),
        ]:
            assert sha(folder / file) == case[key]
        for file in [
            "part.step",
            "mesh.npz",
            "job.inp",
            "job.frd",
            "job.dat",
            "job.sta",
            "solver.log",
            "result.json",
        ]:
            files.append((folder / file, f"cases/{case['id']}/{file}"))
        if case["boundary"].get("elastic_mates"):
            for mate in ["top", "bottom"]:
                for file in ["part.step", "mesh.npz"]:
                    files.append(
                        (folder / mate / file, f"cases/{case['id']}/{mate}/{file}")
                    )
        if case["id"] in native_ids:
            file = folder / "solved.FCStd"
            assert sha(file) == native_ids[case["id"]]["file_sha256"]
            files.append((file, f"FreeCAD/{case['id']}.FCStd"))
    for path in (ROOT / "docs/negative-carrier-b/forces").iterdir():
        if path.is_file():
            files.append((path, f"report/{path.name}"))
    archive = output / "B1-PETG-force-study.zip"
    manifest = []
    with zipfile.ZipFile(
        archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as bundle:
        for path, name in files:
            bundle.write(path, name)
            manifest.append(
                {"file": name, "bytes": path.stat().st_size, "sha256": sha(path)}
            )
        bundle.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len(bundle.namelist()) == len(files) + 1
    print(
        json.dumps(
            {
                "archive": str(archive),
                "files": len(files) + 1,
                "bytes": archive.stat().st_size,
                "sha256": sha(archive),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
